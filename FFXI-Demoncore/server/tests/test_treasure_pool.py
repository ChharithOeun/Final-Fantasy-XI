"""Tests for treasure_pool — group loot lot/pass distribution."""
from __future__ import annotations

import pytest

from server.rng_pool import RngPool
from server.treasure_pool import (
    DEFAULT_WINDOW_SECONDS,
    LOT_MAX,
    LOT_MIN,
    ExpirePolicy,
    LotAction,
    TreasurePool,
)


PARTY = ("alice", "bob", "carol", "dave")


def _new_pool(seed: int = 1234) -> TreasurePool:
    return TreasurePool(party_id="party_1", rng_pool=RngPool(world_seed=seed))


# -- add_drop -------------------------------------------------------

def test_add_drop_creates_open_slot():
    pool = _new_pool()
    slot = pool.add_drop(
        item_id="ridill", drop_tick=1000,
        party_members=PARTY,
    )
    assert slot.slot_id == 1
    assert slot.expires_at_tick == 1000 + DEFAULT_WINDOW_SECONDS
    assert pool.open_slots() == (slot,)


def test_add_drop_rejects_empty_party():
    pool = _new_pool()
    with pytest.raises(ValueError):
        pool.add_drop(item_id="x", drop_tick=0, party_members=())


def test_add_drop_assigns_increasing_slot_ids():
    pool = _new_pool()
    a = pool.add_drop(item_id="a", drop_tick=0, party_members=PARTY)
    b = pool.add_drop(item_id="b", drop_tick=0, party_members=PARTY)
    assert b.slot_id == a.slot_id + 1


# -- lot validation -------------------------------------------------

def test_lot_basic_accepts():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0, party_members=PARTY)
    res = pool.lot(slot_id=slot.slot_id, member_id="alice",
                   value=500, timestamp=10)
    assert res.accepted is True


def test_lot_value_below_min_rejected():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0, party_members=PARTY)
    res = pool.lot(slot_id=slot.slot_id, member_id="alice",
                   value=LOT_MIN - 1, timestamp=10)
    assert not res.accepted


def test_lot_value_above_max_rejected():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0, party_members=PARTY)
    res = pool.lot(slot_id=slot.slot_id, member_id="alice",
                   value=LOT_MAX + 1, timestamp=10)
    assert not res.accepted


def test_lot_unknown_slot_rejected():
    pool = _new_pool()
    res = pool.lot(slot_id=999, member_id="alice",
                   value=500, timestamp=10)
    assert not res.accepted


def test_lot_non_party_member_rejected():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0, party_members=PARTY)
    res = pool.lot(slot_id=slot.slot_id, member_id="stranger",
                   value=500, timestamp=10)
    assert not res.accepted


def test_double_action_rejected():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0, party_members=PARTY)
    pool.lot(slot_id=slot.slot_id, member_id="alice",
             value=500, timestamp=10)
    res = pool.lot(slot_id=slot.slot_id, member_id="alice",
                   value=600, timestamp=11)
    assert not res.accepted


def test_pass_then_lot_rejected():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0, party_members=PARTY)
    pool.pass_(slot_id=slot.slot_id, member_id="alice", timestamp=10)
    res = pool.lot(slot_id=slot.slot_id, member_id="alice",
                   value=500, timestamp=11)
    assert not res.accepted


# -- resolution by lot --------------------------------------------------

def test_highest_lot_wins():
    pool = _new_pool()
    slot = pool.add_drop(item_id="ridill", drop_tick=0,
                         party_members=PARTY)
    pool.lot(slot_id=slot.slot_id, member_id="alice", value=300,
             timestamp=1)
    pool.lot(slot_id=slot.slot_id, member_id="bob", value=900,
             timestamp=2)
    pool.lot(slot_id=slot.slot_id, member_id="carol", value=500,
             timestamp=3)
    pool.pass_(slot_id=slot.slot_id, member_id="dave", timestamp=4)

    final = pool.get(slot.slot_id)
    assert final.awarded_to == "bob"
    assert final.final_action == LotAction.LOT


def test_all_passed_then_expire_frees_to_floor_by_default():
    pool = _new_pool()
    slot = pool.add_drop(
        item_id="rusty_bucket", drop_tick=0,
        party_members=PARTY,
        expire_policy=ExpirePolicy.FREE_TO_FLOOR,
    )
    for who in PARTY:
        pool.pass_(slot_id=slot.slot_id, member_id=who, timestamp=1)
    final = pool.get(slot.slot_id)
    assert final.final_action == LotAction.EXPIRED
    assert final.awarded_to is None


def test_all_passed_random_to_party_picks_a_member():
    pool = _new_pool()
    slot = pool.add_drop(
        item_id="potion", drop_tick=0,
        party_members=PARTY,
        expire_policy=ExpirePolicy.RANDOM_TO_PARTY,
    )
    for who in PARTY:
        pool.pass_(slot_id=slot.slot_id, member_id=who, timestamp=1)
    final = pool.get(slot.slot_id)
    assert final.final_action == LotAction.RECEIVE
    assert final.awarded_to in PARTY


def test_all_passed_discard_policy():
    pool = _new_pool()
    slot = pool.add_drop(
        item_id="rusty_bucket", drop_tick=0,
        party_members=PARTY,
        expire_policy=ExpirePolicy.DISCARD,
    )
    for who in PARTY:
        pool.pass_(slot_id=slot.slot_id, member_id=who, timestamp=1)
    final = pool.get(slot.slot_id)
    assert final.final_action == LotAction.EXPIRED
    assert final.awarded_to is None


# -- ties resolved deterministically ------------------------------------

def test_tie_resolves_via_rng_tie_break_stream_deterministic():
    pool_a = _new_pool(seed=42)
    pool_b = _new_pool(seed=42)

    for pool in (pool_a, pool_b):
        slot = pool.add_drop(item_id="x", drop_tick=0,
                             party_members=PARTY)
        pool.lot(slot_id=slot.slot_id, member_id="alice",
                 value=900, timestamp=1)
        pool.lot(slot_id=slot.slot_id, member_id="bob",
                 value=900, timestamp=2)
        pool.lot(slot_id=slot.slot_id, member_id="carol",
                 value=500, timestamp=3)
        pool.pass_(slot_id=slot.slot_id, member_id="dave",
                   timestamp=4)

    assert pool_a.get(1).awarded_to == pool_b.get(1).awarded_to


def test_tie_winner_is_one_of_top_lotters():
    pool = _new_pool(seed=42)
    slot = pool.add_drop(item_id="x", drop_tick=0,
                         party_members=PARTY)
    pool.lot(slot_id=slot.slot_id, member_id="alice",
             value=900, timestamp=1)
    pool.lot(slot_id=slot.slot_id, member_id="bob",
             value=900, timestamp=2)
    pool.lot(slot_id=slot.slot_id, member_id="carol",
             value=900, timestamp=3)
    pool.pass_(slot_id=slot.slot_id, member_id="dave", timestamp=4)
    assert pool.get(1).awarded_to in {"alice", "bob", "carol"}


# -- receive_directly --------------------------------------------------

def test_receive_directly_bypasses_lot_window():
    pool = _new_pool()
    slot = pool.add_drop(item_id="ex_artifact", drop_tick=0,
                         party_members=PARTY)
    res = pool.receive_directly(
        slot_id=slot.slot_id, member_id="alice", timestamp=5,
    )
    assert res.accepted
    final = pool.get(slot.slot_id)
    assert final.awarded_to == "alice"
    assert final.final_action == LotAction.RECEIVE


def test_receive_directly_rejected_after_resolution():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0, party_members=PARTY)
    pool.receive_directly(slot_id=slot.slot_id, member_id="alice",
                          timestamp=5)
    # Second receive attempt should fail.
    res = pool.receive_directly(slot_id=slot.slot_id,
                                member_id="bob", timestamp=6)
    assert not res.accepted


# -- tick / expiry ----------------------------------------------------

def test_tick_before_expiry_does_nothing():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0,
                         party_members=PARTY)
    pool.lot(slot_id=slot.slot_id, member_id="alice", value=500,
             timestamp=10)
    # tick one second before expiry, no other actions
    early = pool.tick(now_tick=DEFAULT_WINDOW_SECONDS - 1)
    assert early == ()
    assert pool.get(slot.slot_id).final_action is None


def test_tick_at_expiry_resolves_with_lot_winner():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0,
                         party_members=PARTY)
    pool.lot(slot_id=slot.slot_id, member_id="alice", value=500,
             timestamp=10)
    # other 3 members never act; expire window pops with one lotter.
    results = pool.tick(now_tick=DEFAULT_WINDOW_SECONDS)
    assert len(results) == 1
    assert results[0].slot_id == slot.slot_id
    assert results[0].awarded_to == "alice"
    assert results[0].final_action == LotAction.LOT


def test_tick_at_expiry_no_action_frees_to_floor():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0,
                         party_members=PARTY,
                         expire_policy=ExpirePolicy.FREE_TO_FLOOR)
    results = pool.tick(now_tick=DEFAULT_WINDOW_SECONDS)
    assert len(results) == 1
    assert results[0].final_action == LotAction.EXPIRED
    assert results[0].awarded_to is None


def test_tick_only_resolves_each_slot_once():
    pool = _new_pool()
    slot = pool.add_drop(item_id="x", drop_tick=0, party_members=PARTY)
    pool.lot(slot_id=slot.slot_id, member_id="alice", value=500,
             timestamp=10)
    first = pool.tick(now_tick=DEFAULT_WINDOW_SECONDS)
    assert len(first) == 1
    second = pool.tick(now_tick=DEFAULT_WINDOW_SECONDS + 100)
    assert second == ()


# -- composition ------------------------------------------------------

def test_full_lifecycle_realistic_kill():
    """Boss drops 3 items; party of 4 lots variously; expiry handled."""
    pool = _new_pool(seed=0xC0FFEE)
    s1 = pool.add_drop(item_id="ridill", drop_tick=1000,
                       party_members=PARTY,
                       expire_policy=ExpirePolicy.FREE_TO_FLOOR)
    s2 = pool.add_drop(item_id="kraken_club", drop_tick=1000,
                       party_members=PARTY,
                       expire_policy=ExpirePolicy.FREE_TO_FLOOR)
    s3 = pool.add_drop(item_id="potion_x99", drop_tick=1000,
                       party_members=PARTY,
                       expire_policy=ExpirePolicy.RANDOM_TO_PARTY)

    # Ridill: alice + bob fight over it; alice wins
    pool.lot(slot_id=s1.slot_id, member_id="alice",
             value=850, timestamp=1010)
    pool.lot(slot_id=s1.slot_id, member_id="bob",
             value=700, timestamp=1015)
    pool.pass_(slot_id=s1.slot_id, member_id="carol", timestamp=1020)
    pool.pass_(slot_id=s1.slot_id, member_id="dave", timestamp=1025)
    assert pool.get(s1.slot_id).awarded_to == "alice"

    # Kraken Club: only bob is interested, the rest pass
    pool.pass_(slot_id=s2.slot_id, member_id="alice", timestamp=1010)
    pool.lot(slot_id=s2.slot_id, member_id="bob",
             value=999, timestamp=1015)
    pool.pass_(slot_id=s2.slot_id, member_id="carol", timestamp=1020)
    pool.pass_(slot_id=s2.slot_id, member_id="dave", timestamp=1025)
    assert pool.get(s2.slot_id).awarded_to == "bob"

    # Potions: nobody bothers; expiry triggers RANDOM_TO_PARTY
    expired_results = pool.tick(
        now_tick=1000 + DEFAULT_WINDOW_SECONDS,
    )
    s3_alloc = next(a for a in expired_results
                    if a.slot_id == s3.slot_id)
    assert s3_alloc.final_action == LotAction.RECEIVE
    assert s3_alloc.awarded_to in PARTY
