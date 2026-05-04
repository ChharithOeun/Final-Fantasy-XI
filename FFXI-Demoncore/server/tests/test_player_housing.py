"""Tests for the player housing system."""
from __future__ import annotations

from server.player_housing import (
    AmbianceTier,
    DecorSlotKind,
    HouseTier,
    PlayerHousing,
    VisitPermission,
)


def test_charter_house():
    h = PlayerHousing()
    house = h.charter_house(
        player_id="alice", tier=HouseTier.HOUSE,
        nation="bastok",
    )
    assert house is not None
    assert house.tier == HouseTier.HOUSE


def test_double_charter_rejected():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    assert h.charter_house(player_id="alice") is None


def test_upgrade_tier():
    h = PlayerHousing()
    h.charter_house(
        player_id="alice", tier=HouseTier.APARTMENT,
    )
    new_tier = h.upgrade_tier(player_id="alice")
    assert new_tier == HouseTier.HOUSE


def test_upgrade_at_max_returns_none():
    h = PlayerHousing()
    h.charter_house(
        player_id="alice", tier=HouseTier.ESTATE,
    )
    assert h.upgrade_tier(player_id="alice") is None


def test_upgrade_unknown():
    h = PlayerHousing()
    assert h.upgrade_tier(player_id="ghost") is None


def test_place_decor():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    assert h.place_decor(
        player_id="alice",
        slot=DecorSlotKind.HEARTH,
        item_id="warm_fire",
        ambiance_bonus=15,
    )


def test_place_decor_negative_bonus_rejected():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    assert not h.place_decor(
        player_id="alice",
        slot=DecorSlotKind.HEARTH,
        item_id="x", ambiance_bonus=-1,
    )


def test_place_decor_empty_item_rejected():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    assert not h.place_decor(
        player_id="alice",
        slot=DecorSlotKind.HEARTH,
        item_id="",
    )


def test_place_decor_caps_at_tier_allowance():
    h = PlayerHousing()
    h.charter_house(
        player_id="alice", tier=HouseTier.APARTMENT,
    )
    # APARTMENT allows 4 distinct slots
    slots = list(DecorSlotKind)[:4]
    for s in slots:
        h.place_decor(
            player_id="alice", slot=s, item_id="x",
        )
    over = h.place_decor(
        player_id="alice",
        slot=list(DecorSlotKind)[4],
        item_id="x",
    )
    assert not over


def test_place_decor_overwrite_same_slot():
    h = PlayerHousing()
    h.charter_house(
        player_id="alice", tier=HouseTier.APARTMENT,
    )
    h.place_decor(
        player_id="alice", slot=DecorSlotKind.HEARTH,
        item_id="a",
    )
    assert h.place_decor(
        player_id="alice", slot=DecorSlotKind.HEARTH,
        item_id="b",
    )


def test_remove_decor():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    h.place_decor(
        player_id="alice",
        slot=DecorSlotKind.HEARTH, item_id="x",
    )
    assert h.remove_decor(
        player_id="alice", slot=DecorSlotKind.HEARTH,
    )


def test_remove_unknown_slot():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    assert not h.remove_decor(
        player_id="alice", slot=DecorSlotKind.HEARTH,
    )


def test_ambiance_progresses_with_decor():
    h = PlayerHousing()
    h.charter_house(
        player_id="alice", tier=HouseTier.ESTATE,
    )
    assert h.ambiance_for(player_id="alice") == AmbianceTier.BARE
    h.place_decor(
        player_id="alice",
        slot=DecorSlotKind.HEARTH, item_id="x",
        ambiance_bonus=25,
    )
    assert h.ambiance_for(
        player_id="alice",
    ) == AmbianceTier.HOMELY
    h.place_decor(
        player_id="alice",
        slot=DecorSlotKind.GARDEN_1, item_id="y",
        ambiance_bonus=200,
    )
    assert h.ambiance_for(
        player_id="alice",
    ) == AmbianceTier.LEGENDARY


def test_visit_self_always_allowed():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    h.set_visit_permission(
        player_id="alice",
        permission=VisitPermission.PRIVATE,
    )
    res = h.visit(
        visitor_id="alice", host_id="alice",
    )
    assert res.accepted


def test_visit_private_blocks_outsiders():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    h.set_visit_permission(
        player_id="alice",
        permission=VisitPermission.PRIVATE,
    )
    res = h.visit(
        visitor_id="bob", host_id="alice",
    )
    assert not res.accepted


def test_visit_public_anyone():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    h.set_visit_permission(
        player_id="alice",
        permission=VisitPermission.PUBLIC,
    )
    res = h.visit(
        visitor_id="bob", host_id="alice",
    )
    assert res.accepted


def test_visit_friends_only():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    h.set_visit_permission(
        player_id="alice",
        permission=VisitPermission.FRIENDS,
    )
    h.add_friend(player_id="alice", friend_id="bob")
    assert h.visit(
        visitor_id="bob", host_id="alice",
    ).accepted
    assert not h.visit(
        visitor_id="dave", host_id="alice",
    ).accepted


def test_visit_linkshell_only():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    h.set_visit_permission(
        player_id="alice",
        permission=VisitPermission.LINKSHELL,
    )
    h.set_linkshell(
        player_id="alice", linkshell_id="VanguardLS",
    )
    res = h.visit(
        visitor_id="bob", host_id="alice",
        visitor_linkshells=("VanguardLS",),
    )
    assert res.accepted
    res2 = h.visit(
        visitor_id="bob", host_id="alice",
        visitor_linkshells=("Other",),
    )
    assert not res2.accepted


def test_add_friend_self_rejected():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    assert not h.add_friend(
        player_id="alice", friend_id="alice",
    )


def test_add_friend_dedup():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    h.add_friend(player_id="alice", friend_id="bob")
    assert not h.add_friend(
        player_id="alice", friend_id="bob",
    )


def test_visit_unknown_host():
    h = PlayerHousing()
    res = h.visit(
        visitor_id="alice", host_id="ghost",
    )
    assert not res.accepted
    assert "no such house" in res.reason


def test_visit_bonus_increases_with_ambiance():
    h = PlayerHousing()
    h.charter_house(
        player_id="alice", tier=HouseTier.ESTATE,
    )
    h.set_visit_permission(
        player_id="alice",
        permission=VisitPermission.PUBLIC,
    )
    res_bare = h.visit(
        visitor_id="bob", host_id="alice",
    )
    h.place_decor(
        player_id="alice",
        slot=DecorSlotKind.HEARTH, item_id="x",
        ambiance_bonus=200,
    )
    res_legendary = h.visit(
        visitor_id="bob", host_id="alice",
    )
    assert res_legendary.bonus_pct > res_bare.bonus_pct


def test_total_houses():
    h = PlayerHousing()
    h.charter_house(player_id="alice")
    h.charter_house(player_id="bob")
    assert h.total_houses() == 2


def test_ambiance_for_unknown_returns_none():
    h = PlayerHousing()
    assert h.ambiance_for(player_id="ghost") is None
