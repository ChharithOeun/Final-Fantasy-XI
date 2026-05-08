"""Tests for masterwork_synthesis."""
from __future__ import annotations

from server.masterwork_synthesis import (
    AttemptResult, IngredientQuality,
    MasterworkSynthesis, MoonPhase,
)


def _full_eligible(m, **overrides):
    """Default: all gates pass."""
    args = dict(
        crafter_id="cid", recipe_id="r1",
        skill_level=125, breakthrough_active=True,
        moon=MoonPhase.FULL,
        ingredient_quality=IngredientQuality.EXCEPTIONAL,
        now_day=10,
    )
    args.update(overrides)
    return m.attempt(**args)


def test_register_recipe():
    m = MasterworkSynthesis()
    assert m.register_recipe(
        recipe_id="r1", base_level=100,
    ) is True


def test_register_blank_blocked():
    m = MasterworkSynthesis()
    assert m.register_recipe(
        recipe_id="", base_level=100,
    ) is False


def test_register_dup_blocked():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    assert m.register_recipe(
        recipe_id="r1", base_level=100,
    ) is False


def test_attempt_full_eligible_masterwork():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    out = _full_eligible(m)
    assert out.result == AttemptResult.MASTERWORK


def test_attempt_blank_crafter():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    out = _full_eligible(m, crafter_id="")
    assert out.result == AttemptResult.REJECTED
    assert out.rejection_reason == "blank_crafter"


def test_attempt_unknown_recipe():
    m = MasterworkSynthesis()
    out = _full_eligible(m)
    assert out.result == AttemptResult.REJECTED
    assert out.rejection_reason == "unknown_recipe"


def test_attempt_skill_too_low():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    # Need at least 125 (100 + 25 margin)
    out = _full_eligible(m, skill_level=120)
    assert out.result == AttemptResult.REJECTED
    assert out.rejection_reason == "skill_too_low"


def test_attempt_no_breakthrough():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    out = _full_eligible(m, breakthrough_active=False)
    assert out.rejection_reason == "no_breakthrough"


def test_attempt_bad_moon_waxing():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    out = _full_eligible(m, moon=MoonPhase.WAXING)
    assert out.rejection_reason == "bad_moon"


def test_attempt_bad_moon_waning():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    out = _full_eligible(m, moon=MoonPhase.WANING)
    assert out.rejection_reason == "bad_moon"


def test_attempt_new_moon_passes():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    out = _full_eligible(m, moon=MoonPhase.NEW)
    assert out.result == AttemptResult.MASTERWORK


def test_attempt_poor_ingredients():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    out = _full_eligible(
        m, ingredient_quality=IngredientQuality.GOOD,
    )
    assert out.rejection_reason == "poor_ingredients"


def test_daily_cap():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    _full_eligible(m, now_day=10)
    _full_eligible(m, now_day=10)
    _full_eligible(m, now_day=10)
    out = _full_eligible(m, now_day=10)
    assert out.rejection_reason == "daily_cap_hit"


def test_daily_cap_resets_next_day():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    _full_eligible(m, now_day=10)
    _full_eligible(m, now_day=10)
    _full_eligible(m, now_day=10)
    out = _full_eligible(m, now_day=11)
    assert out.result == AttemptResult.MASTERWORK


def test_attempts_today_counter():
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    _full_eligible(m, now_day=10)
    _full_eligible(m, now_day=10)
    assert m.attempts_today(
        crafter_id="cid", recipe_id="r1", now_day=10,
    ) == 2


def test_rejected_attempts_not_counted():
    """Skill-too-low rejection doesn't burn a daily attempt."""
    m = MasterworkSynthesis()
    m.register_recipe(recipe_id="r1", base_level=100)
    _full_eligible(m, skill_level=120, now_day=10)
    assert m.attempts_today(
        crafter_id="cid", recipe_id="r1", now_day=10,
    ) == 0


def test_five_attempt_results():
    assert len(list(AttemptResult)) == 5


def test_four_moon_phases():
    assert len(list(MoonPhase)) == 4


def test_four_ingredient_qualities():
    assert len(list(IngredientQuality)) == 4
