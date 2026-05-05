"""Tests for stratosphere-temple synthesis."""
from __future__ import annotations

from server.stratosphere_temple_synthesis import (
    HQ_BASE_PCT,
    MIN_CRAFTER_LEVEL_TO_USE,
    MIN_WYVERN_REP,
    SUCCESS_CAP_PCT,
    StratosphereTempleSynthesis,
)


def _seed(s: StratosphereTempleSynthesis):
    s.register_recipe(
        recipe_id="sky_lance",
        name="Stratospheric Lance",
        output_ilvl=175,
        materials={"cloud_pearl": 5, "jet_essence": 3, "wyvern_scale": 1},
        difficulty=110,
    )


def test_register_happy():
    s = StratosphereTempleSynthesis()
    assert s.register_recipe(
        recipe_id="r1", name="Sky Bow",
        output_ilvl=150,
        materials={"cloud_pearl": 3},
        difficulty=100,
    ) is True


def test_register_blank():
    s = StratosphereTempleSynthesis()
    assert s.register_recipe(
        recipe_id="", name="X",
        output_ilvl=150, materials={"a": 1}, difficulty=100,
    ) is False


def test_register_bad_ilvl():
    s = StratosphereTempleSynthesis()
    assert s.register_recipe(
        recipe_id="r1", name="X",
        output_ilvl=200, materials={"a": 1}, difficulty=100,
    ) is False


def test_register_no_materials():
    s = StratosphereTempleSynthesis()
    assert s.register_recipe(
        recipe_id="r1", name="X",
        output_ilvl=150, materials={}, difficulty=100,
    ) is False


def test_can_use_happy():
    s = StratosphereTempleSynthesis()
    ok, reason = s.can_use(
        crafter_id="c1",
        wyvern_lord_rep=MIN_WYVERN_REP,
        crafter_skill=MIN_CRAFTER_LEVEL_TO_USE,
    )
    assert ok is True
    assert reason is None


def test_can_use_low_rep():
    s = StratosphereTempleSynthesis()
    ok, _ = s.can_use(
        crafter_id="c1", wyvern_lord_rep=MIN_WYVERN_REP - 1,
        crafter_skill=MIN_CRAFTER_LEVEL_TO_USE,
    )
    assert ok is False


def test_can_use_low_skill():
    s = StratosphereTempleSynthesis()
    ok, _ = s.can_use(
        crafter_id="c1", wyvern_lord_rep=MIN_WYVERN_REP,
        crafter_skill=80,
    )
    assert ok is False


def test_attempt_happy_success():
    s = StratosphereTempleSynthesis()
    _seed(s)
    r = s.attempt(
        crafter_id="c1", recipe_id="sky_lance",
        mats_supplied={
            "cloud_pearl": 5, "jet_essence": 3, "wyvern_scale": 1,
        },
        wyvern_lord_rep=50, crafter_skill=110,
        rng_roll=0, hq_roll=99,
    )
    assert r.accepted is True
    assert r.success is True
    assert r.output_ilvl == 175
    assert r.is_hq is False


def test_attempt_failure_consumes_mats():
    s = StratosphereTempleSynthesis()
    _seed(s)
    r = s.attempt(
        crafter_id="c1", recipe_id="sky_lance",
        mats_supplied={
            "cloud_pearl": 5, "jet_essence": 3, "wyvern_scale": 1,
        },
        wyvern_lord_rep=50, crafter_skill=110,
        rng_roll=99, hq_roll=99,
    )
    assert r.accepted is True
    assert r.success is False
    assert r.consumed_materials["cloud_pearl"] == 5


def test_attempt_hq_proc():
    s = StratosphereTempleSynthesis()
    _seed(s)
    r = s.attempt(
        crafter_id="c1", recipe_id="sky_lance",
        mats_supplied={
            "cloud_pearl": 5, "jet_essence": 3, "wyvern_scale": 1,
        },
        wyvern_lord_rep=50, crafter_skill=200,
        rng_roll=0, hq_roll=0,
    )
    assert r.is_hq is True


def test_attempt_missing_materials():
    s = StratosphereTempleSynthesis()
    _seed(s)
    r = s.attempt(
        crafter_id="c1", recipe_id="sky_lance",
        mats_supplied={"cloud_pearl": 1},
        wyvern_lord_rep=50, crafter_skill=110,
        rng_roll=0, hq_roll=0,
    )
    assert r.accepted is False
    assert r.reason == "missing materials"


def test_attempt_unknown_recipe():
    s = StratosphereTempleSynthesis()
    r = s.attempt(
        crafter_id="c1", recipe_id="ghost",
        mats_supplied={},
        wyvern_lord_rep=50, crafter_skill=110,
        rng_roll=0, hq_roll=0,
    )
    assert r.accepted is False
    assert r.reason == "unknown recipe"


def test_attempt_wyvern_hostile():
    s = StratosphereTempleSynthesis()
    _seed(s)
    r = s.attempt(
        crafter_id="c1", recipe_id="sky_lance",
        mats_supplied={
            "cloud_pearl": 5, "jet_essence": 3, "wyvern_scale": 1,
        },
        wyvern_lord_rep=0, crafter_skill=110,
        rng_roll=0, hq_roll=0,
    )
    assert r.accepted is False


def test_success_chance_capped():
    s = StratosphereTempleSynthesis()
    _seed(s)
    r_succ = s.attempt(
        crafter_id="c1", recipe_id="sky_lance",
        mats_supplied={
            "cloud_pearl": 5, "jet_essence": 3, "wyvern_scale": 1,
        },
        wyvern_lord_rep=50, crafter_skill=999,
        rng_roll=SUCCESS_CAP_PCT - 1, hq_roll=99,
    )
    assert r_succ.success is True
    r_fail = s.attempt(
        crafter_id="c1", recipe_id="sky_lance",
        mats_supplied={
            "cloud_pearl": 5, "jet_essence": 3, "wyvern_scale": 1,
        },
        wyvern_lord_rep=50, crafter_skill=999,
        rng_roll=SUCCESS_CAP_PCT, hq_roll=99,
    )
    assert r_fail.success is False


def test_recipes_for_skill_filter():
    s = StratosphereTempleSynthesis()
    _seed(s)
    out = s.recipes_for(crafter_skill=110)
    assert len(out) == 1
    out2 = s.recipes_for(crafter_skill=70)
    assert len(out2) == 0
