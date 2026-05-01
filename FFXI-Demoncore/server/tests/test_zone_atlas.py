"""Tests for the canonical FFXI zone atlas."""
from __future__ import annotations

import pytest

from server.zone_atlas import (
    ZONES,
    Zone,
    ZoneTier,
    adjacent_zones,
    edge_count,
    get_zone,
    is_known_zone,
    shortest_path,
    zone_count,
    zones_in_nation,
    zones_in_tier,
    zones_with_family,
)


# -- table integrity ---------------------------------------------------

def test_zone_count_matches_table():
    assert zone_count() == len(ZONES)
    assert zone_count() >= 40   # representative atlas, not exhaustive


def test_zone_ids_are_unique():
    # ZONES dict is built from a tuple; if any duplicates existed the
    # later one would silently win, so cross-check counts.
    seen = set()
    for zid in ZONES:
        assert zid not in seen, f"duplicate zone_id {zid}"
        seen.add(zid)


def test_every_zone_has_label_and_tier():
    for z in ZONES.values():
        assert isinstance(z, Zone)
        assert z.label
        assert isinstance(z.tier, ZoneTier)
        assert z.nation in {"bastok", "sandy", "windy",
                            "neutral", "aht_urhgan"}


def test_known_zone_helper():
    assert is_known_zone("bastok_mines")
    assert not is_known_zone("does_not_exist")


def test_get_zone_returns_dataclass():
    z = get_zone("bastok_mines")
    assert z.zone_id == "bastok_mines"
    assert z.tier == ZoneTier.NATION_CITY
    assert z.is_town_safe is True


def test_get_zone_unknown_raises():
    with pytest.raises(KeyError):
        get_zone("not_a_real_zone")


# -- adjacency ---------------------------------------------------------

def test_adjacency_is_symmetric():
    """If A lists B as adjacent, B must list A."""
    for zid in ZONES:
        for nb in adjacent_zones(zid):
            assert zid in adjacent_zones(nb), (
                f"{zid}->{nb} not mirrored"
            )


def test_no_self_adjacency():
    for zid in ZONES:
        assert zid not in adjacent_zones(zid)


def test_adjacency_only_references_known_zones():
    for zid in ZONES:
        for nb in adjacent_zones(zid):
            assert is_known_zone(nb), f"{nb} unknown but adjacent to {zid}"


def test_adjacent_unknown_zone_returns_empty():
    assert adjacent_zones("not_a_real_zone") == ()


def test_edge_count_positive():
    assert edge_count() > 0


def test_bastok_adjacent_to_south_gustaberg():
    """Sanity check on the city outskirts pattern."""
    assert "south_gustaberg" in adjacent_zones("bastok_mines")


def test_jeuno_is_central_hub():
    # Lower Jeuno should be reachable from each nation's mid-tier ring.
    lower_jeuno_neighbors = set(adjacent_zones("lower_jeuno"))
    assert "rolanberry_fields" in lower_jeuno_neighbors  # bastok side
    assert "jugner_forest" in lower_jeuno_neighbors      # sandy side
    assert "buburimu_peninsula" in lower_jeuno_neighbors  # windy side


# -- tier / nation / family lookups ------------------------------------

def test_zones_in_tier_newbie_includes_starter_zones():
    newbie_ids = {z.zone_id for z in zones_in_tier(ZoneTier.NEWBIE)}
    assert "south_gustaberg" in newbie_ids
    assert "east_ronfaure" in newbie_ids
    assert "east_sarutabaruta" in newbie_ids


def test_zones_in_tier_end_game_includes_dynamis():
    eg = {z.zone_id for z in zones_in_tier(ZoneTier.END_GAME)}
    assert "dynamis_bastok" in eg
    assert "sky" in eg
    assert "sea" in eg


def test_zones_in_nation_bastok():
    bastok_ids = {z.zone_id for z in zones_in_nation("bastok")}
    assert "bastok_mines" in bastok_ids
    assert "beadeaux" in bastok_ids
    # Sandy-side zone should NOT show up.
    assert "davoi" not in bastok_ids


def test_zones_in_nation_neutral_covers_jeuno():
    ids = {z.zone_id for z in zones_in_nation("neutral")}
    assert "lower_jeuno" in ids
    assert "port_jeuno" in ids
    assert "selbina" in ids


def test_zones_with_family_quadav_lives_in_beadeaux():
    zones = zones_with_family("quadav")
    ids = {z.zone_id for z in zones}
    assert "beadeaux" in ids


def test_zones_with_family_yagudo_lives_around_windy():
    zones = zones_with_family("yagudo")
    ids = {z.zone_id for z in zones}
    assert "castle_oztroja" in ids
    assert "tahrongi_canyon" in ids
    # Bastok-side zone should NOT spawn yagudo natively.
    assert "south_gustaberg" not in ids


def test_zones_with_family_unknown_returns_empty():
    assert zones_with_family("not_a_real_family") == ()


def test_town_safe_zones_have_no_native_mobs():
    """Town-safe zones don't list native mob families — they are the
    nation safe zones referenced by hardcore_death."""
    for z in ZONES.values():
        if z.is_town_safe:
            assert z.native_families == (), (
                f"{z.zone_id} marked town-safe but has native mobs"
            )


def test_outposts_are_marked_town_safe():
    """Selbina/Mhaura/Norg are waypoints, not combat zones."""
    for z in ZONES.values():
        if z.is_outpost:
            assert z.is_town_safe is True


# -- shortest path -----------------------------------------------------

def test_shortest_path_same_zone_is_single_node():
    assert shortest_path(src="bastok_mines", dst="bastok_mines") == (
        "bastok_mines",
    )


def test_shortest_path_adjacent_pair_is_length_2():
    p = shortest_path(src="bastok_mines", dst="bastok_markets")
    assert p == ("bastok_mines", "bastok_markets")


def test_shortest_path_cross_nation_via_jeuno():
    """Bastok's Beadeaux -> Sandy's Davoi must traverse Jeuno."""
    p = shortest_path(src="beadeaux", dst="davoi")
    assert p is not None
    assert p[0] == "beadeaux"
    assert p[-1] == "davoi"
    assert "lower_jeuno" in p


def test_shortest_path_unknown_zone_returns_none():
    assert shortest_path(src="bastok_mines", dst="not_a_zone") is None
    assert shortest_path(src="not_a_zone", dst="bastok_mines") is None


def test_shortest_path_endgame_reachable_from_starter():
    """A level-1 player in South Gustaberg must theoretically be able
    to walk (chain zones) to Sky via Jeuno + Port Jeuno."""
    p = shortest_path(src="south_gustaberg", dst="sky")
    assert p is not None
    assert p[0] == "south_gustaberg"
    assert p[-1] == "sky"
    # The path should walk through port_jeuno (where the airship to
    # sky launches).
    assert "port_jeuno" in p


def test_shortest_path_returns_consecutive_adjacent_zones():
    """Each pair in the returned path must actually share an edge."""
    p = shortest_path(src="south_gustaberg", dst="castle_oztroja")
    assert p is not None
    for a, b in zip(p, p[1:]):
        assert b in adjacent_zones(a), (
            f"path step {a}->{b} not adjacent"
        )


# -- composition with other modules ------------------------------------

def test_atlas_supports_hardcore_death_boss_assist_lookup():
    """boss_assist eligibility checks 'in boss zone or adjacent zone'.
    The atlas must answer adjacency queries for every zone."""
    boss_zone = "phomiuna_aqueducts"
    adj = adjacent_zones(boss_zone)
    assert isinstance(adj, tuple)
    # Not strictly required to be non-empty, but Phomiuna in our atlas
    # connects out to Lower Jeuno.
    assert "lower_jeuno" in adj


def test_atlas_covers_all_three_starter_nations():
    nations = {z.nation for z in ZONES.values()}
    assert {"bastok", "sandy", "windy"}.issubset(nations)
