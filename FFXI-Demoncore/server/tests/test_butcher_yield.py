"""Tests for butcher_yield."""
from __future__ import annotations

from server.butcher_yield import (
    Carcass, PartKind, ToolKind, butcher_carcass,
)


def _carcass(**overrides):
    base = dict(
        quarry_id="dhalmel", weight_kg=120.0,
        has_horns=True, hide_intact=True,
    )
    base.update(overrides)
    return Carcass(**base)


def test_steel_knife_baseline():
    c = _carcass(weight_kg=100.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    # skill_mult=1.0, all tool factors 1.0
    # meat = 100*1.5 = 150
    assert out.meat == 150
    assert out.hide == 1
    assert out.bone == 80
    assert out.sinew == 40


def test_bare_hands_yields_little():
    c = _carcass(weight_kg=100.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.BARE_HANDS,
    )
    # bare hands: meat 0.3 → 100*1.5*1.0*0.3 = 45
    # hide 0.0 → 0
    # sinew 0.0 → 0
    # bone 0.2 → 16
    assert out.meat == 45
    assert out.hide == 0
    assert out.sinew == 0


def test_cleaver_more_meat():
    c = _carcass(weight_kg=100.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.BUTCHER_CLEAVER,
    )
    # meat 1.3 → 195
    assert out.meat == 195


def test_scrimshaw_more_bone():
    c = _carcass(weight_kg=100.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.SCRIMSHAW_KIT,
    )
    # bone 1.5 → 100*0.8*1.0*1.5 = 120
    assert out.bone == 120


def test_high_skill_more_yield():
    c = _carcass(weight_kg=100.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=100, tool=ToolKind.STEEL_KNIFE,
    )
    # skill_mult 1.5, meat = 100*1.5*1.5 = 225
    assert out.meat == 225


def test_zero_skill_floor():
    c = _carcass(weight_kg=100.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=0, tool=ToolKind.STEEL_KNIFE,
    )
    # skill_mult 0.5, meat 100*1.5*0.5 = 75
    assert out.meat == 75
    # hide requires skill > 0
    assert out.hide == 0


def test_ruined_hide_marked():
    c = _carcass(hide_intact=False)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    assert out.hide == 0
    assert out.hide_ruined is True


def test_intact_hide_with_good_tool():
    c = _carcass()
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    assert out.hide == 1
    assert out.hide_ruined is False


def test_horns_yield_for_horned():
    c = _carcass(has_horns=True, weight_kg=100.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    # has_horns + 100kg → 1 + 1 = 2 horns
    assert out.horn == 2


def test_no_horns_no_horn_yield():
    c = _carcass(has_horns=False)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    assert out.horn == 0


def test_small_horned_one_horn():
    c = _carcass(has_horns=True, weight_kg=20.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    # under 100kg → just 1 horn
    assert out.horn == 1


def test_zero_weight_zero_meat():
    c = _carcass(weight_kg=0.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    assert out.meat == 0
    assert out.bone == 0


def test_quarry_id_carried():
    c = _carcass(quarry_id="boar", weight_kg=50.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    assert out.quarry_id == "boar"


def test_blank_quarry_returns_empty():
    c = _carcass(quarry_id="", weight_kg=50.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    assert out.meat == 0


def test_skill_above_100_caps():
    c = _carcass(weight_kg=100.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=200, tool=ToolKind.STEEL_KNIFE,
    )
    # caps at 1.5x → 225
    assert out.meat == 225


def test_organ_yield_with_steel():
    c = _carcass(weight_kg=100.0)
    out = butcher_carcass(
        carcass=c, butcher_skill=50, tool=ToolKind.STEEL_KNIFE,
    )
    # organ 100*0.3*1.0*1.0 = 30
    assert out.organ == 30


def test_six_part_kinds():
    assert len(list(PartKind)) == 6


def test_five_tool_kinds():
    assert len(list(ToolKind)) == 5
