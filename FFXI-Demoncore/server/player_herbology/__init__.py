"""Player herbology — wild plant ID + herbal remedies.

Players identify wild plants found across zones. Each plant
has an identification difficulty 1..100; identify rolls
observer_skill vs difficulty deterministically. Identified
plants enter the player's almanac. Two or three known plants
can be combined into a herbal remedy with simple effect rules.

Public surface
--------------
    PlantTier enum
    Effect enum
    Plant dataclass (frozen)
    Remedy dataclass (frozen)
    PlayerHerbologySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PlantTier(int, enum.Enum):
    COMMON = 1
    UNCOMMON = 2
    RARE = 3
    LEGENDARY = 4


class Effect(str, enum.Enum):
    HEAL = "heal"
    ANTITOXIN = "antitoxin"
    SLEEP = "sleep"
    VIGOR = "vigor"
    FOCUS = "focus"


@dataclasses.dataclass(frozen=True)
class Plant:
    plant_id: str
    common_name: str
    tier: PlantTier
    id_difficulty: int       # 1..100
    primary_effect: Effect


@dataclasses.dataclass(frozen=True)
class Remedy:
    remedy_id: str
    brewer_id: str
    effects: tuple[Effect, ...]
    potency: int
    used_plants: tuple[str, ...]


@dataclasses.dataclass
class _BState:
    almanac: set[str] = dataclasses.field(
        default_factory=set,
    )


@dataclasses.dataclass
class PlayerHerbologySystem:
    _plants: dict[str, Plant] = dataclasses.field(
        default_factory=dict,
    )
    _botanists: dict[str, _BState] = dataclasses.field(
        default_factory=dict,
    )
    _remedies: dict[str, Remedy] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def register_plant(
        self, *, plant_id: str, common_name: str,
        tier: PlantTier, id_difficulty: int,
        primary_effect: Effect,
    ) -> bool:
        if not plant_id or plant_id in self._plants:
            return False
        if not common_name:
            return False
        if not 1 <= id_difficulty <= 100:
            return False
        self._plants[plant_id] = Plant(
            plant_id=plant_id, common_name=common_name,
            tier=tier, id_difficulty=id_difficulty,
            primary_effect=primary_effect,
        )
        return True

    def identify(
        self, *, botanist_id: str, plant_id: str,
        observer_skill: int, seed: int,
    ) -> bool:
        """Try to identify a plant. Pass = skill +
        variance(0..19) >= difficulty.
        """
        if not botanist_id:
            return False
        if plant_id not in self._plants:
            return False
        if not 1 <= observer_skill <= 100:
            return False
        plant = self._plants[plant_id]
        variance = seed % 20
        roll = observer_skill + variance
        if roll < plant.id_difficulty:
            return False
        if botanist_id not in self._botanists:
            self._botanists[botanist_id] = _BState()
        self._botanists[botanist_id].almanac.add(
            plant_id,
        )
        return True

    def almanac(
        self, *, botanist_id: str,
    ) -> list[str]:
        st = self._botanists.get(botanist_id)
        if st is None:
            return []
        return sorted(st.almanac)

    def brew_remedy(
        self, *, brewer_id: str,
        plant_ids: tuple[str, ...],
        brewer_skill: int,
    ) -> t.Optional[str]:
        """Brew a remedy from 2-3 known plants.
        Effects = unique primary_effects of inputs;
        potency = brewer_skill + sum(plant tiers) * 5.
        """
        if not brewer_id:
            return None
        if not 1 <= brewer_skill <= 100:
            return None
        if len(plant_ids) < 2 or len(plant_ids) > 3:
            return None
        st = self._botanists.get(brewer_id)
        if st is None:
            return None
        # All plants must be in brewer's almanac
        for pid in plant_ids:
            if pid not in st.almanac:
                return None
            if pid not in self._plants:
                return None
        # No duplicates in the recipe
        if len(set(plant_ids)) != len(plant_ids):
            return None
        plants = [self._plants[p] for p in plant_ids]
        effects = tuple(
            sorted(
                {p.primary_effect for p in plants},
                key=lambda e: e.value,
            ),
        )
        potency = brewer_skill + sum(
            p.tier.value for p in plants
        ) * 5
        rid = f"remedy_{self._next}"
        self._next += 1
        self._remedies[rid] = Remedy(
            remedy_id=rid, brewer_id=brewer_id,
            effects=effects, potency=potency,
            used_plants=plant_ids,
        )
        return rid

    def remedy(
        self, *, remedy_id: str,
    ) -> t.Optional[Remedy]:
        return self._remedies.get(remedy_id)

    def plant(
        self, *, plant_id: str,
    ) -> t.Optional[Plant]:
        return self._plants.get(plant_id)


__all__ = [
    "PlantTier", "Effect", "Plant", "Remedy",
    "PlayerHerbologySystem",
]
