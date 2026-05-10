"""Tests for zone_dressing."""
from __future__ import annotations

import pytest

from server.zone_dressing import (
    BUILTIN_BASTOK_MARKETS_DRESSING,
    DressingItem,
    ParentKind,
    PhysicsKind,
    TimeOfDay,
    ZoneDressing,
)


def _item(
    item_id: str = "x",
    zone: str = "bastok_markets",
    prop: str = "props/x.uasset",
    parent: ParentKind = ParentKind.FLOOR,
    tag: str = "",
    tod: TimeOfDay = TimeOfDay.BOTH,
    inter: bool = False,
    phys: PhysicsKind = PhysicsKind.STATIC,
) -> DressingItem:
    return DressingItem(
        item_id=item_id,
        zone_id=zone,
        prop_uri=prop,
        position_xyz=(0.0, 0.0, 0.0),
        rotation_xyz=(0.0, 0.0, 0.0),
        parent_kind=parent,
        narrative_tag=tag,
        time_of_day_variant=tod,
        interactable=inter,
        physics_kind=phys,
    )


# ---- Builtin dressing ----

def test_builtin_has_at_least_30_items():
    assert len(BUILTIN_BASTOK_MARKETS_DRESSING) >= 30


def test_builtin_ids_unique():
    ids = [i.item_id for i in BUILTIN_BASTOK_MARKETS_DRESSING]
    assert len(set(ids)) == len(ids)


def test_builtin_all_in_bastok_markets():
    for i in BUILTIN_BASTOK_MARKETS_DRESSING:
        assert i.zone_id == "bastok_markets"


def test_builtin_has_8_plus_cid_workshop():
    cid_items = [
        i for i in BUILTIN_BASTOK_MARKETS_DRESSING
        if i.narrative_tag == "cid_workshop_lathe"
    ]
    assert len(cid_items) >= 8


def test_builtin_cid_includes_anvil_lathe_forge():
    cid_ids = {
        i.item_id for i in BUILTIN_BASTOK_MARKETS_DRESSING
        if i.narrative_tag == "cid_workshop_lathe"
    }
    for needed in ("cid_forge", "cid_anvil", "cid_lathe"):
        assert needed in cid_ids


def test_builtin_has_6_plus_vendor_stalls():
    stalls = [
        i for i in BUILTIN_BASTOK_MARKETS_DRESSING
        if i.narrative_tag == "vendor_stall"
    ]
    assert len(stalls) >= 6


def test_builtin_has_three_tier_gallery_props():
    gallery = [
        i for i in BUILTIN_BASTOK_MARKETS_DRESSING
        if i.narrative_tag == "three_tier_gallery"
    ]
    assert len(gallery) == 3


def test_builtin_has_destructible_clutter():
    destr = [
        i for i in BUILTIN_BASTOK_MARKETS_DRESSING
        if i.physics_kind == PhysicsKind.DESTRUCTIBLE
    ]
    assert len(destr) >= 4


def test_with_bastok_markets_loads_all():
    zd = ZoneDressing.with_bastok_markets()
    assert (
        len(zd.all_items())
        == len(BUILTIN_BASTOK_MARKETS_DRESSING)
    )


# ---- Registration ----

def test_register_returns_item():
    zd = ZoneDressing()
    out = zd.register_item(_item("a"))
    assert out.item_id == "a"


def test_register_duplicate_raises():
    zd = ZoneDressing()
    zd.register_item(_item("a"))
    with pytest.raises(ValueError):
        zd.register_item(_item("a"))


def test_register_empty_id_raises():
    zd = ZoneDressing()
    with pytest.raises(ValueError):
        zd.register_item(_item(""))


def test_register_empty_zone_raises():
    zd = ZoneDressing()
    with pytest.raises(ValueError):
        zd.register_item(_item(zone=""))


def test_register_empty_prop_uri_raises():
    zd = ZoneDressing()
    with pytest.raises(ValueError):
        zd.register_item(_item(prop=""))


def test_register_zero_scale_raises():
    zd = ZoneDressing()
    with pytest.raises(ValueError):
        bad = DressingItem(
            item_id="x",
            zone_id="z",
            prop_uri="p.uasset",
            position_xyz=(0.0, 0.0, 0.0),
            rotation_xyz=(0.0, 0.0, 0.0),
            scale_xyz=(0.0, 1.0, 1.0),
        )
        zd.register_item(bad)


# ---- Lookup ----

def test_lookup_existing():
    zd = ZoneDressing.with_bastok_markets()
    item = zd.lookup("cid_anvil")
    assert item.narrative_tag == "cid_workshop_lathe"


def test_lookup_unknown_raises():
    zd = ZoneDressing()
    with pytest.raises(KeyError):
        zd.lookup("nope")


def test_has_existing():
    zd = ZoneDressing.with_bastok_markets()
    assert zd.has("cid_forge")


def test_has_unknown():
    zd = ZoneDressing()
    assert not zd.has("nope")


# ---- Filters ----

def test_items_in_zone():
    zd = ZoneDressing()
    zd.register_item(_item("a", zone="bastok_markets"))
    zd.register_item(_item("b", zone="bastok_mines"))
    in_markets = zd.items_in_zone("bastok_markets")
    assert len(in_markets) == 1
    assert in_markets[0].item_id == "a"


def test_items_with_tag():
    zd = ZoneDressing.with_bastok_markets()
    cid = zd.items_with_tag("cid_workshop_lathe")
    assert len(cid) >= 8
    raid = zd.items_with_tag("bandit_raid_evidence")
    assert len(raid) >= 2


def test_filter_by_tod_day_excludes_night_only():
    zd = ZoneDressing()
    zd.register_item(_item("d", tod=TimeOfDay.DAY))
    zd.register_item(_item("n", tod=TimeOfDay.NIGHT))
    zd.register_item(_item("b", tod=TimeOfDay.BOTH))
    day = zd.filter_by_time_of_day(
        "bastok_markets", TimeOfDay.DAY,
    )
    ids = {i.item_id for i in day}
    assert ids == {"d", "b"}


def test_filter_by_tod_night_excludes_day_only():
    zd = ZoneDressing()
    zd.register_item(_item("d", tod=TimeOfDay.DAY))
    zd.register_item(_item("n", tod=TimeOfDay.NIGHT))
    zd.register_item(_item("b", tod=TimeOfDay.BOTH))
    night = zd.filter_by_time_of_day(
        "bastok_markets", TimeOfDay.NIGHT,
    )
    ids = {i.item_id for i in night}
    assert ids == {"n", "b"}


def test_interactable_in_zone():
    zd = ZoneDressing()
    zd.register_item(_item("a", inter=True))
    zd.register_item(_item("b", inter=False))
    inter = zd.interactable_in_zone("bastok_markets")
    assert len(inter) == 1
    assert inter[0].item_id == "a"


def test_destructible_in_zone():
    zd = ZoneDressing()
    zd.register_item(_item("a", phys=PhysicsKind.DESTRUCTIBLE))
    zd.register_item(_item("b", phys=PhysicsKind.STATIC))
    out = zd.destructible_in_zone("bastok_markets")
    assert len(out) == 1
    assert out[0].item_id == "a"


def test_items_with_parent():
    zd = ZoneDressing.with_bastok_markets()
    walls = zd.items_with_parent(
        "bastok_markets", ParentKind.WALL,
    )
    assert len(walls) >= 3  # poster wall + hammer rack + ...
    hung = zd.items_with_parent(
        "bastok_markets", ParentKind.HUNG,
    )
    assert len(hung) >= 1  # hanging lantern


def test_dressing_count():
    zd = ZoneDressing.with_bastok_markets()
    assert zd.dressing_count("bastok_markets") >= 30
    assert zd.dressing_count("nope") == 0


# ---- Sparks anchor is night-only ----

def test_sparks_anchor_is_night_variant():
    zd = ZoneDressing.with_bastok_markets()
    sparks = zd.lookup("cid_sparks_particle_anchor")
    assert sparks.time_of_day_variant == TimeOfDay.NIGHT
