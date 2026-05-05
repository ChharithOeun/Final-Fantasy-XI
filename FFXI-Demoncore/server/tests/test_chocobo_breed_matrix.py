"""Tests for the chocobo breed matrix."""
from __future__ import annotations

from server.chocobo_breed_matrix import ChocoboBreedMatrix
from server.chocobo_colors import ChocoboColor


def test_yellow_yellow_dominant():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=10,
        combined_skill=0,
        roll_pct_color=10,
        roll_pct_rainbow=999_999,
    )
    assert res.accepted
    assert res.egg_color == ChocoboColor.YELLOW


def test_yellow_yellow_variant_high_roll():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=10,
        combined_skill=0,
        roll_pct_color=99,
        roll_pct_rainbow=999_999,
    )
    assert res.egg_color == ChocoboColor.GREEN


def test_rainbow_proc():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=10,
        combined_skill=0,
        roll_pct_color=10,
        roll_pct_rainbow=0,
    )
    assert res.is_rainbow
    assert res.egg_color == ChocoboColor.RAINBOW


def test_rainbow_just_outside():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=10,
        combined_skill=0,
        roll_pct_color=10,
        roll_pct_rainbow=1,
    )
    assert not res.is_rainbow


def test_rainbow_parent_blocked():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.RAINBOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=10,
        combined_skill=0,
        roll_pct_color=10,
        roll_pct_rainbow=999_999,
    )
    assert not res.accepted


def test_invalid_color_roll():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=10,
        combined_skill=0,
        roll_pct_color=200,
        roll_pct_rainbow=999_999,
    )
    assert not res.accepted


def test_invalid_rainbow_roll():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=10,
        combined_skill=0,
        roll_pct_color=10,
        roll_pct_rainbow=10_000_000,
    )
    assert not res.accepted


def test_zero_combined_level():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=0,
        combined_skill=0,
        roll_pct_color=10,
        roll_pct_rainbow=999_999,
    )
    assert not res.accepted


def test_negative_combined_skill():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=100,
        combined_skill=-1,
        roll_pct_color=10,
        roll_pct_rainbow=999_999,
    )
    assert not res.accepted


def test_yellow_brown_mixed():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.BROWN,
        combined_level=100,
        combined_skill=100,
        roll_pct_color=10,
        roll_pct_rainbow=999_999,
    )
    assert res.egg_color == ChocoboColor.YELLOW


def test_swap_order_same_result():
    m = ChocoboBreedMatrix()
    a = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.BROWN,
        combined_level=100,
        combined_skill=100,
        roll_pct_color=92,
        roll_pct_rainbow=999_999,
    )
    b = m.roll(
        male_color=ChocoboColor.BROWN,
        female_color=ChocoboColor.YELLOW,
        combined_level=100,
        combined_skill=100,
        roll_pct_color=92,
        roll_pct_rainbow=999_999,
    )
    assert a.egg_color == b.egg_color


def test_combined_level_widens_variant():
    m = ChocoboBreedMatrix()
    # At combined_level 199, threshold dominant=88. Roll at 81 → dominant.
    low = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=199,
        combined_skill=0,
        roll_pct_color=81,
        roll_pct_rainbow=999_999,
    )
    assert low.egg_color == ChocoboColor.YELLOW
    # At combined_level 200, dominant threshold drops to 84;
    # roll at 85 falls past dominant → variant
    high = m.roll(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
        combined_level=200,
        combined_skill=0,
        roll_pct_color=85,
        roll_pct_rainbow=999_999,
    )
    assert high.egg_color != ChocoboColor.YELLOW


def test_high_skill_also_widens():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.BLUE,
        female_color=ChocoboColor.BLUE,
        combined_level=200,
        combined_skill=1000,
        roll_pct_color=82,
        roll_pct_rainbow=999_999,
    )
    # 88 - 4 - 4 = 80 dominant ceiling; roll 82 escapes to variant
    assert res.egg_color != ChocoboColor.BLUE


def test_recipe_for_same_color():
    m = ChocoboBreedMatrix()
    r = m.recipe_for(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.YELLOW,
    )
    assert r is not None
    assert r.gil_cost == 50_000


def test_recipe_for_mixed():
    m = ChocoboBreedMatrix()
    r = m.recipe_for(
        male_color=ChocoboColor.YELLOW,
        female_color=ChocoboColor.RED,
    )
    assert r.gil_cost == 200_000
    assert len(r.items) > 3


def test_recipe_white_includes_rex_feather():
    m = ChocoboBreedMatrix()
    r = m.recipe_for(
        male_color=ChocoboColor.WHITE,
        female_color=ChocoboColor.YELLOW,
    )
    item_ids = {x[0] for x in r.items}
    assert "rainbow_feather_rex" in item_ids


def test_recipe_grey_includes_rex_feather():
    m = ChocoboBreedMatrix()
    r = m.recipe_for(
        male_color=ChocoboColor.GREY,
        female_color=ChocoboColor.RED,
    )
    item_ids = {x[0] for x in r.items}
    assert "rainbow_feather_rex" in item_ids


def test_recipe_rainbow_blocked():
    m = ChocoboBreedMatrix()
    r = m.recipe_for(
        male_color=ChocoboColor.RAINBOW,
        female_color=ChocoboColor.YELLOW,
    )
    assert r is None


def test_unknown_pair_falls_back():
    m = ChocoboBreedMatrix()
    # GREEN x WHITE not in base dist; falls back to mother dominant
    res = m.roll(
        male_color=ChocoboColor.GREEN,
        female_color=ChocoboColor.WHITE,
        combined_level=100,
        combined_skill=0,
        roll_pct_color=10,
        roll_pct_rainbow=999_999,
    )
    assert res.accepted
    # Roll 10 < 60 → female_color (WHITE)
    assert res.egg_color == ChocoboColor.WHITE


def test_grey_grey_dominant():
    m = ChocoboBreedMatrix()
    res = m.roll(
        male_color=ChocoboColor.GREY,
        female_color=ChocoboColor.GREY,
        combined_level=100,
        combined_skill=0,
        roll_pct_color=50,
        roll_pct_rainbow=999_999,
    )
    assert res.egg_color == ChocoboColor.GREY
