"""Tests for leftover_storage."""
from __future__ import annotations

from server.cookpot_recipes import BuffPayload, DishKind
from server.leftover_storage import (
    LeftoverState, LeftoverStorage, Provenance, ProvisionKind,
)


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


# --- ProvisionKind defaults + NPC stocked tuning ---

def test_default_food_shelf_seven_days():
    s = LeftoverStorage()
    s.stash(
        leftover_id="l1", owner_id="alice",
        dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        stashed_at=10, kind=ProvisionKind.FOOD,
    )
    # 7 * 24 * 3600 = 604800
    # one second short → still fresh
    s.age_all(dt_seconds=604799)
    assert s.state_of(leftover_id="l1") != LeftoverState.SPOILED
    s.age_all(dt_seconds=2)
    assert s.state_of(leftover_id="l1") == LeftoverState.SPOILED


def test_default_drink_shelf_three_months():
    s = LeftoverStorage()
    s.stash(
        leftover_id="l1", owner_id="alice",
        dish=DishKind.WARMING_TEA,
        payload=BuffPayload(cold_resist=15, duration_seconds=600),
        stashed_at=10, kind=ProvisionKind.DRINK,
    )
    # 90 * 24 * 3600 = 7776000
    # half a year of food-grade time → still ok for a drink
    s.age_all(dt_seconds=7000000)
    assert s.state_of(leftover_id="l1") != LeftoverState.SPOILED
    s.age_all(dt_seconds=800000)
    assert s.state_of(leftover_id="l1") == LeftoverState.SPOILED


def test_npc_stocked_does_not_age():
    s = LeftoverStorage()
    s.stash(
        leftover_id="l1", owner_id="vendor_npc",
        dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        stashed_at=10, kind=ProvisionKind.FOOD,
        provenance=Provenance.NPC_STOCKED,
    )
    # bombard with aging — still fresh
    s.age_all(dt_seconds=999_999_999)
    assert s.state_of(leftover_id="l1") == LeftoverState.FRESH


def test_npc_stocked_ages_after_purchase():
    s = LeftoverStorage()
    s.stash(
        leftover_id="l1", owner_id="vendor_npc",
        dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        stashed_at=10, kind=ProvisionKind.FOOD,
        provenance=Provenance.NPC_STOCKED,
    )
    # Player buys it → flips to PLAYER_MADE
    ok = s.transfer_to_player(
        leftover_id="l1", new_owner_id="alice",
    )
    assert ok is True
    # Now it ages normally (food shelf 604800)
    s.age_all(dt_seconds=604801)
    assert s.state_of(leftover_id="l1") == LeftoverState.SPOILED


def test_transfer_already_player_owned_blocked():
    s = LeftoverStorage()
    _stash(s)  # default PLAYER_MADE
    out = s.transfer_to_player(
        leftover_id="l1", new_owner_id="bob",
    )
    assert out is False


def test_transfer_unknown():
    s = LeftoverStorage()
    out = s.transfer_to_player(
        leftover_id="ghost", new_owner_id="alice",
    )
    assert out is False


def test_transfer_blank_owner_blocked():
    s = LeftoverStorage()
    s.stash(
        leftover_id="l1", owner_id="vendor_npc",
        dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(duration_seconds=600),
        stashed_at=10, provenance=Provenance.NPC_STOCKED,
    )
    out = s.transfer_to_player(
        leftover_id="l1", new_owner_id="",
    )
    assert out is False


def test_purchased_npc_stock_loses_npc_owner():
    s = LeftoverStorage()
    s.stash(
        leftover_id="l1", owner_id="vendor_npc",
        dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(str_bonus=5, duration_seconds=600),
        stashed_at=10, provenance=Provenance.NPC_STOCKED,
    )
    s.transfer_to_player(
        leftover_id="l1", new_owner_id="alice",
    )
    # Vendor can no longer consume it; alice can.
    out = s.consume(leftover_id="l1", consumer_id="vendor_npc")
    assert out is None


def test_two_provision_kinds():
    assert len(list(ProvisionKind)) == 2


def test_two_provenances():
    assert len(list(Provenance)) == 2
