"""Debris field — broken features stay as physical obstacles.

When a feature breaks, it doesn't vanish. The chunks
hit the floor and become a DEBRIS PILE — a scattered
field of physical material on the band the player must
fight around. Debris piles affect:

    line_of_sight   — pile blocks LOS for ranged
                      attacks crossing the band sector
    cover           — players adjacent to the pile get
                      a flat damage reduction vs ranged
                      from the opposite sector
    movement        — moving across the pile costs
                      additional yalms
    secondary_hazard— some debris is hot/wet/sharp and
                      ticks small damage on standing in
                      it (LAVA_DEBRIS, BROKEN_GLASS,
                      BURNING_TIMBER)

Debris kinds derive from the broken feature's kind:
    WALL → STONE_RUBBLE   (cover, no hazard)
    FLOOR → SPLINTERED_PLANKS (cover + minor sharp dot)
    CEILING → BURNING_TIMBER  (cover + fire dot)
    ICE_SHEET → ICE_SHARDS    (cover + cold dot)
    PILLAR → STONE_RUBBLE     (cover, big movement penalty)
    BRIDGE → SPLINTERED_PLANKS
    DAM → SOAKED_RUBBLE       (no hazard but adjacent
                               players soaked → +cold,
                               -lightning resist)
    SHIP_HULL → SPLINTERED_PLANKS

Public surface
--------------
    DebrisKind enum
    DebrisPile dataclass (frozen)
    DebrisField
        .on_feature_break(arena_id, feature_id,
                          feature_kind, band) -> DebrisPile
        .piles_for(arena_id, band) -> tuple[DebrisPile, ...]
        .blocks_los(arena_id, from_band, to_band) -> bool
        .cover_dr_for(arena_id, player_band) -> int
        .movement_cost_yalms(arena_id, band) -> int
        .tick_hazards(arena_id, players_in_band, dt_seconds)
            -> tuple[HazardTick, ...]
        .clear_arena(arena_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.arena_environment import FeatureKind


class DebrisKind(str, enum.Enum):
    STONE_RUBBLE = "stone_rubble"
    SPLINTERED_PLANKS = "splintered_planks"
    BURNING_TIMBER = "burning_timber"
    ICE_SHARDS = "ice_shards"
    SOAKED_RUBBLE = "soaked_rubble"


# Per-kind effects
@dataclasses.dataclass(frozen=True)
class _DebrisProfile:
    cover_dr_pct: int
    movement_cost_yalms: int
    blocks_los: bool
    hazard_dps: int
    hazard_status_id: t.Optional[str] = None


_PROFILES: dict[DebrisKind, _DebrisProfile] = {
    DebrisKind.STONE_RUBBLE: _DebrisProfile(
        cover_dr_pct=25, movement_cost_yalms=4,
        blocks_los=True, hazard_dps=0,
    ),
    DebrisKind.SPLINTERED_PLANKS: _DebrisProfile(
        cover_dr_pct=15, movement_cost_yalms=2,
        blocks_los=False, hazard_dps=20,
        hazard_status_id="bleed",
    ),
    DebrisKind.BURNING_TIMBER: _DebrisProfile(
        cover_dr_pct=10, movement_cost_yalms=2,
        blocks_los=False, hazard_dps=80,
        hazard_status_id="burn",
    ),
    DebrisKind.ICE_SHARDS: _DebrisProfile(
        cover_dr_pct=10, movement_cost_yalms=2,
        blocks_los=False, hazard_dps=40,
        hazard_status_id="freeze",
    ),
    DebrisKind.SOAKED_RUBBLE: _DebrisProfile(
        cover_dr_pct=20, movement_cost_yalms=4,
        blocks_los=True, hazard_dps=0,
        hazard_status_id="soaked",
    ),
}


_FEATURE_TO_DEBRIS: dict[FeatureKind, DebrisKind] = {
    FeatureKind.WALL: DebrisKind.STONE_RUBBLE,
    FeatureKind.FLOOR: DebrisKind.SPLINTERED_PLANKS,
    FeatureKind.CEILING: DebrisKind.BURNING_TIMBER,
    FeatureKind.ICE_SHEET: DebrisKind.ICE_SHARDS,
    FeatureKind.PILLAR: DebrisKind.STONE_RUBBLE,
    FeatureKind.BRIDGE: DebrisKind.SPLINTERED_PLANKS,
    FeatureKind.DAM: DebrisKind.SOAKED_RUBBLE,
    FeatureKind.SHIP_HULL: DebrisKind.SPLINTERED_PLANKS,
}


@dataclasses.dataclass(frozen=True)
class DebrisPile:
    feature_id: str
    kind: DebrisKind
    band: int


@dataclasses.dataclass(frozen=True)
class HazardTick:
    player_id: str
    debris_kind: DebrisKind
    damage: int
    status_id: t.Optional[str]


@dataclasses.dataclass
class DebrisField:
    # arena_id -> band -> list[DebrisPile]
    _piles: dict[str, dict[int, list[DebrisPile]]] = dataclasses.field(
        default_factory=dict,
    )

    def on_feature_break(
        self, *, arena_id: str, feature_id: str,
        feature_kind: FeatureKind, band: int,
    ) -> t.Optional[DebrisPile]:
        kind = _FEATURE_TO_DEBRIS.get(feature_kind)
        if kind is None:
            return None
        pile = DebrisPile(
            feature_id=feature_id, kind=kind, band=band,
        )
        bands = self._piles.setdefault(arena_id, {})
        bands.setdefault(band, []).append(pile)
        return pile

    def piles_for(
        self, *, arena_id: str, band: int,
    ) -> tuple[DebrisPile, ...]:
        return tuple(self._piles.get(arena_id, {}).get(band, []))

    def all_piles(
        self, *, arena_id: str,
    ) -> tuple[DebrisPile, ...]:
        out: list[DebrisPile] = []
        for piles in self._piles.get(arena_id, {}).values():
            out.extend(piles)
        return tuple(out)

    def blocks_los(
        self, *, arena_id: str, from_band: int, to_band: int,
    ) -> bool:
        # If any pile sits between the bands inclusive of either
        # end, and that pile blocks LOS, line is broken.
        if from_band == to_band:
            # in same band — any LOS-blocking pile in this band blocks
            for p in self._piles.get(arena_id, {}).get(from_band, []):
                if _PROFILES[p.kind].blocks_los:
                    return True
            return False
        lo = min(from_band, to_band)
        hi = max(from_band, to_band)
        for b in range(lo, hi + 1):
            for p in self._piles.get(arena_id, {}).get(b, []):
                if _PROFILES[p.kind].blocks_los:
                    return True
        return False

    def cover_dr_pct(
        self, *, arena_id: str, player_band: int,
    ) -> int:
        # Best (highest) cover DR from any pile in the band
        best = 0
        for p in self._piles.get(arena_id, {}).get(player_band, []):
            best = max(best, _PROFILES[p.kind].cover_dr_pct)
        return best

    def movement_cost_yalms(
        self, *, arena_id: str, band: int,
    ) -> int:
        # Sum of movement penalties (each pile makes the band
        # harder to cross)
        return sum(
            _PROFILES[p.kind].movement_cost_yalms
            for p in self._piles.get(arena_id, {}).get(band, [])
        )

    def tick_hazards(
        self, *, arena_id: str,
        players_in_band: t.Iterable[tuple[str, int]],
        dt_seconds: float,
    ) -> tuple[HazardTick, ...]:
        out: list[HazardTick] = []
        for player_id, band in players_in_band:
            if not player_id:
                continue
            for pile in self._piles.get(arena_id, {}).get(band, []):
                prof = _PROFILES[pile.kind]
                if prof.hazard_dps <= 0:
                    continue
                dmg = int(prof.hazard_dps * dt_seconds)
                if dmg <= 0:
                    continue
                out.append(HazardTick(
                    player_id=player_id,
                    debris_kind=pile.kind,
                    damage=dmg,
                    status_id=prof.hazard_status_id,
                ))
        return tuple(out)

    def clear_arena(self, *, arena_id: str) -> bool:
        if arena_id in self._piles:
            del self._piles[arena_id]
            return True
        return False


__all__ = [
    "DebrisKind", "DebrisPile", "HazardTick", "DebrisField",
]
