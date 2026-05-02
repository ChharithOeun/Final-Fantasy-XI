"""Pet care — jug pets, food, hunger, loyalty.

BST throws "jug pets" — temporary tamed monsters that fight for them
for a duration. Feeding pet food during the fight extends the timer
and can boost loyalty (which improves performance). Without food,
pets time out and disappear.

Public surface
--------------
    JugSpec catalog (jug name, pet template, level)
    PetFood catalog
    ActivePet runtime state
        .feed(food_id, now_tick) - extends timer + raises loyalty
        .tick(now_tick) - returns False when pet expires
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


BASE_PET_DURATION_SECONDS = 3 * 60   # 3 minutes default
FOOD_EXTENSION_SECONDS = 60          # 1 minute per feed
MAX_LOYALTY = 5
MIN_LOYALTY = 1


@dataclasses.dataclass(frozen=True)
class JugSpec:
    jug_id: str
    label: str
    pet_template_id: str
    level: int


@dataclasses.dataclass(frozen=True)
class PetFood:
    food_id: str
    label: str
    loyalty_delta: int        # +/- loyalty points per feed
    extends_seconds: int = FOOD_EXTENSION_SECONDS


# Sample catalogs
JUG_CATALOG: tuple[JugSpec, ...] = (
    JugSpec("lapinion_familiar", "Lapinion Familiar",
            pet_template_id="rabbit", level=15),
    JugSpec("nursery_nazuna", "Nursery Nazuna",
            pet_template_id="tiger", level=23),
    JugSpec("happy_herald", "Happy Herald",
            pet_template_id="bunny", level=30),
    JugSpec("lifedrinker_larry", "Lifedrinker Larry",
            pet_template_id="leech", level=43),
    JugSpec("dapper_mac", "Dapper Mac",
            pet_template_id="mandragora", level=50),
)

JUG_BY_ID: dict[str, JugSpec] = {j.jug_id: j for j in JUG_CATALOG}


FOOD_CATALOG: tuple[PetFood, ...] = (
    PetFood("pet_food_alpha", "Pet Food Alpha",
            loyalty_delta=1),
    PetFood("pet_food_beta", "Pet Food Beta",
            loyalty_delta=1, extends_seconds=90),
    PetFood("pet_food_gamma", "Pet Food Gamma",
            loyalty_delta=2, extends_seconds=120),
    PetFood("pet_food_zeta", "Pet Food Zeta Biscuit",
            loyalty_delta=3, extends_seconds=180),
)

FOOD_BY_ID: dict[str, PetFood] = {f.food_id: f for f in FOOD_CATALOG}


@dataclasses.dataclass
class ActivePet:
    pet_id: str
    jug_id: str
    summoned_at_tick: int
    expires_at_tick: int
    loyalty: int = 1
    feed_count: int = 0
    released: bool = False

    @property
    def jug(self) -> JugSpec:
        return JUG_BY_ID[self.jug_id]

    @property
    def template_id(self) -> str:
        return self.jug.pet_template_id


@dataclasses.dataclass(frozen=True)
class FeedResult:
    accepted: bool
    extended_seconds: int = 0
    loyalty_after: int = 0
    reason: t.Optional[str] = None


def summon_jug(
    *, jug_id: str, owner_id: str, now_tick: int,
) -> t.Optional[ActivePet]:
    if jug_id not in JUG_BY_ID:
        return None
    return ActivePet(
        pet_id=f"{owner_id}_pet_{now_tick}",
        jug_id=jug_id,
        summoned_at_tick=now_tick,
        expires_at_tick=now_tick + BASE_PET_DURATION_SECONDS,
    )


def feed_pet(
    pet: ActivePet, *, food_id: str, now_tick: int,
) -> FeedResult:
    if pet.released:
        return FeedResult(False, reason="pet not active")
    if now_tick >= pet.expires_at_tick:
        return FeedResult(False, reason="pet already expired")
    food = FOOD_BY_ID.get(food_id)
    if food is None:
        return FeedResult(False, reason="unknown food")
    pet.expires_at_tick += food.extends_seconds
    pet.loyalty = max(
        MIN_LOYALTY,
        min(MAX_LOYALTY, pet.loyalty + food.loyalty_delta),
    )
    pet.feed_count += 1
    return FeedResult(
        accepted=True,
        extended_seconds=food.extends_seconds,
        loyalty_after=pet.loyalty,
    )


def tick_pet(pet: ActivePet, *, now_tick: int) -> bool:
    """Returns True if pet still active. Sets released=True when timer
    runs out."""
    if pet.released:
        return False
    if now_tick >= pet.expires_at_tick:
        pet.released = True
        return False
    return True


def release_pet(pet: ActivePet) -> None:
    pet.released = True


__all__ = [
    "BASE_PET_DURATION_SECONDS", "FOOD_EXTENSION_SECONDS",
    "MAX_LOYALTY", "MIN_LOYALTY",
    "JugSpec", "PetFood",
    "JUG_CATALOG", "JUG_BY_ID",
    "FOOD_CATALOG", "FOOD_BY_ID",
    "ActivePet", "FeedResult",
    "summon_jug", "feed_pet", "tick_pet", "release_pet",
]
