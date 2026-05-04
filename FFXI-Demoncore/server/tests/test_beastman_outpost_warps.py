"""Tests for the beastman outpost warps."""
from __future__ import annotations

from server.beastman_outpost_warps import (
    BeastmanOutpostWarps,
    HomeCity,
    ReputationTier,
)


def _seed(w):
    w.register_outpost(
        outpost_id="meriphataud_op",
        zone_id="meriphataud_mts",
        home_city=HomeCity.OZTROJA,
        distance=2,
        base_price=200,
    )


def test_register():
    w = BeastmanOutpostWarps()
    _seed(w)
    assert w.total_outposts() == 1


def test_register_duplicate():
    w = BeastmanOutpostWarps()
    _seed(w)
    res = w.register_outpost(
        outpost_id="meriphataud_op",
        zone_id="other",
        home_city=HomeCity.HALVUNG,
        distance=2,
        base_price=100,
    )
    assert res is None


def test_register_zero_distance():
    w = BeastmanOutpostWarps()
    res = w.register_outpost(
        outpost_id="bad",
        zone_id="x",
        home_city=HomeCity.OZTROJA,
        distance=0,
        base_price=100,
    )
    assert res is None


def test_register_distance_too_high():
    w = BeastmanOutpostWarps()
    res = w.register_outpost(
        outpost_id="bad",
        zone_id="x",
        home_city=HomeCity.OZTROJA,
        distance=10,
        base_price=100,
    )
    assert res is None


def test_register_negative_price():
    w = BeastmanOutpostWarps()
    res = w.register_outpost(
        outpost_id="bad",
        zone_id="x",
        home_city=HomeCity.OZTROJA,
        distance=1,
        base_price=-1,
    )
    assert res is None


def test_register_empty_zone():
    w = BeastmanOutpostWarps()
    res = w.register_outpost(
        outpost_id="bad",
        zone_id="",
        home_city=HomeCity.OZTROJA,
        distance=1,
        base_price=100,
    )
    assert res is None


def test_unlock_basic():
    w = BeastmanOutpostWarps()
    _seed(w)
    assert w.unlock(
        player_id="kraw",
        outpost_id="meriphataud_op",
    )


def test_unlock_double_rejected():
    w = BeastmanOutpostWarps()
    _seed(w)
    w.unlock(player_id="kraw", outpost_id="meriphataud_op")
    res = w.unlock(player_id="kraw", outpost_id="meriphataud_op")
    assert not res


def test_unlock_unknown_outpost():
    w = BeastmanOutpostWarps()
    res = w.unlock(player_id="kraw", outpost_id="ghost")
    assert not res


def test_is_unlocked():
    w = BeastmanOutpostWarps()
    _seed(w)
    w.unlock(player_id="kraw", outpost_id="meriphataud_op")
    assert w.is_unlocked(
        player_id="kraw", outpost_id="meriphataud_op",
    )
    assert not w.is_unlocked(
        player_id="ghost", outpost_id="meriphataud_op",
    )


def test_price_for_neutral():
    w = BeastmanOutpostWarps()
    _seed(w)
    # base 200 × distance 2 = 400, no discount
    assert w.price_for(
        outpost_id="meriphataud_op",
        reputation=ReputationTier.NEUTRAL,
    ) == 400


def test_price_for_friendly():
    w = BeastmanOutpostWarps()
    _seed(w)
    # 400 - 10% = 360
    assert w.price_for(
        outpost_id="meriphataud_op",
        reputation=ReputationTier.FRIENDLY,
    ) == 360


def test_price_for_kin_half_off():
    w = BeastmanOutpostWarps()
    _seed(w)
    # 400 - 50% = 200
    assert w.price_for(
        outpost_id="meriphataud_op",
        reputation=ReputationTier.KIN,
    ) == 200


def test_price_unknown_outpost():
    w = BeastmanOutpostWarps()
    assert w.price_for(
        outpost_id="ghost",
        reputation=ReputationTier.NEUTRAL,
    ) is None


def test_warp_basic():
    w = BeastmanOutpostWarps()
    _seed(w)
    w.unlock(player_id="kraw", outpost_id="meriphataud_op")
    res = w.warp(
        player_id="kraw",
        outpost_id="meriphataud_op",
        gil_held=500,
        reputation=ReputationTier.NEUTRAL,
    )
    assert res.accepted
    assert res.gil_charged == 400


def test_warp_locked():
    w = BeastmanOutpostWarps()
    _seed(w)
    res = w.warp(
        player_id="kraw",
        outpost_id="meriphataud_op",
        gil_held=999,
        reputation=ReputationTier.NEUTRAL,
    )
    assert not res.accepted


def test_warp_insufficient_gil():
    w = BeastmanOutpostWarps()
    _seed(w)
    w.unlock(player_id="kraw", outpost_id="meriphataud_op")
    res = w.warp(
        player_id="kraw",
        outpost_id="meriphataud_op",
        gil_held=100,
        reputation=ReputationTier.NEUTRAL,
    )
    assert not res.accepted


def test_warp_unknown_outpost():
    w = BeastmanOutpostWarps()
    res = w.warp(
        player_id="kraw",
        outpost_id="ghost",
        gil_held=999,
        reputation=ReputationTier.NEUTRAL,
    )
    assert not res.accepted


def test_per_player_unlock_isolation():
    w = BeastmanOutpostWarps()
    _seed(w)
    w.unlock(player_id="alice", outpost_id="meriphataud_op")
    assert not w.is_unlocked(
        player_id="bob", outpost_id="meriphataud_op",
    )


def test_warp_at_kin_tier():
    w = BeastmanOutpostWarps()
    _seed(w)
    w.unlock(player_id="kraw", outpost_id="meriphataud_op")
    res = w.warp(
        player_id="kraw",
        outpost_id="meriphataud_op",
        gil_held=200,
        reputation=ReputationTier.KIN,
    )
    assert res.accepted
    assert res.gil_charged == 200
