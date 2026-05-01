"""Tier-1 BarkAgent — schedule + bark library.

Per AI_WORLD_DENSITY.md: 'Daily-loop NPCs with hand-authored
schedules and a small bark library. Each NPC has a list of 5-10
location/time pairs and 10-30 contextual chat lines.'

Cost ~0 per agent. Scales to thousands across the world.
"""
from __future__ import annotations

import dataclasses
import random
import typing as t


@dataclasses.dataclass(frozen=True)
class ScheduleEntry:
    """One entry in a Tier-1 NPC's daily schedule.

    `vana_hour` is 0..23 in Vana'diel time.
    """
    vana_hour: int
    zone: str
    position_xy: tuple[float, float]
    activity: str = "idle"   # 'patrol' / 'sleep' / 'sell_wares' / etc.


@dataclasses.dataclass
class BarkAgent:
    """A scripted Tier-1 NPC."""
    agent_id: str
    name: str
    archetype: str
    home_zone: str
    schedule: list[ScheduleEntry] = dataclasses.field(default_factory=list)
    bark_pool: list[str] = dataclasses.field(default_factory=list)
    mood: str = "content"
    last_bark_at: t.Optional[float] = None


def current_schedule_entry(agent: BarkAgent,
                            *,
                            vana_hour: int) -> t.Optional[ScheduleEntry]:
    """Return the schedule entry currently active given the in-game
    hour. Picks the entry with the largest hour <= vana_hour, wrapping
    around midnight."""
    if not agent.schedule:
        return None
    sorted_entries = sorted(agent.schedule, key=lambda e: e.vana_hour)
    matching = [e for e in sorted_entries if e.vana_hour <= vana_hour]
    if matching:
        return matching[-1]
    # Wrap-around: use the latest entry from yesterday (highest hour)
    return sorted_entries[-1]


# Mood-weighted bark selection. The orchestrator passes the agent's
# current mood; we apply tiny weights to bark choices that "feel"
# right for that mood.
MOOD_BARK_AFFINITIES: dict[str, tuple[str, ...]] = {
    "content":   ("welcome", "fresh", "thanks", "good", "splendid"),
    "weary":     ("tired", "long day", "rest", "later"),
    "fearful":   ("careful", "danger", "hide", "watchful"),
    "furious":   ("get out", "leave", "annoying", "no"),
    "mischievous": ("oh ho", "interesting", "perhaps", "secret"),
    "alert":     ("watch", "ready", "guard", "stand fast"),
}


def pick_bark(agent: BarkAgent,
                *,
                rng: t.Optional[random.Random] = None) -> t.Optional[str]:
    """Pick a bark from the agent's pool, weighted toward lines that
    contain mood-affinity keywords. Returns None if the pool is empty.
    """
    if not agent.bark_pool:
        return None
    rng = rng or random.Random()

    keywords = MOOD_BARK_AFFINITIES.get(agent.mood, ())
    if not keywords:
        return rng.choice(agent.bark_pool)

    weights = []
    for line in agent.bark_pool:
        lower = line.lower()
        # +1 weight per keyword match; baseline weight 1.0
        bonus = sum(1.0 for k in keywords if k in lower)
        weights.append(1.0 + bonus)

    total = sum(weights)
    roll = rng.random() * total
    running = 0.0
    for line, weight in zip(agent.bark_pool, weights):
        running += weight
        if roll <= running:
            return line
    return agent.bark_pool[-1]


def update_mood(agent: BarkAgent, new_mood: str) -> None:
    agent.mood = new_mood
