"""Tests for wave-temple synthesis."""
from __future__ import annotations

from server.wave_temple_synthesis import (
    HQ_BASE_PCT,
    MIN_CRAFTER_LEVEL_TO_USE,
    SUCCESS_BASE_PCT,
    SUCCESS_CAP_PCT,
    WaveTempleSynthesis,
)


def _seed(t: WaveTempleSynthesis):
    t.register_recipe(
        recipe_id="abyss_blade",
        name="Abyss Blade",
        output_ilvl=175,
        materials={"vent_steam": 5, "spire_dust": 3, "cult_token": 1},
        difficulty=110,
    )


def test_register_happy():
    t = WaveTempleSynthesis()
    ok = t.register_recipe(
        recipe_id="r1", name="Abyss Bow",
        output_ilvl=150,
        materials={"vent_steam": 3},
        difficulty=100,
    )
    assert ok is True


def test_register_blank():
    t = WaveTempleSynthesis()
    ok = t.register_recipe(
        recipe_id="", name="X",
        output_ilvl=150, materials={"a": 1},
        difficulty=100,
    )
    assert ok is False


def test_register_bad_ilvl():
    t = WaveTempleSynthesis()
    ok = t.register_recipe(
        recipe_id="r1", name="X",
        output_ilvl=200, materials={"a": 1},
        difficulty=100,
    )
    assert ok is False


def test_register_no_materials():
    t = WaveTempleSynthesis()
    ok = t.register_recipe(
        recipe_id="r1", name="X",
        output_ilvl=150, materials={},
        difficulty=100,
    )
    assert ok is False


def test_can_use_happy():
    t = WaveTempleSynthesis()
    ok, reason = t.can_use(
        crafter_id="c1", drowned_pact=True,
        crafter_skill=MIN_CRAFTER_LEVEL_TO_USE,
    )
    assert ok is True
    assert reason is None


def test_can_use_no_pact():
    t = WaveTempleSynthesis()
    ok, _ = t.can_use(
        crafter_id="c1", drowned_pact=False,
        crafter_skill=MIN_CRAFTER_LEVEL_TO_USE,
    )
    assert ok is False


def test_can_use_low_skill():
    t = WaveTempleSynthesis()
    ok, _ = t.can_use(
        crafter_id="c1", drowned_pact=True, crafter_skill=80,
    )
    assert ok is False


def test_attempt_happy_success_low_roll():
    t = WaveTempleSynthesis()
    _seed(t)
    r = t.attempt(
        crafter_id="c1", recipe_id="abyss_blade",
        mats_supplied={"vent_steam": 5, "spire_dust": 3, "cult_token": 1},
        drowned_pact=True, crafter_skill=110,
        rng_roll=0, hq_roll=99,
    )
    assert r.accepted is True
    assert r.success is True
    assert r.output_ilvl == 175
    assert r.is_hq is False


def test_attempt_failure_high_roll():
    t = WaveTempleSynthesis()
    _seed(t)
    r = t.attempt(
        crafter_id="c1", recipe_id="abyss_blade",
        mats_supplied={"vent_steam": 5, "spire_dust": 3, "cult_token": 1},
        drowned_pact=True, crafter_skill=110,
        rng_roll=99, hq_roll=99,
    )
    assert r.accepted is True
    assert r.success is False
    # mats still consumed on failure
    assert r.consumed_materials["vent_steam"] == 5


def test_attempt_hq_proc():
    t = WaveTempleSynthesis()
    _seed(t)
    r = t.attempt(
        crafter_id="c1", recipe_id="abyss_blade",
        mats_supplied={"vent_steam": 5, "spire_dust": 3, "cult_token": 1},
        drowned_pact=True, crafter_skill=200,
        rng_roll=0, hq_roll=0,
    )
    assert r.is_hq is True


def test_attempt_missing_materials():
    t = WaveTempleSynthesis()
    _seed(t)
    r = t.attempt(
        crafter_id="c1", recipe_id="abyss_blade",
        mats_supplied={"vent_steam": 1},  # short
        drowned_pact=True, crafter_skill=110,
        rng_roll=0, hq_roll=0,
    )
    assert r.accepted is False
    assert r.reason == "missing materials"


def test_attempt_unknown_recipe():
    t = WaveTempleSynthesis()
    r = t.attempt(
        crafter_id="c1", recipe_id="ghost",
        mats_supplied={},
        drowned_pact=True, crafter_skill=110,
        rng_roll=0, hq_roll=0,
    )
    assert r.accepted is False
    assert r.reason == "unknown recipe"


def test_attempt_no_pact():
    t = WaveTempleSynthesis()
    _seed(t)
    r = t.attempt(
        crafter_id="c1", recipe_id="abyss_blade",
        mats_supplied={"vent_steam": 5, "spire_dust": 3, "cult_token": 1},
        drowned_pact=False, crafter_skill=110,
        rng_roll=0, hq_roll=0,
    )
    assert r.accepted is False


def test_success_chance_increases_with_skill():
    """At skill = difficulty, base 50%; +5% per 10 over."""
    t = WaveTempleSynthesis()
    _seed(t)
    # at skill = 110 (== difficulty), chance is base 50%.
    # roll = 49 succeeds, roll = 50 fails.
    r_succ = t.attempt(
        crafter_id="c1", recipe_id="abyss_blade",
        mats_supplied={"vent_steam": 5, "spire_dust": 3, "cult_token": 1},
        drowned_pact=True, crafter_skill=110,
        rng_roll=49, hq_roll=99,
    )
    assert r_succ.success is True
    r_fail = t.attempt(
        crafter_id="c1", recipe_id="abyss_blade",
        mats_supplied={"vent_steam": 5, "spire_dust": 3, "cult_token": 1},
        drowned_pact=True, crafter_skill=110,
        rng_roll=50, hq_roll=99,
    )
    assert r_fail.success is False


def test_success_chance_capped():
    """Even with huge skill the cap is 95%."""
    t = WaveTempleSynthesis()
    _seed(t)
    # huge skill bonus; success roll = 94 should hit cap, 95 fails
    r_succ = t.attempt(
        crafter_id="c1", recipe_id="abyss_blade",
        mats_supplied={"vent_steam": 5, "spire_dust": 3, "cult_token": 1},
        drowned_pact=True, crafter_skill=999,
        rng_roll=SUCCESS_CAP_PCT - 1, hq_roll=99,
    )
    assert r_succ.success is True
    r_fail = t.attempt(
        crafter_id="c1", recipe_id="abyss_blade",
        mats_supplied={"vent_steam": 5, "spire_dust": 3, "cult_token": 1},
        drowned_pact=True, crafter_skill=999,
        rng_roll=SUCCESS_CAP_PCT, hq_roll=99,
    )
    assert r_fail.success is False


def test_recipes_for_skill_filter():
    t = WaveTempleSynthesis()
    _seed(t)
    # at skill=110 (== difficulty), recipe surfaces
    out = t.recipes_for(crafter_skill=110)
    assert len(out) == 1
    # at skill=70, far below threshold
    out2 = t.recipes_for(crafter_skill=70)
    assert len(out2) == 0
