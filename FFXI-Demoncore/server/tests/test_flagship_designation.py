"""Tests for flagship designation."""
from __future__ import annotations

from server.flagship_designation import (
    FlagshipDesignation,
    REDESIGNATE_COOLDOWN_SECONDS,
)


def test_designate_happy():
    f = FlagshipDesignation()
    r = f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    assert r.accepted is True
    assert r.flagship_ship_id == "ship_a"


def test_designate_blank_ids():
    f = FlagshipDesignation()
    r = f.designate(
        charter_id="", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    assert r.accepted is False


def test_redesignate_cooldown_blocks():
    f = FlagshipDesignation()
    f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    r = f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_b", now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "redesignate cooldown"
    assert r.cooldown_remaining > 0


def test_redesignate_after_cooldown():
    f = FlagshipDesignation()
    f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    r = f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_b",
        now_seconds=REDESIGNATE_COOLDOWN_SECONDS + 1,
    )
    assert r.accepted is True
    assert r.flagship_ship_id == "ship_b"


def test_designate_wrong_captain_rejected():
    f = FlagshipDesignation()
    f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    r = f.designate(
        charter_id="c1", captain_id="other",
        ship_id="ship_b",
        now_seconds=REDESIGNATE_COOLDOWN_SECONDS + 1,
    )
    assert r.accepted is False


def test_undesignate_happy():
    f = FlagshipDesignation()
    f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    r = f.undesignate(
        charter_id="c1", captain_id="cap",
        now_seconds=10,
    )
    assert r.accepted is True
    assert f.flagship_for(charter_id="c1") is None


def test_undesignate_no_flagship():
    f = FlagshipDesignation()
    r = f.undesignate(
        charter_id="c1", captain_id="cap",
        now_seconds=0,
    )
    assert r.accepted is False


def test_buffs_for_flagship():
    f = FlagshipDesignation()
    f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    b = f.buffs_for(ship_id="ship_a", charter_id="c1")
    assert b.is_flagship is True
    assert b.hp_max_bonus_pct == 20
    assert b.crew_skill_bonus == 5
    assert b.damage_resist_bonus_pct == 10
    assert b.always_keep_as_prize is True


def test_buffs_for_non_flagship():
    f = FlagshipDesignation()
    f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    b = f.buffs_for(ship_id="other_ship", charter_id="c1")
    assert b.is_flagship is False
    assert b.hp_max_bonus_pct == 0


def test_buffs_for_no_charter():
    f = FlagshipDesignation()
    b = f.buffs_for(ship_id="ship_a", charter_id="ghost")
    assert b.is_flagship is False


def test_report_sunk_clears_flagship():
    f = FlagshipDesignation()
    f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    ok = f.report_sunk(charter_id="c1", ship_id="ship_a")
    assert ok is True
    assert f.flagship_for(charter_id="c1") is None


def test_report_sunk_wrong_ship():
    f = FlagshipDesignation()
    f.designate(
        charter_id="c1", captain_id="cap",
        ship_id="ship_a", now_seconds=0,
    )
    ok = f.report_sunk(charter_id="c1", ship_id="other_ship")
    assert ok is False


def test_flagship_for_default_none():
    f = FlagshipDesignation()
    assert f.flagship_for(charter_id="ghost") is None
