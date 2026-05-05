"""Underwater swim — 3-axis movement + breath meter + depth pressure.

Player swimming has three coupled gauges:

  BREATH (0..max_seconds)  - depletes while submerged below the
                              surface; any AIR_REFILL action while
                              at the surface refills to max.
  DEPTH (yalms)            - the current vertical Y-axis offset
                              below sea level. Used to compute
                              pressure damage.
  STAMINA (0..100)         - cost-gated movement reservoir;
                              regenerates while floating still.

Pressure damage starts at DEPTH > 50 yalms and ramps every 25
yalms. Special chocobos (light blue) and gear with the
PRESSURE_NEGATING property suppress pressure damage entirely.

Public surface
--------------
    SwimState dataclass
    PressureTier enum
    UnderwaterSwim
        .enter_water(player_id, max_breath_seconds, now_seconds)
        .descend(player_id, yalms_down, stamina_cost, now_seconds)
        .ascend(player_id, yalms_up, stamina_cost, now_seconds)
        .breath_tick(player_id, now_seconds)
        .surface(player_id, now_seconds)
        .equip_pressure_negator(player_id, equipped)
        .state_for(player_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_SURFACE_DEPTH = 0
_PRESSURE_FLOOR_YALMS = 50
_PRESSURE_RAMP_YALMS = 25
_PRESSURE_TICK_DAMAGE_PER_TIER = 25
_STAMINA_MAX = 100
_STAMINA_REGEN_PER_SEC = 1


class PressureTier(str, enum.Enum):
    SAFE = "safe"
    LIGHT = "light"
    HEAVY = "heavy"
    CRUSHING = "crushing"


@dataclasses.dataclass
class _SwimRecord:
    max_breath_seconds: int
    breath_seconds: int
    depth_yalms: int = 0
    stamina: int = _STAMINA_MAX
    last_tick_seconds: int = 0
    pressure_negator: bool = False
    submerged: bool = False


@dataclasses.dataclass(frozen=True)
class EnterResult:
    accepted: bool
    breath_seconds: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class MoveResult:
    accepted: bool
    depth_yalms: int = 0
    breath_seconds: int = 0
    stamina_after: int = 0
    pressure_tier: PressureTier = PressureTier.SAFE
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class TickResult:
    accepted: bool
    breath_seconds: int = 0
    pressure_damage_dealt: int = 0
    drowning: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class SwimSnapshot:
    submerged: bool
    breath_seconds: int
    max_breath_seconds: int
    depth_yalms: int
    stamina: int
    pressure_tier: PressureTier


def _pressure_tier(
    depth: int, negator: bool,
) -> PressureTier:
    if negator:
        return PressureTier.SAFE
    if depth <= _PRESSURE_FLOOR_YALMS:
        return PressureTier.SAFE
    over = depth - _PRESSURE_FLOOR_YALMS
    if over <= 0:
        return PressureTier.SAFE
    # Ceiling division so any depth past the floor enters LIGHT
    # immediately, with HEAVY/CRUSHING accruing as the player
    # descends further.
    steps = (over + _PRESSURE_RAMP_YALMS - 1) // _PRESSURE_RAMP_YALMS
    if steps == 1:
        return PressureTier.LIGHT
    if steps == 2:
        return PressureTier.HEAVY
    return PressureTier.CRUSHING


@dataclasses.dataclass
class UnderwaterSwim:
    _records: dict[str, _SwimRecord] = dataclasses.field(
        default_factory=dict,
    )

    def enter_water(
        self, *, player_id: str,
        max_breath_seconds: int,
        now_seconds: int,
    ) -> EnterResult:
        if max_breath_seconds <= 0:
            return EnterResult(False, reason="invalid breath")
        rec = self._records.get(player_id)
        if rec is None:
            rec = _SwimRecord(
                max_breath_seconds=max_breath_seconds,
                breath_seconds=max_breath_seconds,
                last_tick_seconds=now_seconds,
            )
            self._records[player_id] = rec
        else:
            rec.max_breath_seconds = max_breath_seconds
            rec.breath_seconds = max_breath_seconds
            rec.depth_yalms = 0
            rec.stamina = _STAMINA_MAX
            rec.last_tick_seconds = now_seconds
            rec.submerged = False
        return EnterResult(
            accepted=True,
            breath_seconds=rec.breath_seconds,
        )

    def descend(
        self, *, player_id: str,
        yalms_down: int,
        stamina_cost: int,
        now_seconds: int,
    ) -> MoveResult:
        rec = self._records.get(player_id)
        if rec is None:
            return MoveResult(False, reason="not in water")
        if yalms_down <= 0 or stamina_cost < 0:
            return MoveResult(False, reason="invalid move")
        if rec.stamina < stamina_cost:
            return MoveResult(
                False, depth_yalms=rec.depth_yalms,
                stamina_after=rec.stamina,
                reason="insufficient stamina",
            )
        rec.depth_yalms += yalms_down
        rec.stamina -= stamina_cost
        rec.submerged = rec.depth_yalms > _SURFACE_DEPTH
        return MoveResult(
            accepted=True,
            depth_yalms=rec.depth_yalms,
            breath_seconds=rec.breath_seconds,
            stamina_after=rec.stamina,
            pressure_tier=_pressure_tier(
                rec.depth_yalms, rec.pressure_negator,
            ),
        )

    def ascend(
        self, *, player_id: str,
        yalms_up: int,
        stamina_cost: int,
        now_seconds: int,
    ) -> MoveResult:
        rec = self._records.get(player_id)
        if rec is None:
            return MoveResult(False, reason="not in water")
        if yalms_up <= 0 or stamina_cost < 0:
            return MoveResult(False, reason="invalid move")
        if rec.stamina < stamina_cost:
            return MoveResult(
                False, depth_yalms=rec.depth_yalms,
                stamina_after=rec.stamina,
                reason="insufficient stamina",
            )
        rec.depth_yalms = max(0, rec.depth_yalms - yalms_up)
        rec.stamina -= stamina_cost
        rec.submerged = rec.depth_yalms > _SURFACE_DEPTH
        return MoveResult(
            accepted=True,
            depth_yalms=rec.depth_yalms,
            breath_seconds=rec.breath_seconds,
            stamina_after=rec.stamina,
            pressure_tier=_pressure_tier(
                rec.depth_yalms, rec.pressure_negator,
            ),
        )

    def breath_tick(
        self, *, player_id: str, now_seconds: int,
    ) -> TickResult:
        rec = self._records.get(player_id)
        if rec is None:
            return TickResult(False, reason="not in water")
        elapsed = max(0, now_seconds - rec.last_tick_seconds)
        rec.last_tick_seconds = now_seconds
        # Stamina regenerates at the surface and at-rest below
        rec.stamina = min(
            _STAMINA_MAX,
            rec.stamina + elapsed * _STAMINA_REGEN_PER_SEC,
        )
        # Breath drain only while submerged
        if rec.submerged:
            rec.breath_seconds = max(0, rec.breath_seconds - elapsed)
        else:
            rec.breath_seconds = rec.max_breath_seconds
        # Pressure damage = tier_count * elapsed * 25
        tier = _pressure_tier(
            rec.depth_yalms, rec.pressure_negator,
        )
        tier_count = {
            PressureTier.SAFE: 0,
            PressureTier.LIGHT: 1,
            PressureTier.HEAVY: 2,
            PressureTier.CRUSHING: 3,
        }[tier]
        damage = tier_count * elapsed * _PRESSURE_TICK_DAMAGE_PER_TIER
        drowning = (
            rec.submerged and rec.breath_seconds <= 0
        )
        return TickResult(
            accepted=True,
            breath_seconds=rec.breath_seconds,
            pressure_damage_dealt=damage,
            drowning=drowning,
        )

    def surface(
        self, *, player_id: str, now_seconds: int,
    ) -> bool:
        rec = self._records.get(player_id)
        if rec is None:
            return False
        rec.depth_yalms = 0
        rec.submerged = False
        rec.breath_seconds = rec.max_breath_seconds
        rec.last_tick_seconds = now_seconds
        return True

    def equip_pressure_negator(
        self, *, player_id: str, equipped: bool,
    ) -> bool:
        rec = self._records.get(player_id)
        if rec is None:
            return False
        rec.pressure_negator = equipped
        return True

    def state_for(
        self, *, player_id: str, now_seconds: int,
    ) -> t.Optional[SwimSnapshot]:
        rec = self._records.get(player_id)
        if rec is None:
            return None
        return SwimSnapshot(
            submerged=rec.submerged,
            breath_seconds=rec.breath_seconds,
            max_breath_seconds=rec.max_breath_seconds,
            depth_yalms=rec.depth_yalms,
            stamina=rec.stamina,
            pressure_tier=_pressure_tier(
                rec.depth_yalms, rec.pressure_negator,
            ),
        )

    def total_swimmers(self) -> int:
        return len(self._records)


__all__ = [
    "PressureTier",
    "EnterResult", "MoveResult", "TickResult", "SwimSnapshot",
    "UnderwaterSwim",
]
