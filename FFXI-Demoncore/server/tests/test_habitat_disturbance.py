"""Tests for habitat_disturbance."""
from __future__ import annotations

from server.habitat_disturbance import (
    HABITAT_REARM_SECONDS,
    HabitatBiome,
    HabitatDisturbance,
)


def test_register_habitat_happy():
    h = HabitatDisturbance()
    ok = h.register_habitat(
        habitat_id="reef_predators", biome=HabitatBiome.UNDERSEA,
        creatures={"reef_shark": 4, "moray_eel": 1},
    )
    assert ok is True


def test_register_blank_blocked():
    h = HabitatDisturbance()
    ok = h.register_habitat(
        habitat_id="", biome=HabitatBiome.UNDERSEA,
        creatures={"x": 1},
    )
    assert ok is False


def test_register_dup_blocked():
    h = HabitatDisturbance()
    h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"x": 1},
    )
    assert h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"x": 1},
    ) is False


def test_register_empty_pool_blocked():
    h = HabitatDisturbance()
    assert h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={},
    ) is False


def test_register_zero_weight_blocked():
    h = HabitatDisturbance()
    assert h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"x": 0},
    ) is False


def test_register_invalid_max_swoop():
    h = HabitatDisturbance()
    assert h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"x": 1}, max_swoop=0,
    ) is False


def test_register_invalid_chance():
    h = HabitatDisturbance()
    assert h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"x": 1}, ambush_chance_pct=101,
    ) is False


def test_link_unknown_habitat_blocked():
    h = HabitatDisturbance()
    assert h.link_habitat_to_feature(
        arena_id="a1", feature_id="north_wall",
        habitat_id="ghost", threshold=1000,
    ) is False


def test_link_zero_threshold_blocked():
    h = HabitatDisturbance()
    h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"x": 1},
    )
    assert h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="r", threshold=0,
    ) is False


def test_link_dup_blocked():
    h = HabitatDisturbance()
    h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"x": 1},
    )
    h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="r", threshold=100,
    )
    assert h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="r", threshold=100,
    ) is False


def test_below_threshold_no_spawn():
    h = HabitatDisturbance(rng_seed=1)
    h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"shark": 1}, ambush_chance_pct=100,
    )
    h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="r", threshold=1000,
    )
    out = h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=500, now_seconds=10,
    )
    assert out == ()


def test_threshold_crossed_with_100pct_chance_spawns():
    h = HabitatDisturbance(rng_seed=1)
    h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"shark": 1}, ambush_chance_pct=100, max_swoop=3,
    )
    h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="r", threshold=500,
    )
    out = h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=600, now_seconds=10,
    )
    assert len(out) >= 1
    assert all(s.creature_id == "shark" for s in out)
    assert all(s.biome == HabitatBiome.UNDERSEA for s in out)


def test_zero_pct_chance_consumes_accumulator_no_spawn():
    h = HabitatDisturbance(rng_seed=1)
    h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"shark": 1}, ambush_chance_pct=0,
    )
    h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="r", threshold=500,
    )
    out = h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=600, now_seconds=10,
    )
    assert out == ()


def test_rearm_after_cooldown():
    h = HabitatDisturbance(rng_seed=1)
    h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"shark": 1}, ambush_chance_pct=100,
    )
    h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="r", threshold=500,
    )
    first = h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=600, now_seconds=10,
    )
    assert len(first) >= 1
    # too soon — rearm window
    blocked = h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=1000, now_seconds=20,
    )
    assert blocked == ()
    # after rearm
    again = h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=600,
        now_seconds=10 + HABITAT_REARM_SECONDS + 1,
    )
    assert len(again) >= 1


def test_unlinked_feature_no_spawn():
    h = HabitatDisturbance(rng_seed=1)
    out = h.accumulate_damage(
        arena_id="a1", feature_id="ghost", amount=100, now_seconds=0,
    )
    assert out == ()


def test_multi_habitat_per_feature():
    h = HabitatDisturbance(rng_seed=1)
    h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"shark": 1}, ambush_chance_pct=100,
    )
    h.register_habitat(
        habitat_id="c", biome=HabitatBiome.CAVE,
        creatures={"bat": 1}, ambush_chance_pct=100,
    )
    h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="r", threshold=100,
    )
    h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="c", threshold=100,
    )
    out = h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=200, now_seconds=10,
    )
    biomes = {s.biome for s in out}
    assert biomes == {HabitatBiome.UNDERSEA, HabitatBiome.CAVE}


def test_reset_clears_accumulators():
    h = HabitatDisturbance(rng_seed=1)
    h.register_habitat(
        habitat_id="r", biome=HabitatBiome.UNDERSEA,
        creatures={"shark": 1}, ambush_chance_pct=100,
    )
    h.link_habitat_to_feature(
        arena_id="a1", feature_id="w", habitat_id="r", threshold=500,
    )
    h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=300, now_seconds=10,
    )
    h.reset(arena_id="a1")
    # back to fresh — 300 dmg shouldn't fire
    out = h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=300, now_seconds=20,
    )
    assert out == ()


def test_zero_amount_skipped():
    h = HabitatDisturbance(rng_seed=1)
    out = h.accumulate_damage(
        arena_id="a1", feature_id="w", amount=0, now_seconds=10,
    )
    assert out == ()
