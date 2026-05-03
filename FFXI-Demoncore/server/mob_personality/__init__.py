"""Per-mob personality traits — the AI's individuality knob.

In Demoncore every mob is AI-driven, but two same-class mobs
shouldn't feel identical. A young Yagudo Initiate fresh out of
the seminary panics at the first fireball. A scarred veteran
Yagudo Acolyte holds the line and casts Banish with cold focus.
A particularly *cunning* one breaks aggro to lure the player
into a trap.

This module exposes the personality vector each AI consumes:
six traits in [0.0, 1.0], with class-typical defaults and
per-individual jitter. The AI agent reads the vector when it
makes decisions — the vector is an INPUT, not behavior code.
The orchestrator's prompt assembly includes the personality
profile, so the per-mob LLM call is steered by it.

Traits
------
    AGGRESSION    - opens aggressively vs. holds back
    COURAGE       - holds ground under pressure vs. flees early
    CURIOSITY     - investigates strange sounds vs. ignores
    TERRITORIALITY- defends turf vs. wanders
    CUNNING       - sets traps / lures vs. plays it straight
    LOYALTY       - rallies to allies vs. self-preserves

Each trait is a probability dial. Multiple traits can be high
or low; combinations create distinct AI flavors:
    high COURAGE + low CUNNING = stubborn brawler
    high CUNNING + low LOYALTY = treacherous rogue
    high TERRITORIALITY + low CURIOSITY = sentry / pillar mob

Public surface
--------------
    PersonalityTrait enum
    PersonalityVector dataclass — value per trait
    MobPersonalityArchetype dataclass — class-typical defaults
    DEFAULT_ARCHETYPES — per mob_class_id baseline
    roll_personality(archetype, jitter, rng) -> PersonalityVector
    PersonalityRegistry
        .assign(mob_id, vector)
        .vector_for(mob_id) -> PersonalityVector
        .describe(vector) -> tuple[str, ...]   # narrative tags
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


class PersonalityTrait(str, enum.Enum):
    AGGRESSION = "aggression"
    COURAGE = "courage"
    CURIOSITY = "curiosity"
    TERRITORIALITY = "territoriality"
    CUNNING = "cunning"
    LOYALTY = "loyalty"


_TRAITS: tuple[PersonalityTrait, ...] = tuple(PersonalityTrait)


@dataclasses.dataclass(frozen=True)
class PersonalityVector:
    aggression: float = 0.5
    courage: float = 0.5
    curiosity: float = 0.5
    territoriality: float = 0.5
    cunning: float = 0.5
    loyalty: float = 0.5

    def __post_init__(self) -> None:
        for t_, v in self.as_dict().items():
            if not (0.0 <= v <= 1.0):
                raise ValueError(
                    f"trait {t_} value {v} out of range 0.0-1.0",
                )

    def as_dict(self) -> dict[PersonalityTrait, float]:
        return {
            PersonalityTrait.AGGRESSION: self.aggression,
            PersonalityTrait.COURAGE: self.courage,
            PersonalityTrait.CURIOSITY: self.curiosity,
            PersonalityTrait.TERRITORIALITY: self.territoriality,
            PersonalityTrait.CUNNING: self.cunning,
            PersonalityTrait.LOYALTY: self.loyalty,
        }

    def get(self, trait: PersonalityTrait) -> float:
        return self.as_dict()[trait]


@dataclasses.dataclass(frozen=True)
class MobPersonalityArchetype:
    """Class-typical defaults. The actual mob gets a jittered
    sample around this baseline."""
    archetype_id: str
    label: str
    baseline: PersonalityVector
    jitter: float = 0.15      # +/- range applied per trait


# --------------------------------------------------------------------
# Default archetypes — one per major mob family
# --------------------------------------------------------------------
DEFAULT_ARCHETYPES: dict[str, MobPersonalityArchetype] = {
    "yagudo_initiate": MobPersonalityArchetype(
        archetype_id="yagudo_initiate",
        label="Yagudo Initiate (young)",
        baseline=PersonalityVector(
            aggression=0.4, courage=0.35, curiosity=0.55,
            territoriality=0.5, cunning=0.4, loyalty=0.6,
        ),
    ),
    "yagudo_acolyte": MobPersonalityArchetype(
        archetype_id="yagudo_acolyte",
        label="Yagudo Acolyte (veteran)",
        baseline=PersonalityVector(
            aggression=0.65, courage=0.7, curiosity=0.4,
            territoriality=0.65, cunning=0.55, loyalty=0.7,
        ),
    ),
    "orc_warlord": MobPersonalityArchetype(
        archetype_id="orc_warlord",
        label="Orc Warlord",
        baseline=PersonalityVector(
            aggression=0.85, courage=0.8, curiosity=0.3,
            territoriality=0.7, cunning=0.5, loyalty=0.7,
        ),
    ),
    "goblin_smithy": MobPersonalityArchetype(
        archetype_id="goblin_smithy",
        label="Goblin Smithy (treacherous)",
        baseline=PersonalityVector(
            aggression=0.55, courage=0.5, curiosity=0.7,
            territoriality=0.5, cunning=0.85, loyalty=0.3,
        ),
    ),
    "skeleton_warrior": MobPersonalityArchetype(
        archetype_id="skeleton_warrior",
        label="Skeleton Warrior (mindless aggression)",
        baseline=PersonalityVector(
            aggression=0.9, courage=0.95, curiosity=0.05,
            territoriality=0.4, cunning=0.1, loyalty=0.9,
        ),
        jitter=0.05,           # undead are very uniform
    ),
    "tonberry_pilgrim": MobPersonalityArchetype(
        archetype_id="tonberry_pilgrim",
        label="Tonberry Pilgrim (slow rage)",
        baseline=PersonalityVector(
            aggression=0.6, courage=0.85, curiosity=0.2,
            territoriality=0.95, cunning=0.4, loyalty=0.85,
        ),
    ),
    "sahagin_swordsman": MobPersonalityArchetype(
        archetype_id="sahagin_swordsman",
        label="Sahagin Swordsman",
        baseline=PersonalityVector(
            aggression=0.65, courage=0.6, curiosity=0.4,
            territoriality=0.8, cunning=0.5, loyalty=0.6,
        ),
    ),
    "bee_soldier": MobPersonalityArchetype(
        archetype_id="bee_soldier",
        label="Bee Soldier (territorial swarm)",
        baseline=PersonalityVector(
            aggression=0.7, courage=0.5, curiosity=0.3,
            territoriality=0.95, cunning=0.2, loyalty=1.0,
        ),
        jitter=0.05,
    ),
    "psychomancer": MobPersonalityArchetype(
        archetype_id="psychomancer",
        label="Psychomancer (cunning manipulator)",
        baseline=PersonalityVector(
            aggression=0.4, courage=0.55, curiosity=0.85,
            territoriality=0.5, cunning=0.95, loyalty=0.4,
        ),
    ),
}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def roll_personality(
    *, archetype: MobPersonalityArchetype,
    rng: t.Optional[random.Random] = None,
) -> PersonalityVector:
    """Sample a per-mob personality from the archetype's baseline +
    jitter. rng injection so tests are deterministic."""
    rng = rng or random.Random()
    j = archetype.jitter
    base = archetype.baseline.as_dict()
    rolled: dict[PersonalityTrait, float] = {}
    for t_ in _TRAITS:
        rolled[t_] = _clamp(base[t_] + rng.uniform(-j, j))
    return PersonalityVector(
        aggression=rolled[PersonalityTrait.AGGRESSION],
        courage=rolled[PersonalityTrait.COURAGE],
        curiosity=rolled[PersonalityTrait.CURIOSITY],
        territoriality=rolled[PersonalityTrait.TERRITORIALITY],
        cunning=rolled[PersonalityTrait.CUNNING],
        loyalty=rolled[PersonalityTrait.LOYALTY],
    )


# --------------------------------------------------------------------
# Narrative tags — translate a vector into "what kind of mob this is"
# for the orchestrator prompt assembly.
# --------------------------------------------------------------------
_TAG_THRESHOLDS: tuple[
    tuple[str, t.Callable[[PersonalityVector], bool]], ...,
] = (
    ("berserker",
     lambda v: v.aggression > 0.8 and v.courage > 0.8),
    ("coward",
     lambda v: v.courage < 0.3),
    ("schemer",
     lambda v: v.cunning > 0.8 and v.aggression < 0.6),
    ("traitor",
     lambda v: v.cunning > 0.7 and v.loyalty < 0.4),
    ("guardian",
     lambda v: v.territoriality > 0.8 and v.loyalty > 0.7),
    ("explorer",
     lambda v: v.curiosity > 0.75 and v.territoriality < 0.5),
    ("brawler",
     lambda v: v.aggression > 0.7 and v.cunning < 0.3),
    ("zealot",
     lambda v: v.loyalty > 0.85 and v.courage > 0.7),
    ("scout",
     lambda v: v.curiosity > 0.6 and v.cunning > 0.6),
)


def describe(vector: PersonalityVector) -> tuple[str, ...]:
    """Return the narrative tags that apply to this vector. The
    orchestrator surfaces these to the AI prompt so the LLM
    plays the role correctly."""
    return tuple(
        tag for tag, predicate in _TAG_THRESHOLDS
        if predicate(vector)
    )


@dataclasses.dataclass
class PersonalityRegistry:
    _by_mob: dict[str, PersonalityVector] = dataclasses.field(
        default_factory=dict,
    )

    def assign(
        self, *, mob_id: str, vector: PersonalityVector,
    ) -> PersonalityVector:
        self._by_mob[mob_id] = vector
        return vector

    def assign_from_archetype(
        self, *, mob_id: str, archetype_id: str,
        rng: t.Optional[random.Random] = None,
    ) -> PersonalityVector:
        archetype = DEFAULT_ARCHETYPES[archetype_id]
        v = roll_personality(archetype=archetype, rng=rng)
        return self.assign(mob_id=mob_id, vector=v)

    def vector_for(
        self, mob_id: str,
    ) -> t.Optional[PersonalityVector]:
        return self._by_mob.get(mob_id)

    def total(self) -> int:
        return len(self._by_mob)


__all__ = [
    "PersonalityTrait", "PersonalityVector",
    "MobPersonalityArchetype", "DEFAULT_ARCHETYPES",
    "roll_personality", "describe",
    "PersonalityRegistry",
]
