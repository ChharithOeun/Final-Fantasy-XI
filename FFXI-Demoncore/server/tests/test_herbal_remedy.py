"""Tests for herbal_remedy."""
from __future__ import annotations

from server.herbal_remedy import HerbalRemedyEngine, RemedyKind


def _setup():
    e = HerbalRemedyEngine()
    e.define_recipe(
        kind=RemedyKind.SUSTENANCE,
        herb_requirements={"red_berry": 3, "wild_grain": 2},
        water_units=1,
    )
    e.define_recipe(
        kind=RemedyKind.WARMTH_TONIC,
        herb_requirements={"ginger_root": 2, "fire_weed": 1},
        water_units=2,
    )
    e.define_recipe(
        kind=RemedyKind.HYDRATION,
        herb_requirements={"mint_leaf": 2},
        water_units=3,
    )
    return e


def test_define_recipe_happy():
    e = _setup()
    assert e.total_recipes() == 3


def test_define_no_herbs_blocked():
    e = HerbalRemedyEngine()
    out = e.define_recipe(
        kind=RemedyKind.SUSTENANCE,
        herb_requirements={}, water_units=1,
    )
    assert out is False


def test_define_zero_qty_blocked():
    e = HerbalRemedyEngine()
    out = e.define_recipe(
        kind=RemedyKind.SUSTENANCE,
        herb_requirements={"x": 0}, water_units=1,
    )
    assert out is False


def test_define_negative_water_blocked():
    e = HerbalRemedyEngine()
    out = e.define_recipe(
        kind=RemedyKind.SUSTENANCE,
        herb_requirements={"x": 1}, water_units=-1,
    )
    assert out is False


def test_define_duplicate_blocked():
    e = _setup()
    again = e.define_recipe(
        kind=RemedyKind.SUSTENANCE,
        herb_requirements={"x": 1}, water_units=1,
    )
    assert again is False


def test_brew_happy():
    e = _setup()
    out = e.brew(
        player_id="alice", kind=RemedyKind.SUSTENANCE,
        herb_inventory={"red_berry": 5, "wild_grain": 3},
        water_available=5, has_fire=True, brewed_at=10,
    )
    assert out is not None
    assert out.kind == RemedyKind.SUSTENANCE


def test_brew_no_fire():
    e = _setup()
    out = e.brew(
        player_id="alice", kind=RemedyKind.SUSTENANCE,
        herb_inventory={"red_berry": 5, "wild_grain": 3},
        water_available=5, has_fire=False, brewed_at=10,
    )
    assert out is None


def test_brew_unknown_recipe():
    e = _setup()
    out = e.brew(
        player_id="alice", kind=RemedyKind.VITALITY_DRAUGHT,
        herb_inventory={"x": 99}, water_available=99,
        has_fire=True, brewed_at=10,
    )
    assert out is None


def test_brew_insufficient_herb():
    e = _setup()
    out = e.brew(
        player_id="alice", kind=RemedyKind.SUSTENANCE,
        herb_inventory={"red_berry": 1, "wild_grain": 5},
        water_available=5, has_fire=True, brewed_at=10,
    )
    assert out is None


def test_brew_insufficient_water():
    e = _setup()
    out = e.brew(
        player_id="alice", kind=RemedyKind.HYDRATION,
        herb_inventory={"mint_leaf": 5},
        water_available=2, has_fire=True, brewed_at=10,
    )
    assert out is None


def test_brew_blank_player():
    e = _setup()
    out = e.brew(
        player_id="", kind=RemedyKind.SUSTENANCE,
        herb_inventory={"red_berry": 5, "wild_grain": 3},
        water_available=5, has_fire=True, brewed_at=10,
    )
    assert out is None


def test_brew_missing_herb_kind():
    e = _setup()
    out = e.brew(
        player_id="alice", kind=RemedyKind.SUSTENANCE,
        herb_inventory={"red_berry": 5},   # missing wild_grain
        water_available=5, has_fire=True, brewed_at=10,
    )
    assert out is None


def test_recipe_for_returns():
    e = _setup()
    r = e.recipe_for(kind=RemedyKind.SUSTENANCE)
    assert r is not None
    assert r.water_units == 1


def test_recipe_for_unknown_returns_none():
    e = _setup()
    out = e.recipe_for(kind=RemedyKind.COOLING_TONIC)
    assert out is None


def test_brew_carries_brewer_id():
    e = _setup()
    out = e.brew(
        player_id="alice", kind=RemedyKind.HYDRATION,
        herb_inventory={"mint_leaf": 3},
        water_available=5, has_fire=True, brewed_at=42,
    )
    assert out is not None
    assert out.brewer_id == "alice"
    assert out.brewed_at == 42


def test_five_remedy_kinds():
    assert len(list(RemedyKind)) == 5


def test_warmth_tonic_complex_brew():
    e = _setup()
    out = e.brew(
        player_id="alice", kind=RemedyKind.WARMTH_TONIC,
        herb_inventory={"ginger_root": 3, "fire_weed": 2},
        water_available=2, has_fire=True, brewed_at=10,
    )
    assert out is not None
    assert out.kind == RemedyKind.WARMTH_TONIC
