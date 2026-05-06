"""Tests for secret_passage."""
from __future__ import annotations

from server.secret_passage import (
    ConditionKind,
    PassageOutcome,
    SecretPassageRegistry,
    UnlockCondition,
)


def _setup_simple():
    r = SecretPassageRegistry()
    r.define_passage(
        passage_id="storm_path",
        source_zone_id="ronfaure",
        target_zone_id="north_gustav",
        conditions=[
            UnlockCondition(
                kind=ConditionKind.WEATHER,
                expected="thunderstorm",
            ),
        ],
    )
    return r


def test_define_passage_happy():
    r = _setup_simple()
    assert r.total_passages() == 1


def test_blank_id_blocked():
    r = SecretPassageRegistry()
    out = r.define_passage(
        passage_id="", source_zone_id="a",
        target_zone_id="b",
        conditions=[
            UnlockCondition(kind=ConditionKind.WEATHER, expected="x")
        ],
    )
    assert out is False


def test_blank_zones_blocked():
    r = SecretPassageRegistry()
    out = r.define_passage(
        passage_id="x", source_zone_id="",
        target_zone_id="b",
        conditions=[
            UnlockCondition(kind=ConditionKind.WEATHER, expected="x")
        ],
    )
    assert out is False


def test_same_zone_blocked():
    r = SecretPassageRegistry()
    out = r.define_passage(
        passage_id="x", source_zone_id="a",
        target_zone_id="a",
        conditions=[
            UnlockCondition(kind=ConditionKind.WEATHER, expected="x")
        ],
    )
    assert out is False


def test_no_conditions_blocked():
    r = SecretPassageRegistry()
    out = r.define_passage(
        passage_id="x", source_zone_id="a",
        target_zone_id="b", conditions=[],
    )
    assert out is False


def test_duplicate_passage_blocked():
    r = _setup_simple()
    again = r.define_passage(
        passage_id="storm_path", source_zone_id="a",
        target_zone_id="b",
        conditions=[
            UnlockCondition(kind=ConditionKind.WEATHER, expected="x")
        ],
    )
    assert again is False


def test_attempt_unknown_passage():
    r = SecretPassageRegistry()
    out = r.attempt_passage(
        passage_id="ghost", player_id="alice",
        attempted_at=10,
    )
    assert out == PassageOutcome.UNKNOWN_PASSAGE


def test_attempt_blank_player():
    r = _setup_simple()
    out = r.attempt_passage(
        passage_id="storm_path", player_id="",
        active_weather="thunderstorm", attempted_at=10,
    )
    assert out == PassageOutcome.INVALID_PLAYER


def test_weather_match_opens():
    r = _setup_simple()
    out = r.attempt_passage(
        passage_id="storm_path", player_id="alice",
        active_weather="thunderstorm", attempted_at=10,
    )
    assert out == PassageOutcome.OPEN


def test_weather_mismatch_blocks():
    r = _setup_simple()
    out = r.attempt_passage(
        passage_id="storm_path", player_id="alice",
        active_weather="clear", attempted_at=10,
    )
    assert out == PassageOutcome.BLOCKED


def test_first_discoverer_recorded():
    r = _setup_simple()
    r.attempt_passage(
        passage_id="storm_path", player_id="alice",
        active_weather="thunderstorm", attempted_at=10,
    )
    assert r.first_discoverer(passage_id="storm_path") == "alice"


def test_first_discoverer_does_not_change():
    r = _setup_simple()
    r.attempt_passage(
        passage_id="storm_path", player_id="alice",
        active_weather="thunderstorm", attempted_at=10,
    )
    r.attempt_passage(
        passage_id="storm_path", player_id="bob",
        active_weather="thunderstorm", attempted_at=20,
    )
    assert r.first_discoverer(passage_id="storm_path") == "alice"


def test_time_of_day_condition():
    r = SecretPassageRegistry()
    r.define_passage(
        passage_id="night_path", source_zone_id="a",
        target_zone_id="b",
        conditions=[
            UnlockCondition(
                kind=ConditionKind.TIME_OF_DAY, expected="night",
            ),
        ],
    )
    out = r.attempt_passage(
        passage_id="night_path", player_id="alice",
        time_of_day="day", attempted_at=10,
    )
    assert out == PassageOutcome.BLOCKED
    out = r.attempt_passage(
        passage_id="night_path", player_id="alice",
        time_of_day="night", attempted_at=20,
    )
    assert out == PassageOutcome.OPEN


def test_key_item_condition():
    r = SecretPassageRegistry()
    r.define_passage(
        passage_id="locked", source_zone_id="a",
        target_zone_id="b",
        conditions=[
            UnlockCondition(
                kind=ConditionKind.KEY_ITEM, expected="brass_key",
            ),
        ],
    )
    out = r.attempt_passage(
        passage_id="locked", player_id="alice",
        key_items=["wooden_key", "iron_key"], attempted_at=10,
    )
    assert out == PassageOutcome.BLOCKED
    out = r.attempt_passage(
        passage_id="locked", player_id="alice",
        key_items=["brass_key"], attempted_at=20,
    )
    assert out == PassageOutcome.OPEN


def test_npc_proximity_condition():
    r = SecretPassageRegistry()
    r.define_passage(
        passage_id="guarded", source_zone_id="a",
        target_zone_id="b",
        conditions=[
            UnlockCondition(
                kind=ConditionKind.NPC_PROXIMITY,
                expected="guide_npc",
            ),
        ],
    )
    out = r.attempt_passage(
        passage_id="guarded", player_id="alice",
        nearby_npcs=["guide_npc"], attempted_at=10,
    )
    assert out == PassageOutcome.OPEN


def test_multiple_conditions_all_must_match():
    r = SecretPassageRegistry()
    r.define_passage(
        passage_id="hard", source_zone_id="a",
        target_zone_id="b",
        conditions=[
            UnlockCondition(kind=ConditionKind.WEATHER, expected="rain"),
            UnlockCondition(kind=ConditionKind.TIME_OF_DAY, expected="night"),
            UnlockCondition(kind=ConditionKind.KEY_ITEM, expected="signet"),
        ],
    )
    # all match → open
    out = r.attempt_passage(
        passage_id="hard", player_id="alice",
        active_weather="rain", time_of_day="night",
        key_items=["signet"], attempted_at=10,
    )
    assert out == PassageOutcome.OPEN
    # one fails → blocked
    out = r.attempt_passage(
        passage_id="hard", player_id="alice",
        active_weather="rain", time_of_day="day",
        key_items=["signet"], attempted_at=20,
    )
    assert out == PassageOutcome.BLOCKED


def test_use_count_increments():
    r = _setup_simple()
    for _ in range(5):
        r.attempt_passage(
            passage_id="storm_path", player_id="alice",
            active_weather="thunderstorm", attempted_at=10,
        )
    p = r.get(passage_id="storm_path")
    assert p is not None
    assert p.use_count == 5


def test_blocked_does_not_count_use():
    r = _setup_simple()
    r.attempt_passage(
        passage_id="storm_path", player_id="alice",
        active_weather="clear", attempted_at=10,
    )
    p = r.get(passage_id="storm_path")
    assert p is not None
    assert p.use_count == 0


def test_five_condition_kinds():
    assert len(list(ConditionKind)) == 5


def test_season_condition():
    r = SecretPassageRegistry()
    r.define_passage(
        passage_id="bloom", source_zone_id="a", target_zone_id="b",
        conditions=[
            UnlockCondition(kind=ConditionKind.SEASON, expected="spring")
        ],
    )
    out = r.attempt_passage(
        passage_id="bloom", player_id="alice",
        season="winter", attempted_at=10,
    )
    assert out == PassageOutcome.BLOCKED
    out = r.attempt_passage(
        passage_id="bloom", player_id="alice",
        season="spring", attempted_at=20,
    )
    assert out == PassageOutcome.OPEN


def test_four_passage_outcomes():
    assert len(list(PassageOutcome)) == 4
