"""Mood propagation — social graph + direct-event paths.

Two entry points:

    apply_event(db, profile, event_kind, payload)
        Synchronous. Resolve the event_kind+role to a mood delta, clamp
        and persist immediately. No LLM.

    propagate_once(db, profiles)
        Walk the relationship graph one step. For each agent, sum the
        weighted mood pulls from their relationships, snap to nearest
        declared mood. Run periodically (every few minutes).

This module does NOT call the LLM. It works on the cheap, fast path —
the LLM-driven reflections are separate and run in their own cycle.
The two paths compose naturally: a strong direct event puts Zaldon
into `gruff`, the next reflection cycle reads memory + recent events
and writes a journal entry consistent with that mood.
"""
from __future__ import annotations

import logging
import re
import typing as t

from .db import AgentDB
from .event_deltas import lookup_delta, nearest_in_axes
from .loader import AgentProfile


log = logging.getLogger("demoncore.mood")


# Relationship kind weights. Authors mark relationships with `kind: ...`;
# unmarked relationships default to "acquaintance".
RELATIONSHIP_WEIGHT: dict[str, float] = {
    "family":       1.0,
    "best_friend":  0.9,
    "friend":       0.6,
    "professional": 0.5,
    "mentor":       0.5,
    "rival":        0.3,
    "acquaintance": 0.2,
    "adversary":   -0.3,   # their good mood pushes you toward bad mood
}


# Negative / positive mood classifications for the propagation pull
NEGATIVE_MOODS = {
    "furious", "gruff", "alarm", "fearful", "alert",
    "weary", "melancholy", "contemplative",
}
POSITIVE_MOODS = {"content", "mischievous", "drunk"}


def _classify(mood: str) -> str:
    if mood in NEGATIVE_MOODS:
        return "negative"
    if mood in POSITIVE_MOODS:
        return "positive"
    return "neutral"


def _infer_relationship_kind(descr: str) -> str:
    """Use the prose to guess the relationship kind if not explicitly tagged.

    Uses word-boundary regex matching so substrings inside other words
    don't trigger ('person' contains 'son' — we don't want that to match
    'family').
    """
    s = descr.lower()

    def has(*words: str) -> bool:
        return any(re.search(rf"\b{re.escape(w)}\b", s) for w in words)

    # Check most specific kinds first — adversary / hate / enemy before
    # family, because "I hate my father" should classify as adversary, not
    # family.
    if has("enemy", "enemies", "hate", "hates", "hated", "adversary",
           "adversaries", "loathe", "despise"):
        return "adversary"
    if has("father", "daughter", "son", "mother", "brother", "sister",
           "family", "parent", "child", "wife", "husband", "spouse",
           "estranged"):
        return "family"
    if has("best") or "boyhood" in s or "lifelong" in s:
        return "best_friend"
    if has("respect", "professional") or "collaborat" in s:
        return "professional"
    if has("mentor", "apprentice", "teacher", "student"):
        return "mentor"
    if has("rival") or "compet" in s:
        return "rival"
    if has("friend"):
        return "friend"
    return "acquaintance"


def _get_relationship_kind(edge_descr) -> str:
    """Edge entry can be a string (legacy) or dict {kind, descr}."""
    if isinstance(edge_descr, dict):
        return edge_descr.get("kind", "acquaintance")
    if isinstance(edge_descr, str):
        return _infer_relationship_kind(edge_descr)
    return "acquaintance"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_event(db: AgentDB, profile: AgentProfile,
                event_kind: str, payload: t.Optional[dict] = None) -> bool:
    """Apply a single event's mood delta to the agent immediately.

    Returns True if the agent's mood changed, False otherwise.
    Does nothing if the agent is Tier 0/1/4 (mood-less).
    """
    if profile.tier not in ("2_reflection", "3_hero"):
        return False

    delta = lookup_delta(event_kind, profile.role)
    if delta is None:
        return False  # no delta defined for this event/role combo

    target_mood, intensity_delta = delta
    mood_axes = profile.raw.get("mood_axes")
    if not mood_axes and profile.tier == "3_hero":
        # Tier 3 heroes don't have to declare mood_axes — accept any mood
        applied_mood = target_mood
    else:
        applied_mood = nearest_in_axes(target_mood, list(mood_axes or []))
        if applied_mood is None:
            log.debug("no mood_axes match for %s on event %s (target=%s, axes=%r)",
                      profile.id, event_kind, target_mood, mood_axes)
            return False

    if profile.tier == "2_reflection":
        st = db.get_tier2_state(profile.id)
        if st is None:
            return False
        if st.mood == applied_mood:
            return False
        # Memory gets a short note appended — orchestrator's reflection
        # cycle will fold this into a coherent first-person summary later.
        new_memory = (st.memory_summary
                      + f" [event: {event_kind} -> {applied_mood}]")[:1000]
        db.update_tier2(profile.id, applied_mood, new_memory)
        log.info("event %s flipped %s mood: %s -> %s",
                 event_kind, profile.id, st.mood, applied_mood)
        return True
    else:  # tier 3_hero
        # For tier 3 we don't store a mood column in tier3 state today.
        # We append a small journal note instead so the next reflection
        # picks it up. Future revision: add a separate hero_mood column.
        import time
        db.update_tier3(profile.id, append_journal={
            "ts": int(time.time()),
            "entry": f"[event: {event_kind} -> mood lean: {applied_mood}]",
        })
        return True


def propagate_once(db: AgentDB,
                   profiles: dict[str, AgentProfile]) -> dict[str, str]:
    """One pass of mood propagation across the relationship graph.

    Returns a {agent_id: new_mood} mapping for the agents whose mood
    actually changed. Reads-then-writes: snapshots all state first, so
    propagation is symmetric (if A pulls B and B pulls A, both see the
    same starting state).
    """
    snapshot: dict[str, str] = {}
    for aid, prof in profiles.items():
        if prof.tier == "2_reflection":
            st = db.get_tier2_state(aid)
            if st:
                snapshot[aid] = st.mood

    changes: dict[str, str] = {}
    for aid, prof in profiles.items():
        my_mood = snapshot.get(aid)
        if my_mood is None:
            continue

        # Aggregate pull from each relationship
        pulls: dict[str, float] = {}  # candidate_mood -> total weight
        relationships = prof.raw.get("relationships") or {}
        for target_id, edge in relationships.items():
            target_mood = snapshot.get(target_id)
            if target_mood is None:
                continue
            kind = _get_relationship_kind(edge)
            weight = RELATIONSHIP_WEIGHT.get(kind, 0.2)
            if abs(weight) < 0.01:
                continue
            tier_of_target = _classify(target_mood)
            tier_of_me = _classify(my_mood)
            if tier_of_target == tier_of_me:
                continue  # already in alignment, no pull
            # The pull's strength = weight, sign = direction
            pulls[target_mood] = pulls.get(target_mood, 0.0) + weight

        if not pulls:
            continue

        # Pick the strongest pull
        best_mood, best_weight = max(pulls.items(), key=lambda kv: kv[1])
        if best_weight < 0.3:
            continue  # ignore tiny pulls

        # Snap to nearest declared mood
        mood_axes = list(prof.raw.get("mood_axes") or [])
        snapped = nearest_in_axes(best_mood, mood_axes)
        if snapped is None or snapped == my_mood:
            continue

        # Persist
        st = db.get_tier2_state(aid)
        if st is None:
            continue
        new_memory = (st.memory_summary
                      + f" [propagation pull from {best_mood} -> {snapped}]")[:1000]
        db.update_tier2(aid, snapped, new_memory)
        changes[aid] = snapped
        log.info("propagation: %s mood %s -> %s (pull from %s, weight=%.2f)",
                 aid, my_mood, snapped, best_mood, best_weight)

    return changes
