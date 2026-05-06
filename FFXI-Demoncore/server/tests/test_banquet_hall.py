"""Tests for banquet_hall."""
from __future__ import annotations

from server.banquet_hall import BanquetHall, BanquetState
from server.cookpot_recipes import BuffPayload


def _setup():
    h = BanquetHall()
    h.schedule(
        banquet_id="b1", host_npc_id="chef_anya",
        town_id="bastok",
        payload=BuffPayload(
            str_bonus=10, vit_bonus=10, duration_seconds=1800,
        ),
        scheduled_at=10,
    )
    return h


def test_schedule_happy():
    h = _setup()
    assert h.state(banquet_id="b1") == BanquetState.SCHEDULED


def test_schedule_blank_id_blocked():
    h = BanquetHall()
    out = h.schedule(
        banquet_id="", host_npc_id="x", town_id="t",
        payload=BuffPayload(duration_seconds=600),
        scheduled_at=10,
    )
    assert out is False


def test_schedule_blank_host_blocked():
    h = BanquetHall()
    out = h.schedule(
        banquet_id="b", host_npc_id="", town_id="t",
        payload=BuffPayload(duration_seconds=600),
        scheduled_at=10,
    )
    assert out is False


def test_schedule_blank_town_blocked():
    h = BanquetHall()
    out = h.schedule(
        banquet_id="b", host_npc_id="x", town_id="",
        payload=BuffPayload(duration_seconds=600),
        scheduled_at=10,
    )
    assert out is False


def test_schedule_duplicate_blocked():
    h = _setup()
    out = h.schedule(
        banquet_id="b1", host_npc_id="other",
        town_id="other_town",
        payload=BuffPayload(duration_seconds=600),
        scheduled_at=20,
    )
    assert out is False


def test_open_serving_happy():
    h = _setup()
    assert h.open_serving(banquet_id="b1", opened_at=20) is True
    assert h.state(banquet_id="b1") == BanquetState.SERVING


def test_open_serving_unknown():
    h = BanquetHall()
    assert h.open_serving(banquet_id="ghost", opened_at=20) is False


def test_open_serving_twice_blocked():
    h = _setup()
    h.open_serving(banquet_id="b1", opened_at=20)
    assert h.open_serving(banquet_id="b1", opened_at=30) is False


def test_enter_before_serving_blocked():
    h = _setup()
    out = h.enter(banquet_id="b1", player_id="alice")
    assert out is None


def test_enter_during_serving_returns_aura():
    h = _setup()
    h.open_serving(banquet_id="b1", opened_at=20)
    out = h.enter(banquet_id="b1", player_id="alice")
    assert out is not None
    # 30% of 10 = 3
    assert out.str_bonus == 3
    assert out.vit_bonus == 3


def test_enter_records_attendance():
    h = _setup()
    h.open_serving(banquet_id="b1", opened_at=20)
    h.enter(banquet_id="b1", player_id="alice")
    assert "alice" in h.attendees(banquet_id="b1")


def test_double_enter_blocked():
    h = _setup()
    h.open_serving(banquet_id="b1", opened_at=20)
    h.enter(banquet_id="b1", player_id="alice")
    out = h.enter(banquet_id="b1", player_id="alice")
    assert out is None


def test_enter_blank_player_blocked():
    h = _setup()
    h.open_serving(banquet_id="b1", opened_at=20)
    out = h.enter(banquet_id="b1", player_id="")
    assert out is None


def test_enter_unknown_banquet_blocked():
    h = BanquetHall()
    out = h.enter(banquet_id="ghost", player_id="alice")
    assert out is None


def test_end_serving_happy():
    h = _setup()
    h.open_serving(banquet_id="b1", opened_at=20)
    assert h.end_serving(banquet_id="b1", ended_at=100) is True
    assert h.state(banquet_id="b1") == BanquetState.ENDED


def test_end_serving_unscheduled_blocked():
    h = _setup()
    # still SCHEDULED, can't end
    assert h.end_serving(banquet_id="b1", ended_at=100) is False


def test_enter_after_ended_blocked():
    h = _setup()
    h.open_serving(banquet_id="b1", opened_at=20)
    h.end_serving(banquet_id="b1", ended_at=100)
    out = h.enter(banquet_id="b1", player_id="alice")
    assert out is None


def test_state_unknown_none():
    h = BanquetHall()
    assert h.state(banquet_id="ghost") is None


def test_attendees_unknown_empty():
    h = BanquetHall()
    assert h.attendees(banquet_id="ghost") == []


def test_three_banquet_states():
    assert len(list(BanquetState)) == 3


def test_total_banquets():
    h = _setup()
    h.schedule(
        banquet_id="b2", host_npc_id="chef_b",
        town_id="windurst",
        payload=BuffPayload(duration_seconds=600),
        scheduled_at=20,
    )
    assert h.total_banquets() == 2
