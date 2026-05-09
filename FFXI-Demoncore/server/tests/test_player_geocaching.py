"""Tests for player_geocaching."""
from __future__ import annotations

from server.player_geocaching import (
    PlayerGeocachingSystem, CacheState,
)


def _hide(s: PlayerGeocachingSystem) -> str:
    return s.hide_cache(
        hider_id="naji", zone_id="ronfaure",
        coord_x=100, coord_y=200,
        clue="Beneath the third oak west of the river.",
    )


def test_hide_happy():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    assert cid is not None


def test_hide_empty_hider_blocked():
    s = PlayerGeocachingSystem()
    assert s.hide_cache(
        hider_id="", zone_id="z",
        coord_x=10, coord_y=10, clue="c",
    ) is None


def test_hide_empty_clue_blocked():
    s = PlayerGeocachingSystem()
    assert s.hide_cache(
        hider_id="x", zone_id="z",
        coord_x=10, coord_y=10, clue="",
    ) is None


def test_hide_invalid_coord():
    s = PlayerGeocachingSystem()
    assert s.hide_cache(
        hider_id="x", zone_id="z",
        coord_x=2000, coord_y=10, clue="c",
    ) is None
    assert s.hide_cache(
        hider_id="x", zone_id="z",
        coord_x=10, coord_y=-5, clue="c",
    ) is None


def test_attempt_find_exact_match():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    fid = s.attempt_find(
        cache_id=cid, finder_id="bob",
        guess_x=100, guess_y=200, found_day=10,
    )
    assert fid is not None


def test_attempt_find_within_tolerance():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    fid = s.attempt_find(
        cache_id=cid, finder_id="bob",
        guess_x=103, guess_y=197, found_day=10,
    )
    assert fid is not None


def test_attempt_find_outside_tolerance():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    assert s.attempt_find(
        cache_id=cid, finder_id="bob",
        guess_x=120, guess_y=200, found_day=10,
    ) is None


def test_attempt_find_hider_blocked():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    assert s.attempt_find(
        cache_id=cid, finder_id="naji",
        guess_x=100, guess_y=200, found_day=10,
    ) is None


def test_attempt_find_duplicate_finder_blocked():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    s.attempt_find(
        cache_id=cid, finder_id="bob",
        guess_x=100, guess_y=200, found_day=10,
    )
    assert s.attempt_find(
        cache_id=cid, finder_id="bob",
        guess_x=100, guess_y=200, found_day=11,
    ) is None


def test_multiple_finders_ok():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    s.attempt_find(
        cache_id=cid, finder_id="bob",
        guess_x=100, guess_y=200, found_day=10,
    )
    fid = s.attempt_find(
        cache_id=cid, finder_id="cara",
        guess_x=100, guess_y=200, found_day=11,
    )
    assert fid is not None
    assert s.cache(cache_id=cid).find_count == 2


def test_attempt_find_unknown_cache():
    s = PlayerGeocachingSystem()
    assert s.attempt_find(
        cache_id="ghost", finder_id="bob",
        guess_x=10, guess_y=10, found_day=10,
    ) is None


def test_attempt_find_negative_day():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    assert s.attempt_find(
        cache_id=cid, finder_id="bob",
        guess_x=100, guess_y=200, found_day=-1,
    ) is None


def test_retire_happy():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    assert s.retire(
        cache_id=cid, hider_id="naji",
    ) is True


def test_retire_wrong_hider_blocked():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    assert s.retire(
        cache_id=cid, hider_id="bob",
    ) is False


def test_retire_double_blocked():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    s.retire(cache_id=cid, hider_id="naji")
    assert s.retire(
        cache_id=cid, hider_id="naji",
    ) is False


def test_attempt_find_after_retire_blocked():
    s = PlayerGeocachingSystem()
    cid = _hide(s)
    s.retire(cache_id=cid, hider_id="naji")
    assert s.attempt_find(
        cache_id=cid, finder_id="bob",
        guess_x=100, guess_y=200, found_day=10,
    ) is None


def test_hider_fame_aggregates():
    s = PlayerGeocachingSystem()
    cid_a = _hide(s)
    cid_b = s.hide_cache(
        hider_id="naji", zone_id="ronfaure",
        coord_x=300, coord_y=400, clue="other clue",
    )
    s.attempt_find(
        cache_id=cid_a, finder_id="bob",
        guess_x=100, guess_y=200, found_day=10,
    )
    s.attempt_find(
        cache_id=cid_a, finder_id="cara",
        guess_x=100, guess_y=200, found_day=11,
    )
    s.attempt_find(
        cache_id=cid_b, finder_id="dave",
        guess_x=300, guess_y=400, found_day=12,
    )
    assert s.hider_fame(hider_id="naji") == 3


def test_finder_count_aggregates():
    s = PlayerGeocachingSystem()
    cid_a = _hide(s)
    cid_b = s.hide_cache(
        hider_id="naji", zone_id="ronfaure",
        coord_x=500, coord_y=600, clue="another",
    )
    s.attempt_find(
        cache_id=cid_a, finder_id="bob",
        guess_x=100, guess_y=200, found_day=10,
    )
    s.attempt_find(
        cache_id=cid_b, finder_id="bob",
        guess_x=500, guess_y=600, found_day=11,
    )
    assert s.finder_count(finder_id="bob") == 2


def test_caches_in_zone_filters_state():
    s = PlayerGeocachingSystem()
    cid_a = _hide(s)
    cid_b = s.hide_cache(
        hider_id="naji", zone_id="ronfaure",
        coord_x=500, coord_y=600, clue="another",
    )
    s.retire(cache_id=cid_b, hider_id="naji")
    in_zone = s.caches_in_zone(zone_id="ronfaure")
    # Only the still-hidden one
    assert len(in_zone) == 1
    assert in_zone[0].cache_id == cid_a


def test_unknown_cache():
    s = PlayerGeocachingSystem()
    assert s.cache(cache_id="ghost") is None


def test_unknown_find():
    s = PlayerGeocachingSystem()
    assert s.find(find_id="ghost") is None


def test_enum_count():
    assert len(list(CacheState)) == 2
