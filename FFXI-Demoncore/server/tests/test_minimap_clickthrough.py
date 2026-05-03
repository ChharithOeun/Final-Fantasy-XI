"""Tests for the minimap clickthrough dispatcher."""
from __future__ import annotations

from server.minimap_engine import (
    DotKind, MinimapEngine,
)
from server.minimap_difficulty_check import (
    MinimapDifficultyChecker,
)
from server.minimap_player_profile import (
    AudienceLevel, MinimapPlayerProfileRegistry,
)
from server.minimap_clickthrough import (
    ClickRouteKind, MinimapClickthrough, PressKind,
)


def _wired_world():
    """Construct a fully wired set of registries with a viewer
    'alice', a party-member 'bob', another player 'carol',
    a hostile orc 'orc_a', and an NPC 'merchant_a'."""
    eng = MinimapEngine()
    chk = MinimapDifficultyChecker()
    prof = MinimapPlayerProfileRegistry()

    # Entities
    eng.register_entity(
        entity_id="alice", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=0, y=0,
    )
    eng.register_entity(
        entity_id="bob", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=5, y=0,
    )
    eng.register_entity(
        entity_id="carol", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=8, y=0,
    )
    eng.register_entity(
        entity_id="orc_a", kind=DotKind.MOB_HOSTILE,
        zone_id="ronfaure", x=10, y=0,
    )
    eng.register_entity(
        entity_id="merchant_a", kind=DotKind.NPC,
        zone_id="ronfaure", x=2, y=0,
    )
    eng.declare_party(
        leader_id="alice", member_ids=["bob"],
    )

    chk.register_mob(
        mob_id="orc_a", level=20,
        label="Orcish Footsoldier",
    )

    prof.upsert_profile(
        player_id="bob", name="Bob", nation="Bastok",
        level=50, main_job="WHM",
    )
    prof.upsert_profile(
        player_id="carol", name="Carol", nation="Windurst",
        level=30, main_job="BLM",
    )

    dispatcher = MinimapClickthrough(
        engine=eng, difficulty_checker=chk,
        profile_registry=prof,
    )
    return dispatcher, eng, chk, prof


def test_click_self_blocked():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="alice", target_entity_id="alice",
    )
    assert not res.accepted
    assert res.route == ClickRouteKind.SELF_BLOCKED


def test_click_party_member_returns_profile():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="alice", target_entity_id="bob",
    )
    assert res.accepted
    assert res.route == ClickRouteKind.PROFILE_SNAPSHOT
    assert (
        res.profile_snapshot.audience
        == AudienceLevel.STRANGER
    )
    # Stranger by default — bob is on alice's party in the
    # engine but we haven't declared profile-relation yet.
    # Just confirm we got a profile of bob:
    assert "name" in res.profile_snapshot.fields


def test_click_other_player_returns_profile():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="alice", target_entity_id="carol",
    )
    assert res.accepted
    assert res.route == ClickRouteKind.PROFILE_SNAPSHOT


def test_click_hostile_mob_returns_check():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="alice", target_entity_id="orc_a",
        viewer_level=20,
    )
    assert res.accepted
    assert res.route == ClickRouteKind.DIFFICULTY_CHECK
    assert res.difficulty_check.mob_id == "orc_a"


def test_click_npc_returns_npc_route():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="alice", target_entity_id="merchant_a",
    )
    assert res.accepted
    assert res.route == ClickRouteKind.NPC_INTERACTION
    assert res.npc_id == "merchant_a"


def test_click_unknown_viewer():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="ghost", target_entity_id="orc_a",
    )
    assert not res.accepted
    assert res.route == ClickRouteKind.UNKNOWN_TARGET


def test_click_target_not_in_snapshot():
    d, eng, _, _ = _wired_world()
    eng.register_entity(
        entity_id="off_map", kind=DotKind.MOB_HOSTILE,
        zone_id="other_zone", x=0, y=0,
    )
    res = d.handle_click(
        viewer_id="alice", target_entity_id="off_map",
    )
    assert not res.accepted
    assert res.route == ClickRouteKind.NOT_VISIBLE


def test_click_mob_unregistered_in_checker():
    d, eng, _, _ = _wired_world()
    eng.register_entity(
        entity_id="anon_orc", kind=DotKind.MOB_HOSTILE,
        zone_id="ronfaure", x=15, y=0,
    )
    res = d.handle_click(
        viewer_id="alice", target_entity_id="anon_orc",
    )
    assert not res.accepted
    assert res.route == ClickRouteKind.UNKNOWN_TARGET


def test_click_player_unregistered_in_profile():
    d, eng, _, _ = _wired_world()
    eng.register_entity(
        entity_id="anon_player", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=15, y=0,
    )
    res = d.handle_click(
        viewer_id="alice", target_entity_id="anon_player",
    )
    assert not res.accepted
    assert res.route == ClickRouteKind.UNKNOWN_TARGET


def test_press_kind_propagated():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="alice", target_entity_id="orc_a",
        viewer_level=20, press_kind=PressKind.LONG,
    )
    assert res.press_kind == PressKind.LONG


def test_double_press_kind():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="alice", target_entity_id="bob",
        press_kind=PressKind.DOUBLE,
    )
    assert res.press_kind == PressKind.DOUBLE


def test_friend_relation_changes_profile_audience():
    d, _, _, prof = _wired_world()
    prof.declare_relation(
        viewer_id="alice", target_id="carol",
        audience=AudienceLevel.FRIEND,
    )
    res = d.handle_click(
        viewer_id="alice", target_entity_id="carol",
    )
    assert (
        res.profile_snapshot.audience
        == AudienceLevel.FRIEND
    )


def test_difficulty_check_carries_level_delta():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="alice", target_entity_id="orc_a",
        viewer_level=15,
    )
    assert res.difficulty_check.level_delta == 5


def test_fomor_excluded_from_dispatch():
    d, eng, chk, _ = _wired_world()
    eng.register_entity(
        entity_id="fomor_a", kind=DotKind.MOB_HOSTILE,
        zone_id="ronfaure", x=4, y=0,
    )
    eng.mark_fomor(entity_id="fomor_a")
    chk.register_mob(mob_id="fomor_a", level=30)
    res = d.handle_click(
        viewer_id="alice", target_entity_id="fomor_a",
    )
    # Fomor is not on the snapshot
    assert not res.accepted
    assert res.route == ClickRouteKind.NOT_VISIBLE


def test_short_press_default():
    d, _, _, _ = _wired_world()
    res = d.handle_click(
        viewer_id="alice", target_entity_id="orc_a",
        viewer_level=20,
    )
    assert res.press_kind == PressKind.SHORT
