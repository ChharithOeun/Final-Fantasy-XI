"""Mob breeding — generations, cub growth, pack inheritance.

Mobs reproduce. Cubs are born inside a pack, weak and vulnerable;
they grow into juveniles, then adults. Pack-level traits (tribe
chief identity, hunting style, language) propagate to offspring
on a fade — slightly mutated each generation.

This is what produces continuity in the world: the orcs you
fought five game-years ago have CHILDREN now, those children have
inherited the tribal grudge.

Public surface
--------------
    LifeStage enum
    MobLineage dataclass — running pack lineage
    MobIndividual dataclass — single mob's record
    BreedingEvent dataclass
    MobBreedingRegistry
        .register_pack(pack_id, mob_kind, founders)
        .breed(pack_id, sire_id, dam_id) -> Optional[cub]
        .age_step(elapsed_seconds)
        .members_of(pack_id)
        .all_cubs() / .all_adults() etc
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default ageing thresholds (seconds in game-time).
SECONDS_TO_JUVENILE = 1000
SECONDS_TO_ADULT = 3000
SECONDS_TO_ELDER = 10000

# Trait fade per generation.
TRAIT_FADE_PER_GENERATION = 0.15


class LifeStage(str, enum.Enum):
    CUB = "cub"
    JUVENILE = "juvenile"
    ADULT = "adult"
    ELDER = "elder"
    DECEASED = "deceased"


@dataclasses.dataclass
class MobIndividual:
    mob_uid: str
    pack_id: str
    mob_kind: str
    parent_sire_id: t.Optional[str] = None
    parent_dam_id: t.Optional[str] = None
    generation: int = 0
    age_seconds: float = 0.0
    stage: LifeStage = LifeStage.ADULT
    inherited_traits: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )
    born_at_seconds: float = 0.0


@dataclasses.dataclass
class MobLineage:
    pack_id: str
    mob_kind: str
    chief_uid: t.Optional[str] = None
    members: list[str] = dataclasses.field(
        default_factory=list,
    )
    base_traits: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )
    generations_observed: int = 0


@dataclasses.dataclass(frozen=True)
class BreedingEvent:
    cub_uid: str
    pack_id: str
    sire_id: str
    dam_id: str
    born_at_seconds: float


def _stage_for_age(age: float) -> LifeStage:
    if age < SECONDS_TO_JUVENILE:
        return LifeStage.CUB
    if age < SECONDS_TO_ADULT:
        return LifeStage.JUVENILE
    if age < SECONDS_TO_ELDER:
        return LifeStage.ADULT
    return LifeStage.ELDER


@dataclasses.dataclass
class MobBreedingRegistry:
    trait_fade_per_generation: float = TRAIT_FADE_PER_GENERATION
    _packs: dict[str, MobLineage] = dataclasses.field(
        default_factory=dict,
    )
    _individuals: dict[str, MobIndividual] = dataclasses.field(
        default_factory=dict,
    )
    _next_cub: int = 0

    def register_pack(
        self, *, pack_id: str, mob_kind: str,
        founders: tuple[str, ...] = (),
        base_traits: t.Optional[dict[str, float]] = None,
        chief_uid: t.Optional[str] = None,
    ) -> t.Optional[MobLineage]:
        if pack_id in self._packs:
            return None
        lineage = MobLineage(
            pack_id=pack_id, mob_kind=mob_kind,
            chief_uid=chief_uid,
            base_traits=dict(base_traits or {}),
        )
        for f_uid in founders:
            ind = MobIndividual(
                mob_uid=f_uid, pack_id=pack_id,
                mob_kind=mob_kind,
                generation=0,
                age_seconds=SECONDS_TO_ADULT,
                stage=LifeStage.ADULT,
                inherited_traits=dict(base_traits or {}),
            )
            self._individuals[f_uid] = ind
            lineage.members.append(f_uid)
        self._packs[pack_id] = lineage
        return lineage

    def pack(self, pack_id: str) -> t.Optional[MobLineage]:
        return self._packs.get(pack_id)

    def individual(
        self, mob_uid: str,
    ) -> t.Optional[MobIndividual]:
        return self._individuals.get(mob_uid)

    def breed(
        self, *, pack_id: str, sire_id: str, dam_id: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[BreedingEvent]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return None
        sire = self._individuals.get(sire_id)
        dam = self._individuals.get(dam_id)
        if sire is None or dam is None:
            return None
        if sire.pack_id != pack_id or dam.pack_id != pack_id:
            return None
        # Both parents must be adult or elder
        if sire.stage not in (
            LifeStage.ADULT, LifeStage.ELDER,
        ):
            return None
        if dam.stage not in (
            LifeStage.ADULT, LifeStage.ELDER,
        ):
            return None
        # Generation = max parents + 1
        gen = max(sire.generation, dam.generation) + 1
        # Inherit traits — average of parents, faded a tick
        cub_traits: dict[str, float] = {}
        for k in set(sire.inherited_traits) | set(dam.inherited_traits):
            avg = (
                sire.inherited_traits.get(k, 0.0)
                + dam.inherited_traits.get(k, 0.0)
            ) / 2.0
            faded = avg * (
                1.0 - self.trait_fade_per_generation
            )
            cub_traits[k] = faded
        cub_uid = f"{pack_id}_cub_{self._next_cub}"
        self._next_cub += 1
        cub = MobIndividual(
            mob_uid=cub_uid, pack_id=pack_id,
            mob_kind=pack.mob_kind,
            parent_sire_id=sire_id, parent_dam_id=dam_id,
            generation=gen, age_seconds=0.0,
            stage=LifeStage.CUB,
            inherited_traits=cub_traits,
            born_at_seconds=now_seconds,
        )
        self._individuals[cub_uid] = cub
        pack.members.append(cub_uid)
        if gen > pack.generations_observed:
            pack.generations_observed = gen
        return BreedingEvent(
            cub_uid=cub_uid, pack_id=pack_id,
            sire_id=sire_id, dam_id=dam_id,
            born_at_seconds=now_seconds,
        )

    def age_step(
        self, *, elapsed_seconds: float,
    ) -> int:
        if elapsed_seconds <= 0:
            return 0
        affected = 0
        for ind in self._individuals.values():
            if ind.stage == LifeStage.DECEASED:
                continue
            ind.age_seconds += elapsed_seconds
            new_stage = _stage_for_age(ind.age_seconds)
            if new_stage != ind.stage:
                ind.stage = new_stage
                affected += 1
        return affected

    def kill(self, mob_uid: str) -> bool:
        ind = self._individuals.get(mob_uid)
        if ind is None or ind.stage == LifeStage.DECEASED:
            return False
        ind.stage = LifeStage.DECEASED
        return True

    def members_of(
        self, pack_id: str,
        stage_filter: t.Optional[LifeStage] = None,
    ) -> tuple[MobIndividual, ...]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return ()
        out = []
        for uid in pack.members:
            ind = self._individuals.get(uid)
            if ind is None:
                continue
            if stage_filter is not None and ind.stage != stage_filter:
                continue
            out.append(ind)
        return tuple(out)

    def total_individuals(self) -> int:
        return len(self._individuals)


__all__ = [
    "SECONDS_TO_JUVENILE", "SECONDS_TO_ADULT",
    "SECONDS_TO_ELDER",
    "TRAIT_FADE_PER_GENERATION",
    "LifeStage", "MobIndividual", "MobLineage",
    "BreedingEvent", "MobBreedingRegistry",
]
