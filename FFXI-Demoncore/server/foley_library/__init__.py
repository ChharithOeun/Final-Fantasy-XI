"""Foley library — per-surface footsteps + interaction
foley.

Foley is the discipline of recreating the sound of bodies
in space — the click of a heel on cobble, the rustle of a
cloak when an arm raises, the metal-on-metal jingle of mail
plate when an axe is lifted. This module owns the catalog
of those sounds and the rules for picking which sample to
play at runtime.

Three axes:
  * SURFACE — wood, stone (dry/wet), metal (grated/plate),
    grass, dirt, sand, marsh squelch, water shallow/deep,
    snow, ice, cobble, marble, carpet, mog-house rug. The
    floor under the foot.
  * GAIT — Galka heavy, Hume normal, Elvaan long stride,
    Mithra prowl, Taru light. The body that's moving.
  * KIND — footstep vs sword draw vs cloth rustle vs
    armor-plate jingle vs eating-crunch. What action.

A footstep is picked by (surface, gait); the library holds
1..N samples for each combo and round-robins / random-
picks at runtime to avoid the clicky repeat-machine-gun
problem of single-sample foley.

Interaction foley: action + costume composes overlays. A
plate-armor character drawing a sword fires SWORD_DRAW +
ARMOR_PLATE_JINGLE — two samples on the same frame, mixed
by surround_audio_mixer.

Public surface
--------------
    Surface enum
    Gait enum
    FoleyKind enum
    FoleyEntry dataclass (frozen)
    FoleyLibrary
    populate_default_library
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Surface(enum.Enum):
    WOOD = "wood"
    STONE_DRY = "stone_dry"
    STONE_WET = "stone_wet"
    METAL_GRATED = "metal_grated"
    METAL_PLATE = "metal_plate"
    GRASS = "grass"
    DIRT = "dirt"
    SAND = "sand"
    MARSH_SQUELCH = "marsh_squelch"
    WATER_SHALLOW = "water_shallow"
    WATER_DEEP = "water_deep"
    SNOW = "snow"
    ICE = "ice"
    COBBLE = "cobble"
    MARBLE = "marble"
    CARPET = "carpet"
    MOG_HOUSE_RUG = "mog_house_rug"


class Gait(enum.Enum):
    GALKA_HEAVY = "galka_heavy"
    HUME_NORMAL = "hume_normal"
    ELVAAN_LONG_STRIDE = "elvaan_long_stride"
    MITHRA_PROWL = "mithra_prowl"
    TARU_LIGHT = "taru_light"


class FoleyKind(enum.Enum):
    FOOTSTEP = "footstep"
    SWORD_DRAW = "sword_draw"
    SWORD_SHEATHE = "sword_sheathe"
    AXE_HEFT = "axe_heft"
    CLOTH_RUSTLE = "cloth_rustle"
    ARMOR_PLATE_JINGLE = "armor_plate_jingle"
    ARMOR_MAIL_SHIFT = "armor_mail_shift"
    ARMOR_LEATHER_CREAK = "armor_leather_creak"
    BACKPACK_SET_DOWN = "backpack_set_down"
    INVENTORY_OPEN = "inventory_open"
    INVENTORY_FLIP = "inventory_flip"
    DOOR_WOODEN_CREAK = "door_wooden_creak"
    DOOR_METAL_RUSTY = "door_metal_rusty"
    CHEST_OPEN = "chest_open"
    BOTTLE_UNCORK = "bottle_uncork"
    EATING_CRUNCH = "eating_crunch"
    EATING_LIQUID = "eating_liquid"


# Race -> default gait mapping (canonical FFXI races).
_RACE_TO_GAIT: dict[str, Gait] = {
    "galka": Gait.GALKA_HEAVY,
    "hume": Gait.HUME_NORMAL,
    "elvaan": Gait.ELVAAN_LONG_STRIDE,
    "mithra": Gait.MITHRA_PROWL,
    "tarutaru": Gait.TARU_LIGHT,
    "taru": Gait.TARU_LIGHT,
}


# Costume kind -> armor overlay foley kind.
_COSTUME_TO_OVERLAY: dict[str, FoleyKind] = {
    "plate": FoleyKind.ARMOR_PLATE_JINGLE,
    "plate_armor": FoleyKind.ARMOR_PLATE_JINGLE,
    "mail": FoleyKind.ARMOR_MAIL_SHIFT,
    "chain": FoleyKind.ARMOR_MAIL_SHIFT,
    "leather": FoleyKind.ARMOR_LEATHER_CREAK,
    "cloth": FoleyKind.CLOTH_RUSTLE,
    "robe": FoleyKind.CLOTH_RUSTLE,
}


# Action label -> base foley kind (the "what is happening"
# event that the action triggers).
_ACTION_TO_KIND: dict[str, FoleyKind] = {
    "sword_draw": FoleyKind.SWORD_DRAW,
    "sword_sheathe": FoleyKind.SWORD_SHEATHE,
    "axe_heft": FoleyKind.AXE_HEFT,
    "open_inventory": FoleyKind.INVENTORY_OPEN,
    "flip_inventory": FoleyKind.INVENTORY_FLIP,
    "set_down_backpack": FoleyKind.BACKPACK_SET_DOWN,
    "open_door_wooden": FoleyKind.DOOR_WOODEN_CREAK,
    "open_door_metal": FoleyKind.DOOR_METAL_RUSTY,
    "open_chest": FoleyKind.CHEST_OPEN,
    "uncork_bottle": FoleyKind.BOTTLE_UNCORK,
    "eat_crunch": FoleyKind.EATING_CRUNCH,
    "eat_liquid": FoleyKind.EATING_LIQUID,
}


@dataclasses.dataclass(frozen=True)
class FoleyEntry:
    foley_id: str
    kind: FoleyKind
    surface: t.Optional[Surface]
    gait: t.Optional[Gait]
    sample_uris: tuple[str, ...]


@dataclasses.dataclass
class FoleyLibrary:
    _entries: dict[str, FoleyEntry] = dataclasses.field(
        default_factory=dict,
    )
    # Cursor for round-robin sample picking per entry.
    _cursors: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    # --------------------------------------------- register
    def register_foley(
        self,
        foley_id: str,
        kind: FoleyKind,
        sample_uris: tuple[str, ...] | list[str],
        surface: t.Optional[Surface] = None,
        gait: t.Optional[Gait] = None,
    ) -> None:
        if not foley_id:
            raise ValueError("foley_id required")
        if foley_id in self._entries:
            raise ValueError(
                f"duplicate foley_id: {foley_id}",
            )
        if not sample_uris:
            raise ValueError("at least one sample_uri required")
        if kind == FoleyKind.FOOTSTEP and surface is None:
            raise ValueError("footstep entries must have a surface")
        if kind == FoleyKind.FOOTSTEP and gait is None:
            raise ValueError("footstep entries must have a gait")
        entry = FoleyEntry(
            foley_id=foley_id,
            kind=kind,
            surface=surface,
            gait=gait,
            sample_uris=tuple(sample_uris),
        )
        self._entries[foley_id] = entry
        self._cursors[foley_id] = 0

    def get_entry(self, foley_id: str) -> FoleyEntry:
        if foley_id not in self._entries:
            raise KeyError(f"unknown foley_id: {foley_id}")
        return self._entries[foley_id]

    def entry_count(self) -> int:
        return len(self._entries)

    # --------------------------------------------- pick_footstep
    def pick_footstep(
        self, surface: Surface, gait: Gait,
    ) -> str:
        for entry in self._entries.values():
            if (
                entry.kind == FoleyKind.FOOTSTEP
                and entry.surface == surface
                and entry.gait == gait
            ):
                idx = self._cursors[entry.foley_id]
                sample = entry.sample_uris[
                    idx % len(entry.sample_uris)
                ]
                self._cursors[entry.foley_id] = idx + 1
                return sample
        raise KeyError(
            f"no footstep for surface={surface.value} "
            f"gait={gait.value}",
        )

    # --------------------------------------------- foley_for_action
    def foley_for_action(
        self,
        action: str,
        costume_kind: str = "",
    ) -> tuple[str, ...]:
        """Return sample URIs to play for an action +
        costume combo. Returns the action's primary sample
        plus an armor-overlay sample if costume warrants it."""
        if action not in _ACTION_TO_KIND:
            raise KeyError(f"unknown action: {action}")
        primary_kind = _ACTION_TO_KIND[action]
        primary_sample = self._first_sample_of_kind(primary_kind)
        out: list[str] = []
        if primary_sample:
            out.append(primary_sample)
        # Apply costume overlay if relevant — only on
        # actions involving body movement (sword/axe/draw,
        # not chest_open, etc).
        if (
            costume_kind
            and costume_kind in _COSTUME_TO_OVERLAY
            and primary_kind in (
                FoleyKind.SWORD_DRAW,
                FoleyKind.SWORD_SHEATHE,
                FoleyKind.AXE_HEFT,
                FoleyKind.BACKPACK_SET_DOWN,
            )
        ):
            overlay_kind = _COSTUME_TO_OVERLAY[costume_kind]
            overlay_sample = self._first_sample_of_kind(
                overlay_kind,
            )
            if overlay_sample:
                out.append(overlay_sample)
        return tuple(out)

    def _first_sample_of_kind(
        self, kind: FoleyKind,
    ) -> str:
        for entry in self._entries.values():
            if entry.kind == kind:
                idx = self._cursors[entry.foley_id]
                sample = entry.sample_uris[
                    idx % len(entry.sample_uris)
                ]
                self._cursors[entry.foley_id] = idx + 1
                return sample
        return ""

    # --------------------------------------------- queries
    def foleys_for_surface(
        self, surface: Surface,
    ) -> tuple[FoleyEntry, ...]:
        return tuple(
            sorted(
                (
                    e for e in self._entries.values()
                    if e.surface == surface
                ),
                key=lambda e: e.foley_id,
            )
        )

    def gaits_for_race(self, race: str) -> tuple[Gait, ...]:
        race_l = race.lower()
        if race_l in _RACE_TO_GAIT:
            return (_RACE_TO_GAIT[race_l],)
        return ()

    def all_kinds(self) -> tuple[FoleyKind, ...]:
        return tuple(
            sorted(
                {e.kind for e in self._entries.values()},
                key=lambda k: k.value,
            )
        )


# ---------------------------------------------------------
# Default catalog.
# ---------------------------------------------------------

def populate_default_library(lib: FoleyLibrary) -> int:
    """Populate the canonical foley set: footsteps for all
    17 surfaces x 5 gaits, plus all interaction foleys.

    Returns the count of registered entries."""
    n = 0
    # Footsteps: surface x gait. 4 sample variants each.
    for surface in Surface:
        for gait in Gait:
            samples = tuple(
                f"sfx/foot/{surface.value}_"
                f"{gait.value}_v{v}.ogg"
                for v in range(1, 5)
            )
            foley_id = f"foot_{surface.value}_{gait.value}"
            lib.register_foley(
                foley_id=foley_id,
                kind=FoleyKind.FOOTSTEP,
                sample_uris=samples,
                surface=surface,
                gait=gait,
            )
            n += 1
    # Non-footstep foleys.
    interactions: tuple[tuple[FoleyKind, str, int], ...] = (
        (FoleyKind.SWORD_DRAW, "sword_draw", 3),
        (FoleyKind.SWORD_SHEATHE, "sword_sheathe", 3),
        (FoleyKind.AXE_HEFT, "axe_heft", 3),
        (FoleyKind.CLOTH_RUSTLE, "cloth_rustle", 4),
        (FoleyKind.ARMOR_PLATE_JINGLE, "armor_plate_jingle", 4),
        (FoleyKind.ARMOR_MAIL_SHIFT, "armor_mail_shift", 4),
        (FoleyKind.ARMOR_LEATHER_CREAK,
            "armor_leather_creak", 3),
        (FoleyKind.BACKPACK_SET_DOWN,
            "backpack_set_down", 2),
        (FoleyKind.INVENTORY_OPEN, "inventory_open", 1),
        (FoleyKind.INVENTORY_FLIP, "inventory_flip", 3),
        (FoleyKind.DOOR_WOODEN_CREAK, "door_wooden_creak", 2),
        (FoleyKind.DOOR_METAL_RUSTY, "door_metal_rusty", 2),
        (FoleyKind.CHEST_OPEN, "chest_open", 2),
        (FoleyKind.BOTTLE_UNCORK, "bottle_uncork", 2),
        (FoleyKind.EATING_CRUNCH, "eating_crunch", 3),
        (FoleyKind.EATING_LIQUID, "eating_liquid", 2),
    )
    for kind, base_name, count in interactions:
        samples = tuple(
            f"sfx/foley/{base_name}_v{v}.ogg"
            for v in range(1, count + 1)
        )
        lib.register_foley(
            foley_id=base_name,
            kind=kind,
            sample_uris=samples,
        )
        n += 1
    return n


__all__ = [
    "Surface",
    "Gait",
    "FoleyKind",
    "FoleyEntry",
    "FoleyLibrary",
    "populate_default_library",
]
