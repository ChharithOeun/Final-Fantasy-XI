"""Marine ecology — predator/prey populations per (zone, band).

The deep should feel alive between player visits.  Each
(zone, band) cell tracks populations of fish, sharks,
sahuagin, and kraken. Each tick:

1. Prey grows toward CARRYING_CAPACITY logistically.
2. Predators eat prey at PREDATION_RATE * predators
   * (prey / capacity).
3. Predators lose population if prey is too sparse
   (starvation cliff at PREY_STARVE_FLOOR).
4. If a cell's prey collapses below MIGRATION_FLOOR,
   predators are flagged for migrate_targets — adjacent
   bands they should drift to next tick.

The kraken-cult food chain is canonical:
    kraken -> shark, sahuagin
    shark  -> fish
    sahuagin -> fish

Public surface
--------------
    Species enum
    Cell dataclass (frozen)
    MarineEcology
        .register_cell(zone_id, band, populations)
        .set_population(zone_id, band, species, count)
        .tick(now_seconds)
        .populations_in(zone_id, band) -> dict[Species, int]
        .migration_targets(zone_id, band)
            -> tuple[(zone, band), ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Species(str, enum.Enum):
    FISH = "fish"
    SHARK = "shark"
    SAHUAGIN = "sahuagin"
    KRAKEN = "kraken"


# every species has a per-cell carrying capacity (food + space)
CARRYING_CAPACITY: dict[Species, int] = {
    Species.FISH: 500,
    Species.SHARK: 30,
    Species.SAHUAGIN: 40,
    Species.KRAKEN: 3,
}

# logistic prey growth multiplier per tick
PREY_GROWTH_RATE = 0.10

# fraction of prey eaten per predator per tick (scaled by
# prey/capacity to make starvation a cliff, not a slope)
PREDATION_RATE = 0.05

# below this fraction of capacity prey can't sustain predators
PREY_STARVE_FLOOR = 0.10

# below this fraction of capacity, predators migrate
MIGRATION_FLOOR = 0.20

# starvation kills this many predators per tick
STARVATION_DEATHS = 1


# canonical food web
_PREDATORS_OF: dict[Species, list[Species]] = {
    Species.FISH: [Species.SHARK, Species.SAHUAGIN],
    Species.SHARK: [Species.KRAKEN],
    Species.SAHUAGIN: [Species.KRAKEN],
    Species.KRAKEN: [],
}

# what each predator eats
_PREY_OF: dict[Species, list[Species]] = {
    Species.SHARK: [Species.FISH],
    Species.SAHUAGIN: [Species.FISH],
    Species.KRAKEN: [Species.SHARK, Species.SAHUAGIN],
    Species.FISH: [],
}


_Cell = tuple[str, int]


@dataclasses.dataclass
class _CellState:
    populations: dict[Species, int] = dataclasses.field(
        default_factory=dict,
    )
    migration_targets: list[_Cell] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass(frozen=True)
class CellSnapshot:
    zone_id: str
    band: int
    populations: dict[Species, int]


@dataclasses.dataclass
class MarineEcology:
    _cells: dict[_Cell, _CellState] = dataclasses.field(default_factory=dict)

    def register_cell(
        self, *, zone_id: str, band: int,
        populations: t.Optional[dict[Species, int]] = None,
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
        species: Species, count: int,
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
    ) -> dict[Species, int]:
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
        # 1. logistic prey growth
        for species, count in list(cell.populations.items()):
            if _PREY_OF[species]:
                # this is a predator; growth handled later via prey
                continue
            cap = CARRYING_CAPACITY[species]
            if count <= 0 or cap <= 0:
                continue
            growth = int(
                count * PREY_GROWTH_RATE * (1 - count / cap),
            )
            cell.populations[species] = min(cap, count + max(0, growth))
        # 2. predation: each predator eats fraction of prey
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
        # 3. starvation if prey below floor
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
            # 4. flag migration if prey is below MIGRATION_FLOOR
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
    "Species", "CellSnapshot", "MarineEcology",
    "CARRYING_CAPACITY", "PREY_GROWTH_RATE",
    "PREDATION_RATE", "PREY_STARVE_FLOOR",
    "MIGRATION_FLOOR", "STARVATION_DEATHS",
]
