"""Limit Break — Genkai gates, merit cap, job points.

Three progression strands beyond the natural level cap:

  GENKAI 1-5: each unlocks +5 levels (50, 55, 60, 65, 70).
              Above 70, Maat's Cap quests unlock 71-75.
              Above 75, expansion-tied gates push to 99.
  MERIT POINTS: post-cap currency earned via XP gain at max level.
                Spent on stat/skill/category enhancements.
  JOB POINTS: post-119 currency. CapacityPoints accumulate during
              max-level fights and convert to JP at thresholds
              (10000 cap = 1 JP). JP buy permanent buffs to that job.

Public surface
--------------
    GenkaiTier            enum 0..5 (0 = none)
    GenkaiProgress        per-player tracker
    merit_cap_for_level   scaled cap on accumulated merits
    JobPointBank          per-(player, job) pool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GenkaiTier(int, enum.Enum):
    """Each tier unlocks +5 max level."""
    NONE = 0    # cap 50
    LB1 = 1     # cap 55
    LB2 = 2     # cap 60
    LB3 = 3     # cap 65
    LB4 = 4     # cap 70
    LB5 = 5     # cap 75


GENKAI_LEVEL_CAP: dict[GenkaiTier, int] = {
    GenkaiTier.NONE: 50,
    GenkaiTier.LB1: 55,
    GenkaiTier.LB2: 60,
    GenkaiTier.LB3: 65,
    GenkaiTier.LB4: 70,
    GenkaiTier.LB5: 75,
}


def level_cap_for_tier(tier: GenkaiTier) -> int:
    return GENKAI_LEVEL_CAP[tier]


def merit_cap_for_level(level: int) -> int:
    """Number of merits a player at *level* can hold concurrently.

    Pre-75 capped at 0. Then ramps:
      75 -> 10
      85 -> 15
      99 -> 20
      119 -> 30
    Linear interpolation above 75.
    """
    if level < 75:
        return 0
    if level >= 119:
        return 30
    # linear ramp: 75 -> 10, 99 -> 20, 119 -> 30
    if level <= 99:
        return 10 + (level - 75) * 10 // 24
    return 20 + (level - 99) * 10 // 20


@dataclasses.dataclass
class GenkaiProgress:
    player_id: str
    completed_tiers: set[GenkaiTier] = dataclasses.field(
        default_factory=set,
    )

    def current_tier(self) -> GenkaiTier:
        if not self.completed_tiers:
            return GenkaiTier.NONE
        return max(self.completed_tiers, key=lambda t: t.value)

    def complete(self, tier: GenkaiTier) -> bool:
        if tier == GenkaiTier.NONE:
            return False
        # Must complete tiers in order: cannot do LB3 without LB1, LB2.
        prereq = GenkaiTier(tier.value - 1)
        if prereq != GenkaiTier.NONE and \
                prereq not in self.completed_tiers:
            return False
        if tier in self.completed_tiers:
            return False
        self.completed_tiers.add(tier)
        return True

    def level_cap(self) -> int:
        return level_cap_for_tier(self.current_tier())


# Capacity Points to Job Points conversion.
CAP_POINTS_PER_JP = 10_000


@dataclasses.dataclass
class JobPointBank:
    player_id: str
    job: str                              # e.g. "warrior"
    capacity_points: int = 0
    job_points_earned: int = 0
    job_points_spent: int = 0

    def add_capacity(self, amount: int) -> int:
        """Add capacity points; auto-convert to JP at thresholds.
        Returns number of JP newly earned this call."""
        if amount < 0:
            raise ValueError("amount must be >= 0")
        self.capacity_points += amount
        new_jp = self.capacity_points // CAP_POINTS_PER_JP
        self.capacity_points -= new_jp * CAP_POINTS_PER_JP
        self.job_points_earned += new_jp
        return new_jp

    @property
    def job_points_available(self) -> int:
        return self.job_points_earned - self.job_points_spent

    def spend(self, amount: int) -> bool:
        if amount <= 0:
            return False
        if amount > self.job_points_available:
            return False
        self.job_points_spent += amount
        return True


__all__ = [
    "GenkaiTier", "GENKAI_LEVEL_CAP",
    "level_cap_for_tier", "merit_cap_for_level",
    "GenkaiProgress",
    "CAP_POINTS_PER_JP", "JobPointBank",
]
