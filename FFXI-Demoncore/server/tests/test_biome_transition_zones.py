"""Tests for biome transition zones."""
from __future__ import annotations

from server.biome_transition_zones import (
    BiomeKind,
    BiomeTransitionZones,
    GateKind,
)


def test_register_happy():
    z = BiomeTransitionZones()
    assert z.register(
        transit_id="harbor",
        name="Bastok Harbor",
        zone_id="bastok_markets", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
    ) is True


def test_register_blank_id():
    z = BiomeTransitionZones()
    assert z.register(
        transit_id="", name="X",
        zone_id="z", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
    ) is False


def test_register_same_biome_blocked():
    z = BiomeTransitionZones()
    assert z.register(
        transit_id="t1", name="X", zone_id="z", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_LAND,
    ) is False


def test_register_double_blocked():
    z = BiomeTransitionZones()
    z.register(
        transit_id="t1", name="X", zone_id="z", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
    )
    assert z.register(
        transit_id="t1", name="Y", zone_id="z", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
    ) is False


def test_transitions_at_returns_match():
    z = BiomeTransitionZones()
    z.register(
        transit_id="harbor", name="Harbor",
        zone_id="bastok", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
    )
    out = z.transitions_at(zone_id="bastok", band=0)
    assert len(out) == 1
    assert out[0].name == "Harbor"


def test_transitions_at_filters_by_band():
    z = BiomeTransitionZones()
    z.register(
        transit_id="harbor", name="Harbor",
        zone_id="bastok", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
    )
    out = z.transitions_at(zone_id="bastok", band=2)
    assert out == ()


def test_can_transit_ungated_ok():
    z = BiomeTransitionZones()
    z.register(
        transit_id="t1", name="X",
        zone_id="z", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
    )
    ok, _ = z.can_transit(transit_id="t1")
    assert ok is True


def test_can_transit_unknown():
    z = BiomeTransitionZones()
    ok, reason = z.can_transit(transit_id="ghost")
    assert ok is False
    assert reason == "unknown transit"


def test_can_transit_key_item_blocked():
    z = BiomeTransitionZones()
    z.register(
        transit_id="t1", name="Sub Bay",
        zone_id="norg", band=0,
        from_biome=BiomeKind.SURFACE_SEA,
        to_biome=BiomeKind.DEEP,
        gate_kind=GateKind.KEY_ITEM,
        gate_key="submersible_pass",
    )
    ok, reason = z.can_transit(transit_id="t1")
    assert ok is False
    assert reason == "missing key item"


def test_can_transit_key_item_with_key():
    z = BiomeTransitionZones()
    z.register(
        transit_id="t1", name="Sub Bay",
        zone_id="norg", band=0,
        from_biome=BiomeKind.SURFACE_SEA,
        to_biome=BiomeKind.DEEP,
        gate_kind=GateKind.KEY_ITEM,
        gate_key="submersible_pass",
    )
    ok, _ = z.can_transit(
        transit_id="t1",
        player_keys=["submersible_pass"],
    )
    assert ok is True


def test_can_transit_faction_rep_blocked():
    z = BiomeTransitionZones()
    z.register(
        transit_id="aerie", name="Wyvern Aerie",
        zone_id="reisen", band=3,
        from_biome=BiomeKind.MID,
        to_biome=BiomeKind.STRATOSPHERE,
        gate_kind=GateKind.FACTION_REP,
        gate_key="wyvern_lords",
        gate_threshold=25,
    )
    ok, _ = z.can_transit(
        transit_id="aerie",
        faction_reps={"wyvern_lords": 10},
    )
    assert ok is False


def test_can_transit_faction_rep_with_threshold():
    z = BiomeTransitionZones()
    z.register(
        transit_id="aerie", name="Wyvern Aerie",
        zone_id="reisen", band=3,
        from_biome=BiomeKind.MID,
        to_biome=BiomeKind.STRATOSPHERE,
        gate_kind=GateKind.FACTION_REP,
        gate_key="wyvern_lords",
        gate_threshold=25,
    )
    ok, _ = z.can_transit(
        transit_id="aerie",
        faction_reps={"wyvern_lords": 30},
    )
    assert ok is True


def test_path_same_biome_empty():
    z = BiomeTransitionZones()
    p = z.find_path_across_biomes(
        start_biome=BiomeKind.SURFACE_LAND,
        end_biome=BiomeKind.SURFACE_LAND,
    )
    assert p == ()


def test_path_one_hop():
    z = BiomeTransitionZones()
    z.register(
        transit_id="harbor", name="Harbor",
        zone_id="bastok", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
    )
    p = z.find_path_across_biomes(
        start_biome=BiomeKind.SURFACE_LAND,
        end_biome=BiomeKind.SURFACE_SEA,
    )
    assert p is not None
    assert len(p) == 1


def test_path_multi_hop():
    z = BiomeTransitionZones()
    # surface land -> surface sea -> deep
    z.register(
        transit_id="harbor", name="Harbor",
        zone_id="bastok", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
    )
    z.register(
        transit_id="sub_bay", name="Sub Bay",
        zone_id="norg", band=0,
        from_biome=BiomeKind.SURFACE_SEA,
        to_biome=BiomeKind.DEEP,
    )
    p = z.find_path_across_biomes(
        start_biome=BiomeKind.SURFACE_LAND,
        end_biome=BiomeKind.DEEP,
    )
    assert p is not None
    assert len(p) == 2


def test_path_unreachable():
    z = BiomeTransitionZones()
    p = z.find_path_across_biomes(
        start_biome=BiomeKind.SURFACE_LAND,
        end_biome=BiomeKind.STRATOSPHERE,
    )
    assert p is None


def test_path_uses_bidirectional_in_reverse():
    z = BiomeTransitionZones()
    z.register(
        transit_id="harbor", name="Harbor",
        zone_id="bastok", band=0,
        from_biome=BiomeKind.SURFACE_LAND,
        to_biome=BiomeKind.SURFACE_SEA,
        bidirectional=True,
    )
    # can go SEA -> LAND too
    p = z.find_path_across_biomes(
        start_biome=BiomeKind.SURFACE_SEA,
        end_biome=BiomeKind.SURFACE_LAND,
    )
    assert p is not None
    assert len(p) == 1
