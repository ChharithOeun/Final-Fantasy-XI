"""Predator-prey ecology — population dynamics with feedback.

Each zone runs a simplified Lotka-Volterra-style model. Predator
populations rise when prey is plentiful, crash when prey is
sparse; prey populations recover when predators are scarce.
A third actor — VEGETATION / forage — feeds the prey side.

This wires into mob_migration and resource_depletion: when prey
crashes in a zone, predators MIGRATE outward (PREDATOR_PRESSURE);
when forage crashes, prey migrates.

Public surface
--------------
    SpeciesRole enum
    SpeciesPopulation dataclass
    EcologyZone dataclass
    EcologyTickResult dataclass
    PredatorPreyEcology
        .seed(zone_id, species_id, role, population)
        .add_predator_prey_link(zone_id, predator, prey,
            kill_efficiency, conversion)
        .add_forage_link(zone_id, herbivore, forage_capacity)
        .tick(zone_id, elapsed_seconds) -> EcologyTickResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default rates (per-second equivalents in slow time units).
DEFAULT_PREY_GROWTH = 0.005
DEFAULT_PREDATOR_DECAY = 0.003
MIN_POPULATION_FLOOR = 0
MAX_POPULATION_CEILING = 10_000


class SpeciesRole(str, enum.Enum):
    PREDATOR = "predator"
    HERBIVORE = "herbivore"
    SCAVENGER = "scavenger"
    APEX = "apex"


@dataclasses.dataclass
class SpeciesPopulation:
    species_id: str
    role: SpeciesRole
    population: int = 0
    baseline_growth: float = DEFAULT_PREY_GROWTH
    baseline_decay: float = DEFAULT_PREDATOR_DECAY


@dataclasses.dataclass
class _PredatorPreyLink:
    predator: str
    prey: str
    kill_efficiency: float       # fraction of prey predator can take
    conversion: float            # how much prey -> predator growth


@dataclasses.dataclass
class _ForageLink:
    herbivore: str
    forage_capacity: int         # zone supports up to this herbivore
                                 # population without crashing


@dataclasses.dataclass
class EcologyZone:
    zone_id: str
    species: dict[str, SpeciesPopulation] = dataclasses.field(
        default_factory=dict,
    )
    predator_prey_links: list[_PredatorPreyLink] = (
        dataclasses.field(default_factory=list)
    )
    forage_links: list[_ForageLink] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass(frozen=True)
class EcologyTickResult:
    zone_id: str
    elapsed_seconds: float
    deltas: dict[str, int]
    crashed_species: tuple[str, ...] = ()
    booming_species: tuple[str, ...] = ()


@dataclasses.dataclass
class PredatorPreyEcology:
    crash_threshold: int = 3        # at or below = crashed
    boom_threshold_multiplier: float = 1.5
    _zones: dict[str, EcologyZone] = dataclasses.field(
        default_factory=dict,
    )

    def _zone(self, zone_id: str) -> EcologyZone:
        return self._zones.setdefault(
            zone_id, EcologyZone(zone_id=zone_id),
        )

    def seed(
        self, *, zone_id: str, species_id: str,
        role: SpeciesRole, population: int,
        baseline_growth: t.Optional[float] = None,
        baseline_decay: t.Optional[float] = None,
    ) -> SpeciesPopulation:
        zone = self._zone(zone_id)
        sp = SpeciesPopulation(
            species_id=species_id, role=role,
            population=max(MIN_POPULATION_FLOOR, population),
            baseline_growth=(
                baseline_growth
                if baseline_growth is not None
                else DEFAULT_PREY_GROWTH
            ),
            baseline_decay=(
                baseline_decay
                if baseline_decay is not None
                else DEFAULT_PREDATOR_DECAY
            ),
        )
        zone.species[species_id] = sp
        return sp

    def population(
        self, *, zone_id: str, species_id: str,
    ) -> int:
        zone = self._zones.get(zone_id)
        if zone is None:
            return 0
        sp = zone.species.get(species_id)
        return sp.population if sp else 0

    def add_predator_prey_link(
        self, *, zone_id: str, predator: str, prey: str,
        kill_efficiency: float = 0.01,
        conversion: float = 0.005,
    ) -> bool:
        zone = self._zone(zone_id)
        if (
            predator not in zone.species
            or prey not in zone.species
        ):
            return False
        zone.predator_prey_links.append(_PredatorPreyLink(
            predator=predator, prey=prey,
            kill_efficiency=kill_efficiency,
            conversion=conversion,
        ))
        return True

    def add_forage_link(
        self, *, zone_id: str, herbivore: str,
        forage_capacity: int,
    ) -> bool:
        zone = self._zone(zone_id)
        if herbivore not in zone.species:
            return False
        zone.forage_links.append(_ForageLink(
            herbivore=herbivore,
            forage_capacity=forage_capacity,
        ))
        return True

    def tick(
        self, *, zone_id: str, elapsed_seconds: float,
    ) -> EcologyTickResult:
        zone = self._zones.get(zone_id)
        if zone is None or elapsed_seconds <= 0:
            return EcologyTickResult(
                zone_id=zone_id,
                elapsed_seconds=elapsed_seconds,
                deltas={},
            )

        before = {
            s: zone.species[s].population
            for s in zone.species
        }

        # Step 1: prey & herbivore baseline growth
        for sp in zone.species.values():
            if sp.role in (
                SpeciesRole.HERBIVORE, SpeciesRole.SCAVENGER,
            ):
                grow = int(
                    sp.population * sp.baseline_growth
                    * elapsed_seconds,
                )
                sp.population = min(
                    MAX_POPULATION_CEILING,
                    sp.population + grow,
                )

        # Step 2: predator decay (starvation absent prey)
        for sp in zone.species.values():
            if sp.role in (
                SpeciesRole.PREDATOR, SpeciesRole.APEX,
            ):
                decay = int(
                    sp.population * sp.baseline_decay
                    * elapsed_seconds,
                )
                sp.population = max(
                    MIN_POPULATION_FLOOR,
                    sp.population - decay,
                )

        # Step 3: predator-prey kills
        for link in zone.predator_prey_links:
            pred = zone.species[link.predator]
            prey = zone.species[link.prey]
            kills = int(
                pred.population * prey.population
                * link.kill_efficiency * elapsed_seconds
                / 100,
            )
            kills = min(kills, prey.population)
            prey.population -= kills
            # predator gains a fraction of kills as new pop
            pred_growth = int(kills * link.conversion * 100)
            pred.population = min(
                MAX_POPULATION_CEILING,
                pred.population + pred_growth,
            )

        # Step 4: forage caps — herbivore over capacity loses
        # individuals to starvation
        for forage in zone.forage_links:
            sp = zone.species[forage.herbivore]
            if sp.population > forage.forage_capacity:
                excess = sp.population - forage.forage_capacity
                # Slow starvation: lose 5% of excess per tick sec
                starved = int(excess * 0.05 * elapsed_seconds)
                sp.population = max(
                    forage.forage_capacity,
                    sp.population - starved,
                )

        # Compute deltas + flags
        deltas: dict[str, int] = {}
        crashed: list[str] = []
        booming: list[str] = []
        for sid, sp in zone.species.items():
            d = sp.population - before[sid]
            deltas[sid] = d
            if sp.population <= self.crash_threshold:
                crashed.append(sid)
            if (
                before[sid] > 0
                and sp.population
                >= int(
                    before[sid] * self.boom_threshold_multiplier,
                )
            ):
                booming.append(sid)
        return EcologyTickResult(
            zone_id=zone_id,
            elapsed_seconds=elapsed_seconds,
            deltas=deltas,
            crashed_species=tuple(crashed),
            booming_species=tuple(booming),
        )

    def total_zones(self) -> int:
        return len(self._zones)


__all__ = [
    "DEFAULT_PREY_GROWTH", "DEFAULT_PREDATOR_DECAY",
    "MIN_POPULATION_FLOOR", "MAX_POPULATION_CEILING",
    "SpeciesRole", "SpeciesPopulation", "EcologyZone",
    "EcologyTickResult", "PredatorPreyEcology",
]
