"""Beastman fishing — beastman-side tide fishing system.

The beastman analog to FFXI fishing. Each FISHING SPOT is tied
to a beastman zone, accepts certain RODS + BAITS, and rolls
catches from a CATCH TABLE weighted by base_chance and gated by
fishing_skill_required.

Skill grows with successful catches (capped at 100), with
diminishing gain past skill 70 (+1 every 3 catches instead of
every catch).

Public surface
--------------
    RodKind enum     STONE_ROD / BONE_ROD / CORAL_ROD /
                     FEATHER_ROD
    BaitKind enum    KELP / GRUB / FISH_GUTS / SHADOW_LURE
    Catch dataclass
    FishingSpot dataclass
    BeastmanFishing
        .register_spot(spot_id, zone_id, rods, baits, catches)
        .cast(player_id, spot_id, rod, bait, roll_pct)
        .skill_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RodKind(str, enum.Enum):
    STONE_ROD = "stone_rod"
    BONE_ROD = "bone_rod"
    CORAL_ROD = "coral_rod"
    FEATHER_ROD = "feather_rod"


class BaitKind(str, enum.Enum):
    KELP = "kelp"
    GRUB = "grub"
    FISH_GUTS = "fish_guts"
    SHADOW_LURE = "shadow_lure"


@dataclasses.dataclass(frozen=True)
class Catch:
    item_id: str
    base_chance_pct: int           # 0..100
    skill_required: int = 0


@dataclasses.dataclass(frozen=True)
class FishingSpot:
    spot_id: str
    zone_id: str
    rods: tuple[RodKind, ...]
    baits: tuple[BaitKind, ...]
    catches: tuple[Catch, ...]


@dataclasses.dataclass(frozen=True)
class CastResult:
    accepted: bool
    spot_id: str
    item_id: str = ""
    new_skill: int = 0
    reason: t.Optional[str] = None


_SKILL_CAP = 100
_SKILL_DIMINISH_THRESHOLD = 70


@dataclasses.dataclass
class BeastmanFishing:
    _spots: dict[str, FishingSpot] = dataclasses.field(
        default_factory=dict,
    )
    _skill: dict[str, int] = dataclasses.field(default_factory=dict)
    _catches_since_gain: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def register_spot(
        self, *, spot_id: str,
        zone_id: str,
        rods: tuple[RodKind, ...],
        baits: tuple[BaitKind, ...],
        catches: tuple[Catch, ...],
    ) -> t.Optional[FishingSpot]:
        if spot_id in self._spots:
            return None
        if not zone_id:
            return None
        if not rods or not baits or not catches:
            return None
        for c in catches:
            if not (0 <= c.base_chance_pct <= 100):
                return None
            if c.skill_required < 0:
                return None
        s = FishingSpot(
            spot_id=spot_id, zone_id=zone_id,
            rods=tuple(rods),
            baits=tuple(baits),
            catches=tuple(catches),
        )
        self._spots[spot_id] = s
        return s

    def cast(
        self, *, player_id: str,
        spot_id: str,
        rod: RodKind, bait: BaitKind,
        roll_pct: int,
    ) -> CastResult:
        s = self._spots.get(spot_id)
        if s is None:
            return CastResult(
                False, spot_id, reason="unknown spot",
            )
        if rod not in s.rods:
            return CastResult(
                False, spot_id, reason="rod not allowed here",
            )
        if bait not in s.baits:
            return CastResult(
                False, spot_id, reason="bait not allowed here",
            )
        if not (0 <= roll_pct <= 100):
            return CastResult(
                False, spot_id, reason="invalid roll",
            )
        skill = self._skill.get(player_id, 0)
        # Walk catches; first one whose skill_required is met AND
        # whose roll_pct < base_chance_pct wins
        for c in s.catches:
            if skill < c.skill_required:
                continue
            if roll_pct < c.base_chance_pct:
                new_skill = self._gain_skill(player_id, skill)
                return CastResult(
                    accepted=True, spot_id=spot_id,
                    item_id=c.item_id,
                    new_skill=new_skill,
                )
        # No catch this cast — skill unchanged
        return CastResult(
            accepted=True, spot_id=spot_id,
            item_id="", new_skill=skill,
        )

    def _gain_skill(self, player_id: str, current: int) -> int:
        if current >= _SKILL_CAP:
            return _SKILL_CAP
        if current < _SKILL_DIMINISH_THRESHOLD:
            new = current + 1
        else:
            cnt = self._catches_since_gain.get(player_id, 0) + 1
            if cnt >= 3:
                new = current + 1
                cnt = 0
            else:
                new = current
            self._catches_since_gain[player_id] = cnt
        new = min(_SKILL_CAP, new)
        self._skill[player_id] = new
        return new

    def skill_for(self, *, player_id: str) -> int:
        return self._skill.get(player_id, 0)

    def total_spots(self) -> int:
        return len(self._spots)


__all__ = [
    "RodKind", "BaitKind",
    "Catch", "FishingSpot", "CastResult",
    "BeastmanFishing",
]
