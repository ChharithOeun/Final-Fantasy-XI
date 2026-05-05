"""Tests for the beastman oath council."""
from __future__ import annotations

from server.beastman_oath_council import (
    BeastmanOathCouncil,
    CouncilCity,
    OathKind,
    OathState,
)


def _seed(c):
    c.register_oath(
        oath_id="oath_loyal_oz",
        city=CouncilCity.OZTROJA,
        kind=OathKind.LOYALTY,
        duration_days=30,
        obligation_threshold=10,
        reward_standing=500,
        break_penalty=200,
    )


def test_register():
    c = BeastmanOathCouncil()
    _seed(c)
    assert c.total_oaths() == 1


def test_register_duplicate():
    c = BeastmanOathCouncil()
    _seed(c)
    res = c.register_oath(
        oath_id="oath_loyal_oz",
        city=CouncilCity.HALVUNG,
        kind=OathKind.LOYALTY,
        duration_days=10,
        obligation_threshold=5,
        reward_standing=100,
        break_penalty=50,
    )
    assert res is None


def test_register_zero_duration():
    c = BeastmanOathCouncil()
    res = c.register_oath(
        oath_id="bad",
        city=CouncilCity.OZTROJA,
        kind=OathKind.LOYALTY,
        duration_days=0,
        obligation_threshold=5,
        reward_standing=10, break_penalty=5,
    )
    assert res is None


def test_register_zero_threshold():
    c = BeastmanOathCouncil()
    res = c.register_oath(
        oath_id="bad",
        city=CouncilCity.OZTROJA,
        kind=OathKind.LOYALTY,
        duration_days=10,
        obligation_threshold=0,
        reward_standing=10, break_penalty=5,
    )
    assert res is None


def test_register_negative_reward():
    c = BeastmanOathCouncil()
    res = c.register_oath(
        oath_id="bad",
        city=CouncilCity.OZTROJA,
        kind=OathKind.LOYALTY,
        duration_days=10,
        obligation_threshold=5,
        reward_standing=-1, break_penalty=5,
    )
    assert res is None


def test_swear_basic():
    c = BeastmanOathCouncil()
    _seed(c)
    res = c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    assert res.accepted
    assert res.expires_at_day == 30


def test_swear_unknown():
    c = BeastmanOathCouncil()
    res = c.swear(
        player_id="kraw", oath_id="ghost", now_day=0,
    )
    assert not res.accepted


def test_swear_double_blocked():
    c = BeastmanOathCouncil()
    _seed(c)
    c.register_oath(
        oath_id="oath_revenge_oz",
        city=CouncilCity.OZTROJA,
        kind=OathKind.VENGEANCE,
        duration_days=10,
        obligation_threshold=3,
        reward_standing=100, break_penalty=50,
    )
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    res = c.swear(
        player_id="kraw", oath_id="oath_revenge_oz", now_day=1,
    )
    assert not res.accepted


def test_swear_different_city_allowed():
    c = BeastmanOathCouncil()
    _seed(c)
    c.register_oath(
        oath_id="oath_halv",
        city=CouncilCity.HALVUNG,
        kind=OathKind.TRIBUTE,
        duration_days=10,
        obligation_threshold=5,
        reward_standing=100, break_penalty=50,
    )
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    res = c.swear(
        player_id="kraw", oath_id="oath_halv", now_day=0,
    )
    assert res.accepted


def test_report_obligation_basic():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    res = c.report_obligation(
        player_id="kraw", oath_id="oath_loyal_oz", increment=3,
    )
    assert res.accepted
    assert res.progress == 3
    assert not res.fulfilled


def test_report_obligation_clamps():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    res = c.report_obligation(
        player_id="kraw", oath_id="oath_loyal_oz", increment=999,
    )
    assert res.progress == 10
    assert res.fulfilled


def test_report_zero_increment():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    res = c.report_obligation(
        player_id="kraw", oath_id="oath_loyal_oz", increment=0,
    )
    assert not res.accepted


def test_report_inactive():
    c = BeastmanOathCouncil()
    _seed(c)
    res = c.report_obligation(
        player_id="kraw", oath_id="oath_loyal_oz", increment=1,
    )
    assert not res.accepted


def test_complete_basic():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    c.report_obligation(
        player_id="kraw", oath_id="oath_loyal_oz", increment=10,
    )
    res = c.complete(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=10,
    )
    assert res.accepted
    assert res.standing_awarded == 500
    assert res.state == OathState.FULFILLED


def test_complete_obligation_incomplete():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    res = c.complete(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=5,
    )
    assert not res.accepted


def test_complete_after_duration():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    c.report_obligation(
        player_id="kraw", oath_id="oath_loyal_oz", increment=10,
    )
    res = c.complete(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=100,
    )
    assert not res.accepted
    assert res.state == OathState.BROKEN


def test_break_oath_basic():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    res = c.break_oath(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=5,
    )
    assert res.accepted
    assert res.standing_penalty == 200


def test_break_inactive():
    c = BeastmanOathCouncil()
    _seed(c)
    res = c.break_oath(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    assert not res.accepted


def test_active_oath_for():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    assert c.active_oath_for(
        player_id="kraw", city=CouncilCity.OZTROJA,
    ) == "oath_loyal_oz"


def test_active_oath_for_after_break():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    c.break_oath(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=5,
    )
    assert c.active_oath_for(
        player_id="kraw", city=CouncilCity.OZTROJA,
    ) is None


def test_active_oath_for_none():
    c = BeastmanOathCouncil()
    assert c.active_oath_for(
        player_id="ghost", city=CouncilCity.OZTROJA,
    ) is None


def test_swear_after_fulfill_re_eligible():
    c = BeastmanOathCouncil()
    _seed(c)
    c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=0,
    )
    c.report_obligation(
        player_id="kraw", oath_id="oath_loyal_oz", increment=10,
    )
    c.complete(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=5,
    )
    # Re-swearing the same oath is allowed since previous is FULFILLED
    res = c.swear(
        player_id="kraw", oath_id="oath_loyal_oz", now_day=10,
    )
    assert res.accepted
