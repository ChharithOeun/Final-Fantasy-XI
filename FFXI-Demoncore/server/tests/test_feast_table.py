"""Tests for feast_table."""
from __future__ import annotations

from server.cookpot_recipes import BuffPayload
from server.feast_table import FeastState, FeastTable


def test_open_happy():
    t = FeastTable()
    ok = t.open(
        feast_id="f1", host_id="alice",
        dish_token="dish_x", opened_at=10,
    )
    assert ok is True
    assert t.state(feast_id="f1") == FeastState.OPEN


def test_open_blank_id():
    t = FeastTable()
    out = t.open(
        feast_id="", host_id="alice",
        dish_token="d", opened_at=10,
    )
    assert out is False


def test_open_blank_host():
    t = FeastTable()
    out = t.open(
        feast_id="f", host_id="",
        dish_token="d", opened_at=10,
    )
    assert out is False


def test_open_blank_dish():
    t = FeastTable()
    out = t.open(
        feast_id="f", host_id="alice",
        dish_token="", opened_at=10,
    )
    assert out is False


def test_open_duplicate_blocked():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    out = t.open(
        feast_id="f", host_id="bob",
        dish_token="d2", opened_at=20,
    )
    assert out is False


def test_host_in_initial_members():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    assert t.members(feast_id="f") == ["alice"]


def test_join_happy():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    ok = t.join(feast_id="f", joiner_id="bob")
    assert ok is True
    assert "bob" in t.members(feast_id="f")


def test_join_unknown_feast():
    t = FeastTable()
    out = t.join(feast_id="ghost", joiner_id="bob")
    assert out is False


def test_join_blank_joiner():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    out = t.join(feast_id="f", joiner_id="")
    assert out is False


def test_join_duplicate_blocked():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    t.join(feast_id="f", joiner_id="bob")
    out = t.join(feast_id="f", joiner_id="bob")
    assert out is False


def test_commit_returns_members_and_payload():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    t.join(feast_id="f", joiner_id="bob")
    t.join(feast_id="f", joiner_id="cara")
    payload = BuffPayload(
        str_bonus=8, vit_bonus=4, duration_seconds=1800,
    )
    out = t.commit(feast_id="f", payload=payload, committed_at=20)
    assert out is not None
    members, fed_payload = out
    assert set(members) == {"alice", "bob", "cara"}
    # 75% of 8 = 6
    assert fed_payload.str_bonus == 6
    assert fed_payload.duration_seconds == 1800


def test_commit_locks_state_to_active():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    payload = BuffPayload(str_bonus=4, duration_seconds=600)
    t.commit(feast_id="f", payload=payload, committed_at=20)
    assert t.state(feast_id="f") == FeastState.ACTIVE


def test_join_after_commit_blocked():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    payload = BuffPayload(str_bonus=4, duration_seconds=600)
    t.commit(feast_id="f", payload=payload, committed_at=20)
    out = t.join(feast_id="f", joiner_id="latecomer")
    assert out is False


def test_commit_unknown_feast():
    t = FeastTable()
    out = t.commit(
        feast_id="ghost",
        payload=BuffPayload(duration_seconds=600),
        committed_at=20,
    )
    assert out is None


def test_commit_twice_blocked():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    payload = BuffPayload(str_bonus=4, duration_seconds=600)
    t.commit(feast_id="f", payload=payload, committed_at=20)
    out = t.commit(feast_id="f", payload=payload, committed_at=30)
    assert out is None


def test_expire_changes_state():
    t = FeastTable()
    t.open(
        feast_id="f", host_id="alice",
        dish_token="d", opened_at=10,
    )
    assert t.expire(feast_id="f") is True
    assert t.state(feast_id="f") == FeastState.EXPIRED


def test_expire_unknown():
    t = FeastTable()
    assert t.expire(feast_id="ghost") is False


def test_state_unknown_none():
    t = FeastTable()
    assert t.state(feast_id="ghost") is None


def test_three_feast_states():
    assert len(list(FeastState)) == 3


def test_total_feasts():
    t = FeastTable()
    t.open(feast_id="a", host_id="alice", dish_token="d", opened_at=10)
    t.open(feast_id="b", host_id="bob", dish_token="d", opened_at=20)
    assert t.total_feasts() == 2
