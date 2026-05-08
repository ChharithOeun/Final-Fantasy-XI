"""VR pet interaction — pet your chocobo, scratch your puppet.

In flat-screen FFXI you press a button; your chocobo
acknowledges. In VR you reach down, touch its neck,
stroke. The chocobo nuzzles your hand. The Automaton's
eyes light up. The Trust NPC turns toward you and
beams. Bonding becomes embodied.

Five interaction kinds we recognize, distinguished by
hand motion + duration + body part touched:
    PET             slow stroke down the neck/back, ≥1s
    SCRATCH         small repeated motions on a spot, ≥0.5s
    HUG             both hands wrap around, ≥2s
    FEED            held item moved to mouth area
    PLAY_TUG        rapid back/forth motion against a held
                    object the pet's gripping (rope toy,
                    PUP wrench, BST jug)

Per-pet bond increment per interaction (the
pet_bonding module owns the actual values; we report
the kind + duration + body part for it to credit).

Body parts (rough zones around the pet's local space):
    HEAD / NECK / BACK / FLANK / BELLY / TAIL / MUZZLE
    Player hand position relative to pet origin gets
    classified into one of these.

Each interaction has a cool-down — petting the same
chocobo every 0.5s isn't 100 pets, it's 1 pet. The
INTERACTION_COOLDOWN_MS is per-(player, pet, kind).

Public surface
--------------
    InteractionKind enum
    BodyPart enum
    PetState dataclass (frozen) — pet pos + species
    InteractionEvent dataclass (frozen)
    VrPetInteraction
        .register_pet(pet_id, x, y, z, species) -> bool
        .move_pet(pet_id, x, y, z) -> bool
        .ingest_touch(player_id, pet_id, hand_x, hand_y,
                      hand_z, kind, duration_ms,
                      timestamp_ms) -> Optional[InteractionEvent]
        .events_for(player_id) -> list[InteractionEvent]
        .clear_pet(pet_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


_TOUCH_RADIUS_M = 1.0
_INTERACTION_COOLDOWN_MS = 1500


class InteractionKind(str, enum.Enum):
    PET = "pet"
    SCRATCH = "scratch"
    HUG = "hug"
    FEED = "feed"
    PLAY_TUG = "play_tug"


class BodyPart(str, enum.Enum):
    HEAD = "head"
    NECK = "neck"
    BACK = "back"
    FLANK = "flank"
    BELLY = "belly"
    TAIL = "tail"
    MUZZLE = "muzzle"


@dataclasses.dataclass(frozen=True)
class PetState:
    pet_id: str
    x: float
    y: float
    z: float
    species: str  # "chocobo" / "automaton" / "trust" / etc


@dataclasses.dataclass(frozen=True)
class InteractionEvent:
    player_id: str
    pet_id: str
    kind: InteractionKind
    body_part: BodyPart
    duration_ms: int
    timestamp_ms: int


def _classify_body_part(
    pet: PetState, hx: float, hy: float, hz: float,
) -> BodyPart:
    """Rough zone classifier based on local offset.
    The pet's coord system: +Z=front, +Y=up, +X=right."""
    dx = hx - pet.x
    dy = hy - pet.y
    dz = hz - pet.z
    if dz > 0.5:
        return BodyPart.MUZZLE if dy > 0.6 else BodyPart.HEAD
    if dz < -0.5:
        return BodyPart.TAIL
    # Mid-body region
    if dy > 0.4:
        return BodyPart.NECK
    if dy < -0.4:
        return BodyPart.BELLY
    if abs(dx) > 0.3:
        return BodyPart.FLANK
    return BodyPart.BACK


def _dist_pet(pet: PetState, hx, hy, hz) -> float:
    return math.sqrt(
        (pet.x - hx) ** 2 + (pet.y - hy) ** 2
        + (pet.z - hz) ** 2
    )


@dataclasses.dataclass
class VrPetInteraction:
    _pets: dict[str, PetState] = dataclasses.field(
        default_factory=dict,
    )
    _events: list[InteractionEvent] = dataclasses.field(
        default_factory=list,
    )

    def register_pet(
        self, *, pet_id: str, x: float, y: float, z: float,
        species: str,
    ) -> bool:
        if not pet_id or not species:
            return False
        if pet_id in self._pets:
            return False
        self._pets[pet_id] = PetState(
            pet_id=pet_id, x=x, y=y, z=z, species=species,
        )
        return True

    def move_pet(
        self, *, pet_id: str, x: float, y: float, z: float,
    ) -> bool:
        if pet_id not in self._pets:
            return False
        old = self._pets[pet_id]
        self._pets[pet_id] = PetState(
            pet_id=pet_id, x=x, y=y, z=z, species=old.species,
        )
        return True

    def ingest_touch(
        self, *, player_id: str, pet_id: str,
        hand_x: float, hand_y: float, hand_z: float,
        kind: InteractionKind, duration_ms: int,
        timestamp_ms: int,
    ) -> t.Optional[InteractionEvent]:
        if not player_id or pet_id not in self._pets:
            return None
        if duration_ms <= 0:
            return None
        # Minimum durations per kind
        min_dur = {
            InteractionKind.PET: 1000,
            InteractionKind.SCRATCH: 500,
            InteractionKind.HUG: 2000,
            InteractionKind.FEED: 200,
            InteractionKind.PLAY_TUG: 500,
        }
        if duration_ms < min_dur[kind]:
            return None
        pet = self._pets[pet_id]
        if _dist_pet(pet, hand_x, hand_y, hand_z) > _TOUCH_RADIUS_M:
            return None
        # Cooldown: same (player, pet, kind) within 1500ms
        for prev in reversed(self._events):
            if (prev.player_id == player_id
                    and prev.pet_id == pet_id
                    and prev.kind == kind):
                if (timestamp_ms - prev.timestamp_ms
                        < _INTERACTION_COOLDOWN_MS):
                    return None
                break
        body_part = _classify_body_part(
            pet, hand_x, hand_y, hand_z,
        )
        ev = InteractionEvent(
            player_id=player_id, pet_id=pet_id,
            kind=kind, body_part=body_part,
            duration_ms=duration_ms,
            timestamp_ms=timestamp_ms,
        )
        self._events.append(ev)
        return ev

    def events_for(
        self, *, player_id: str,
    ) -> list[InteractionEvent]:
        return [
            e for e in self._events
            if e.player_id == player_id
        ]

    def events_for_pet(
        self, *, pet_id: str,
    ) -> list[InteractionEvent]:
        return [
            e for e in self._events
            if e.pet_id == pet_id
        ]

    def clear_pet(self, *, pet_id: str) -> bool:
        if pet_id not in self._pets:
            return False
        del self._pets[pet_id]
        before = len(self._events)
        self._events = [
            e for e in self._events if e.pet_id != pet_id
        ]
        return True


__all__ = [
    "InteractionKind", "BodyPart", "PetState",
    "InteractionEvent", "VrPetInteraction",
]
