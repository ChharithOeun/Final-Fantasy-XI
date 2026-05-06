"""Cooking skill — the player's craft proficiency 0..100.

Cookpot recipes can be cooked by any player. Whether the
result is BASIC, GOOD, or HQ depends on the player's
cooking skill versus the recipe's difficulty. Higher-tier
recipes also gate behind a min_skill — you can't even
attempt master-level dishes until you've put in the work.

The fully menu-driven, turn-based context here:
the player picks a recipe from the cooking menu, the
attempt resolves into a CookOutcome carrying the quality
tier. There's no QTE, no twitch — your skill versus the
recipe's difficulty determines the curve, and a deterministic
roller (caller-injectable for tests/replays) picks the slot.

Quality tiers
-------------
    FAILED  — wasted ingredients, no dish (catastrophic)
    BASIC   — the dish, base payload
    GOOD    — +25% on stat bonuses
    HQ      — +50% on stat bonuses + 2x duration

Skill grows on every successful cook (more on harder
recipes). Skill caps at 100; ranks (NOVICE/JOURNEYMAN/
ARTISAN/MASTER) are surface-level summaries.

Public surface
--------------
    SkillRank enum
    CookOutcome enum
    CookAttemptResult dataclass (frozen)
    CookingSkillRegistry
        .grant_baseline(player_id) -> bool
        .skill_of(player_id) -> int
        .rank_of(player_id) -> SkillRank
        .can_attempt(player_id, recipe_difficulty,
                     min_skill_required) -> bool
        .resolve_attempt(player_id, recipe_difficulty,
                         min_skill_required, roll_pct)
            -> CookAttemptResult
        .add_xp(player_id, amount) -> int  (new skill)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SkillRank(str, enum.Enum):
    NONE = "none"
    NOVICE = "novice"
    JOURNEYMAN = "journeyman"
    ARTISAN = "artisan"
    MASTER = "master"


class CookOutcome(str, enum.Enum):
    FAILED = "failed"
    BASIC = "basic"
    GOOD = "good"
    HQ = "hq"


_RANK_THRESHOLDS = (
    (80, SkillRank.MASTER),
    (50, SkillRank.ARTISAN),
    (20, SkillRank.JOURNEYMAN),
    (1, SkillRank.NOVICE),
)


@dataclasses.dataclass(frozen=True)
class CookAttemptResult:
    outcome: CookOutcome
    skill_xp_gained: int    # 0 on FAILED


@dataclasses.dataclass
class CookingSkillRegistry:
    _skill: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def grant_baseline(self, *, player_id: str) -> bool:
        if not player_id:
            return False
        if player_id in self._skill:
            return False
        self._skill[player_id] = 0
        return True

    def skill_of(self, *, player_id: str) -> int:
        return self._skill.get(player_id, 0)

    def rank_of(self, *, player_id: str) -> SkillRank:
        skill = self._skill.get(player_id, 0)
        for thr, rank in _RANK_THRESHOLDS:
            if skill >= thr:
                return rank
        return SkillRank.NONE

    def can_attempt(
        self, *, player_id: str,
        min_skill_required: int,
    ) -> bool:
        return self.skill_of(player_id=player_id) >= min_skill_required

    def add_xp(
        self, *, player_id: str, amount: int,
    ) -> int:
        if amount <= 0 or not player_id:
            return self.skill_of(player_id=player_id)
        cur = self._skill.get(player_id, 0)
        new = cur + amount
        if new > 100:
            new = 100
        self._skill[player_id] = new
        return new

    def resolve_attempt(
        self, *, player_id: str,
        recipe_difficulty: int,
        min_skill_required: int,
        roll_pct: int,
    ) -> CookAttemptResult:
        # gate
        if not self.can_attempt(
            player_id=player_id,
            min_skill_required=min_skill_required,
        ):
            return CookAttemptResult(
                outcome=CookOutcome.FAILED, skill_xp_gained=0,
            )
        skill = self.skill_of(player_id=player_id)
        margin = skill - recipe_difficulty
        # base success threshold by margin
        # margin >= 30: never fail
        # margin >= 0:  fail at roll < 5
        # margin < 0:   linear penalty (each -10 = +15% fail)
        if margin >= 30:
            fail_threshold = 0
        elif margin >= 0:
            fail_threshold = 5
        else:
            fail_threshold = 5 + int(abs(margin) * 1.5)
            if fail_threshold > 95:
                fail_threshold = 95
        if roll_pct < fail_threshold:
            return CookAttemptResult(
                outcome=CookOutcome.FAILED, skill_xp_gained=0,
            )
        # success — pick quality tier
        # GOOD threshold scales with margin; HQ very strict
        if margin >= 20 and roll_pct >= 95:
            outcome = CookOutcome.HQ
        elif margin >= 10 and roll_pct >= 80:
            outcome = CookOutcome.GOOD
        else:
            outcome = CookOutcome.BASIC
        # XP scales with how challenging the recipe was
        # for this player. Harder recipes = more growth.
        if margin >= 20:
            xp = 1
        elif margin >= 0:
            xp = 3
        else:
            xp = 5  # cooking above your level grows you fastest
        # already-mastered skill grants no further XP
        if self.skill_of(player_id=player_id) >= 100:
            xp = 0
        self.add_xp(player_id=player_id, amount=xp)
        return CookAttemptResult(
            outcome=outcome, skill_xp_gained=xp,
        )

    def total_known_players(self) -> int:
        return len(self._skill)


__all__ = [
    "SkillRank", "CookOutcome", "CookAttemptResult",
    "CookingSkillRegistry",
]
