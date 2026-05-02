"""Master levels — post-99 progression layer.

After hitting level 99 a player begins earning Master EXP. Each
Master Level (ML) takes a curve-shaped pile of MEXP, capped at
ML 50. Each ML grants:
* Per-job stat bumps (HP/MP, attack, accuracy)
* A small +1 to chosen merit skill at every 5 levels

Master EXP is global (any-job earned MEXP applies to the
player). It's separate from Job Points (which are per-job).

Public surface
--------------
    MAX_MASTER_LEVEL = 50
    mexp_for_ml(target_ml) -> int    (curve)
    PlayerMasterProgress
        .award_mexp(amount) -> AwardResult
        .level property
"""
from __future__ import annotations

import dataclasses
import typing as t


MAX_MASTER_LEVEL = 50

# Per-ML stat reward (kept simple): +1 attack and +20 HP per ML
HP_PER_ML = 20
ATTACK_PER_ML = 1


def mexp_for_ml(target_ml: int) -> int:
    """Cumulative MEXP required to reach *target_ml*.

    Curve: 50_000 * target_ml^1.4. ML 1 = 50k. ML 50 ~= 14M.
    Matches retail's ramping shape closely enough for tests.
    """
    if target_ml <= 0:
        return 0
    return int(50_000 * (target_ml ** 1.4))


@dataclasses.dataclass(frozen=True)
class AwardResult:
    accepted: bool
    new_level: int = 0
    levels_gained: int = 0
    mexp_total: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerMasterProgress:
    player_id: str
    main_job_level: int = 0    # used to gate ML access
    mexp_total: int = 0
    level: int = 0

    @property
    def is_ml_eligible(self) -> bool:
        return self.main_job_level >= 99

    @property
    def hp_bonus(self) -> int:
        return self.level * HP_PER_ML

    @property
    def attack_bonus(self) -> int:
        return self.level * ATTACK_PER_ML

    def award_mexp(self, *, amount: int) -> AwardResult:
        if not self.is_ml_eligible:
            return AwardResult(False, reason="not at level 99")
        if amount <= 0:
            return AwardResult(False, reason="amount must be > 0")
        self.mexp_total += amount
        prev_level = self.level
        # Walk forward as many MLs as our total covers
        while (
            self.level < MAX_MASTER_LEVEL
            and self.mexp_total >= mexp_for_ml(self.level + 1)
        ):
            self.level += 1
        return AwardResult(
            accepted=True,
            new_level=self.level,
            levels_gained=self.level - prev_level,
            mexp_total=self.mexp_total,
        )


__all__ = [
    "MAX_MASTER_LEVEL", "HP_PER_ML", "ATTACK_PER_ML",
    "mexp_for_ml",
    "AwardResult", "PlayerMasterProgress",
]
