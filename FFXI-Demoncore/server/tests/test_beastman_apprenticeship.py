"""Tests for the beastman apprenticeship."""
from __future__ import annotations

from server.beastman_apprenticeship import (
    BeastmanApprenticeship,
    MasterTier,
    Trade,
)


def _seed(a):
    a.register_master(
        master_id="oz_combat_master",
        trade=Trade.COMBAT_ARTS,
        tier=MasterTier.NOVICE_MASTER,
        base_xp=200,
        session_gil_cost=100,
    )


def test_register():
    a = BeastmanApprenticeship()
    _seed(a)
    assert a.total_masters() == 1


def test_register_duplicate():
    a = BeastmanApprenticeship()
    _seed(a)
    res = a.register_master(
        master_id="oz_combat_master",
        trade=Trade.LORE,
        tier=MasterTier.NOVICE_MASTER,
        base_xp=100, session_gil_cost=50,
    )
    assert res is None


def test_register_zero_xp():
    a = BeastmanApprenticeship()
    res = a.register_master(
        master_id="bad",
        trade=Trade.COMBAT_ARTS,
        tier=MasterTier.NOVICE_MASTER,
        base_xp=0, session_gil_cost=10,
    )
    assert res is None


def test_register_negative_gil():
    a = BeastmanApprenticeship()
    res = a.register_master(
        master_id="bad",
        trade=Trade.COMBAT_ARTS,
        tier=MasterTier.NOVICE_MASTER,
        base_xp=100, session_gil_cost=-1,
    )
    assert res is None


def test_bind_basic():
    a = BeastmanApprenticeship()
    _seed(a)
    res = a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    assert res.accepted


def test_bind_unknown_master():
    a = BeastmanApprenticeship()
    res = a.bind(
        player_id="kraw",
        master_id="ghost",
        player_level=50,
    )
    assert not res.accepted


def test_bind_below_tier_floor():
    a = BeastmanApprenticeship()
    a.register_master(
        master_id="grand",
        trade=Trade.COMBAT_ARTS,
        tier=MasterTier.GRAND_MASTER,
        base_xp=500, session_gil_cost=1000,
    )
    res = a.bind(
        player_id="kraw",
        master_id="grand",
        player_level=50,
    )
    assert not res.accepted


def test_bind_seasoned_at_30():
    a = BeastmanApprenticeship()
    a.register_master(
        master_id="seasoned",
        trade=Trade.MAGIC_ARTS,
        tier=MasterTier.SEASONED_MASTER,
        base_xp=300, session_gil_cost=300,
    )
    res = a.bind(
        player_id="kraw",
        master_id="seasoned",
        player_level=30,
    )
    assert res.accepted


def test_bind_already_bound():
    a = BeastmanApprenticeship()
    _seed(a)
    a.register_master(
        master_id="other",
        trade=Trade.LORE,
        tier=MasterTier.NOVICE_MASTER,
        base_xp=100, session_gil_cost=10,
    )
    a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    res = a.bind(
        player_id="kraw",
        master_id="other",
        player_level=5,
    )
    assert not res.accepted


def test_train_basic():
    a = BeastmanApprenticeship()
    _seed(a)
    a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    res = a.train(
        player_id="kraw",
        gil_held=1000,
        trade_level=0,
    )
    assert res.accepted
    # base 200 * 100% multiplier * 100% retain = 200
    assert res.xp_awarded == 200
    assert res.gil_charged == 100
    assert res.trade == Trade.COMBAT_ARTS


def test_train_grand_master_high_xp():
    a = BeastmanApprenticeship()
    a.register_master(
        master_id="grand",
        trade=Trade.MAGIC_ARTS,
        tier=MasterTier.GRAND_MASTER,
        base_xp=200, session_gil_cost=500,
    )
    a.bind(
        player_id="kraw",
        master_id="grand",
        player_level=99,
    )
    res = a.train(
        player_id="kraw",
        gil_held=1000,
        trade_level=0,
    )
    # 200 * 350% = 700
    assert res.xp_awarded == 700


def test_train_diminishes_with_trade_level():
    a = BeastmanApprenticeship()
    _seed(a)
    a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    # trade_level 50 = 5 steps × 5% = 25% off → 75% retain
    res = a.train(
        player_id="kraw",
        gil_held=1000,
        trade_level=50,
    )
    # 200 * 75% = 150
    assert res.xp_awarded == 150


def test_train_diminish_floor_at_25():
    a = BeastmanApprenticeship()
    _seed(a)
    a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    # very high trade_level → floor at 25%
    res = a.train(
        player_id="kraw",
        gil_held=1000,
        trade_level=999,
    )
    assert res.xp_awarded == 50


def test_train_insufficient_gil():
    a = BeastmanApprenticeship()
    _seed(a)
    a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    res = a.train(
        player_id="kraw",
        gil_held=10,
        trade_level=0,
    )
    assert not res.accepted


def test_train_not_bound():
    a = BeastmanApprenticeship()
    res = a.train(
        player_id="ghost",
        gil_held=999,
        trade_level=0,
    )
    assert not res.accepted


def test_train_negative_trade_level():
    a = BeastmanApprenticeship()
    _seed(a)
    a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    res = a.train(
        player_id="kraw",
        gil_held=1000,
        trade_level=-1,
    )
    assert not res.accepted


def test_unbind():
    a = BeastmanApprenticeship()
    _seed(a)
    a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    assert a.unbind(player_id="kraw")
    # Re-bind allowed after unbind
    res = a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    assert res.accepted


def test_unbind_not_bound():
    a = BeastmanApprenticeship()
    assert not a.unbind(player_id="ghost")


def test_bound_master_lookup():
    a = BeastmanApprenticeship()
    _seed(a)
    a.bind(
        player_id="kraw",
        master_id="oz_combat_master",
        player_level=5,
    )
    assert a.bound_master(
        player_id="kraw",
    ) == "oz_combat_master"


def test_bound_master_none():
    a = BeastmanApprenticeship()
    assert a.bound_master(player_id="ghost") is None
