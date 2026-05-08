"""Tests for crafting_breakthrough."""
from __future__ import annotations

from server.crafting_breakthrough import (
    CraftingBreakthrough,
)


def test_roll_breakthrough_low_skill_no_chance():
    c = CraftingBreakthrough()
    out = c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=50, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    assert out.chance_pct == 0.0
    assert out.breakthrough_fired is False


def test_roll_breakthrough_high_skill_capped():
    c = CraftingBreakthrough()
    out = c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    # 100 margin -> chance = 100, capped at 8
    assert out.chance_pct == 8.0


def test_breakthrough_fires_with_low_roll():
    c = CraftingBreakthrough()
    # rng_seed=0 -> roll=0, chance 8% = 800; 0 < 800
    out = c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    assert out.breakthrough_fired is True
    assert out.variant_id is not None


def test_breakthrough_misses_with_high_roll():
    c = CraftingBreakthrough()
    # rng_seed=9999 -> roll=9999; chance 8% = 800; not fired
    out = c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=9999, now_ms=1000,
    )
    assert out.breakthrough_fired is False


def test_attempts_today_decay():
    c = CraftingBreakthrough()
    out = c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=4, rng_seed=0, now_ms=1000,
    )
    # 8 - 4*0.5 = 6
    assert out.chance_pct == 6.0


def test_blank_crafter_no_chance():
    c = CraftingBreakthrough()
    out = c.roll_breakthrough(
        crafter_id="", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    assert out.breakthrough_fired is False


def test_first_discoverer_recorded():
    c = CraftingBreakthrough()
    out = c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    assert out.is_server_first is True
    assert c.first_discoverer(
        variant_id=out.variant_id,
    ) == "cid"


def test_second_discoverer_not_first():
    c = CraftingBreakthrough()
    out1 = c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    # Same rng_seed -> same variant_id, different crafter
    out2 = c.roll_breakthrough(
        crafter_id="boyahda", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=2000,
    )
    assert out1.is_server_first is True
    assert out2.is_server_first is False


def test_breakthrough_active_after_fire():
    c = CraftingBreakthrough()
    c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    assert c.is_active(
        crafter_id="cid", now_ms=10000,
    ) is True


def test_breakthrough_expires_after_60s():
    c = CraftingBreakthrough()
    c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    # After 70 sec
    assert c.is_active(
        crafter_id="cid", now_ms=71000,
    ) is False


def test_consume_active():
    c = CraftingBreakthrough()
    c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    assert c.consume(
        crafter_id="cid", now_ms=10000,
    ) is True
    # No longer active
    assert c.is_active(
        crafter_id="cid", now_ms=10001,
    ) is False


def test_consume_inactive_blocked():
    c = CraftingBreakthrough()
    assert c.consume(
        crafter_id="cid", now_ms=1000,
    ) is False


def test_discovered_recipes_listed():
    c = CraftingBreakthrough()
    c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=0, now_ms=1000,
    )
    c.roll_breakthrough(
        crafter_id="cid", recipe_id="r2",
        skill_level=200, recipe_level=100,
        attempts_today=0, rng_seed=1, now_ms=2000,
    )
    out = c.discovered_recipes(crafter_id="cid")
    assert len(out) == 2


def test_discovered_recipes_unknown_crafter():
    c = CraftingBreakthrough()
    assert c.discovered_recipes(
        crafter_id="ghost",
    ) == []


def test_first_discoverer_unknown_variant():
    c = CraftingBreakthrough()
    assert c.first_discoverer(
        variant_id="ghost::v0",
    ) is None


def test_zero_chance_when_decay_exceeds_base():
    c = CraftingBreakthrough()
    out = c.roll_breakthrough(
        crafter_id="cid", recipe_id="r1",
        skill_level=125, recipe_level=100,  # 25 margin
        attempts_today=100, rng_seed=0, now_ms=1000,
    )
    # 25*0.01*100 = 25, capped 8, minus 100*0.5=50 = -42 -> 0
    assert out.chance_pct == 0.0
    assert out.breakthrough_fired is False
