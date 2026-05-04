"""Tests for the beastman trial grounds."""
from __future__ import annotations

from server.beastman_trial_grounds import (
    BeastmanTrialGrounds,
    DropSlot,
    TrialState,
    TrialTier,
)


def _seed(g):
    g.register_trial(
        trial_id="oz_t2",
        tier=TrialTier.T2,
        party_max=6,
        key_item_id="oztroja_seal",
        cooldown_hours=20,
        drops=(
            DropSlot(item_id="raptor_helm", base_drop_pct=50),
            DropSlot(item_id="celata", base_drop_pct=10),
        ),
    )


def test_register_trial():
    g = BeastmanTrialGrounds()
    _seed(g)
    assert g.total_trials() == 1


def test_register_trial_duplicate():
    g = BeastmanTrialGrounds()
    _seed(g)
    res = g.register_trial(
        trial_id="oz_t2",
        tier=TrialTier.T1,
        party_max=3,
        key_item_id="x",
        cooldown_hours=20,
        drops=(),
    )
    assert res is None


def test_register_trial_zero_party():
    g = BeastmanTrialGrounds()
    res = g.register_trial(
        trial_id="bad",
        tier=TrialTier.T1,
        party_max=0,
        key_item_id="x",
        cooldown_hours=20,
        drops=(),
    )
    assert res is None


def test_register_trial_invalid_drop_pct():
    g = BeastmanTrialGrounds()
    res = g.register_trial(
        trial_id="bad",
        tier=TrialTier.T1,
        party_max=3,
        key_item_id="x",
        cooldown_hours=20,
        drops=(DropSlot(item_id="x", base_drop_pct=200),),
    )
    assert res is None


def test_register_trial_empty_key():
    g = BeastmanTrialGrounds()
    res = g.register_trial(
        trial_id="bad",
        tier=TrialTier.T1,
        party_max=3,
        key_item_id="",
        cooldown_hours=20,
        drops=(),
    )
    assert res is None


def test_start_basic():
    g = BeastmanTrialGrounds()
    _seed(g)
    res = g.start(
        trial_id="oz_t2",
        party_ids=("a", "b", "c"),
        key_item_held=True,
        now_seconds=0,
    )
    assert res.accepted
    assert res.state == TrialState.IN_PROGRESS


def test_start_no_key():
    g = BeastmanTrialGrounds()
    _seed(g)
    res = g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=False,
        now_seconds=0,
    )
    assert not res.accepted


def test_start_oversized_party():
    g = BeastmanTrialGrounds()
    _seed(g)
    res = g.start(
        trial_id="oz_t2",
        party_ids=tuple(f"p{i}" for i in range(10)),
        key_item_held=True,
        now_seconds=0,
    )
    assert not res.accepted


def test_start_double_in_progress():
    g = BeastmanTrialGrounds()
    _seed(g)
    g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    res = g.start(
        trial_id="oz_t2",
        party_ids=("b",),
        key_item_held=True,
        now_seconds=10,
    )
    assert not res.accepted


def test_start_unknown_trial():
    g = BeastmanTrialGrounds()
    res = g.start(
        trial_id="ghost",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    assert not res.accepted


def test_resolve_victory():
    g = BeastmanTrialGrounds()
    _seed(g)
    g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    res = g.resolve(
        trial_id="oz_t2", victory=True, now_seconds=600,
    )
    assert res.accepted
    assert res.state == TrialState.VICTORY


def test_resolve_defeat():
    g = BeastmanTrialGrounds()
    _seed(g)
    g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    res = g.resolve(
        trial_id="oz_t2", victory=False, now_seconds=600,
    )
    assert res.accepted
    assert res.state == TrialState.DEFEAT


def test_resolve_not_in_progress():
    g = BeastmanTrialGrounds()
    _seed(g)
    res = g.resolve(
        trial_id="oz_t2", victory=True, now_seconds=0,
    )
    assert not res.accepted


def test_roll_drop_dropped():
    g = BeastmanTrialGrounds()
    _seed(g)
    g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    g.resolve(
        trial_id="oz_t2", victory=True, now_seconds=600,
    )
    res = g.roll_drop(
        trial_id="oz_t2", slot_index=0, roll_pct=20,
    )
    assert res.accepted
    assert res.dropped


def test_roll_drop_not_dropped():
    g = BeastmanTrialGrounds()
    _seed(g)
    g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    g.resolve(
        trial_id="oz_t2", victory=True, now_seconds=600,
    )
    res = g.roll_drop(
        trial_id="oz_t2", slot_index=1, roll_pct=99,
    )
    assert res.accepted
    assert not res.dropped


def test_roll_drop_no_clear():
    g = BeastmanTrialGrounds()
    _seed(g)
    res = g.roll_drop(
        trial_id="oz_t2", slot_index=0, roll_pct=20,
    )
    assert not res.accepted


def test_roll_drop_bad_slot():
    g = BeastmanTrialGrounds()
    _seed(g)
    g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    g.resolve(
        trial_id="oz_t2", victory=True, now_seconds=600,
    )
    res = g.roll_drop(
        trial_id="oz_t2", slot_index=99, roll_pct=20,
    )
    assert not res.accepted


def test_roll_drop_invalid_roll():
    g = BeastmanTrialGrounds()
    _seed(g)
    g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    g.resolve(
        trial_id="oz_t2", victory=True, now_seconds=600,
    )
    res = g.roll_drop(
        trial_id="oz_t2", slot_index=0, roll_pct=200,
    )
    assert not res.accepted


def test_cooldown_blocks_restart():
    g = BeastmanTrialGrounds()
    _seed(g)
    g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    g.resolve(
        trial_id="oz_t2", victory=True, now_seconds=600,
    )
    res = g.start(
        trial_id="oz_t2",
        party_ids=("b",),
        key_item_held=True,
        now_seconds=1000,
    )
    assert not res.accepted


def test_cooldown_lifts_after_window():
    g = BeastmanTrialGrounds()
    _seed(g)
    g.start(
        trial_id="oz_t2",
        party_ids=("a",),
        key_item_held=True,
        now_seconds=0,
    )
    g.resolve(
        trial_id="oz_t2", victory=True, now_seconds=600,
    )
    s = g.state_for(
        trial_id="oz_t2",
        now_seconds=600 + 21 * 3600,
    )
    assert s == TrialState.STAGED


def test_state_for_unknown():
    g = BeastmanTrialGrounds()
    assert g.state_for(
        trial_id="ghost", now_seconds=0,
    ) == TrialState.STAGED
