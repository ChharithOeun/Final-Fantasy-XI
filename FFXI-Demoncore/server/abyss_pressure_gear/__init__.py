"""Abyss pressure gear — wearable gear that mitigates pressure.

The underwater_swim system stacks pressure tiers as depth
increases. Without help, even ABYSS_PERMIT divers take
constant pressure damage past 350 yalms. ABYSS PRESSURE GEAR
reduces that ramp by SUITING the diver against ambient
pressure. We track a per-player EQUIPPED set; the system
publishes a NEGATE TIER count and a BREATH EFFICIENCY
multiplier that callers fold into underwater_swim.

Gear pieces:
  PRESSURE_HOOD     - head; -1 pressure tier
  ABYSS_VEST        - body; -1 pressure tier, +25% breath
  CRUSHING_GREAVES  - legs; -1 pressure tier
  GILL_ENGINE       - back; +50% breath efficiency
  HOLLOW_BAND       - ring; -1 pressure tier (kraken-loot
                      crafted from kraken_ink_market)

Stacking rules:
  pressure_tiers_negated caps at 4 (one per slot HOOD/VEST/
  GREAVES/RING).
  breath_efficiency multipliers ADD (not multiply).
  GILL_ENGINE alone doesn't negate any tier; ABYSS_VEST does
  but also stacks 25% breath.

Public surface
--------------
    GearSlot enum
    GearPiece enum
    GearProfile dataclass
    AbyssPressureGear
        .equip(player_id, piece)
        .unequip(player_id, piece)
        .pressure_tiers_negated(player_id)
        .breath_efficiency_multiplier(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GearSlot(str, enum.Enum):
    HEAD = "head"
    BODY = "body"
    LEGS = "legs"
    BACK = "back"
    RING = "ring"


class GearPiece(str, enum.Enum):
    PRESSURE_HOOD = "pressure_hood"
    ABYSS_VEST = "abyss_vest"
    CRUSHING_GREAVES = "crushing_greaves"
    GILL_ENGINE = "gill_engine"
    HOLLOW_BAND = "hollow_band"


@dataclasses.dataclass(frozen=True)
class GearProfile:
    piece: GearPiece
    slot: GearSlot
    pressure_tiers: int       # how many tiers this piece negates
    breath_bonus_pct: int     # additive % breath efficiency


_PROFILES: dict[GearPiece, GearProfile] = {
    GearPiece.PRESSURE_HOOD: GearProfile(
        piece=GearPiece.PRESSURE_HOOD, slot=GearSlot.HEAD,
        pressure_tiers=1, breath_bonus_pct=0,
    ),
    GearPiece.ABYSS_VEST: GearProfile(
        piece=GearPiece.ABYSS_VEST, slot=GearSlot.BODY,
        pressure_tiers=1, breath_bonus_pct=25,
    ),
    GearPiece.CRUSHING_GREAVES: GearProfile(
        piece=GearPiece.CRUSHING_GREAVES, slot=GearSlot.LEGS,
        pressure_tiers=1, breath_bonus_pct=0,
    ),
    GearPiece.GILL_ENGINE: GearProfile(
        piece=GearPiece.GILL_ENGINE, slot=GearSlot.BACK,
        pressure_tiers=0, breath_bonus_pct=50,
    ),
    GearPiece.HOLLOW_BAND: GearProfile(
        piece=GearPiece.HOLLOW_BAND, slot=GearSlot.RING,
        pressure_tiers=1, breath_bonus_pct=0,
    ),
}

_MAX_PRESSURE_NEGATE = 4


@dataclasses.dataclass(frozen=True)
class EquipResult:
    accepted: bool
    piece: t.Optional[GearPiece] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class AbyssPressureGear:
    # player -> slot -> equipped piece
    _equipped: dict[str, dict[GearSlot, GearPiece]] = dataclasses.field(
        default_factory=dict,
    )

    def equip(
        self, *, player_id: str, piece: GearPiece,
    ) -> EquipResult:
        if not player_id:
            return EquipResult(False, reason="bad player")
        prof = _PROFILES.get(piece)
        if prof is None:
            return EquipResult(False, reason="unknown piece")
        slot_map = self._equipped.setdefault(player_id, {})
        # any existing piece in same slot is replaced
        slot_map[prof.slot] = piece
        return EquipResult(True, piece=piece)

    def unequip(
        self, *, player_id: str, piece: GearPiece,
    ) -> EquipResult:
        prof = _PROFILES.get(piece)
        if prof is None:
            return EquipResult(False, reason="unknown piece")
        slot_map = self._equipped.get(player_id)
        if slot_map is None or slot_map.get(prof.slot) != piece:
            return EquipResult(False, reason="not equipped")
        del slot_map[prof.slot]
        return EquipResult(True, piece=piece)

    def equipped_pieces(
        self, *, player_id: str,
    ) -> tuple[GearPiece, ...]:
        slot_map = self._equipped.get(player_id, {})
        return tuple(slot_map.values())

    def pressure_tiers_negated(
        self, *, player_id: str,
    ) -> int:
        total = 0
        for piece in self.equipped_pieces(player_id=player_id):
            total += _PROFILES[piece].pressure_tiers
        return min(total, _MAX_PRESSURE_NEGATE)

    def breath_efficiency_multiplier(
        self, *, player_id: str,
    ) -> float:
        # base 1.0 + sum(bonus%/100) per equipped piece
        bonus_pct = 0
        for piece in self.equipped_pieces(player_id=player_id):
            bonus_pct += _PROFILES[piece].breath_bonus_pct
        return 1.0 + bonus_pct / 100.0


__all__ = [
    "GearSlot", "GearPiece", "GearProfile",
    "EquipResult", "AbyssPressureGear",
]
