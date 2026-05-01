"""Mob memory — per-spawn kill_count + level scaling.

Per NPC_PROGRESSION.md: A goblin in West Ronfaure spawns at level 7.
After 3 newbie kills it's level 8; after 10 it's level 9. Soft cap
at base + 5 levels. Resets when the mob is killed (next spawn starts
at base).

This makes notable-mob lore happen organically: 'the goblin everyone
in the LS knows about because it's been killing people for a week.'
"""
from __future__ import annotations

import dataclasses
import typing as t


MOB_LEVEL_SCALING_CAP = 5            # base + 5 max
KILL_COUNT_THRESHOLDS = (3, 10, 20, 35, 50)   # kills required for +1, +2, +3, +4, +5


@dataclasses.dataclass
class MobSnapshot:
    """Per-mob-spawn memory. One per active spawn (not per mob_id)."""
    spawn_id: str
    base_level: int
    zone: str
    species: str                   # 'goblin' / 'orc' / etc.
    territory: str = ""            # subzone / patrol-route ID
    kill_count: int = 0            # players this spawn has killed
    spawn_timestamp: float = 0.0   # for the survival-time XP track


def increment_kill_count(state: MobSnapshot, *, count: int = 1) -> int:
    """Record kills credited to this spawn. Returns the new mob level."""
    state.kill_count += count
    return mob_level(state)


def mob_level(state: MobSnapshot) -> int:
    """Resolve the current effective level from kill_count.

    base; +1 at 3 kills; +2 at 10; +3 at 20; +4 at 35; +5 at 50.
    """
    bonus = 0
    for threshold in KILL_COUNT_THRESHOLDS:
        if state.kill_count >= threshold:
            bonus += 1
        else:
            break
    return state.base_level + min(bonus, MOB_LEVEL_SCALING_CAP)


def reset_on_death(state: MobSnapshot) -> int:
    """The mob died. Per the doc: scaling resets to base on death.
    Returns the new (base) level."""
    state.kill_count = 0
    return state.base_level


def is_notable(state: MobSnapshot, *, threshold: int = 10) -> bool:
    """A spawn becomes 'notable' when it crosses a kill threshold —
    drives the orchestrator to publish lore (linkshell-shouts, NPC
    dialogue mentions)."""
    return state.kill_count >= threshold
