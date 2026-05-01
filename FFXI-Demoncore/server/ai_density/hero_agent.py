"""Tier-3 HeroAgent — full generative agent for hero NPCs.

Per AI_WORLD_DENSITY.md: 'Hero NPCs (Cid, Volker, Cornelia, Cardinal
Mildaurion). Full memory streams, daily reflections, planning. They
have opinions, friendships, goals, and they pursue those goals across
in-game days even when no player is watching.'

Doc example: 'Cid is working on a new airship; goes into the workshop
at 8am, has lunch with his daughter, talks to Volker about politics
in the evening.'

This module models the data layer: daily schedule, relationships,
goals, journal. Actual LLM-driven planning is delegated to chharbot's
generative-agents bridge; we provide deterministic helpers + the
data shapes the bridge consumes.
"""
from __future__ import annotations

import dataclasses
import typing as t


HERO_REFLECTION_INTERVAL_GAME_MINUTES = 5     # snapshot every 5 game-minutes


@dataclasses.dataclass(frozen=True)
class DailyScheduleEntry:
    """One slot in a hero NPC's daily life loop."""
    vana_hour: int
    activity: str               # "workshop_airship_design" / "lunch_with_daughter"
    location: str
    duration_hours: float = 1.0
    relationship_focus: t.Optional[str] = None     # other_agent_id, if applicable


@dataclasses.dataclass
class Relationship:
    """Hero's tracked relationship with another agent."""
    other_agent_id: str
    other_name: str
    affinity: float = 0.0                   # -1.0..1.0
    relationship_kind: str = "acquaintance"  # 'family' / 'friend' / 'rival'
    last_interaction_at: t.Optional[float] = None
    notes: str = ""


@dataclasses.dataclass
class Goal:
    """A long-running project the hero is pursuing."""
    goal_id: str
    description: str
    progress_pct: float = 0.0
    target_completion_day: t.Optional[int] = None
    notes: str = ""


@dataclasses.dataclass
class JournalEntry:
    """Periodic writeup that drives procedural side-quest generation."""
    timestamp: float
    text: str
    spawned_quest_id: t.Optional[str] = None


@dataclasses.dataclass
class HeroAgent:
    """A Tier-3 fully-generative hero NPC."""
    agent_id: str
    name: str
    role: str
    home_zone: str
    schedule: list[DailyScheduleEntry] = dataclasses.field(default_factory=list)
    relationships: dict[str, Relationship] = dataclasses.field(default_factory=dict)
    goals: list[Goal] = dataclasses.field(default_factory=list)
    journal: list[JournalEntry] = dataclasses.field(default_factory=list)
    last_snapshot_at: t.Optional[float] = None


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def current_activity(agent: HeroAgent,
                       *,
                       vana_hour: int) -> t.Optional[DailyScheduleEntry]:
    """Resolve which activity slot the hero is in right now."""
    if not agent.schedule:
        return None
    sorted_entries = sorted(agent.schedule, key=lambda e: e.vana_hour)
    matching = [e for e in sorted_entries if e.vana_hour <= vana_hour]
    if matching:
        return matching[-1]
    return sorted_entries[-1]


def add_relationship(agent: HeroAgent,
                       *,
                       other_agent_id: str,
                       other_name: str,
                       relationship_kind: str = "acquaintance",
                       affinity: float = 0.0) -> None:
    agent.relationships[other_agent_id] = Relationship(
        other_agent_id=other_agent_id,
        other_name=other_name,
        relationship_kind=relationship_kind,
        affinity=affinity,
    )


def adjust_affinity(agent: HeroAgent,
                     *,
                     other_agent_id: str,
                     delta: float,
                     now: float) -> float:
    """Bump the affinity for a tracked relationship. Returns the new
    affinity value (clamped -1.0..1.0)."""
    rel = agent.relationships.get(other_agent_id)
    if rel is None:
        return 0.0
    rel.affinity = max(-1.0, min(1.0, rel.affinity + delta))
    rel.last_interaction_at = now
    return rel.affinity


def add_goal(agent: HeroAgent,
              *,
              goal_id: str,
              description: str,
              target_completion_day: t.Optional[int] = None) -> Goal:
    goal = Goal(goal_id=goal_id, description=description,
                  target_completion_day=target_completion_day)
    agent.goals.append(goal)
    return goal


def progress_goal(agent: HeroAgent,
                    *,
                    goal_id: str,
                    delta_pct: float) -> float:
    """Advance a goal's progress. Returns the new progress percentage."""
    for goal in agent.goals:
        if goal.goal_id == goal_id:
            goal.progress_pct = max(0.0, min(100.0, goal.progress_pct + delta_pct))
            return goal.progress_pct
    return 0.0


def write_journal_entry(agent: HeroAgent,
                          *,
                          text: str,
                          timestamp: float,
                          spawned_quest_id: t.Optional[str] = None) -> JournalEntry:
    entry = JournalEntry(timestamp=timestamp, text=text,
                            spawned_quest_id=spawned_quest_id)
    agent.journal.append(entry)
    return entry


def needs_snapshot(agent: HeroAgent,
                    *,
                    now: float,
                    vana_minutes_per_real_second: float = 1.0) -> bool:
    """5-game-minute snapshot cadence. The orchestrator passes
    vana_minutes_per_real_second to convert."""
    if agent.last_snapshot_at is None:
        return True
    interval_real = (HERO_REFLECTION_INTERVAL_GAME_MINUTES * 60.0
                       / max(0.001, vana_minutes_per_real_second))
    return (now - agent.last_snapshot_at) >= interval_real


def snapshot_taken(agent: HeroAgent, *, now: float) -> None:
    agent.last_snapshot_at = now
