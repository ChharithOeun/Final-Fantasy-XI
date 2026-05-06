"""Tests for leftover_storage."""
from __future__ import annotations

from server.cookpot_recipes import BuffPayload, DishKind
from server.leftover_storage import LeftoverState, LeftoverStorage


def _stash(s, lid="l1", **overrides):
    kwargs = dict(
        leftover_id=lid, owner_id="alice",
        dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(str_bonus=10, duration_seconds=600),
        shelf_life_seconds=1000, stashed_at=10,
    )
    kwargs.update(overrides)
    return s.stash(**kwargs)


def test_stash_happy():
    s = LeftoverStorage()
    assert _stash(s) is True


def test_stash_blank_id():
    s = LeftoverStorage()
    assert _stash(s, lid="") is False


def test_stash_blank_owner():
    s = LeftoverStorage()
    assert _stash(s, owner_id="") is False


def test_stash_zero_shelf_life():
    s = LeftoverStorage()
    assert _stash(s, shelf_life_seconds=0) is False


def test_stash_duplicate_blocked():
    s = LeftoverStorage()
    _stash(s)
    assert _stash(s) is False


def test_state_fresh_initially():
    s = LeftoverStorage()
    _stash(s)
    assert s.state_of(leftover_id="l1") == LeftoverState.FRESH


def test_state_stale_past_half():
    s = LeftoverStorage()
    _stash(s)  # shelf 1000
    s.age_all(dt_seconds=600)
    assert s.state_of(leftover_id="l1") == LeftoverState.STALE


def test_state_spoiled_past_shelf():
    s = LeftoverStorage()
    _stash(s)
    s.age_all(dt_seconds=1100)
    assert s.state_of(leftover_id="l1") == LeftoverState.SPOILED


def test_age_returns_new_spoil_count():
    s = LeftoverStorage()
    _stash(s, lid="a", shelf_life_seconds=500)
    _stash(s, lid="b", shelf_life_seconds=2000)
    out = s.age_all(dt_seconds=600)
    # only "a" newly spoiled
    assert out == 1


def test_age_zero_dt():
    s = LeftoverStorage()
    _stash(s)
    assert s.age_all(dt_seconds=0) == 0


def test_consume_fresh_full_magnitude():
    s = LeftoverStorage()
    _stash(s, payload=BuffPayload(
        str_bonus=10, duration_seconds=600,
    ))
    out = s.consume(leftover_id="l1", consumer_id="alice")
    assert out is not None
    # at age 0 → mag 1.0 → str_bonus 10
    assert out.str_bonus == 10
    # leftover consumed
    assert s.total_leftovers() == 0


def test_consume_stale_diminished():
    s = LeftoverStorage()
    _stash(s, payload=BuffPayload(
        str_bonus=10, duration_seconds=600,
    ), shelf_life_seconds=1000)
    s.age_all(dt_seconds=500)  # at 50% → mag 0.75
    out = s.consume(leftover_id="l1", consumer_id="alice")
    assert out is not None
    # 10 * 0.75 = 7
    assert out.str_bonus == 7


def test_consume_spoiled_returns_none():
    s = LeftoverStorage()
    _stash(s, shelf_life_seconds=100)
    s.age_all(dt_seconds=200)
    out = s.consume(leftover_id="l1", consumer_id="alice")
    assert out is None


def test_consume_unknown():
    s = LeftoverStorage()
    out = s.consume(leftover_id="ghost", consumer_id="alice")
    assert out is None


def test_consume_wrong_owner_blocked():
    s = LeftoverStorage()
    _stash(s)
    out = s.consume(leftover_id="l1", consumer_id="bob")
    assert out is None
    # not consumed
    assert s.total_leftovers() == 1


def test_reheat_reduces_duration():
    s = LeftoverStorage()
    _stash(s, payload=BuffPayload(
        str_bonus=10, duration_seconds=1000,
    ))
    s.reheat(leftover_id="l1")
    out = s.consume(leftover_id="l1", consumer_id="alice")
    assert out is not None
    # 1 reheat → 80% duration → 800
    assert out.duration_seconds == 800
    # str_bonus magnitude unaffected (no age)
    assert out.str_bonus == 10


def test_reheat_stacks():
    s = LeftoverStorage()
    _stash(s, payload=BuffPayload(
        str_bonus=10, duration_seconds=1000,
    ))
    s.reheat(leftover_id="l1")
    s.reheat(leftover_id="l1")
    out = s.consume(leftover_id="l1", consumer_id="alice")
    assert out is not None
    # 2 reheats → 0.8 * 0.8 = 0.64 → 640
    assert out.duration_seconds == 640


def test_reheat_unknown():
    s = LeftoverStorage()
    assert s.reheat(leftover_id="ghost") is False


def test_reheat_spoiled_blocked():
    s = LeftoverStorage()
    _stash(s, shelf_life_seconds=100)
    s.age_all(dt_seconds=200)
    assert s.reheat(leftover_id="l1") is False


def test_three_leftover_states():
    assert len(list(LeftoverState)) == 3


def test_state_of_unknown_none():
    s = LeftoverStorage()
    assert s.state_of(leftover_id="ghost") is None


def test_total_leftovers():
    s = LeftoverStorage()
    _stash(s, lid="a")
    _stash(s, lid="b")
    assert s.total_leftovers() == 2
