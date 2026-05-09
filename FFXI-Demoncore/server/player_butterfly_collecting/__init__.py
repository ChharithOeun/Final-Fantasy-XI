"""Player butterfly collecting — net + pin specimens for display.

Collectors net butterflies in zones during their active seasons.
Captured specimens have a freshness clock — they decay 10 per
day post-capture. Pin within a few days or the specimen is
worthless. Pinned specimens lock at their pin-day freshness
and go into the collector's display case.

Lifecycle (per specimen)
    CAPTURED     just netted, freshness clock running
    PINNED       mounted, freshness locked
    SPOILED      decayed past zero before pinning

Public surface
--------------
    SpecimenStage enum
    Butterfly dataclass (frozen)
    Specimen dataclass (frozen)
    PlayerButterflyCollectingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_DAILY_DECAY = 10


class SpecimenStage(str, enum.Enum):
    CAPTURED = "captured"
    PINNED = "pinned"
    SPOILED = "spoiled"


@dataclasses.dataclass(frozen=True)
class Butterfly:
    species_id: str
    common_name: str
    rarity_value: int
    active_zones: tuple[str, ...]
    active_seasons: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Specimen:
    specimen_id: str
    collector_id: str
    species_id: str
    captured_day: int
    stage: SpecimenStage
    freshness_at_pin: int


@dataclasses.dataclass
class PlayerButterflyCollectingSystem:
    _species: dict[str, Butterfly] = dataclasses.field(
        default_factory=dict,
    )
    _specimens: dict[str, Specimen] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def register_species(
        self, *, species_id: str, common_name: str,
        rarity_value: int,
        active_zones: tuple[str, ...],
        active_seasons: tuple[str, ...],
    ) -> bool:
        if not species_id or species_id in self._species:
            return False
        if not common_name:
            return False
        if rarity_value < 0:
            return False
        if not active_zones or not active_seasons:
            return False
        self._species[species_id] = Butterfly(
            species_id=species_id,
            common_name=common_name,
            rarity_value=rarity_value,
            active_zones=active_zones,
            active_seasons=active_seasons,
        )
        return True

    def net_specimen(
        self, *, collector_id: str, species_id: str,
        zone_id: str, season: str, captured_day: int,
    ) -> t.Optional[str]:
        if not collector_id:
            return None
        if species_id not in self._species:
            return None
        if captured_day < 0:
            return None
        sp = self._species[species_id]
        if zone_id not in sp.active_zones:
            return None
        if season not in sp.active_seasons:
            return None
        sid = f"spec_{self._next}"
        self._next += 1
        self._specimens[sid] = Specimen(
            specimen_id=sid, collector_id=collector_id,
            species_id=species_id,
            captured_day=captured_day,
            stage=SpecimenStage.CAPTURED,
            freshness_at_pin=0,
        )
        return sid

    def freshness_on_day(
        self, *, specimen_id: str, current_day: int,
    ) -> int:
        """Compute current freshness (100 at capture
        day, decaying _DAILY_DECAY per day). Returns
        0 if pinned (use freshness_at_pin instead) or
        spoiled.
        """
        sp = self._specimens.get(specimen_id)
        if sp is None:
            return 0
        if sp.stage != SpecimenStage.CAPTURED:
            return 0
        days = current_day - sp.captured_day
        if days < 0:
            return 0
        return max(0, 100 - days * _DAILY_DECAY)

    def pin(
        self, *, specimen_id: str, current_day: int,
    ) -> t.Optional[int]:
        """Pin the specimen, locking freshness.
        Returns final freshness or None if the
        specimen has decayed to 0 (then SPOILED).
        """
        if specimen_id not in self._specimens:
            return None
        sp = self._specimens[specimen_id]
        if sp.stage != SpecimenStage.CAPTURED:
            return None
        if current_day < sp.captured_day:
            return None
        freshness = self.freshness_on_day(
            specimen_id=specimen_id,
            current_day=current_day,
        )
        if freshness <= 0:
            self._specimens[specimen_id] = (
                dataclasses.replace(
                    sp, stage=SpecimenStage.SPOILED,
                )
            )
            return None
        self._specimens[specimen_id] = (
            dataclasses.replace(
                sp, stage=SpecimenStage.PINNED,
                freshness_at_pin=freshness,
            )
        )
        return freshness

    def display_value(
        self, *, specimen_id: str,
    ) -> int:
        """Display gil value of a pinned specimen
        = rarity * freshness_at_pin / 10."""
        sp = self._specimens.get(specimen_id)
        if sp is None or sp.stage != SpecimenStage.PINNED:
            return 0
        sb = self._species[sp.species_id]
        return sb.rarity_value * sp.freshness_at_pin // 10

    def collection(
        self, *, collector_id: str,
    ) -> list[Specimen]:
        """Return collector's pinned specimens."""
        return [
            sp for sp in self._specimens.values()
            if (sp.collector_id == collector_id
                and sp.stage == SpecimenStage.PINNED)
        ]

    def specimen(
        self, *, specimen_id: str,
    ) -> t.Optional[Specimen]:
        return self._specimens.get(specimen_id)

    def species(
        self, *, species_id: str,
    ) -> t.Optional[Butterfly]:
        return self._species.get(species_id)


__all__ = [
    "SpecimenStage", "Butterfly", "Specimen",
    "PlayerButterflyCollectingSystem",
]
