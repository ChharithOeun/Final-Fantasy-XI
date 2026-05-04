"""Tests for the beastman records of eminence."""
from __future__ import annotations

from server.beastman_records_of_eminence import (
    BeastmanRecordsOfEminence,
    Cadence,
)


def _seed(r):
    r.register_objective(
        obj_id="hunt_humes",
        cadence=Cadence.DAILY,
        target_count=10,
        sparks_reward=200,
        gil_reward=500,
    )


def test_register():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    assert r.total_objectives() == 1


def test_register_duplicate():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    res = r.register_objective(
        obj_id="hunt_humes",
        cadence=Cadence.WEEKLY,
        target_count=99,
        sparks_reward=0,
        gil_reward=0,
    )
    assert res is None


def test_register_zero_target_rejected():
    r = BeastmanRecordsOfEminence()
    res = r.register_objective(
        obj_id="bad",
        cadence=Cadence.DAILY,
        target_count=0,
        sparks_reward=10,
        gil_reward=10,
    )
    assert res is None


def test_register_negative_reward_rejected():
    r = BeastmanRecordsOfEminence()
    res = r.register_objective(
        obj_id="bad",
        cadence=Cadence.DAILY,
        target_count=5,
        sparks_reward=-1,
        gil_reward=10,
    )
    assert res is None


def test_activate():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    res = r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    assert res.accepted


def test_activate_unknown_rejected():
    r = BeastmanRecordsOfEminence()
    res = r.activate(
        player_id="kraw",
        obj_id="ghost",
        now_seconds=0,
    )
    assert not res.accepted


def test_activate_double_rejected():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    res = r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=10,
    )
    assert not res.accepted


def test_activate_cap_enforced():
    r = BeastmanRecordsOfEminence()
    for i in range(10):
        r.register_objective(
            obj_id=f"daily_{i}",
            cadence=Cadence.DAILY,
            target_count=5,
            sparks_reward=10,
            gil_reward=10,
        )
    for i in range(8):
        r.activate(
            player_id="kraw",
            obj_id=f"daily_{i}",
            now_seconds=0,
        )
    res = r.activate(
        player_id="kraw",
        obj_id="daily_9",
        now_seconds=0,
    )
    assert not res.accepted


def test_progress_increments():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    res = r.progress(
        player_id="kraw",
        obj_id="hunt_humes",
        increment=3,
    )
    assert res.accepted
    assert res.progress == 3
    assert not res.completed


def test_progress_clamps_at_target():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    res = r.progress(
        player_id="kraw",
        obj_id="hunt_humes",
        increment=999,
    )
    assert res.progress == 10
    assert res.completed


def test_progress_not_active():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    res = r.progress(
        player_id="ghost",
        obj_id="hunt_humes",
        increment=1,
    )
    assert not res.accepted


def test_progress_zero_increment():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    res = r.progress(
        player_id="kraw",
        obj_id="hunt_humes",
        increment=0,
    )
    assert not res.accepted


def test_claim_basic():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    r.progress(
        player_id="kraw",
        obj_id="hunt_humes",
        increment=10,
    )
    res = r.claim(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=10,
    )
    assert res.accepted
    assert res.sparks_awarded == 200
    assert res.gil_awarded == 500


def test_claim_double_blocked():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    r.progress(
        player_id="kraw",
        obj_id="hunt_humes",
        increment=10,
    )
    r.claim(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=10,
    )
    res = r.claim(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=20,
    )
    assert not res.accepted


def test_claim_not_complete():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    res = r.claim(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=10,
    )
    assert not res.accepted


def test_campaign_clears_on_claim():
    r = BeastmanRecordsOfEminence()
    r.register_objective(
        obj_id="long_arc",
        cadence=Cadence.CAMPAIGN,
        target_count=5,
        sparks_reward=1000,
        gil_reward=5000,
    )
    r.activate(
        player_id="kraw",
        obj_id="long_arc",
        now_seconds=0,
    )
    r.progress(
        player_id="kraw",
        obj_id="long_arc",
        increment=5,
    )
    r.claim(
        player_id="kraw",
        obj_id="long_arc",
        now_seconds=10,
    )
    assert r.active_count(
        player_id="kraw",
        cadence=Cadence.CAMPAIGN,
    ) == 0


def test_reset_due_clears_daily():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    r.activate(
        player_id="kraw",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    n = r.reset_due(
        player_id="kraw",
        now_seconds=86_500,
    )
    assert n == 1
    assert r.active_count(
        player_id="kraw",
        cadence=Cadence.DAILY,
    ) == 0


def test_reset_due_skips_campaign():
    r = BeastmanRecordsOfEminence()
    r.register_objective(
        obj_id="long_arc",
        cadence=Cadence.CAMPAIGN,
        target_count=5,
        sparks_reward=10,
        gil_reward=10,
    )
    r.activate(
        player_id="kraw",
        obj_id="long_arc",
        now_seconds=0,
    )
    n = r.reset_due(
        player_id="kraw",
        now_seconds=999_999_999,
    )
    assert n == 0


def test_active_count_per_cadence():
    r = BeastmanRecordsOfEminence()
    r.register_objective(
        obj_id="d1",
        cadence=Cadence.DAILY,
        target_count=5, sparks_reward=10, gil_reward=10,
    )
    r.register_objective(
        obj_id="w1",
        cadence=Cadence.WEEKLY,
        target_count=5, sparks_reward=10, gil_reward=10,
    )
    r.activate(player_id="kraw", obj_id="d1", now_seconds=0)
    r.activate(player_id="kraw", obj_id="w1", now_seconds=0)
    assert r.active_count(
        player_id="kraw", cadence=Cadence.DAILY,
    ) == 1
    assert r.active_count(
        player_id="kraw", cadence=Cadence.WEEKLY,
    ) == 1


def test_per_player_isolation():
    r = BeastmanRecordsOfEminence()
    _seed(r)
    r.activate(
        player_id="alice",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    res = r.activate(
        player_id="bob",
        obj_id="hunt_humes",
        now_seconds=0,
    )
    assert res.accepted
