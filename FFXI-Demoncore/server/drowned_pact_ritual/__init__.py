"""Drowned pact ritual — formally accept the cult; gain dark abilities.

After kraken_cult_recruitment reaches PLEDGED stage, the
player can perform the DROWNED PACT RITUAL at a SUNKEN_CROWN
flagship. The ritual is a 3-step ceremony that pushes
corruption to the HOLLOWED threshold and grants three dark
abilities the player keeps for life (or until cult_redemption
strips them).

Ritual steps:
  IMMERSION   - the player descends into the trench
  CONFESSION  - the player declares allegiance
  DROWNING    - the player accepts a brief simulated drowning;
                emerges with the dark abilities

Dark abilities granted:
  ABYSS_BREATH    - permanent +50% breath efficiency
                    underwater (stacks with abyss_pressure_gear)
  KRAKEN_HUNGER   - melee hits gain HP-leech vs surface
                    factions (PvE)
  TIDAL_STRIDE    - bypass tide_cycle_clock zone access gates

Per-player: ritual is one-time. Once PERFORMED you are
HOLLOWED and locked to the cult faction (per corruption_taint).
The ritual can be ABORTED before DROWNING — corruption
adjusts back down (15 corruption refunded).

Public surface
--------------
    RitualStage / DarkAbility enums
    RitualState dataclass
    DrownedPactRitual
        .begin(player_id, has_pledge, now_seconds)
        .advance(player_id, now_seconds)
        .abort(player_id, now_seconds)
        .has_ability(player_id, ability)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RitualStage(str, enum.Enum):
    NOT_STARTED = "not_started"
    IMMERSION = "immersion"
    CONFESSION = "confession"
    DROWNING = "drowning"
    PERFORMED = "performed"
    ABORTED = "aborted"


class DarkAbility(str, enum.Enum):
    ABYSS_BREATH = "abyss_breath"
    KRAKEN_HUNGER = "kraken_hunger"
    TIDAL_STRIDE = "tidal_stride"


_NEXT_STAGE: dict[RitualStage, RitualStage] = {
    RitualStage.IMMERSION: RitualStage.CONFESSION,
    RitualStage.CONFESSION: RitualStage.DROWNING,
    RitualStage.DROWNING: RitualStage.PERFORMED,
}

# corruption gained on each step
_CORRUPTION_PER_STEP = {
    RitualStage.IMMERSION: 0,    # sunk-cost, no taint yet
    RitualStage.CONFESSION: 5,
    RitualStage.DROWNING: 10,
}

ABORT_CORRUPTION_REFUND = 15


@dataclasses.dataclass
class RitualState:
    player_id: str
    stage: RitualStage = RitualStage.NOT_STARTED
    started_at: int = 0
    last_advanced_at: int = 0
    abilities: tuple[DarkAbility, ...] = ()


@dataclasses.dataclass(frozen=True)
class RitualResult:
    accepted: bool
    new_stage: t.Optional[RitualStage] = None
    corruption_gained: int = 0
    corruption_refund: int = 0
    abilities_granted: tuple[DarkAbility, ...] = ()
    reason: t.Optional[str] = None


@dataclasses.dataclass
class DrownedPactRitual:
    _states: dict[str, RitualState] = dataclasses.field(default_factory=dict)

    def state(self, *, player_id: str) -> t.Optional[RitualState]:
        return self._states.get(player_id)

    def begin(
        self, *, player_id: str,
        has_pledge: bool,
        now_seconds: int,
    ) -> RitualResult:
        if not player_id:
            return RitualResult(False, reason="bad player")
        if not has_pledge:
            return RitualResult(False, reason="no pledge")
        existing = self._states.get(player_id)
        if existing is not None and existing.stage in (
            RitualStage.IMMERSION, RitualStage.CONFESSION,
            RitualStage.DROWNING,
        ):
            return RitualResult(False, reason="ritual in progress")
        if existing is not None and existing.stage == RitualStage.PERFORMED:
            return RitualResult(False, reason="already performed")
        self._states[player_id] = RitualState(
            player_id=player_id,
            stage=RitualStage.IMMERSION,
            started_at=now_seconds,
            last_advanced_at=now_seconds,
        )
        return RitualResult(
            accepted=True, new_stage=RitualStage.IMMERSION,
            corruption_gained=_CORRUPTION_PER_STEP[
                RitualStage.IMMERSION
            ],
        )

    def advance(
        self, *, player_id: str, now_seconds: int,
    ) -> RitualResult:
        rec = self._states.get(player_id)
        if rec is None or rec.stage not in _NEXT_STAGE:
            return RitualResult(False, reason="cannot advance")
        next_stage = _NEXT_STAGE[rec.stage]
        rec.stage = next_stage
        rec.last_advanced_at = now_seconds
        granted: tuple[DarkAbility, ...] = ()
        if next_stage == RitualStage.PERFORMED:
            granted = (
                DarkAbility.ABYSS_BREATH,
                DarkAbility.KRAKEN_HUNGER,
                DarkAbility.TIDAL_STRIDE,
            )
            rec.abilities = granted
        # corruption gained corresponds to the stage we JUST left
        # (the work that produced the advance)
        prev_stage = next(
            (s for s, n in _NEXT_STAGE.items() if n == next_stage),
            None,
        )
        gain = _CORRUPTION_PER_STEP.get(prev_stage, 0) if prev_stage else 0
        return RitualResult(
            accepted=True,
            new_stage=next_stage,
            corruption_gained=gain,
            abilities_granted=granted,
        )

    def abort(
        self, *, player_id: str, now_seconds: int,
    ) -> RitualResult:
        rec = self._states.get(player_id)
        if rec is None:
            return RitualResult(False, reason="no ritual")
        if rec.stage in (
            RitualStage.NOT_STARTED, RitualStage.PERFORMED,
            RitualStage.ABORTED,
        ):
            return RitualResult(False, reason="cannot abort")
        if rec.stage == RitualStage.DROWNING:
            return RitualResult(
                False, reason="too late to abort",
            )
        rec.stage = RitualStage.ABORTED
        return RitualResult(
            accepted=True,
            new_stage=RitualStage.ABORTED,
            corruption_refund=ABORT_CORRUPTION_REFUND,
        )

    def has_ability(
        self, *, player_id: str, ability: DarkAbility,
    ) -> bool:
        rec = self._states.get(player_id)
        if rec is None:
            return False
        return ability in rec.abilities


__all__ = [
    "RitualStage", "DarkAbility",
    "RitualState", "RitualResult",
    "DrownedPactRitual",
    "ABORT_CORRUPTION_REFUND",
]
