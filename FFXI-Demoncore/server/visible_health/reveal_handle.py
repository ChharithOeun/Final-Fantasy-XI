"""RevealHandle + RevealManager — server-authoritative reveal lifecycle.

Per VISUAL_HEALTH_SYSTEM.md the LSB endpoint contract is:
    `lsb_admin_api/reveal/{caster_id}/{target_id}` returns
    {hp, mp, max_hp, max_mp, expires_at} if the caster has an
    active reveal handle on the target. Otherwise 403.

Multiple reveals can be active simultaneously per (caster,target)
pair — the manager merges so the endpoint returns the broadest
available info: a Drain plus a Scan grants the caster both HP and
MP intel even though Drain alone only gives HP.

Reveals can be granted at the party scope too (Glee Tango, MB
post-burst). The widget on the client side reads the merged result.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .reveal_skills import REVEAL_SKILLS, RevealKind, RevealScope


@dataclasses.dataclass
class RevealHandle:
    """One active reveal grant."""
    caster_id: str
    target_id: str
    source_skill: str
    expires_at: float
    kind: RevealKind
    scope: RevealScope


@dataclasses.dataclass(frozen=True)
class RevealReadout:
    """What an observer sees when querying a target's reveal state."""
    target_id: str
    hp_visible: bool
    mp_visible: bool
    expires_at: float = 0.0          # latest active expiry
    sources: tuple[str, ...] = ()    # skill_ids contributing


class RevealManager:
    """Per-server registry of active RevealHandle entries.

    A reveal is keyed by (caster_id, target_id, source_skill) so the
    same caster firing the same skill twice refreshes rather than
    stacks (matches the doc's 'multiple reveals can be active
    simultaneously per player' meaning multiple SOURCES, not multiple
    duplicates).

    Party-scope reveals (Glee Tango, MB) get registered with
    party_id as the caster_id so the readout sees them for any
    party member querying.
    """

    def __init__(self) -> None:
        # (observer_id, target_id) -> list of RevealHandle
        # observer_id == caster_id for caster-only scope
        # observer_id == party_id for party scope (every party
        # member queries with the same key)
        self._by_observer_target: dict[
            tuple[str, str], list[RevealHandle]] = {}

    # ------------------------------------------------------------------
    # Grant
    # ------------------------------------------------------------------

    def grant(self,
                *,
                observer_id: str,
                target_id: str,
                source_skill: str,
                now: float,
                duration_override: t.Optional[float] = None) -> RevealHandle:
        """Grant a reveal handle. Returns the handle.

        Replaces any existing handle keyed by (observer, target,
        source_skill) — so a second Scan refreshes rather than stacks.
        """
        if source_skill not in REVEAL_SKILLS:
            raise ValueError(f"unknown reveal skill {source_skill!r}")
        skill = REVEAL_SKILLS[source_skill]
        duration = duration_override
        if duration is None:
            duration = skill.duration_seconds
        if duration < 0:
            raise ValueError("duration must be non-negative")
        handle = RevealHandle(
            caster_id=observer_id,
            target_id=target_id,
            source_skill=source_skill,
            expires_at=now + duration,
            kind=skill.kind,
            scope=skill.scope,
        )
        key = (observer_id, target_id)
        bucket = self._by_observer_target.setdefault(key, [])
        # Remove any prior handle from the same source
        bucket[:] = [h for h in bucket if h.source_skill != source_skill]
        bucket.append(handle)
        return handle

    # ------------------------------------------------------------------
    # Peek
    # ------------------------------------------------------------------

    def peek(self,
                *,
                observer_id: str,
                target_id: str,
                now: float) -> RevealReadout:
        """Resolve what the observer can see on the target right now."""
        bucket = self._by_observer_target.get((observer_id, target_id), [])
        active = [h for h in bucket if h.expires_at > now]
        # Prune in place
        if len(active) != len(bucket):
            self._by_observer_target[(observer_id, target_id)] = active

        hp_visible = False
        mp_visible = False
        latest_expiry = 0.0
        sources: list[str] = []
        for h in active:
            sources.append(h.source_skill)
            if h.expires_at > latest_expiry:
                latest_expiry = h.expires_at
            if h.kind in (RevealKind.HP_NUMERIC,
                              RevealKind.HP_AND_MP_NUMERIC,
                              RevealKind.PARTY_HP_NUMERIC,
                              RevealKind.PARTY_HP_AND_MP_NUMERIC):
                hp_visible = True
            if h.kind in (RevealKind.MP_NUMERIC,
                              RevealKind.HP_AND_MP_NUMERIC,
                              RevealKind.PARTY_HP_AND_MP_NUMERIC):
                mp_visible = True
        return RevealReadout(
            target_id=target_id,
            hp_visible=hp_visible,
            mp_visible=mp_visible,
            expires_at=latest_expiry,
            sources=tuple(sources),
        )

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def expire_all(self, *, now: float) -> int:
        """Remove every expired handle across all keys.

        Returns number removed. The peek path also self-prunes; this
        method is for periodic GC when there's no peek traffic.
        """
        removed = 0
        for key in list(self._by_observer_target.keys()):
            bucket = self._by_observer_target[key]
            keep = [h for h in bucket if h.expires_at > now]
            removed += len(bucket) - len(keep)
            if keep:
                self._by_observer_target[key] = keep
            else:
                del self._by_observer_target[key]
        return removed

    def active_handles(self,
                          *,
                          observer_id: str,
                          target_id: str,
                          now: float) -> list[RevealHandle]:
        """All non-expired handles for one observer-target pair."""
        bucket = self._by_observer_target.get((observer_id, target_id), [])
        return [h for h in bucket if h.expires_at > now]

    def __len__(self) -> int:
        """Count of all (observer, target) keys (live or stale)."""
        return len(self._by_observer_target)
