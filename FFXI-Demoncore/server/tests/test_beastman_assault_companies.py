"""Tests for the beastman assault companies."""
from __future__ import annotations

from server.beastman_assault_companies import (
    BeastmanAssaultCompanies,
    MercRank,
    ObjectiveKind,
)


def _seed(c):
    c.form_squad(
        squad_id="alpha",
        members=("kraw", "zlar", "syrene"),
    )
    c.register_mission(
        mission_id="m_warehouse",
        kind=ObjectiveKind.SABOTAGE_SUPPLY,
        zone_id="bastok_mines",
        rank_required=MercRank.PRIVATE,
        timer_seconds=1800,
        merc_payout=500,
    )


def test_form_squad():
    c = BeastmanAssaultCompanies()
    _seed(c)
    assert c.total_squads() == 1


def test_form_squad_too_small():
    c = BeastmanAssaultCompanies()
    res = c.form_squad(
        squad_id="a", members=("solo",),
    )
    assert res is None


def test_form_squad_too_large():
    c = BeastmanAssaultCompanies()
    res = c.form_squad(
        squad_id="a",
        members=tuple(f"p{i}" for i in range(7)),
    )
    assert res is None


def test_form_squad_duplicate_member():
    c = BeastmanAssaultCompanies()
    res = c.form_squad(
        squad_id="a", members=("a", "a", "b"),
    )
    assert res is None


def test_register_mission():
    c = BeastmanAssaultCompanies()
    _seed(c)
    assert c.total_missions() == 1


def test_register_mission_zero_timer():
    c = BeastmanAssaultCompanies()
    res = c.register_mission(
        mission_id="bad",
        kind=ObjectiveKind.HOLD_GROUND,
        zone_id="x",
        rank_required=MercRank.PRIVATE,
        timer_seconds=0,
        merc_payout=100,
    )
    assert res is None


def test_register_mission_zero_payout():
    c = BeastmanAssaultCompanies()
    res = c.register_mission(
        mission_id="bad",
        kind=ObjectiveKind.HOLD_GROUND,
        zone_id="x",
        rank_required=MercRank.PRIVATE,
        timer_seconds=600,
        merc_payout=0,
    )
    assert res is None


def test_deploy_basic():
    c = BeastmanAssaultCompanies()
    _seed(c)
    res = c.deploy(
        squad_id="alpha",
        mission_id="m_warehouse",
        now_seconds=0,
    )
    assert res.accepted
    assert res.deadline == 1800


def test_deploy_already_active():
    c = BeastmanAssaultCompanies()
    _seed(c)
    c.deploy(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=0,
    )
    res = c.deploy(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=10,
    )
    assert not res.accepted


def test_deploy_rank_too_low():
    c = BeastmanAssaultCompanies()
    _seed(c)
    c.register_mission(
        mission_id="m_hard",
        kind=ObjectiveKind.ASSASSINATE,
        zone_id="z",
        rank_required=MercRank.SERGEANT,
        timer_seconds=1800,
        merc_payout=2000,
    )
    res = c.deploy(
        squad_id="alpha", mission_id="m_hard", now_seconds=0,
    )
    assert not res.accepted


def test_deploy_unknown_squad_or_mission():
    c = BeastmanAssaultCompanies()
    _seed(c)
    res = c.deploy(
        squad_id="ghost", mission_id="m_warehouse", now_seconds=0,
    )
    assert not res.accepted


def test_complete_basic():
    c = BeastmanAssaultCompanies()
    _seed(c)
    c.deploy(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=0,
    )
    res = c.complete(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=600,
    )
    assert res.accepted
    assert res.merc_awarded == 500


def test_complete_after_timer():
    c = BeastmanAssaultCompanies()
    _seed(c)
    c.deploy(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=0,
    )
    res = c.complete(
        squad_id="alpha", mission_id="m_warehouse",
        now_seconds=999_999,
    )
    assert not res.accepted


def test_complete_not_on_mission():
    c = BeastmanAssaultCompanies()
    _seed(c)
    res = c.complete(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=0,
    )
    assert not res.accepted


def test_promotion_at_5_corporal():
    c = BeastmanAssaultCompanies()
    _seed(c)
    for i in range(5):
        c.deploy(
            squad_id="alpha",
            mission_id="m_warehouse",
            now_seconds=i * 2000,
        )
        last = c.complete(
            squad_id="alpha",
            mission_id="m_warehouse",
            now_seconds=i * 2000 + 500,
        )
    assert last.new_rank == MercRank.CORPORAL
    assert last.promoted


def test_no_promotion_below_threshold():
    c = BeastmanAssaultCompanies()
    _seed(c)
    c.deploy(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=0,
    )
    res = c.complete(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=500,
    )
    assert res.new_rank == MercRank.PRIVATE
    assert not res.promoted


def test_fail_releases_deployment():
    c = BeastmanAssaultCompanies()
    _seed(c)
    c.deploy(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=0,
    )
    assert c.fail(
        squad_id="alpha",
        mission_id="m_warehouse",
        reason="wipe",
    )
    # Re-deploy should now succeed
    res = c.deploy(
        squad_id="alpha", mission_id="m_warehouse", now_seconds=2000,
    )
    assert res.accepted


def test_fail_unknown_deployment():
    c = BeastmanAssaultCompanies()
    _seed(c)
    res = c.fail(
        squad_id="alpha",
        mission_id="m_warehouse",
        reason="nope",
    )
    assert not res


def test_squad_rank_lookup():
    c = BeastmanAssaultCompanies()
    _seed(c)
    assert c.squad_rank(squad_id="alpha") == MercRank.PRIVATE


def test_squad_rank_unknown():
    c = BeastmanAssaultCompanies()
    assert c.squad_rank(squad_id="ghost") is None


def test_form_squad_duplicate_id():
    c = BeastmanAssaultCompanies()
    _seed(c)
    res = c.form_squad(
        squad_id="alpha", members=("a", "b", "c"),
    )
    assert res is None


def test_register_mission_duplicate_id():
    c = BeastmanAssaultCompanies()
    _seed(c)
    res = c.register_mission(
        mission_id="m_warehouse",
        kind=ObjectiveKind.HOLD_GROUND,
        zone_id="z",
        rank_required=MercRank.PRIVATE,
        timer_seconds=600,
        merc_payout=200,
    )
    assert res is None
