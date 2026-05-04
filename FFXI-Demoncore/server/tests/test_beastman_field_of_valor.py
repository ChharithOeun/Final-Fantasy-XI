"""Tests for the beastman field of valor."""
from __future__ import annotations

from server.beastman_field_of_valor import (
    BeastmanFieldOfValor,
    RegimenTier,
)


def _seed(f):
    f.register_regimen(
        regimen_id="oz_trainee_a",
        zone_id="oztroja_outer",
        tier=RegimenTier.TRAINEE,
        mob_kills={"hume_courier": 3, "hume_scout": 2},
        xp_reward=500,
        gil_reward=200,
        tabs_reward=50,
    )


def test_register():
    f = BeastmanFieldOfValor()
    _seed(f)
    assert f.total_regimens() == 1


def test_register_duplicate():
    f = BeastmanFieldOfValor()
    _seed(f)
    res = f.register_regimen(
        regimen_id="oz_trainee_a",
        zone_id="x",
        tier=RegimenTier.TRAINEE,
        mob_kills={"a": 1},
        xp_reward=10, gil_reward=10, tabs_reward=10,
    )
    assert res is None


def test_register_empty_kills():
    f = BeastmanFieldOfValor()
    res = f.register_regimen(
        regimen_id="bad",
        zone_id="x",
        tier=RegimenTier.TRAINEE,
        mob_kills={},
        xp_reward=10, gil_reward=10, tabs_reward=10,
    )
    assert res is None


def test_register_zero_kill_count():
    f = BeastmanFieldOfValor()
    res = f.register_regimen(
        regimen_id="bad",
        zone_id="x",
        tier=RegimenTier.TRAINEE,
        mob_kills={"a": 0},
        xp_reward=10, gil_reward=10, tabs_reward=10,
    )
    assert res is None


def test_register_negative_reward():
    f = BeastmanFieldOfValor()
    res = f.register_regimen(
        regimen_id="bad",
        zone_id="x",
        tier=RegimenTier.TRAINEE,
        mob_kills={"a": 1},
        xp_reward=-1, gil_reward=10, tabs_reward=10,
    )
    assert res is None


def test_accept():
    f = BeastmanFieldOfValor()
    _seed(f)
    res = f.accept(
        player_id="kraw", regimen_id="oz_trainee_a",
    )
    assert res.accepted


def test_accept_unknown():
    f = BeastmanFieldOfValor()
    res = f.accept(
        player_id="kraw", regimen_id="ghost",
    )
    assert not res.accepted


def test_accept_double_blocked():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.register_regimen(
        regimen_id="oz_trainee_b",
        zone_id="oztroja_outer",
        tier=RegimenTier.TRAINEE,
        mob_kills={"hume_archer": 3},
        xp_reward=500, gil_reward=200, tabs_reward=50,
    )
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    res = f.accept(player_id="kraw", regimen_id="oz_trainee_b")
    assert not res.accepted


def test_record_kill_basic():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    res = f.record_kill(
        player_id="kraw",
        regimen_id="oz_trainee_a",
        mob_id="hume_courier",
    )
    assert res.accepted
    assert res.progress == 1
    assert not res.completed_overall


def test_record_kill_not_in_regimen():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    res = f.record_kill(
        player_id="kraw",
        regimen_id="oz_trainee_a",
        mob_id="orc_warrior",
    )
    assert not res.accepted


def test_record_kill_not_active_player():
    f = BeastmanFieldOfValor()
    _seed(f)
    res = f.record_kill(
        player_id="ghost",
        regimen_id="oz_trainee_a",
        mob_id="hume_courier",
    )
    assert not res.accepted


def test_record_kill_quota_already_met():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    for _ in range(3):
        f.record_kill(
            player_id="kraw",
            regimen_id="oz_trainee_a",
            mob_id="hume_courier",
        )
    res = f.record_kill(
        player_id="kraw",
        regimen_id="oz_trainee_a",
        mob_id="hume_courier",
    )
    assert res.accepted
    assert res.progress == 3


def test_record_kill_completes_overall():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    for _ in range(3):
        f.record_kill(
            player_id="kraw",
            regimen_id="oz_trainee_a",
            mob_id="hume_courier",
        )
    res = f.record_kill(
        player_id="kraw",
        regimen_id="oz_trainee_a",
        mob_id="hume_scout",
    )
    assert not res.completed_overall  # 1/2 still
    res2 = f.record_kill(
        player_id="kraw",
        regimen_id="oz_trainee_a",
        mob_id="hume_scout",
    )
    assert res2.completed_overall


def test_complete_basic():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    for _ in range(3):
        f.record_kill(
            player_id="kraw",
            regimen_id="oz_trainee_a",
            mob_id="hume_courier",
        )
    for _ in range(2):
        f.record_kill(
            player_id="kraw",
            regimen_id="oz_trainee_a",
            mob_id="hume_scout",
        )
    res = f.complete(
        player_id="kraw", regimen_id="oz_trainee_a",
    )
    assert res.accepted
    assert res.xp_awarded == 500
    assert res.tabs_awarded == 50


def test_complete_not_done():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    res = f.complete(
        player_id="kraw", regimen_id="oz_trainee_a",
    )
    assert not res.accepted


def test_complete_not_active():
    f = BeastmanFieldOfValor()
    _seed(f)
    res = f.complete(
        player_id="kraw", regimen_id="oz_trainee_a",
    )
    assert not res.accepted


def test_complete_releases_player_for_next():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.register_regimen(
        regimen_id="oz_warrior_a",
        zone_id="oztroja_outer",
        tier=RegimenTier.WARRIOR,
        mob_kills={"hume_pikeman": 2},
        xp_reward=2000, gil_reward=800, tabs_reward=100,
    )
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    for _ in range(3):
        f.record_kill(
            player_id="kraw",
            regimen_id="oz_trainee_a",
            mob_id="hume_courier",
        )
    for _ in range(2):
        f.record_kill(
            player_id="kraw",
            regimen_id="oz_trainee_a",
            mob_id="hume_scout",
        )
    f.complete(player_id="kraw", regimen_id="oz_trainee_a")
    res = f.accept(
        player_id="kraw", regimen_id="oz_warrior_a",
    )
    assert res.accepted


def test_active_for():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    assert f.active_for(player_id="kraw") == "oz_trainee_a"


def test_active_for_none():
    f = BeastmanFieldOfValor()
    assert f.active_for(player_id="ghost") is None


def test_per_player_isolation():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.accept(player_id="alice", regimen_id="oz_trainee_a")
    res = f.accept(player_id="bob", regimen_id="oz_trainee_a")
    assert res.accepted


def test_record_kill_wrong_regimen_id():
    f = BeastmanFieldOfValor()
    _seed(f)
    f.accept(player_id="kraw", regimen_id="oz_trainee_a")
    res = f.record_kill(
        player_id="kraw",
        regimen_id="ghost",
        mob_id="hume_courier",
    )
    assert not res.accepted
