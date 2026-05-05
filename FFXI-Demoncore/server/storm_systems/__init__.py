"""Storm systems — aerial weather phases.

Five phases cycle per zone, on a 24h game-hour cycle (each
phase 5 in-game hours; total 25h with one extra at end of
SUPERCELL):

    CLEAR        - 5h, no effect
    CIRRUS       - 5h, light wind only
    BUILDING     - 5h, mild lightning at HIGH
    THUNDERHEAD  - 5h, MID/HIGH unsafe; lightning damage
    SUPERCELL    - 5h, MID/HIGH/STRATOSPHERE all unsafe;
                   high lightning risk; jet streams
                   become unstable

Each zone has an independent storm_seed offset so the cycle
doesn't move in lockstep — what's clear over Bastok might
be a thunderhead over Norg.

Public surface
--------------
    StormPhase enum
    StormSystems
        .register_zone(zone_id, storm_seed_offset)
        .phase_at(zone_id, now_game_hours) -> StormPhase
        .is_band_unsafe(zone_id, band, now_game_hours) -> bool
        .lightning_risk(zone_id, band, now_game_hours) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class StormPhase(str, enum.Enum):
    CLEAR = "clear"
    CIRRUS = "cirrus"
    BUILDING = "building"
    THUNDERHEAD = "thunderhead"
    SUPERCELL = "supercell"


HOURS_PER_PHASE = 5
TOTAL_CYCLE_HOURS = HOURS_PER_PHASE * 5

_PHASE_ORDER = (
    StormPhase.CLEAR,
    StormPhase.CIRRUS,
    StormPhase.BUILDING,
    StormPhase.THUNDERHEAD,
    StormPhase.SUPERCELL,
)


# bands made dangerous in each phase
_UNSAFE_BANDS_BY_PHASE: dict[StormPhase, frozenset[int]] = {
    StormPhase.CLEAR: frozenset(),
    StormPhase.CIRRUS: frozenset(),
    StormPhase.BUILDING: frozenset(),  # building isn't unsafe yet, just risky
    StormPhase.THUNDERHEAD: frozenset({2, 3}),  # MID, HIGH
    StormPhase.SUPERCELL: frozenset({2, 3, 4}),  # MID, HIGH, STRAT
}

# lightning_risk[phase][band] -> 0..100
_LIGHTNING_RISK: dict[StormPhase, dict[int, int]] = {
    StormPhase.CLEAR: {},
    StormPhase.CIRRUS: {},
    StormPhase.BUILDING: {3: 15},
    StormPhase.THUNDERHEAD: {2: 40, 3: 70},
    StormPhase.SUPERCELL: {2: 60, 3: 90, 4: 50},
}


@dataclasses.dataclass
class StormSystems:
    _seeds: dict[str, int] = dataclasses.field(default_factory=dict)

    def register_zone(
        self, *, zone_id: str,
        storm_seed_offset: int = 0,
    ) -> bool:
        if not zone_id:
            return False
        self._seeds[zone_id] = storm_seed_offset % TOTAL_CYCLE_HOURS
        return True

    def phase_at(
        self, *, zone_id: str, now_game_hours: int,
    ) -> t.Optional[StormPhase]:
        if zone_id not in self._seeds:
            return None
        offset = self._seeds[zone_id]
        cycle_pos = (now_game_hours + offset) % TOTAL_CYCLE_HOURS
        idx = cycle_pos // HOURS_PER_PHASE
        return _PHASE_ORDER[idx]

    def is_band_unsafe(
        self, *, zone_id: str, band: int,
        now_game_hours: int,
    ) -> bool:
        phase = self.phase_at(
            zone_id=zone_id, now_game_hours=now_game_hours,
        )
        if phase is None:
            return False
        return band in _UNSAFE_BANDS_BY_PHASE[phase]

    def lightning_risk(
        self, *, zone_id: str, band: int,
        now_game_hours: int,
    ) -> int:
        phase = self.phase_at(
            zone_id=zone_id, now_game_hours=now_game_hours,
        )
        if phase is None:
            return 0
        return _LIGHTNING_RISK[phase].get(band, 0)


__all__ = [
    "StormPhase", "StormSystems",
    "HOURS_PER_PHASE", "TOTAL_CYCLE_HOURS",
]
