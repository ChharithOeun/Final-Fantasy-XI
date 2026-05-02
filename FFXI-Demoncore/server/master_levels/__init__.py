"""Master Levels — true post-99 progression to level 150.

Demoncore overhaul of the canonical FFXI ML system. Instead of
a parallel "Master Level 1-50" gauge that sits alongside a
permanently-99 job level, the player's actual job level extends
past 99 all the way to 150. Each level past 99 is gated by:

* JOB_MASTER_JP_REQUIREMENT (2100 JP) — must hit Job Master to
  even attempt the first Shadow Genkai
* a Shadow Genkai quest unlocks +5 cap at each milestone
  (100, 105, 110, ..., 150)
* MEXP earned in normal play fills the bar, but the cap holds
  you at each milestone until the next Shadow Genkai is cleared

Why this matters: at lvl 100+ a player's tertiary subjob
unlocks more skills/abilities/magic — the game's strategy
space genuinely changes. ML 150 is the soft cap; soft because
later content can extend the chain without breaking the model.

Public surface
--------------
    JOB_MASTER_JP_REQUIREMENT, MASTER_LEVEL_FLOOR (99),
    MASTER_LEVEL_CEILING (150), MASTER_GENKAI_INTERVAL (5)
    HP_PER_ML, ATTACK_PER_ML
    mexp_for_level(target_level) -> int   (curve)
    PlayerMasterLevel
        .award_mexp(amount) -> AwardResult
        .level / .effective_cap / .next_genkai_target / .hp_bonus
        .needs_genkai_to_advance property
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.shadow_genkai import (
    SHADOW_GENKAI_BY_TARGET,
    PlayerShadowGenkai,
)


# -- Gates ------------------------------------------------------------
JOB_MASTER_JP_REQUIREMENT = 2100
MASTER_LEVEL_FLOOR = 99
MASTER_LEVEL_CEILING = 150
MASTER_GENKAI_INTERVAL = 5

# -- Per-level rewards (applied per level above 99) -------------------
HP_PER_ML = 25
MP_PER_ML = 15

# +1 to EVERY hard stat per ML. The seven hard stats are
# STR/DEX/VIT/AGI/INT/MND/CHR. Derived stats (attack/accuracy/
# magic damage) all flow naturally from these.
HARD_STAT_PER_ML = 1
HARD_STATS = ("str", "dex", "vit", "agi", "int", "mnd", "chr")

# Combat + magic skill caps go up 5 per ML so players can keep
# skilling up — important because skill levels gate access to
# weaponskills, songs, ninjutsu, blue magic, etc.
SKILL_CAP_PER_ML = 5


def mexp_for_level(target_level: int) -> int:
    """Cumulative MEXP required to reach *target_level* from 99.

    Level 100 = 50,000 MEXP. Each subsequent level scales
    geometrically: at 150 cumulative is ~26M. Curve is
    50_000 * (target_level - 99)^1.4.
    """
    if target_level <= MASTER_LEVEL_FLOOR:
        return 0
    delta = target_level - MASTER_LEVEL_FLOOR
    return int(50_000 * (delta ** 1.4))


def is_genkai_milestone(level: int) -> bool:
    """True at 100, 105, 110, ..., 150."""
    first_milestone = MASTER_LEVEL_FLOOR + 1   # 100
    return (
        level >= first_milestone
        and ((level - first_milestone) % MASTER_GENKAI_INTERVAL == 0)
        and level <= MASTER_LEVEL_CEILING
    )


@dataclasses.dataclass(frozen=True)
class AwardResult:
    accepted: bool
    new_level: int = MASTER_LEVEL_FLOOR
    levels_gained: int = 0
    mexp_total: int = 0
    blocked_by_genkai_at: t.Optional[int] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerMasterLevel:
    """Per-player + per-job ML progression."""
    player_id: str
    job: str
    job_jp_total: int = 0          # for job-master gate check
    level: int = MASTER_LEVEL_FLOOR
    mexp_total: int = 0

    # Each player+job has its own Shadow Genkai cursor.
    shadow_genkai: PlayerShadowGenkai = dataclasses.field(
        default=None,        # type: ignore[assignment]
    )

    def __post_init__(self) -> None:
        if self.shadow_genkai is None:
            self.shadow_genkai = PlayerShadowGenkai(
                player_id=self.player_id, job=self.job,
            )

    # ------------------------------------------------------------------
    # Derived state
    # ------------------------------------------------------------------
    @property
    def has_job_master(self) -> bool:
        return self.job_jp_total >= JOB_MASTER_JP_REQUIREMENT

    @property
    def effective_cap(self) -> int:
        """How high we can level right now without another Genkai.

        Always at least 99. Walks the Shadow Genkai cursor: each
        cleared genkai bumps the cap by 5, capped at 150.
        """
        cap = MASTER_LEVEL_FLOOR
        # The shadow_genkai tracker stores completed *target* levels
        for tgt in sorted(self.shadow_genkai.completed_target_levels):
            if tgt > cap:
                cap = tgt
        return min(cap, MASTER_LEVEL_CEILING)

    @property
    def next_genkai_target(self) -> t.Optional[int]:
        """The next ML the player is gated behind, or None if at 150."""
        if self.level >= MASTER_LEVEL_CEILING:
            return None
        nxt = self.effective_cap + MASTER_GENKAI_INTERVAL
        if nxt > MASTER_LEVEL_CEILING:
            return None
        return nxt

    @property
    def needs_genkai_to_advance(self) -> bool:
        """True iff the player is XP-locked at the cap."""
        return self.level >= self.effective_cap

    # Stat bonuses derived from levels above 99
    @property
    def levels_above_floor(self) -> int:
        return max(0, self.level - MASTER_LEVEL_FLOOR)

    @property
    def hp_bonus(self) -> int:
        return self.levels_above_floor * HP_PER_ML

    @property
    def mp_bonus(self) -> int:
        return self.levels_above_floor * MP_PER_ML

    @property
    def hard_stat_bonus(self) -> int:
        """Flat +N applied to every hard stat (STR/DEX/VIT/AGI/INT/MND/CHR)."""
        return self.levels_above_floor * HARD_STAT_PER_ML

    @property
    def skill_cap_bonus(self) -> int:
        """How much each combat/magic skill cap is raised."""
        return self.levels_above_floor * SKILL_CAP_PER_ML

    def stat_bonuses(self) -> dict[str, int]:
        """Return a dict of {hard_stat_name: bonus} for all 7 stats."""
        bonus = self.hard_stat_bonus
        return {s: bonus for s in HARD_STATS}

    # ------------------------------------------------------------------
    # MEXP awarding
    # ------------------------------------------------------------------
    def award_mexp(self, *, amount: int) -> AwardResult:
        if amount <= 0:
            return AwardResult(False, new_level=self.level,
                                reason="amount must be > 0")
        if self.level >= MASTER_LEVEL_CEILING:
            return AwardResult(False, new_level=self.level,
                                reason="already at level 150")
        # First-time entry: must have Job Master AND first Shadow
        # Genkai cleared. Without those, MEXP can still be banked
        # (so XP from level-99 fights isn't wasted while you train),
        # but level can't tick over the floor.
        cap = self.effective_cap
        prev_level = self.level
        self.mexp_total += amount
        # Walk forward as far as the cap allows
        while (
            self.level < cap
            and self.mexp_total >= mexp_for_level(self.level + 1)
        ):
            self.level += 1
        gained = self.level - prev_level
        # If we hit the cap and another genkai is required, surface it
        blocked_at: t.Optional[int] = None
        if self.level == cap and cap < MASTER_LEVEL_CEILING:
            blocked_at = cap + MASTER_GENKAI_INTERVAL
        return AwardResult(
            accepted=True, new_level=self.level,
            levels_gained=gained,
            mexp_total=self.mexp_total,
            blocked_by_genkai_at=blocked_at,
        )

    # ------------------------------------------------------------------
    # Wire JP and Shadow Genkai
    # ------------------------------------------------------------------
    def add_job_jp(self, *, amount: int) -> bool:
        if amount <= 0:
            return False
        self.job_jp_total += amount
        return True

    def attempt_genkai(self, *, target_level: int) -> bool:
        """Player just cleared the Shadow Genkai whose reward is
        *target_level*. Updates the cap if accepted."""
        quest = SHADOW_GENKAI_BY_TARGET.get(target_level)
        if quest is None:
            return False
        return self.shadow_genkai.complete(
            quest_id=quest.quest_id,
            has_job_master=self.has_job_master,
        )


__all__ = [
    "JOB_MASTER_JP_REQUIREMENT",
    "MASTER_LEVEL_FLOOR", "MASTER_LEVEL_CEILING",
    "MASTER_GENKAI_INTERVAL",
    "HP_PER_ML", "MP_PER_ML",
    "HARD_STAT_PER_ML", "HARD_STATS", "SKILL_CAP_PER_ML",
    "mexp_for_level", "is_genkai_milestone",
    "AwardResult", "PlayerMasterLevel",
]
