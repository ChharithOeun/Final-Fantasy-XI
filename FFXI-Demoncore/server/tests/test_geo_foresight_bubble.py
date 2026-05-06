"""Tests for geo_foresight_bubble."""
from __future__ import annotations

from server.geo_foresight_bubble import (
    CAST_MP_COST,
    DEFAULT_RADIUS_YALMS,
    ForesightFlavor,
    GEO_LUOPAN_HP,
    GeoForesightBubble,
    INITIAL_VISIBILITY_SECONDS,
    MAX_DURATION_SECONDS,
)
from server.telegraph_visibility_gate import (
    TelegraphVisibilityGate, VisibilitySource,
)


def test_cast_indi_happy():
    g = GeoForesightBubble()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    assert out.accepted is True
    assert out.flavor == ForesightFlavor.INDI_FORESIGHT
    assert out.mp_cost == CAST_MP_COST


def test_cast_geo_requires_anchor():
    g = GeoForesightBubble()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.GEO_FORESIGHT,
        now_seconds=10,
    )
    assert out.accepted is False


def test_cast_geo_with_anchor():
    g = GeoForesightBubble()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.GEO_FORESIGHT,
        anchor_id="luopan_1", now_seconds=10,
    )
    assert out.accepted is True


def test_blank_caster_blocked():
    g = GeoForesightBubble()
    out = g.cast(
        caster_id="", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    assert out.accepted is False


def test_double_cast_same_flavor_blocked():
    g = GeoForesightBubble()
    g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=20,
    )
    assert out.accepted is False


def test_both_flavors_can_coexist():
    g = GeoForesightBubble()
    out1 = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    out2 = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.GEO_FORESIGHT,
        anchor_id="luopan_1", now_seconds=11,
    )
    assert out1.accepted is True
    assert out2.accepted is True


def test_tick_grants_visibility_to_allies():
    g = GeoForesightBubble()
    gate = TelegraphVisibilityGate()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    n = g.tick(
        bubble_id=out.bubble_id, now_seconds=11,
        allies_in_radius=["bob", "carol"], gate=gate,
    )
    assert n == 2
    assert gate.is_visible(player_id="bob", now_seconds=12) is True
    assert gate.is_visible(player_id="carol", now_seconds=12) is True


def test_visibility_expires_after_grant():
    g = GeoForesightBubble()
    gate = TelegraphVisibilityGate()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    g.tick(
        bubble_id=out.bubble_id, now_seconds=11,
        allies_in_radius=["bob"], gate=gate,
    )
    # past INITIAL_VISIBILITY_SECONDS
    assert gate.is_visible(
        player_id="bob",
        now_seconds=11 + INITIAL_VISIBILITY_SECONDS + 1,
    ) is False


def test_tick_after_max_duration_ends_bubble():
    g = GeoForesightBubble()
    gate = TelegraphVisibilityGate()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=0,
    )
    g.tick(
        bubble_id=out.bubble_id,
        now_seconds=MAX_DURATION_SECONDS + 1,
        allies_in_radius=["bob"], gate=gate,
    )
    # bubble should be ended; subsequent tick yields 0
    n = g.tick(
        bubble_id=out.bubble_id,
        now_seconds=MAX_DURATION_SECONDS + 5,
        allies_in_radius=["bob"], gate=gate,
    )
    assert n == 0


def test_geo_luopan_hp_drains():
    g = GeoForesightBubble()
    gate = TelegraphVisibilityGate()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.GEO_FORESIGHT,
        anchor_id="luopan_1", now_seconds=10,
    )
    # tick 100 seconds at 5 hp/sec = 500 lost; hp = 100
    g.tick(
        bubble_id=out.bubble_id, now_seconds=11,
        allies_in_radius=["bob"], gate=gate,
        dt_seconds=100,
    )
    b = g.active_bubble(
        caster_id="geo_alice", flavor=ForesightFlavor.GEO_FORESIGHT,
    )
    assert b is not None
    assert b.luopan_hp == 100


def test_geo_luopan_dies_ends_bubble():
    g = GeoForesightBubble()
    gate = TelegraphVisibilityGate()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.GEO_FORESIGHT,
        anchor_id="luopan_1", now_seconds=10,
    )
    # drain enough to kill it
    g.tick(
        bubble_id=out.bubble_id, now_seconds=11,
        allies_in_radius=["bob"], gate=gate,
        dt_seconds=GEO_LUOPAN_HP // 5 + 5,
    )
    assert g.active_bubble(
        caster_id="geo_alice", flavor=ForesightFlavor.GEO_FORESIGHT,
    ) is None


def test_damage_luopan_kills_it():
    g = GeoForesightBubble()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.GEO_FORESIGHT,
        anchor_id="luopan_1", now_seconds=10,
    )
    g.damage_luopan(bubble_id=out.bubble_id, amount=GEO_LUOPAN_HP)
    assert g.active_bubble(
        caster_id="geo_alice", flavor=ForesightFlavor.GEO_FORESIGHT,
    ) is None


def test_damage_indi_returns_false():
    g = GeoForesightBubble()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    assert g.damage_luopan(
        bubble_id=out.bubble_id, amount=100,
    ) is False


def test_end_bubble_explicitly():
    g = GeoForesightBubble()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    assert g.end_bubble(bubble_id=out.bubble_id) is True
    assert g.active_bubble(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
    ) is None


def test_recast_after_ending():
    g = GeoForesightBubble()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    g.end_bubble(bubble_id=out.bubble_id)
    # recast allowed
    out2 = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=20,
    )
    assert out2.accepted is True


def test_tick_unknown_bubble_no_effect():
    g = GeoForesightBubble()
    gate = TelegraphVisibilityGate()
    n = g.tick(
        bubble_id="ghost", now_seconds=10,
        allies_in_radius=["bob"], gate=gate,
    )
    assert n == 0


def test_default_radius():
    assert DEFAULT_RADIUS_YALMS == 8


def test_visibility_source_is_geo_foresight():
    g = GeoForesightBubble()
    gate = TelegraphVisibilityGate()
    out = g.cast(
        caster_id="geo_alice", flavor=ForesightFlavor.INDI_FORESIGHT,
        now_seconds=10,
    )
    g.tick(
        bubble_id=out.bubble_id, now_seconds=11,
        allies_in_radius=["bob"], gate=gate,
    )
    sources = gate.active_sources(player_id="bob", now_seconds=12)
    assert VisibilitySource.GEO_FORESIGHT in sources
