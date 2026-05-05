"""Corruption taint — 0..100 corruption track with stat effects.

Players can accumulate CORRUPTION TAINT through cult
recruitment steps, abyssal fragment overuse, drinking
kraken ink, etc. Taint is bounded [0, 100] and bands into
4 levels with progressive effects (positive AND negative).

Bands:
  CLEAN      0..9     - no effect
  TINGED    10..29    - small dark damage bonus, -5% surface NPC trust
  SICKENED  30..59    - +10% dark/abyss damage, -15% surface NPC trust,
                        +1 pressure tier negate (skin grows tougher)
  ABYSSAL   60..99    - +25% dark/abyss damage, -50% surface NPC trust,
                        +2 pressure tier negate, surface healer refusals
  HOLLOWED 100        - terminal: locks the player into cult faction
                        permanently (only redemption_quest can rewind)

Decay/cleansing:
  Taint does NOT decay naturally. It only goes down via:
    - cult_redemption_quest milestones
    - SILMARIL_SIRENHALL purification rite (-1 per visit, 24h CD)
  We don't implement those here — we just publish add() and
  cleanse() so callers can drive taint up or down.

Public surface
--------------
    TaintBand enum
    TaintEffects dataclass
    CorruptionTaint
        .add(player_id, amount, source)
        .cleanse(player_id, amount, source)
        .level(player_id) -> int
        .band(player_id) -> TaintBand
        .effects(player_id) -> TaintEffects
        .is_hollowed(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TaintBand(str, enum.Enum):
    CLEAN = "clean"
    TINGED = "tinged"
    SICKENED = "sickened"
    ABYSSAL = "abyssal"
    HOLLOWED = "hollowed"


@dataclasses.dataclass(frozen=True)
class TaintEffects:
    band: TaintBand
    dark_damage_bonus_pct: int
    surface_npc_trust_delta_pct: int
    pressure_tiers_negated_bonus: int
    surface_healers_refuse: bool
    locked_to_cult: bool


_BAND_EFFECTS: dict[TaintBand, TaintEffects] = {
    TaintBand.CLEAN: TaintEffects(
        band=TaintBand.CLEAN,
        dark_damage_bonus_pct=0,
        surface_npc_trust_delta_pct=0,
        pressure_tiers_negated_bonus=0,
        surface_healers_refuse=False,
        locked_to_cult=False,
    ),
    TaintBand.TINGED: TaintEffects(
        band=TaintBand.TINGED,
        dark_damage_bonus_pct=3,
        surface_npc_trust_delta_pct=-5,
        pressure_tiers_negated_bonus=0,
        surface_healers_refuse=False,
        locked_to_cult=False,
    ),
    TaintBand.SICKENED: TaintEffects(
        band=TaintBand.SICKENED,
        dark_damage_bonus_pct=10,
        surface_npc_trust_delta_pct=-15,
        pressure_tiers_negated_bonus=1,
        surface_healers_refuse=False,
        locked_to_cult=False,
    ),
    TaintBand.ABYSSAL: TaintEffects(
        band=TaintBand.ABYSSAL,
        dark_damage_bonus_pct=25,
        surface_npc_trust_delta_pct=-50,
        pressure_tiers_negated_bonus=2,
        surface_healers_refuse=True,
        locked_to_cult=False,
    ),
    TaintBand.HOLLOWED: TaintEffects(
        band=TaintBand.HOLLOWED,
        dark_damage_bonus_pct=40,
        surface_npc_trust_delta_pct=-100,
        pressure_tiers_negated_bonus=3,
        surface_healers_refuse=True,
        locked_to_cult=True,
    ),
}


@dataclasses.dataclass(frozen=True)
class TaintChange:
    accepted: bool
    new_level: int = 0
    new_band: t.Optional[TaintBand] = None
    delta_applied: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class CorruptionTaint:
    _levels: dict[str, int] = dataclasses.field(default_factory=dict)

    @staticmethod
    def _band_for(level: int) -> TaintBand:
        if level >= 100:
            return TaintBand.HOLLOWED
        if level >= 60:
            return TaintBand.ABYSSAL
        if level >= 30:
            return TaintBand.SICKENED
        if level >= 10:
            return TaintBand.TINGED
        return TaintBand.CLEAN

    def level(self, *, player_id: str) -> int:
        return self._levels.get(player_id, 0)

    def band(self, *, player_id: str) -> TaintBand:
        return self._band_for(self.level(player_id=player_id))

    def effects(self, *, player_id: str) -> TaintEffects:
        return _BAND_EFFECTS[self.band(player_id=player_id)]

    def is_hollowed(self, *, player_id: str) -> bool:
        return self.level(player_id=player_id) >= 100

    def add(
        self, *, player_id: str,
        amount: int,
        source: str,
    ) -> TaintChange:
        if not player_id or not source:
            return TaintChange(False, reason="bad ids")
        if amount <= 0:
            return TaintChange(False, reason="bad amount")
        # once HOLLOWED you cannot accumulate further
        current = self._levels.get(player_id, 0)
        if current >= 100:
            return TaintChange(
                False, new_level=100,
                new_band=TaintBand.HOLLOWED,
                reason="already hollowed",
            )
        new = min(100, current + amount)
        delta = new - current
        self._levels[player_id] = new
        return TaintChange(
            accepted=True,
            new_level=new,
            new_band=self._band_for(new),
            delta_applied=delta,
        )

    def cleanse(
        self, *, player_id: str,
        amount: int,
        source: str,
    ) -> TaintChange:
        if not player_id or not source:
            return TaintChange(False, reason="bad ids")
        if amount <= 0:
            return TaintChange(False, reason="bad amount")
        current = self._levels.get(player_id, 0)
        # HOLLOWED can ONLY be cleansed by source="cult_redemption_quest"
        if current >= 100 and source != "cult_redemption_quest":
            return TaintChange(
                False, new_level=100,
                new_band=TaintBand.HOLLOWED,
                reason="hollowed lock; redemption only",
            )
        new = max(0, current - amount)
        delta = new - current   # negative
        self._levels[player_id] = new
        return TaintChange(
            accepted=True,
            new_level=new,
            new_band=self._band_for(new),
            delta_applied=delta,
        )


__all__ = [
    "TaintBand", "TaintEffects",
    "TaintChange", "CorruptionTaint",
]
