"""Tests for the wanted poster system."""
from __future__ import annotations

from server.wanted_poster import (
    CrimeKind,
    NotorietyTier,
    TIER_2_NOTORIETY,
    TIER_3_NOTORIETY,
    TIER_5_NOTORIETY,
    WantedPosterRegistry,
)


def test_no_crime_no_poster():
    reg = WantedPosterRegistry()
    assert reg.poster_for("alice") is None


def test_first_crime_creates_poster():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.THEFT,
        zone_id="bastok",
    )
    poster = reg.poster_for("alice")
    assert poster is not None
    assert poster.notoriety == 5
    assert poster.tier == NotorietyTier.NONE


def test_tier_1_after_50_notoriety():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.MURDER,
        zone_id="bastok",
    )
    poster = reg.poster_for("alice")
    assert poster.tier == NotorietyTier.TIER_1


def test_tier_2_posts_in_three_nations():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.MURDER,
        zone_id="bastok", magnitude=4,
    )
    poster = reg.poster_for("alice")
    assert poster.notoriety == 200
    assert poster.tier == NotorietyTier.TIER_2
    assert "bastok" in poster.posted_zones
    assert "san_doria" in poster.posted_zones


def test_tier_3_adds_beastman_camp():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.TREASON,
        zone_id="bastok", magnitude=2,
    )
    # 200 * 2 = 400 -> TIER_3
    poster = reg.poster_for("alice")
    assert poster.tier == NotorietyTier.TIER_3
    assert "beastman_camp" in poster.posted_zones


def test_tier_5_kill_on_sight():
    reg = WantedPosterRegistry()
    for _ in range(10):
        reg.report_crime(
            player_id="alice",
            kind=CrimeKind.TREASON,
            zone_id="bastok",
        )
    poster = reg.poster_for("alice")
    assert poster.tier == NotorietyTier.TIER_5
    assert poster.notoriety >= TIER_5_NOTORIETY
    assert "norg" in poster.posted_zones


def test_bounty_scales_with_tier():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.MURDER,
        zone_id="bastok",
    )
    tier_1 = reg.poster_for("alice").bounty_gil
    reg.report_crime(
        player_id="alice", kind=CrimeKind.MURDER,
        zone_id="bastok", magnitude=5,
    )
    tier_2_or_higher = reg.poster_for("alice").bounty_gil
    assert tier_2_or_higher > tier_1


def test_clear_notoriety_succeeds():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.MURDER,
        zone_id="bastok",
    )
    assert reg.clear_notoriety(player_id="alice")
    poster = reg.poster_for("alice")
    assert poster.notoriety == 0
    assert poster.tier == NotorietyTier.NONE
    assert poster.bounty_gil == 0
    assert poster.posted_zones == []


def test_clear_unknown_returns_false():
    reg = WantedPosterRegistry()
    assert not reg.clear_notoriety(player_id="ghost")


def test_clear_no_notoriety_returns_false():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.THEFT,
        zone_id="bastok",
    )
    reg.clear_notoriety(player_id="alice")
    # Already cleared
    assert not reg.clear_notoriety(player_id="alice")


def test_reduce_notoriety_partial():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.MURDER,
        zone_id="bastok", magnitude=5,
    )
    new_notoriety = reg.reduce_notoriety(
        player_id="alice", amount=100,
    )
    assert new_notoriety == 150


def test_reduce_below_tier_demotes():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.MURDER,
        zone_id="bastok", magnitude=4,
    )
    # 200 = TIER_2
    reg.reduce_notoriety(
        player_id="alice", amount=100,
    )
    # 100 -> TIER_1
    assert reg.poster_for("alice").tier == NotorietyTier.TIER_1


def test_reduce_unknown_returns_none():
    reg = WantedPosterRegistry()
    assert reg.reduce_notoriety(
        player_id="ghost", amount=10,
    ) is None


def test_reduce_invalid_amount_rejected():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.THEFT,
        zone_id="bastok",
    )
    assert reg.reduce_notoriety(
        player_id="alice", amount=0,
    ) is None


def test_posters_in_zone_filter():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.MURDER,
        zone_id="bastok", magnitude=4,
    )
    reg.report_crime(
        player_id="bob", kind=CrimeKind.THEFT,
        zone_id="bastok",
    )
    bastok_posters = reg.posters_in_zone("bastok")
    assert len(bastok_posters) == 1
    assert bastok_posters[0].player_id == "alice"


def test_crimes_logged_persist():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="alice", kind=CrimeKind.MURDER,
        zone_id="bastok",
    )
    reg.report_crime(
        player_id="alice", kind=CrimeKind.ARSON,
        zone_id="bastok",
    )
    poster = reg.poster_for("alice")
    assert CrimeKind.MURDER in poster.crimes_logged
    assert CrimeKind.ARSON in poster.crimes_logged


def test_total_posters():
    reg = WantedPosterRegistry()
    reg.report_crime(
        player_id="a", kind=CrimeKind.THEFT,
        zone_id="z",
    )
    reg.report_crime(
        player_id="b", kind=CrimeKind.THEFT,
        zone_id="z",
    )
    assert reg.total_posters() == 2


def test_tier_3_threshold_constants():
    assert TIER_2_NOTORIETY < TIER_3_NOTORIETY < TIER_5_NOTORIETY
