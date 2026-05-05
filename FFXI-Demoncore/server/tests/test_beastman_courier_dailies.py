"""Tests for the beastman courier dailies."""
from __future__ import annotations

from server.beastman_courier_dailies import (
    BeastmanCourierDailies,
    Difficulty,
    TaskState,
)


def _seed(c):
    c.register_task(
        task_id="deliver_seal",
        difficulty=Difficulty.EASY,
        gil_reward=200,
        sparks_reward=50,
    )


def test_register():
    c = BeastmanCourierDailies()
    _seed(c)
    assert c.total_tasks() == 1


def test_register_duplicate():
    c = BeastmanCourierDailies()
    _seed(c)
    res = c.register_task(
        task_id="deliver_seal",
        difficulty=Difficulty.HARD,
        gil_reward=999,
        sparks_reward=100,
    )
    assert res is None


def test_register_zero_total():
    c = BeastmanCourierDailies()
    res = c.register_task(
        task_id="bad",
        difficulty=Difficulty.EASY,
        gil_reward=0,
        sparks_reward=0,
    )
    assert res is None


def test_register_negative_reward():
    c = BeastmanCourierDailies()
    res = c.register_task(
        task_id="bad",
        difficulty=Difficulty.EASY,
        gil_reward=-1,
        sparks_reward=10,
    )
    assert res is None


def test_accept_basic():
    c = BeastmanCourierDailies()
    _seed(c)
    res = c.accept(
        player_id="kraw",
        task_id="deliver_seal",
        now_seconds=0,
    )
    assert res.accepted
    assert res.state == TaskState.ACTIVE


def test_accept_unknown():
    c = BeastmanCourierDailies()
    res = c.accept(
        player_id="kraw", task_id="ghost", now_seconds=0,
    )
    assert not res.accepted


def test_accept_double_blocked():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    res = c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=10,
    )
    assert not res.accepted


def test_per_day_cap():
    c = BeastmanCourierDailies()
    for i in range(5):
        c.register_task(
            task_id=f"t_{i}",
            difficulty=Difficulty.EASY,
            gil_reward=100, sparks_reward=10,
        )
    c.accept(player_id="kraw", task_id="t_0", now_seconds=0)
    c.accept(player_id="kraw", task_id="t_1", now_seconds=0)
    c.accept(player_id="kraw", task_id="t_2", now_seconds=0)
    res = c.accept(player_id="kraw", task_id="t_3", now_seconds=0)
    assert not res.accepted


def test_bank_basic():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    res = c.bank(player_id="kraw", task_id="deliver_seal")
    assert res.accepted
    assert res.state == TaskState.BANKED


def test_bank_not_accepted():
    c = BeastmanCourierDailies()
    _seed(c)
    res = c.bank(player_id="kraw", task_id="deliver_seal")
    assert not res.accepted


def test_bank_already_banked():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    c.bank(player_id="kraw", task_id="deliver_seal")
    res = c.bank(player_id="kraw", task_id="deliver_seal")
    assert not res.accepted


def test_bank_cap():
    c = BeastmanCourierDailies()
    for i in range(8):
        c.register_task(
            task_id=f"t_{i}",
            difficulty=Difficulty.EASY,
            gil_reward=100, sparks_reward=10,
        )
    # Bank 5 over multiple days
    for i in range(5):
        c.accept(
            player_id="kraw", task_id=f"t_{i}",
            now_seconds=0,
        )
        c.bank(player_id="kraw", task_id=f"t_{i}")
    # Try to bank a 6th
    c.accept(
        player_id="kraw", task_id="t_5", now_seconds=0,
    )
    res = c.bank(player_id="kraw", task_id="t_5")
    assert not res.accepted


def test_complete_basic():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    res = c.complete(
        player_id="kraw", task_id="deliver_seal",
    )
    assert res.accepted
    assert res.gil_awarded == 200


def test_complete_already_completed():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    c.complete(player_id="kraw", task_id="deliver_seal")
    res = c.complete(player_id="kraw", task_id="deliver_seal")
    assert not res.accepted


def test_complete_not_accepted():
    c = BeastmanCourierDailies()
    _seed(c)
    res = c.complete(
        player_id="kraw", task_id="deliver_seal",
    )
    assert not res.accepted


def test_complete_from_banked():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    c.bank(player_id="kraw", task_id="deliver_seal")
    res = c.complete(
        player_id="kraw", task_id="deliver_seal",
    )
    assert res.accepted


def test_roll_over_drops_active():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    n = c.roll_over_day(
        player_id="kraw", now_seconds=86_500,
    )
    assert n == 1


def test_roll_over_keeps_banked():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    c.bank(player_id="kraw", task_id="deliver_seal")
    n = c.roll_over_day(
        player_id="kraw", now_seconds=86_500,
    )
    assert n == 0
    assert c.banked_count(player_id="kraw") == 1


def test_active_count():
    c = BeastmanCourierDailies()
    _seed(c)
    assert c.active_count(player_id="ghost") == 0
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    assert c.active_count(player_id="kraw") == 1


def test_banked_count():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="kraw", task_id="deliver_seal", now_seconds=0,
    )
    c.bank(player_id="kraw", task_id="deliver_seal")
    assert c.banked_count(player_id="kraw") == 1


def test_per_player_isolation():
    c = BeastmanCourierDailies()
    _seed(c)
    c.accept(
        player_id="alice", task_id="deliver_seal", now_seconds=0,
    )
    res = c.accept(
        player_id="bob", task_id="deliver_seal", now_seconds=0,
    )
    assert res.accepted
