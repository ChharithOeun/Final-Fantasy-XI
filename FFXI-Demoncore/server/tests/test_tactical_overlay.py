"""Tests for tactical_overlay."""
from __future__ import annotations

from server.tactical_overlay import (
    ConTier, OverlayItemKind, TacticalOverlay,
    _AoeRef, _MobRef, _PartyRef, _RangeCircle,
)


def _mob(mid, x=0.0, y=0.0, dist=10.0,
         tier=ConTier.DECENT):
    return _MobRef(
        mob_id=mid, x=x, y=y,
        distance_to_player=dist, con_tier=tier,
    )


def test_build_frame_empty():
    f = TacticalOverlay.build_frame(
        player_id="bob", mobs=[], aoes=[], party=[],
        range_circles=[],
        reveal_predicate=lambda _: True,
    )
    assert len(f.items) == 0
    assert f.truncated_mobs is False


def test_build_frame_with_mob():
    f = TacticalOverlay.build_frame(
        player_id="bob",
        mobs=[_mob("orc1", x=5.0, y=10.0, dist=8.0)],
        aoes=[], party=[], range_circles=[],
        reveal_predicate=lambda _: True,
    )
    assert len(f.items) == 1
    item = f.items[0]
    assert item.kind == OverlayItemKind.MOB
    assert item.x == 5.0


def test_build_frame_mobs_sorted_by_distance():
    f = TacticalOverlay.build_frame(
        player_id="bob",
        mobs=[
            _mob("far", dist=30.0),
            _mob("near", dist=5.0),
            _mob("mid", dist=15.0),
        ],
        aoes=[], party=[], range_circles=[],
        reveal_predicate=lambda _: True,
    )
    mobs = [
        i for i in f.items
        if i.kind == OverlayItemKind.MOB
    ]
    assert mobs[0].entity_id == "near"
    assert mobs[1].entity_id == "mid"
    assert mobs[2].entity_id == "far"


def test_build_frame_predicate_filters_invisible_mob():
    """Sneaked / invisible mob shouldn't appear."""
    f = TacticalOverlay.build_frame(
        player_id="bob",
        mobs=[_mob("seen"), _mob("hidden")],
        aoes=[], party=[], range_circles=[],
        reveal_predicate=lambda eid: eid != "hidden",
    )
    mob_ids = [
        i.entity_id for i in f.items
        if i.kind == OverlayItemKind.MOB
    ]
    assert "seen" in mob_ids
    assert "hidden" not in mob_ids


def test_build_frame_mob_cap_50():
    mobs = [
        _mob(f"mob_{i}", dist=float(i)) for i in range(60)
    ]
    f = TacticalOverlay.build_frame(
        player_id="bob", mobs=mobs, aoes=[], party=[],
        range_circles=[],
        reveal_predicate=lambda _: True,
    )
    mob_items = [
        i for i in f.items
        if i.kind == OverlayItemKind.MOB
    ]
    assert len(mob_items) == 50
    assert f.truncated_mobs is True


def test_build_frame_mob_cap_not_triggered_when_under_50():
    mobs = [_mob(f"m{i}", dist=float(i)) for i in range(20)]
    f = TacticalOverlay.build_frame(
        player_id="bob", mobs=mobs, aoes=[], party=[],
        range_circles=[],
        reveal_predicate=lambda _: True,
    )
    assert f.truncated_mobs is False


def test_build_frame_with_aoe():
    f = TacticalOverlay.build_frame(
        player_id="bob", mobs=[],
        aoes=[_AoeRef(
            aoe_id="aoe_1", x=3.0, y=3.0, radius=8.0,
        )],
        party=[], range_circles=[],
        reveal_predicate=lambda _: True,
    )
    aoe_items = [
        i for i in f.items
        if i.kind == OverlayItemKind.AOE
    ]
    assert len(aoe_items) == 1
    assert aoe_items[0].radius == 8.0


def test_build_frame_party_self_always_shown():
    """Even if predicate returns False for player_id,
    self should still appear (you can always see your
    own dot)."""
    f = TacticalOverlay.build_frame(
        player_id="bob",
        mobs=[], aoes=[],
        party=[_PartyRef(
            player_id="bob", x=0.0, y=0.0, job="RDM",
        )],
        range_circles=[],
        reveal_predicate=lambda _: False,
    )
    party = [
        i for i in f.items
        if i.kind == OverlayItemKind.PARTY
    ]
    assert len(party) == 1
    assert party[0].entity_id == "bob"


def test_build_frame_party_filters_disguised_member():
    f = TacticalOverlay.build_frame(
        player_id="bob",
        mobs=[], aoes=[],
        party=[
            _PartyRef(
                player_id="bob", x=0.0, y=0.0, job="RDM",
            ),
            _PartyRef(
                player_id="cara", x=5.0, y=5.0,
                job="WHM",
            ),
        ],
        range_circles=[],
        reveal_predicate=lambda eid: eid != "cara",
    )
    party_ids = [
        i.entity_id for i in f.items
        if i.kind == OverlayItemKind.PARTY
    ]
    assert "bob" in party_ids
    assert "cara" not in party_ids


def test_build_frame_range_circle():
    f = TacticalOverlay.build_frame(
        player_id="bob", mobs=[], aoes=[], party=[],
        range_circles=[_RangeCircle(
            label="melee", x=0.0, y=0.0, radius=3.0,
        )],
        reveal_predicate=lambda _: True,
    )
    rc = [
        i for i in f.items
        if i.kind == OverlayItemKind.RANGE_CIRCLE
    ]
    assert len(rc) == 1
    assert rc[0].label == "melee"


def test_build_frame_carries_player_id():
    f = TacticalOverlay.build_frame(
        player_id="bob", mobs=[], aoes=[], party=[],
        range_circles=[],
        reveal_predicate=lambda _: True,
    )
    assert f.player_id == "bob"


def test_build_frame_mob_con_tier():
    f = TacticalOverlay.build_frame(
        player_id="bob",
        mobs=[_mob("nm", tier=ConTier.DEADLY)],
        aoes=[], party=[], range_circles=[],
        reveal_predicate=lambda _: True,
    )
    assert f.items[0].con_tier == "deadly"


def test_build_frame_aoe_always_visible():
    """AOE telegraphs are public — predicate doesn't
    apply (you can always see the death zone)."""
    f = TacticalOverlay.build_frame(
        player_id="bob", mobs=[],
        aoes=[_AoeRef(
            aoe_id="big_aoe", x=0.0, y=0.0,
            radius=15.0,
        )],
        party=[], range_circles=[],
        reveal_predicate=lambda _: False,
    )
    aoe_items = [
        i for i in f.items
        if i.kind == OverlayItemKind.AOE
    ]
    assert len(aoe_items) == 1


def test_build_frame_combined():
    f = TacticalOverlay.build_frame(
        player_id="bob",
        mobs=[_mob("orc", dist=5.0)],
        aoes=[_AoeRef(
            aoe_id="a1", x=0.0, y=0.0, radius=10.0,
        )],
        party=[_PartyRef(
            player_id="bob", x=0.0, y=0.0, job="RDM",
        )],
        range_circles=[_RangeCircle(
            label="cast", x=0.0, y=0.0, radius=20.0,
        )],
        reveal_predicate=lambda _: True,
    )
    kinds = {i.kind for i in f.items}
    assert kinds == {
        OverlayItemKind.MOB, OverlayItemKind.AOE,
        OverlayItemKind.PARTY,
        OverlayItemKind.RANGE_CIRCLE,
    }


def test_four_overlay_kinds():
    assert len(list(OverlayItemKind)) == 4


def test_five_con_tiers():
    assert len(list(ConTier)) == 5
