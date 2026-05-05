"""Aerial ecology — sky-based predator/prey populations.

Mirror of marine_ecology for the aerial bands. Same logistic
prey growth, predation, starvation, and migration mechanics
— different cast:

    SKY_FISH         — small flying eels (LOW band prey)
    STORM_PETREL     — bird flocks (LOW/MID prey)
    ROC              — giant raptor predator (MID/HIGH)
    WYVERN           — apex dragon (HIGH/STRATOSPHERE)

Food web:
    sky_fish    -> petrel, roc
    petrel      -> roc, wyvern
    roc         -> wyvern
    wyvern      -> (no predators; stochastic die-off only)

Public surface
--------------
    SkySpecies enum
    AerialEcology
        .register_cell(zone_id, band, populations)
        .set_population(zone_id, band, species, count)
        .tick(now_seconds)
        .populations_in(zone_id, band) -> dict[SkySpecies, int]
        .migration_targets(zone_id, band)
            -> tuple[(zone, band), ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SkySpecies(str, enum.Enum):
    SKY_FISH = "sky_fish"
    STORM_PETREL = "storm_petrel"
    ROC = "roc"
    WYVERN = "wyvern"


CARRYING_CAPACITY: dict[SkySpecies, int] = {
    SkySpecies.SKY_FISH: 600,
    SkySpecies.STORM_PETREL: 200,
    SkySpecies.ROC: 25,
    SkySpecies.WYVERN: 4,
}

PREY_GROWTH_RATE = 0.10
PREDATION_RATE = 0.05
PREY_STARVE_FLOOR = 0.10
MIGRATION_FLOOR = 0.20
STARVATION_DEATHS = 1


_PREY_OF: dict[SkySpecies, list[SkySpecies]] = {
    SkySpecies.SKY_FISH: [],
    SkySpecies.STORM_PETREL: [SkySpecies.SKY_FISH],
    SkySpecies.ROC: [SkySpecies.SKY_FISH, SkySpecies.STORM_PETREL],
    SkySpecies.WYVERN: [SkySpecies.STORM_PETREL, SkySpecies.ROC],
}


_Cell = tuple[str, int]


@dataclasses.dataclass
class _CellState:
    populations: dict[SkySpecies, int] = dataclasses.field(
        default_factory=dict,
    )
    migration_targets: list[_Cell] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class AerialEcology:
    _cells: dict[_Cell, _CellState] = dataclasses.field(default_factory=dict)

    def register_cell(
        self, *, zone_id: str, band: int,
        populations: t.Optional[dict[SkySpecies, int]] = None,
    ) -> bool:
        if not zone_id:
            return False
        key: _Cell = (zone_id, band)
        if key in self._cells:
            return False
        self._cells[key] = _CellState(
            populations=dict(populations or {}),
        )
        return True

    def set_population(
        self, *, zone_id: str, band: int,
        species: SkySpecies, count: int,
    ) -> bool:
        cell = self._cells.get((zone_id, band))
        if cell is None:
            return False
        cell.populations[species] = max(0, count)
        return True

    def tick(self, *, now_seconds: int) -> None:
        for (zone_id, band), cell in self._cells.items():
            self._tick_cell(zone_id, band, cell)

    def populations_in(
        self, *, zone_id: str, band: int,
    ) -> dict[SkySpecies, int]:
        cell = self._cells.get((zone_id, band))
        if cell is None:
            return {}
        return dict(cell.populations)

    def migration_targets(
        self, *, zone_id: str, band: int,
    ) -> tuple[_Cell, ...]:
        cell = self._cells.get((zone_id, band))
        if cell is None:
            return ()
        return tuple(cell.migration_targets)

    # ---

    def _tick_cell(
        self, zone_id: str, band: int, cell: _CellState,
    ) -> None:
        cell.migration_targets = []
        # 1. logistic growth for pure prey species
        for species, count in list(cell.populations.items()):
            if _PREY_OF[species]:
                continue
            cap = CARRYING_CAPACITY[species]
            if count <= 0 or cap <= 0:
                continue
            growth = int(
                count * PREY_GROWTH_RATE * (1 - count / cap),
            )
            cell.populations[species] = min(cap, count + max(0, growth))
        # 2. predation
        for species, count in list(cell.populations.items()):
            prey_list = _PREY_OF[species]
            if not prey_list or count <= 0:
                continue
            for prey in prey_list:
                prey_count = cell.populations.get(prey, 0)
                if prey_count <= 0:
                    continue
                prey_cap = CARRYING_CAPACITY[prey]
                density = prey_count / prey_cap if prey_cap else 0.0
                eaten = int(count * PREDATION_RATE * density)
                cell.populations[prey] = max(0, prey_count - eaten)
        # 3. starvation + migration flag
        for species, count in list(cell.populations.items()):
            prey_list = _PREY_OF[species]
            if not prey_list or count <= 0:
                continue
            total_prey_density = 0.0
            for prey in prey_list:
                cap = CARRYING_CAPACITY[prey]
                if cap > 0:
                    total_prey_density += (
                        cell.populations.get(prey, 0) / cap
                    )
            if total_prey_density < PREY_STARVE_FLOOR:
                cell.populations[species] = max(
                    0, count - STARVATION_DEATHS,
                )
            if total_prey_density < MIGRATION_FLOOR:
                cell.migration_targets.extend(
                    self._adjacent_cells(zone_id, band)
                )

    def _adjacent_cells(
        self, zone_id: str, band: int,
    ) -> list[_Cell]:
        out: list[_Cell] = []
        for offset in (-1, +1):
            adj: _Cell = (zone_id, band + offset)
            if adj in self._cells:
                out.append(adj)
        return out


__all__ = [
    "SkySpecies", "AerialEcology",
    "CARRYING_CAPACITY", "PREY_GROWTH_RATE",
    "PREDATION_RATE", "PREY_STARVE_FLOOR",
    "MIGRATION_FLOOR", "STARVATION_DEATHS",
]
