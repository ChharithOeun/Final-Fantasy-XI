"""Tests for body_proportions."""
from __future__ import annotations

from server.body_proportions import BodyProportions


def test_default_profile_neutral():
    b = BodyProportions()
    p = b.profile(player_id="bob")
    assert p.height_modifier == 0.0
    assert p.build_modifier == 0.0
    assert p.posture_modifier == 0.0


def test_set_height():
    b = BodyProportions()
    assert b.set_height(
        player_id="bob", value=0.5, now_day=10,
    ) is True
    assert b.profile(
        player_id="bob",
    ).height_modifier == 0.5


def test_set_height_out_of_range_blocked():
    b = BodyProportions()
    assert b.set_height(
        player_id="bob", value=1.5, now_day=10,
    ) is False


def test_set_height_blank_blocked():
    b = BodyProportions()
    assert b.set_height(
        player_id="", value=0.5, now_day=10,
    ) is False


def test_set_build():
    b = BodyProportions()
    assert b.set_build(
        player_id="bob", value=0.7, now_day=10,
    ) is True


def test_set_posture():
    b = BodyProportions()
    assert b.set_posture(
        player_id="bob", value=-0.5, now_day=10,
    ) is True


def test_lockout_blocks_quick_re_change():
    b = BodyProportions()
    b.set_height(
        player_id="bob", value=0.5, now_day=10,
    )
    # Same day re-change blocked
    assert b.set_height(
        player_id="bob", value=0.6, now_day=10,
    ) is False


def test_lockout_releases_after_day():
    b = BodyProportions()
    b.set_height(
        player_id="bob", value=0.5, now_day=10,
    )
    assert b.set_height(
        player_id="bob", value=0.6, now_day=11,
    ) is True


def test_lockout_until():
    b = BodyProportions()
    b.set_height(
        player_id="bob", value=0.5, now_day=10,
    )
    assert b.lockout_until(player_id="bob") == 11


def test_lockout_until_no_state_zero():
    b = BodyProportions()
    assert b.lockout_until(player_id="bob") == 0


def test_reset():
    b = BodyProportions()
    b.set_height(
        player_id="bob", value=0.5, now_day=10,
    )
    assert b.reset(
        player_id="bob", now_day=11,
    ) is True
    assert b.profile(
        player_id="bob",
    ).height_modifier == 0.0


def test_reset_no_state_blocked():
    b = BodyProportions()
    assert b.reset(
        player_id="bob", now_day=10,
    ) is False


def test_height_stat_impact():
    b = BodyProportions()
    b.set_height(
        player_id="bob", value=1.0, now_day=10,
    )
    impacts = b.stat_impacts(player_id="bob")
    assert impacts.reach_bonus == 3
    assert impacts.evasion_bonus == -3


def test_build_stat_impact():
    b = BodyProportions()
    b.set_build(
        player_id="bob", value=1.0, now_day=10,
    )
    impacts = b.stat_impacts(player_id="bob")
    assert impacts.str_bonus == 3
    assert impacts.agi_bonus == -3
    assert impacts.hp_bonus == 30


def test_posture_upright_chr_acc():
    b = BodyProportions()
    b.set_posture(
        player_id="bob", value=1.0, now_day=10,
    )
    impacts = b.stat_impacts(player_id="bob")
    assert impacts.chr_bonus == 3
    assert impacts.acc_bonus == 3
    assert impacts.stealth_bonus == 0


def test_posture_hunched_stealth():
    b = BodyProportions()
    b.set_posture(
        player_id="bob", value=-1.0, now_day=10,
    )
    impacts = b.stat_impacts(player_id="bob")
    assert impacts.stealth_bonus == 3
    assert impacts.chr_bonus == 0


def test_zero_default_zero_impacts():
    b = BodyProportions()
    impacts = b.stat_impacts(player_id="bob")
    assert impacts.str_bonus == 0
    assert impacts.hp_bonus == 0


def test_combined_modifiers():
    b = BodyProportions()
    b.set_height(
        player_id="bob", value=0.5, now_day=10,
    )
    b.set_build(
        player_id="bob", value=1.0, now_day=11,
    )
    impacts = b.stat_impacts(player_id="bob")
    assert impacts.reach_bonus == 1  # 0.5*3 = 1
    assert impacts.str_bonus == 3
