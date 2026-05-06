"""Tests for meal_buff_engine."""
from __future__ import annotations

from server.cookpot_recipes import BuffPayload
from server.meal_buff_engine import BuffSlot, MealBuffEngine


def test_apply_happy():
    e = MealBuffEngine()
    ok = e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        applied_at=10,
    )
    assert ok is True
    assert e.has_buff(player_id="alice", slot=BuffSlot.MEAL) is True


def test_apply_blank_player_blocked():
    e = MealBuffEngine()
    out = e.apply(
        player_id="", slot=BuffSlot.MEAL,
        payload=BuffPayload(duration_seconds=600), applied_at=10,
    )
    assert out is False


def test_apply_zero_duration_blocked():
    e = MealBuffEngine()
    out = e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(duration_seconds=0), applied_at=10,
    )
    assert out is False


def test_meal_replaces_meal():
    e = MealBuffEngine()
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        applied_at=10,
    )
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=10, duration_seconds=600),
        applied_at=20,
    )
    agg = e.aggregate_for(player_id="alice")
    # second meal replaces first → str_bonus should be 10, not 15
    assert agg.str_bonus == 10


def test_drink_stacks_with_meal():
    e = MealBuffEngine()
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        applied_at=10,
    )
    e.apply(
        player_id="alice", slot=BuffSlot.DRINK,
        payload=BuffPayload(cold_resist=15, duration_seconds=600),
        applied_at=10,
    )
    agg = e.aggregate_for(player_id="alice")
    assert agg.str_bonus == 5
    assert agg.cold_resist == 15


def test_aggregate_zero_no_buffs():
    e = MealBuffEngine()
    agg = e.aggregate_for(player_id="alice")
    assert agg.str_bonus == 0
    assert agg.cold_resist == 0


def test_aggregate_blank_player_zero():
    e = MealBuffEngine()
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        applied_at=10,
    )
    agg = e.aggregate_for(player_id="")
    assert agg.str_bonus == 0


def test_tick_decrements():
    e = MealBuffEngine()
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        applied_at=10,
    )
    out = e.tick(dt_seconds=300)
    assert out == 0   # not expired yet
    assert e.has_buff(player_id="alice", slot=BuffSlot.MEAL) is True


def test_tick_expires_buff():
    e = MealBuffEngine()
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        applied_at=10,
    )
    out = e.tick(dt_seconds=600)
    assert out == 1
    assert e.has_buff(player_id="alice", slot=BuffSlot.MEAL) is False


def test_tick_zero_dt_no_expiry():
    e = MealBuffEngine()
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        applied_at=10,
    )
    out = e.tick(dt_seconds=0)
    assert out == 0


def test_clear_removes_all_for_player():
    e = MealBuffEngine()
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        applied_at=10,
    )
    e.apply(
        player_id="alice", slot=BuffSlot.DRINK,
        payload=BuffPayload(cold_resist=15, duration_seconds=600),
        applied_at=10,
    )
    out = e.clear(player_id="alice")
    assert out == 2
    assert e.total_active() == 0


def test_clear_other_players_unaffected():
    e = MealBuffEngine()
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        applied_at=10,
    )
    e.apply(
        player_id="bob", slot=BuffSlot.MEAL,
        payload=BuffPayload(str_bonus=10, duration_seconds=600),
        applied_at=10,
    )
    e.clear(player_id="alice")
    assert e.has_buff(player_id="bob", slot=BuffSlot.MEAL) is True


def test_has_buff_false_for_unknown():
    e = MealBuffEngine()
    assert e.has_buff(
        player_id="ghost", slot=BuffSlot.MEAL,
    ) is False


def test_two_buff_slots():
    assert len(list(BuffSlot)) == 2


def test_aggregate_includes_all_payload_dims():
    e = MealBuffEngine()
    e.apply(
        player_id="alice", slot=BuffSlot.MEAL,
        payload=BuffPayload(
            str_bonus=2, dex_bonus=3, vit_bonus=4,
            regen_per_tick=5, refresh_per_tick=6,
            hp_max_pct=7, mp_max_pct=8,
            cold_resist=9, heat_resist=10,
            duration_seconds=600,
        ),
        applied_at=10,
    )
    agg = e.aggregate_for(player_id="alice")
    assert agg.dex_bonus == 3
    assert agg.regen_per_tick == 5
    assert agg.heat_resist == 10
