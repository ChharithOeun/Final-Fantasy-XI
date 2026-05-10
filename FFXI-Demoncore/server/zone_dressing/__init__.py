"""Zone dressing — per-zone set decoration.

The set-dec department in code. ``zone_atlas`` owns the
shell of a zone — its volume, its bounds, its lighting
profile. ``character_model_library`` owns who walks through
it. This module owns *everything else on the floor* — every
crate, anvil, hung lantern, market awning, mythril ingot
pile, sparks-particle anchor, leather apron stand, wanted
poster, oil drum, and rope coil that turns a Bastok Markets
shell into a working forge district.

Each item carries the data the renderer and the gameplay
layer both need: parent kind (FLOOR / WALL / CEILING /
FURNITURE / HUNG), narrative tag (so a quest can say "show
me everything tagged ``cid_workshop_lathe``"), time-of-day
variant (DAY / NIGHT / BOTH), interactable flag, and
physics kind (STATIC / DYNAMIC / DESTRUCTIBLE).

Public surface
--------------
    ParentKind enum
    PhysicsKind enum
    TimeOfDay enum
    DressingItem dataclass (frozen)
    ZoneDressing
    BUILTIN_BASTOK_MARKETS_DRESSING tuple
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ParentKind(enum.Enum):
    FLOOR = "floor"
    WALL = "wall"
    CEILING = "ceiling"
    FURNITURE = "furniture"
    HUNG = "hung"


class PhysicsKind(enum.Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    DESTRUCTIBLE = "destructible"


class TimeOfDay(enum.Enum):
    DAY = "day"
    NIGHT = "night"
    BOTH = "both"


@dataclasses.dataclass(frozen=True)
class DressingItem:
    item_id: str
    zone_id: str
    prop_uri: str
    position_xyz: tuple[float, float, float]
    rotation_xyz: tuple[float, float, float]
    scale_xyz: tuple[float, float, float] = (1.0, 1.0, 1.0)
    parent_kind: ParentKind = ParentKind.FLOOR
    narrative_tag: str = ""
    time_of_day_variant: TimeOfDay = TimeOfDay.BOTH
    interactable: bool = False
    physics_kind: PhysicsKind = PhysicsKind.STATIC


# ----------------------------------------------------------------
# Bastok Markets default dressing — Cid's workshop, vendor stalls,
# wall posters, ambient clutter, three-tier gallery overlook.
# Total > 30 items.
# ----------------------------------------------------------------
def _b(item_id: str, prop: str, **kwargs: t.Any) -> DressingItem:
    return DressingItem(
        item_id=item_id,
        zone_id="bastok_markets",
        prop_uri=f"props/{prop}.uasset",
        position_xyz=kwargs.get("pos", (0.0, 0.0, 0.0)),
        rotation_xyz=kwargs.get("rot", (0.0, 0.0, 0.0)),
        scale_xyz=kwargs.get("scale", (1.0, 1.0, 1.0)),
        parent_kind=kwargs.get("parent", ParentKind.FLOOR),
        narrative_tag=kwargs.get("tag", ""),
        time_of_day_variant=kwargs.get("tod", TimeOfDay.BOTH),
        interactable=kwargs.get("inter", False),
        physics_kind=kwargs.get(
            "phys", PhysicsKind.STATIC,
        ),
    )


_CID = "cid_workshop_lathe"
_RAID = "bandit_raid_evidence"
_VENDOR = "vendor_stall"
_NOTICE = "wall_notice"
_CLUTTER = "ambient_clutter"
_GALLERY = "three_tier_gallery"


BUILTIN_BASTOK_MARKETS_DRESSING: tuple[DressingItem, ...] = (
    # ---- Cid workshop (8 items) ----
    _b("cid_forge", "cid/forge",
       pos=(12.0, 0.0, 4.0), tag=_CID, inter=True,
       phys=PhysicsKind.STATIC),
    _b("cid_anvil", "cid/anvil",
       pos=(13.5, 0.0, 4.5), tag=_CID, inter=True,
       phys=PhysicsKind.STATIC),
    _b("cid_lathe", "cid/lathe",
       pos=(11.0, 0.0, 5.5), tag=_CID, inter=True,
       phys=PhysicsKind.DYNAMIC),
    _b("cid_hammer_rack", "cid/hammer_rack",
       pos=(14.5, 1.2, 4.0), tag=_CID,
       parent=ParentKind.WALL),
    _b("cid_mythril_ingot_pile", "cid/mythril_ingots",
       pos=(15.0, 0.0, 4.0), tag=_CID,
       phys=PhysicsKind.DYNAMIC),
    _b("cid_water_trough", "cid/water_trough",
       pos=(13.0, 0.0, 5.5), tag=_CID, inter=True),
    _b("cid_sparks_particle_anchor", "cid/sparks_anchor",
       pos=(13.5, 1.2, 4.5), tag=_CID,
       parent=ParentKind.FURNITURE,
       tod=TimeOfDay.NIGHT),
    _b("cid_leather_apron_stand", "cid/apron_stand",
       pos=(11.5, 0.0, 6.0), tag=_CID, inter=True),
    # ---- Vendor stalls (6 items) ----
    _b("stall_mythril_smith", "stalls/mythril_smith",
       pos=(20.0, 0.0, 10.0), tag=_VENDOR, inter=True),
    _b("stall_weapons", "stalls/weapons",
       pos=(22.0, 0.0, 10.0), tag=_VENDOR, inter=True),
    _b("stall_armor", "stalls/armor",
       pos=(24.0, 0.0, 10.0), tag=_VENDOR, inter=True),
    _b("stall_fish", "stalls/fish",
       pos=(20.0, 0.0, 13.0), tag=_VENDOR, inter=True,
       tod=TimeOfDay.DAY),
    _b("stall_fruit", "stalls/fruit",
       pos=(22.0, 0.0, 13.0), tag=_VENDOR, inter=True,
       tod=TimeOfDay.DAY),
    _b("stall_ironworks_tickets", "stalls/ironworks_tickets",
       pos=(24.0, 0.0, 13.0), tag=_VENDOR, inter=True),
    # ---- Wall posters / notices (4 items) ----
    _b("poster_notices_board", "posters/notices_board",
       pos=(8.0, 1.5, 0.0), tag=_NOTICE,
       parent=ParentKind.WALL, inter=True),
    _b("poster_wanted_bandit", "posters/wanted_bandit",
       pos=(8.0, 1.8, 0.5), tag=_RAID,
       parent=ParentKind.WALL, inter=True),
    _b("poster_musketeer_recruit", "posters/musketeer_recruit",
       pos=(8.0, 1.8, 1.0), tag=_NOTICE,
       parent=ParentKind.WALL),
    _b("poster_mythril_industry", "posters/mythril_industry",
       pos=(28.0, 1.8, 5.0), tag=_NOTICE,
       parent=ParentKind.WALL),
    # ---- Ambient clutter (8 items) ----
    _b("crate_a", "clutter/crate_a",
       pos=(5.0, 0.0, 7.0), tag=_CLUTTER,
       phys=PhysicsKind.DESTRUCTIBLE),
    _b("crate_b", "clutter/crate_b",
       pos=(5.0, 0.0, 7.6), tag=_CLUTTER,
       phys=PhysicsKind.DESTRUCTIBLE),
    _b("crate_c_stacked", "clutter/crate_c",
       pos=(5.0, 0.6, 7.3), tag=_CLUTTER,
       phys=PhysicsKind.DESTRUCTIBLE),
    _b("barrel_water", "clutter/barrel_water",
       pos=(6.5, 0.0, 7.0), tag=_CLUTTER,
       phys=PhysicsKind.DESTRUCTIBLE),
    _b("barrel_oil", "clutter/barrel_oil",
       pos=(7.5, 0.0, 7.0), tag=_CLUTTER,
       phys=PhysicsKind.DESTRUCTIBLE),
    _b("rope_coil", "clutter/rope_coil",
       pos=(6.0, 0.0, 8.0), tag=_CLUTTER,
       phys=PhysicsKind.DYNAMIC),
    _b("oil_drum_a", "clutter/oil_drum_a",
       pos=(8.0, 0.0, 7.0), tag=_CLUTTER,
       phys=PhysicsKind.DESTRUCTIBLE),
    _b("hanging_lantern_a", "clutter/lantern_a",
       pos=(10.0, 2.4, 5.0), tag=_CLUTTER,
       parent=ParentKind.HUNG,
       tod=TimeOfDay.NIGHT),
    # ---- Three-tier gallery overlook (3 items) ----
    _b("gallery_railing_lower", "gallery/railing_lower",
       pos=(0.0, 3.0, 0.0), tag=_GALLERY,
       parent=ParentKind.FURNITURE,
       phys=PhysicsKind.STATIC),
    _b("gallery_railing_mid", "gallery/railing_mid",
       pos=(0.0, 6.0, 0.0), tag=_GALLERY,
       parent=ParentKind.FURNITURE),
    _b("gallery_railing_upper", "gallery/railing_upper",
       pos=(0.0, 9.0, 0.0), tag=_GALLERY,
       parent=ParentKind.FURNITURE),
    # ---- A couple bandit-raid evidence drops ----
    _b("evidence_dagger", "raid/dagger",
       pos=(7.5, 0.0, 7.5), tag=_RAID, inter=True,
       phys=PhysicsKind.DYNAMIC),
    _b("evidence_torn_sash", "raid/torn_sash",
       pos=(8.0, 0.0, 7.8), tag=_RAID, inter=True,
       phys=PhysicsKind.DYNAMIC),
)


# ----------------------------------------------------------------
# ZoneDressing
# ----------------------------------------------------------------
@dataclasses.dataclass
class ZoneDressing:
    """Per-zone dressing book."""
    _items: dict[str, DressingItem] = dataclasses.field(
        default_factory=dict,
    )

    @classmethod
    def with_bastok_markets(cls) -> "ZoneDressing":
        zd = cls()
        for item in BUILTIN_BASTOK_MARKETS_DRESSING:
            zd.register_item(item)
        return zd

    def register_item(
        self, item: DressingItem,
    ) -> DressingItem:
        if not item.item_id:
            raise ValueError("item_id required")
        if item.item_id in self._items:
            raise ValueError(
                f"item_id already registered: {item.item_id}",
            )
        if not item.zone_id:
            raise ValueError("zone_id required")
        if not item.prop_uri:
            raise ValueError("prop_uri required")
        if any(s <= 0 for s in item.scale_xyz):
            raise ValueError("scale components must be > 0")
        self._items[item.item_id] = item
        return item

    def lookup(self, item_id: str) -> DressingItem:
        if item_id not in self._items:
            raise KeyError(f"unknown item: {item_id}")
        return self._items[item_id]

    def has(self, item_id: str) -> bool:
        return item_id in self._items

    def all_items(self) -> tuple[DressingItem, ...]:
        return tuple(self._items.values())

    def items_in_zone(
        self, zone_id: str,
    ) -> tuple[DressingItem, ...]:
        return tuple(
            i for i in self._items.values()
            if i.zone_id == zone_id
        )

    def items_with_tag(
        self, tag: str,
    ) -> tuple[DressingItem, ...]:
        return tuple(
            i for i in self._items.values()
            if i.narrative_tag == tag
        )

    def filter_by_time_of_day(
        self,
        zone_id: str,
        tod: TimeOfDay,
    ) -> tuple[DressingItem, ...]:
        """Items visible at the given time-of-day.

        BOTH-tagged items always show; DAY-only show only at DAY;
        NIGHT-only show only at NIGHT.
        """
        out: list[DressingItem] = []
        for i in self._items.values():
            if i.zone_id != zone_id:
                continue
            v = i.time_of_day_variant
            if v == TimeOfDay.BOTH:
                out.append(i)
            elif v == tod:
                out.append(i)
        return tuple(out)

    def interactable_in_zone(
        self, zone_id: str,
    ) -> tuple[DressingItem, ...]:
        return tuple(
            i for i in self.items_in_zone(zone_id)
            if i.interactable
        )

    def destructible_in_zone(
        self, zone_id: str,
    ) -> tuple[DressingItem, ...]:
        return tuple(
            i for i in self.items_in_zone(zone_id)
            if i.physics_kind == PhysicsKind.DESTRUCTIBLE
        )

    def items_with_parent(
        self, zone_id: str, parent_kind: ParentKind,
    ) -> tuple[DressingItem, ...]:
        return tuple(
            i for i in self.items_in_zone(zone_id)
            if i.parent_kind == parent_kind
        )

    def dressing_count(self, zone_id: str) -> int:
        return len(self.items_in_zone(zone_id))


__all__ = [
    "ParentKind", "PhysicsKind", "TimeOfDay",
    "DressingItem", "ZoneDressing",
    "BUILTIN_BASTOK_MARKETS_DRESSING",
]
