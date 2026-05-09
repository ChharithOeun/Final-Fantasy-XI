"""Tests for chocobo_racing_track."""
from __future__ import annotations

from server.chocobo_racing_track import (
    ChocoboRacingTrackSystem, RaceState,
)


def _setup_full_field(s, race_id, field=4):
    for i in range(field):
        s.register_runner(
            race_id=race_id,
            chocobo_id=f"choco_{i}",
            owner_id=f"owner_{i}",
            speed=50 + i * 10,
            stamina=50 + i * 5,
        )


def test_schedule_happy():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="bastok_track",
        distance_furlongs=10,
    )
    assert rid is not None


def test_schedule_invalid_distance():
    s = ChocoboRacingTrackSystem()
    assert s.schedule_race(
        track_id="x", distance_furlongs=0,
    ) is None


def test_schedule_invalid_field():
    s = ChocoboRacingTrackSystem()
    assert s.schedule_race(
        track_id="x", distance_furlongs=10,
        field_min=8, field_max=4,
    ) is None


def test_register_runner_happy():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    runner_id = s.register_runner(
        race_id=rid, chocobo_id="choco_a",
        owner_id="bob", speed=70, stamina=60,
    )
    assert runner_id is not None


def test_register_dup_chocobo_blocked():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    s.register_runner(
        race_id=rid, chocobo_id="choco_a",
        owner_id="bob", speed=70, stamina=60,
    )
    second = s.register_runner(
        race_id=rid, chocobo_id="choco_a",
        owner_id="cara", speed=80, stamina=80,
    )
    assert second is None


def test_register_invalid_speed():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    runner_id = s.register_runner(
        race_id=rid, chocobo_id="x",
        owner_id="bob", speed=0, stamina=60,
    )
    assert runner_id is None


def test_register_field_full():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
        field_min=2, field_max=2,
    )
    s.register_runner(
        race_id=rid, chocobo_id="a", owner_id="o1",
        speed=50, stamina=50,
    )
    s.register_runner(
        race_id=rid, chocobo_id="b", owner_id="o2",
        speed=50, stamina=50,
    )
    assert s.register_runner(
        race_id=rid, chocobo_id="c", owner_id="o3",
        speed=50, stamina=50,
    ) is None


def test_open_bets_requires_min_field():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
        field_min=4,
    )
    s.register_runner(
        race_id=rid, chocobo_id="a", owner_id="o1",
        speed=50, stamina=50,
    )
    assert s.open_bets(race_id=rid) is False


def test_open_bets_happy():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s, rid, field=4)
    assert s.open_bets(race_id=rid) is True


def test_register_after_bets_open_blocked():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s, rid, field=4)
    s.open_bets(race_id=rid)
    assert s.register_runner(
        race_id=rid, chocobo_id="late",
        owner_id="x", speed=50, stamina=50,
    ) is None


def test_place_bet_happy():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s, rid, field=4)
    s.open_bets(race_id=rid)
    runner = s.runners(race_id=rid)[0]
    bid = s.place_bet(
        race_id=rid, bettor_id="bob",
        runner_id=runner.runner_id,
        wager_gil=1000, placed_day=10,
    )
    assert bid is not None


def test_place_bet_zero_wager():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s, rid, field=4)
    s.open_bets(race_id=rid)
    runner = s.runners(race_id=rid)[0]
    bid = s.place_bet(
        race_id=rid, bettor_id="bob",
        runner_id=runner.runner_id,
        wager_gil=0, placed_day=10,
    )
    assert bid is None


def test_place_bet_unknown_runner():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s, rid, field=4)
    s.open_bets(race_id=rid)
    bid = s.place_bet(
        race_id=rid, bettor_id="bob",
        runner_id="ghost", wager_gil=100,
        placed_day=10,
    )
    assert bid is None


def test_pool_accumulates():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s, rid, field=4)
    s.open_bets(race_id=rid)
    runners = s.runners(race_id=rid)
    s.place_bet(
        race_id=rid, bettor_id="bob",
        runner_id=runners[0].runner_id,
        wager_gil=1000, placed_day=10,
    )
    s.place_bet(
        race_id=rid, bettor_id="cara",
        runner_id=runners[1].runner_id,
        wager_gil=500, placed_day=10,
    )
    assert s.race(
        race_id=rid,
    ).pool_total_gil == 1500


def test_start_race_then_resolve():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s, rid, field=4)
    s.open_bets(race_id=rid)
    s.start_race(race_id=rid)
    winner = s.resolve_race(race_id=rid, seed=42)
    assert winner is not None
    assert s.race(
        race_id=rid,
    ).state == RaceState.SETTLED


def test_resolve_deterministic_same_seed():
    s1 = ChocoboRacingTrackSystem()
    rid1 = s1.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s1, rid1, field=4)
    s1.open_bets(race_id=rid1)
    s1.start_race(race_id=rid1)
    w1 = s1.resolve_race(race_id=rid1, seed=42)
    s2 = ChocoboRacingTrackSystem()
    rid2 = s2.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s2, rid2, field=4)
    s2.open_bets(race_id=rid2)
    s2.start_race(race_id=rid2)
    w2 = s2.resolve_race(race_id=rid2, seed=42)
    # Both rids identical structure -> same winner
    # at same logical position
    assert w1.split("_")[-1] == w2.split("_")[-1]


def test_resolve_strong_chocobo_wins():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
        field_min=2, field_max=2,
    )
    s.register_runner(
        race_id=rid, chocobo_id="weak",
        owner_id="o1", speed=20, stamina=20,
    )
    s.register_runner(
        race_id=rid, chocobo_id="strong",
        owner_id="o2", speed=99, stamina=99,
    )
    s.open_bets(race_id=rid)
    s.start_race(race_id=rid)
    winner_id = s.resolve_race(
        race_id=rid, seed=0,
    )
    runners = s.runners(race_id=rid)
    winner = next(
        r for r in runners
        if r.runner_id == winner_id
    )
    assert winner.chocobo_id == "strong"


def test_payout_winning_bet():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
        field_min=2, field_max=2,
    )
    s.register_runner(
        race_id=rid, chocobo_id="weak",
        owner_id="o1", speed=20, stamina=20,
    )
    s.register_runner(
        race_id=rid, chocobo_id="strong",
        owner_id="o2", speed=99, stamina=99,
    )
    s.open_bets(race_id=rid)
    runners = s.runners(race_id=rid)
    strong_id = next(
        r.runner_id for r in runners
        if r.chocobo_id == "strong"
    )
    weak_id = next(
        r.runner_id for r in runners
        if r.chocobo_id == "weak"
    )
    s.place_bet(
        race_id=rid, bettor_id="bob",
        runner_id=strong_id,
        wager_gil=1000, placed_day=10,
    )
    s.place_bet(
        race_id=rid, bettor_id="cara",
        runner_id=weak_id,
        wager_gil=1000, placed_day=10,
    )
    s.start_race(race_id=rid)
    s.resolve_race(race_id=rid, seed=0)
    # Pool 2000, house 5% -> 1900 prize
    # Bob is the only winning bettor -> all 1900
    assert s.payout(
        race_id=rid, bettor_id="bob",
    ) == 1900


def test_payout_losing_bet_zero():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
        field_min=2, field_max=2,
    )
    s.register_runner(
        race_id=rid, chocobo_id="weak",
        owner_id="o1", speed=20, stamina=20,
    )
    s.register_runner(
        race_id=rid, chocobo_id="strong",
        owner_id="o2", speed=99, stamina=99,
    )
    s.open_bets(race_id=rid)
    runners = s.runners(race_id=rid)
    weak_id = next(
        r.runner_id for r in runners
        if r.chocobo_id == "weak"
    )
    s.place_bet(
        race_id=rid, bettor_id="cara",
        runner_id=weak_id,
        wager_gil=1000, placed_day=10,
    )
    s.start_race(race_id=rid)
    s.resolve_race(race_id=rid, seed=0)
    assert s.payout(
        race_id=rid, bettor_id="cara",
    ) == 0


def test_payout_unsettled_zero():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s, rid, field=4)
    s.open_bets(race_id=rid)
    assert s.payout(
        race_id=rid, bettor_id="bob",
    ) == 0


def test_start_without_bets_open_blocked():
    s = ChocoboRacingTrackSystem()
    rid = s.schedule_race(
        track_id="x", distance_furlongs=10,
    )
    _setup_full_field(s, rid, field=4)
    assert s.start_race(race_id=rid) is False


def test_race_unknown():
    s = ChocoboRacingTrackSystem()
    assert s.race(race_id="ghost") is None


def test_enum_count():
    assert len(list(RaceState)) == 4
