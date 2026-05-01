"""Tier-2 ReflectionAgent — hourly LLM-driven memory + bark tuning.

Per AI_WORLD_DENSITY.md: 'Named NPCs with light personalities. Run a
small local LLM (Llama 3 8B-Instruct on Ollama) once an hour to
'reflect' on what happened to them, update a one-sentence memory,
and adjust their bark library.'

Each agent carries:
    name, role, personality, memory_summary, current_mood, bark_pool

The orchestrator invokes reflect_on_events() once an hour. The LLM
call is stubbed in this engine — real Ollama integration lives in
chharbot. Here we encode the data flow + a deterministic fallback
that summarizes events without calling out.
"""
from __future__ import annotations

import dataclasses
import typing as t


# Hourly cadence. The orchestrator (chharbot world tick) calls
# reflect_on_events at this interval per agent.
REFLECTION_INTERVAL_SECONDS = 3600.0
MEMORY_SUMMARY_MAX_CHARS = 240        # 1-2 sentences fit


@dataclasses.dataclass
class WitnessedEvent:
    """One event the agent observed during the last reflection window."""
    timestamp: float
    kind: str                    # "outlaw_broke_barrel" / "festival" / etc.
    summary: str                  # short human-readable description
    valence: float = 0.0         # -1.0 (bad) to +1.0 (good)


@dataclasses.dataclass
class ReflectionAgent:
    """A Tier-2 named NPC with hourly reflection."""
    agent_id: str
    name: str
    role: str
    personality: str
    home_zone: str
    memory_summary: str = ""
    current_mood: str = "content"
    bark_pool: list[str] = dataclasses.field(default_factory=list)
    last_reflected_at: t.Optional[float] = None
    pending_events: list[WitnessedEvent] = dataclasses.field(
        default_factory=list)


def add_witnessed_event(agent: ReflectionAgent,
                          *,
                          kind: str,
                          summary: str,
                          valence: float,
                          timestamp: float) -> None:
    """Record an event for the next reflection cycle."""
    agent.pending_events.append(WitnessedEvent(
        timestamp=timestamp, kind=kind,
        summary=summary, valence=valence,
    ))


def needs_reflection(agent: ReflectionAgent, *, now: float) -> bool:
    """Has the reflection window elapsed since last cycle?"""
    if agent.last_reflected_at is None:
        # First-ever reflection only fires when there are pending events
        return bool(agent.pending_events)
    return (now - agent.last_reflected_at) >= REFLECTION_INTERVAL_SECONDS


def _deterministic_mood(events: list[WitnessedEvent]) -> str:
    """Pick a mood from the event valence sum. Pure-function fallback
    when the LLM isn't available (CI / offline)."""
    if not events:
        return "content"
    avg = sum(e.valence for e in events) / len(events)
    if avg <= -0.5:
        return "furious"
    if avg <= -0.2:
        return "weary"
    if avg >= 0.5:
        return "content"
    if avg >= 0.2:
        return "alert"
    return "content"


def _deterministic_summary(agent: ReflectionAgent,
                            events: list[WitnessedEvent]) -> str:
    """Build a one-sentence summary from the most-impactful event.
    Fallback when LLM unavailable."""
    if not events:
        return agent.memory_summary or f"A quiet day for {agent.name}."
    # Pick the event with the largest absolute valence
    best = max(events, key=lambda e: abs(e.valence))
    summary = f"{best.summary}"
    return summary[:MEMORY_SUMMARY_MAX_CHARS]


def reflect_on_events(agent: ReflectionAgent,
                        *,
                        now: float,
                        llm_summarizer: t.Optional[t.Callable[
                            [ReflectionAgent, list[WitnessedEvent]], str]
                        ] = None,
                        ) -> tuple[str, str]:
    """Run one reflection cycle. Returns (new_mood, new_memory_summary).

    The orchestrator may pass `llm_summarizer` (the chharbot-Ollama
    bridge) to use the real LLM. Without it, deterministic fallbacks
    keep the engine functional in CI."""
    events = list(agent.pending_events)
    new_mood = _deterministic_mood(events)
    if llm_summarizer is not None:
        try:
            new_summary = llm_summarizer(agent, events)
        except Exception:
            new_summary = _deterministic_summary(agent, events)
    else:
        new_summary = _deterministic_summary(agent, events)
    new_summary = (new_summary or "")[:MEMORY_SUMMARY_MAX_CHARS]

    agent.current_mood = new_mood
    agent.memory_summary = new_summary
    agent.last_reflected_at = now
    agent.pending_events.clear()
    return new_mood, new_summary
