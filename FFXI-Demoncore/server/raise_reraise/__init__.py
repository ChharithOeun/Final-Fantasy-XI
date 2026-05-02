"""Raise / Reraise — resurrection mechanics + Weakness debuff.

When a player is KO'd, they can be raised by another player or by
their own pre-cast Reraise. After raise, they get the Weakness
status (5 minutes), reduced HP/MP, and partial EXP recovery.

Tier scaling:
    Raise I    -> 25% HP, 25% MP, 50% EXP recovered
    Raise II   -> 50% HP, 50% MP, 75% EXP recovered
    Raise III  -> 75% HP, 75% MP, 90% EXP recovered
    Tractor    -> repositions corpse, no HP recovery
    Reraise I  -> auto-Raise I
    Reraise II -> auto-Raise II
    Reraise III-> auto-Raise III

Public surface
--------------
    RaiseTier enum
    RaiseSpec catalog
    apply_raise(...) -> RaiseResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RaiseTier(int, enum.Enum):
    NONE = 0
    RAISE_I = 1
    RAISE_II = 2
    RAISE_III = 3


class RaiseSource(str, enum.Enum):
    SPELL_RAISE = "spell_raise"           # caster raises
    SCROLL = "scroll"                      # consumable scroll
    RERAISE = "reraise"                    # self-applied
    TRACTOR = "tractor"                    # repositions only


WEAKNESS_DURATION_SECONDS = 5 * 60        # 5 minutes


@dataclasses.dataclass(frozen=True)
class RaiseSpec:
    tier: RaiseTier
    hp_recovery_pct: int
    mp_recovery_pct: int
    exp_recovery_pct: int


RAISE_SPECS: dict[RaiseTier, RaiseSpec] = {
    RaiseTier.RAISE_I:   RaiseSpec(
        RaiseTier.RAISE_I, 25, 25, 50,
    ),
    RaiseTier.RAISE_II:  RaiseSpec(
        RaiseTier.RAISE_II, 50, 50, 75,
    ),
    RaiseTier.RAISE_III: RaiseSpec(
        RaiseTier.RAISE_III, 75, 75, 90,
    ),
}


@dataclasses.dataclass(frozen=True)
class RaiseInputs:
    target_max_hp: int
    target_max_mp: int
    exp_lost_on_death: int
    tier: RaiseTier
    source: RaiseSource


@dataclasses.dataclass(frozen=True)
class RaiseResult:
    accepted: bool
    hp_restored: int = 0
    mp_restored: int = 0
    exp_recovered: int = 0
    weakness_until_tick: t.Optional[int] = None
    reason: t.Optional[str] = None


def apply_raise(
    *, inputs: RaiseInputs, now_tick: int,
) -> RaiseResult:
    if inputs.source == RaiseSource.TRACTOR:
        # Tractor: zero recovery, just unlocks raise/walk-back.
        return RaiseResult(
            accepted=True,
            hp_restored=0, mp_restored=0,
            exp_recovered=0,
            weakness_until_tick=None,
        )
    spec = RAISE_SPECS.get(inputs.tier)
    if spec is None:
        return RaiseResult(False, reason="invalid raise tier")
    hp = inputs.target_max_hp * spec.hp_recovery_pct // 100
    mp = inputs.target_max_mp * spec.mp_recovery_pct // 100
    exp = inputs.exp_lost_on_death * spec.exp_recovery_pct // 100
    weakness = now_tick + WEAKNESS_DURATION_SECONDS
    return RaiseResult(
        accepted=True,
        hp_restored=hp, mp_restored=mp,
        exp_recovered=exp,
        weakness_until_tick=weakness,
    )


@dataclasses.dataclass
class ReraiseState:
    """Pre-cast Reraise hanging on the player."""
    tier: RaiseTier = RaiseTier.NONE
    expires_at_tick: int = 0

    def is_active(self, *, now_tick: int) -> bool:
        return (
            self.tier != RaiseTier.NONE
            and now_tick < self.expires_at_tick
        )

    def consume_on_death(
        self, *, now_tick: int, target_max_hp: int,
        target_max_mp: int, exp_lost_on_death: int,
    ) -> RaiseResult:
        if not self.is_active(now_tick=now_tick):
            return RaiseResult(
                False, reason="no active Reraise",
            )
        result = apply_raise(
            inputs=RaiseInputs(
                target_max_hp=target_max_hp,
                target_max_mp=target_max_mp,
                exp_lost_on_death=exp_lost_on_death,
                tier=self.tier,
                source=RaiseSource.RERAISE,
            ),
            now_tick=now_tick,
        )
        # Consume the reraise
        self.tier = RaiseTier.NONE
        self.expires_at_tick = 0
        return result


def cast_reraise(
    *, tier: RaiseTier, duration_seconds: int = 60 * 60,
    now_tick: int,
) -> ReraiseState:
    """Apply a Reraise tier with default 1 hour persistence."""
    return ReraiseState(
        tier=tier,
        expires_at_tick=now_tick + duration_seconds,
    )


__all__ = [
    "RaiseTier", "RaiseSource",
    "WEAKNESS_DURATION_SECONDS",
    "RaiseSpec", "RAISE_SPECS",
    "RaiseInputs", "RaiseResult",
    "apply_raise", "ReraiseState", "cast_reraise",
]
