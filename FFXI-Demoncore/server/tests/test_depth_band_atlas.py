"""Tests for depth band atlas."""
from __future__ import annotations

from server.depth_band_atlas import (
    DepthBandAtlas,
    TransitionKind,
)


def test_register_zone_happy():
    a = DepthBandAtlas()
    ok = a.register_zone(zone_id="reef", available_bands=[1, 2, 3])
    assert ok is True
    assert a.bands_in(zone_id="reef") == (1, 2, 3)


def test_register_zone_blank():
    a = DepthBandAtlas()
    ok = a.register_zone(zone_id="", available_bands=[0])
    assert ok is False


def test_bands_in_unknown_zone():
    a = DepthBandAtlas()
    assert a.bands_in(zone_id="ghost") == ()


def test_add_transition_happy():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1, 2])
    ok = a.add_transition(
        from_zone="reef", from_band=1,
        to_zone="reef", to_band=2,
        kind=TransitionKind.DESCEND,
    )
    assert ok is True


def test_add_transition_unknown_zone():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1])
    ok = a.add_transition(
        from_zone="reef", from_band=1,
        to_zone="ghost", to_band=1,
        kind=TransitionKind.ZONE_LINE,
    )
    assert ok is False


def test_add_transition_invalid_band():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1, 2])
    ok = a.add_transition(
        from_zone="reef", from_band=99,
        to_zone="reef", to_band=2,
        kind=TransitionKind.DESCEND,
    )
    assert ok is False


def test_path_same_node():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1])
    p = a.path(
        start_zone="reef", start_band=1,
        end_zone="reef", end_band=1,
    )
    assert p == [("reef", 1)]


def test_path_simple_descend():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1, 2, 3])
    a.add_transition(
        from_zone="reef", from_band=1,
        to_zone="reef", to_band=2,
        kind=TransitionKind.DESCEND,
    )
    a.add_transition(
        from_zone="reef", from_band=2,
        to_zone="reef", to_band=3,
        kind=TransitionKind.DESCEND,
    )
    p = a.path(
        start_zone="reef", start_band=1,
        end_zone="reef", end_band=3,
    )
    assert p == [("reef", 1), ("reef", 2), ("reef", 3)]


def test_path_across_zones():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1, 2])
    a.register_zone(zone_id="trench", available_bands=[3, 4])
    a.add_transition(
        from_zone="reef", from_band=2,
        to_zone="trench", to_band=3,
        kind=TransitionKind.ZONE_LINE,
    )
    p = a.path(
        start_zone="reef", start_band=2,
        end_zone="trench", end_band=3,
    )
    assert p == [("reef", 2), ("trench", 3)]


def test_path_unreachable_returns_none():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1])
    a.register_zone(zone_id="trench", available_bands=[3])
    p = a.path(
        start_zone="reef", start_band=1,
        end_zone="trench", end_band=3,
    )
    assert p is None


def test_path_unknown_zone_returns_none():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1])
    p = a.path(
        start_zone="reef", start_band=1,
        end_zone="ghost", end_band=1,
    )
    assert p is None


def test_path_invalid_band_returns_none():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1])
    p = a.path(
        start_zone="reef", start_band=99,
        end_zone="reef", end_band=1,
    )
    assert p is None


def test_gated_transition_blocked_without_key():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1, 4])
    a.add_transition(
        from_zone="reef", from_band=1,
        to_zone="reef", to_band=4,
        kind=TransitionKind.DESCEND,
        gate_key_item="depth_gear",
    )
    p = a.path(
        start_zone="reef", start_band=1,
        end_zone="reef", end_band=4,
    )
    assert p is None


def test_gated_transition_works_with_key():
    a = DepthBandAtlas()
    a.register_zone(zone_id="reef", available_bands=[1, 4])
    a.add_transition(
        from_zone="reef", from_band=1,
        to_zone="reef", to_band=4,
        kind=TransitionKind.DESCEND,
        gate_key_item="depth_gear",
    )
    p = a.path(
        start_zone="reef", start_band=1,
        end_zone="reef", end_band=4,
        available_keys=["depth_gear"],
    )
    assert p == [("reef", 1), ("reef", 4)]


def test_bfs_picks_shortest_path():
    a = DepthBandAtlas()
    a.register_zone(zone_id="z", available_bands=[1, 2, 3, 4])
    # direct shortcut 1 -> 4
    a.add_transition(
        from_zone="z", from_band=1, to_zone="z", to_band=4,
        kind=TransitionKind.DESCEND,
    )
    # long way: 1 -> 2 -> 3 -> 4
    a.add_transition(
        from_zone="z", from_band=1, to_zone="z", to_band=2,
        kind=TransitionKind.DESCEND,
    )
    a.add_transition(
        from_zone="z", from_band=2, to_zone="z", to_band=3,
        kind=TransitionKind.DESCEND,
    )
    a.add_transition(
        from_zone="z", from_band=3, to_zone="z", to_band=4,
        kind=TransitionKind.DESCEND,
    )
    p = a.path(start_zone="z", start_band=1, end_zone="z", end_band=4)
    assert p == [("z", 1), ("z", 4)]


def test_path_through_gated_alternative():
    a = DepthBandAtlas()
    a.register_zone(zone_id="z", available_bands=[1, 2, 3])
    # gated direct
    a.add_transition(
        from_zone="z", from_band=1, to_zone="z", to_band=3,
        kind=TransitionKind.DESCEND, gate_key_item="suit",
    )
    # ungated indirect
    a.add_transition(
        from_zone="z", from_band=1, to_zone="z", to_band=2,
        kind=TransitionKind.DESCEND,
    )
    a.add_transition(
        from_zone="z", from_band=2, to_zone="z", to_band=3,
        kind=TransitionKind.DESCEND,
    )
    # without suit: must take long way
    p = a.path(
        start_zone="z", start_band=1, end_zone="z", end_band=3,
    )
    assert p == [("z", 1), ("z", 2), ("z", 3)]
    # with suit: shortcut
    p2 = a.path(
        start_zone="z", start_band=1, end_zone="z", end_band=3,
        available_keys=["suit"],
    )
    assert p2 == [("z", 1), ("z", 3)]
