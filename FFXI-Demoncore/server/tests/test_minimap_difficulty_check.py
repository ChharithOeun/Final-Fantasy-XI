"""Tests for the minimap difficulty checker."""
from __future__ import annotations

from server.minimap_difficulty_check import (
    ConVerdict,
    DefenseLean,
    ELEMENT_HINT_SKILL_GATE,
    ElementHint,
    MinimapDifficultyChecker,
)


def test_register_mob():
    chk = MinimapDifficultyChecker()
    card = chk.register_mob(
        mob_id="orc_a", level=20,
        defense_lean=DefenseLean.HEAVY_DEF,
    )
    assert card is not None
    assert card.level == 20


def test_double_register_rejected():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="orc_a", level=10)
    second = chk.register_mob(mob_id="orc_a", level=20)
    assert second is None


def test_invalid_level_rejected():
    chk = MinimapDifficultyChecker()
    assert chk.register_mob(mob_id="x", level=0) is None
    assert chk.register_mob(mob_id="y", level=-5) is None


def test_too_weak_far_below():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="m", level=5)
    res = chk.check_mob(mob_id="m", viewer_level=50)
    assert res.verdict == ConVerdict.TOO_WEAK


def test_easy_prey():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="m", level=46)
    res = chk.check_mob(mob_id="m", viewer_level=50)
    assert res.verdict == ConVerdict.EASY_PREY


def test_decent_challenge():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="m", level=49)
    res = chk.check_mob(mob_id="m", viewer_level=50)
    assert res.verdict == ConVerdict.DECENT_CHALLENGE


def test_even_match_at_zero_delta():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="m", level=50)
    res = chk.check_mob(mob_id="m", viewer_level=50)
    assert res.verdict == ConVerdict.EVEN_MATCH


def test_tough_one_to_three_above():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="m", level=53)
    res = chk.check_mob(mob_id="m", viewer_level=50)
    assert res.verdict == ConVerdict.TOUGH


def test_very_tough():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="m", level=57)
    res = chk.check_mob(mob_id="m", viewer_level=50)
    assert res.verdict == ConVerdict.VERY_TOUGH


def test_incredibly_tough():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="m", level=80)
    res = chk.check_mob(mob_id="m", viewer_level=50)
    assert res.verdict == ConVerdict.INCREDIBLY_TOUGH


def test_check_unknown_mob():
    chk = MinimapDifficultyChecker()
    res = chk.check_mob(mob_id="ghost", viewer_level=50)
    assert res is None


def test_defense_lean_propagated():
    chk = MinimapDifficultyChecker()
    chk.register_mob(
        mob_id="m", level=50,
        defense_lean=DefenseLean.HIGH_EVA,
    )
    res = chk.check_mob(mob_id="m", viewer_level=50)
    assert res.defense_lean == DefenseLean.HIGH_EVA


def test_element_hint_gated_below_threshold():
    chk = MinimapDifficultyChecker()
    chk.register_mob(
        mob_id="m", level=50,
        element_weakness=ElementHint.FIRE,
    )
    res = chk.check_mob(
        mob_id="m", viewer_level=50,
        enfeebling_skill=ELEMENT_HINT_SKILL_GATE - 1,
    )
    assert res.element_hint == ElementHint.NONE


def test_element_hint_revealed_at_gate():
    chk = MinimapDifficultyChecker()
    chk.register_mob(
        mob_id="m", level=50,
        element_weakness=ElementHint.ICE,
    )
    res = chk.check_mob(
        mob_id="m", viewer_level=50,
        enfeebling_skill=ELEMENT_HINT_SKILL_GATE,
    )
    assert res.element_hint == ElementHint.ICE


def test_no_weakness_no_hint_even_with_skill():
    chk = MinimapDifficultyChecker()
    chk.register_mob(
        mob_id="m", level=50,
        element_weakness=ElementHint.NONE,
    )
    res = chk.check_mob(
        mob_id="m", viewer_level=50,
        enfeebling_skill=999,
    )
    assert res.element_hint == ElementHint.NONE


def test_label_falls_back_to_mob_id():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="orc_chief", level=20)
    res = chk.check_mob(
        mob_id="orc_chief", viewer_level=20,
    )
    assert res.label == "orc_chief"


def test_label_uses_supplied_value():
    chk = MinimapDifficultyChecker()
    chk.register_mob(
        mob_id="orc_chief", level=20,
        label="Orcish Chieftain",
    )
    res = chk.check_mob(
        mob_id="orc_chief", viewer_level=20,
    )
    assert res.label == "Orcish Chieftain"


def test_total_mobs_count():
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="a", level=10)
    chk.register_mob(mob_id="b", level=10)
    assert chk.total_mobs() == 2


def test_zero_or_negative_viewer_level_clamped():
    """A viewer_level of 0 should still produce a sane delta
    (clamped to 1)."""
    chk = MinimapDifficultyChecker()
    chk.register_mob(mob_id="m", level=10)
    res = chk.check_mob(mob_id="m", viewer_level=0)
    assert res.level_delta == 9
