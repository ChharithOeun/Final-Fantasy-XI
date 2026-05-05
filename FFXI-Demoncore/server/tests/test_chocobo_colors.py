"""Tests for the chocobo color registry."""
from __future__ import annotations

from server.chocobo_colors import (
    ChocoboColor,
    ChocoboColorRegistry,
    Element,
    Tier,
)


def test_all_ten_colors():
    r = ChocoboColorRegistry()
    assert r.total_colors() == 10


def test_yellow_profile():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.YELLOW)
    assert p.element == Element.NONE
    assert p.movement.run_speed_tier == Tier.HIGHEST
    assert not p.movement.can_swim
    assert not p.movement.can_fly


def test_brown_profile():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.BROWN)
    assert p.element == Element.EARTH
    assert p.hp_tier == Tier.HIGHEST
    assert p.movement.run_speed_tier == Tier.LOWEST


def test_light_blue_can_dive():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.LIGHT_BLUE)
    assert p.movement.can_swim
    assert p.movement.can_dive
    assert p.element == Element.WATER


def test_blue_skates():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.BLUE)
    assert p.movement.skates_on_ice
    assert p.element == Element.ICE


def test_light_purple_flash_step():
    r = ChocoboColorRegistry()
    abs_ = r.ability_ids(color=ChocoboColor.LIGHT_PURPLE)
    assert "flash_step_30y" in abs_


def test_green_thf_kit():
    r = ChocoboColorRegistry()
    abs_ = r.ability_ids(color=ChocoboColor.GREEN)
    assert "thf_lockpick_high" in abs_
    assert "thf_sata" in abs_


def test_red_walks_on_lava():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.RED)
    assert p.movement.walks_on_lava
    assert p.element == Element.FIRE


def test_white_holy():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.WHITE)
    assert p.element == Element.HOLY
    assert p.mp_tier == Tier.HIGHEST
    abs_ = r.ability_ids(color=ChocoboColor.WHITE)
    assert "raise_iii" in abs_
    assert "double_mb_vs_undead_fomor" in abs_


def test_rainbow_cannot_breed():
    r = ChocoboColorRegistry()
    assert not r.can_breed(color=ChocoboColor.RAINBOW)


def test_rainbow_random_element():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.RAINBOW)
    assert p.element == Element.RANDOM


def test_grey_double_jump_glide():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.GREY)
    assert p.movement.double_jump
    assert p.movement.glide
    assert p.element == Element.DARK


def test_grey_aoe_warp():
    r = ChocoboColorRegistry()
    abs_ = r.ability_ids(color=ChocoboColor.GREY)
    assert "aoe_warp_ii_party" in abs_


def test_all_have_skillchain():
    r = ChocoboColorRegistry()
    for c in r.all_colors():
        if c == ChocoboColor.RAINBOW:
            assert "solo_skillchain" in r.ability_ids(color=c)
        else:
            assert "skillchain" in r.ability_ids(color=c)


def test_yellow_jump_highest():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.YELLOW)
    assert p.movement.jump_height_tier == Tier.HIGHEST


def test_brown_aoe_stoneskin():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.BROWN)
    found = [a for a in p.abilities if a.ability_id == "aoe_stoneskin"]
    assert len(found) == 1
    assert found[0].cooldown_seconds == 180


def test_can_breed_default_true():
    r = ChocoboColorRegistry()
    for c in r.all_colors():
        if c == ChocoboColor.RAINBOW:
            continue
        assert r.can_breed(color=c)


def test_all_colors_iter():
    r = ChocoboColorRegistry()
    cs = r.all_colors()
    assert ChocoboColor.YELLOW in cs
    assert ChocoboColor.RAINBOW in cs


def test_white_immunities():
    r = ChocoboColorRegistry()
    abs_ = r.ability_ids(color=ChocoboColor.WHITE)
    assert "immune_sleep_silence" in abs_


def test_rainbow_walks_on_all_terrain():
    r = ChocoboColorRegistry()
    p = r.profile_for(color=ChocoboColor.RAINBOW)
    assert p.movement.walks_on_water
    assert p.movement.walks_on_lava
