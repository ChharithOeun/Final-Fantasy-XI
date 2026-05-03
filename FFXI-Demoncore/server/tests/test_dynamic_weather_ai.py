"""Tests for the dynamic weather AI."""
from __future__ import annotations

from server.dynamic_weather_ai import (
    ActorKind,
    DynamicWeatherAI,
    WeatherIntensity,
    WeatherKind,
    WeatherSnapshot,
)


def test_no_observation_returns_neutral_directive():
    ai = DynamicWeatherAI()
    d = ai.directive_for(
        actor_kind=ActorKind.MERCHANT_CARAVAN,
        zone_id="ronfaure",
    )
    assert not d.take_shelter
    assert not d.delay_route
    assert d.aggression_mod_pct == 0


def test_observe_then_current_returns_snapshot():
    ai = DynamicWeatherAI()
    snap = WeatherSnapshot(
        zone_id="ronfaure", kind=WeatherKind.RAIN,
        intensity=WeatherIntensity.HEAVY,
    )
    ai.observe(snapshot=snap)
    assert ai.current("ronfaure") is snap


def test_caravan_delays_in_heavy_rain():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="ronfaure", kind=WeatherKind.RAIN,
        intensity=WeatherIntensity.HEAVY,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.MERCHANT_CARAVAN,
        zone_id="ronfaure",
    )
    assert d.delay_route
    assert d.mood_shift == "anxious"


def test_caravan_terrified_in_extreme_blizzard():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="xarcabard", kind=WeatherKind.BLIZZARD,
        intensity=WeatherIntensity.EXTREME,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.MERCHANT_CARAVAN,
        zone_id="xarcabard",
    )
    assert d.delay_route and d.take_shelter
    assert d.mood_shift == "terrified"


def test_beastman_thrives_in_sandstorm():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="altepa", kind=WeatherKind.SANDSTORM,
        intensity=WeatherIntensity.HEAVY,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.BEASTMAN_PATROL,
        zone_id="altepa",
    )
    assert d.aggression_mod_pct == 10
    assert d.visibility_mod_pct == -60


def test_beastman_shelters_in_extreme_rain():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="ronfaure", kind=WeatherKind.RAIN,
        intensity=WeatherIntensity.EXTREME,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.BEASTMAN_PATROL,
        zone_id="ronfaure",
    )
    assert d.take_shelter and d.delay_route


def test_fisherman_lucky_in_light_rain():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="bibiki_bay", kind=WeatherKind.RAIN,
        intensity=WeatherIntensity.LIGHT,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.FISHERMAN_NPC,
        zone_id="bibiki_bay",
    )
    assert d.mood_shift == "lucky"
    assert "good fishing" in d.notes


def test_fisherman_takes_shelter_in_thunder():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="bibiki_bay", kind=WeatherKind.THUNDER,
        intensity=WeatherIntensity.HEAVY,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.FISHERMAN_NPC,
        zone_id="bibiki_bay",
    )
    assert d.take_shelter and d.delay_route


def test_dragon_aggro_in_thunder():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="dragons_aery", kind=WeatherKind.THUNDER,
        intensity=WeatherIntensity.HEAVY,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.DRAGON_NM,
        zone_id="dragons_aery",
    )
    assert d.aggression_mod_pct == 30
    assert "lightning" in d.notes


def test_dragon_roosts_in_clear():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="dragons_aery", kind=WeatherKind.CLEAR,
        intensity=WeatherIntensity.NONE,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.DRAGON_NM,
        zone_id="dragons_aery",
    )
    assert d.mood_shift == "roosting"


def test_farmer_content_in_light_rain():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="sarutabaruta", kind=WeatherKind.RAIN,
        intensity=WeatherIntensity.LIGHT,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.FARMER_NPC,
        zone_id="sarutabaruta",
    )
    assert d.mood_shift == "content"


def test_farmer_exhausted_in_heatwave():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="altepa", kind=WeatherKind.HEATWAVE,
        intensity=WeatherIntensity.HEAVY,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.FARMER_NPC,
        zone_id="altepa",
    )
    assert d.mood_shift == "exhausted"
    assert d.speed_mod_pct == -20


def test_bird_flock_scatters_in_thunder():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="ronfaure", kind=WeatherKind.THUNDER,
        intensity=WeatherIntensity.HEAVY,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.BIRD_FLOCK,
        zone_id="ronfaure",
    )
    assert d.take_shelter
    assert d.mood_shift == "scattered"


def test_guard_aggressive_in_fog():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="batallia", kind=WeatherKind.FOG,
        intensity=WeatherIntensity.HEAVY,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.PLAYER_GUARD_NPC,
        zone_id="batallia",
    )
    assert d.aggression_mod_pct == 15


def test_clear_overrides():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="bastok", kind=WeatherKind.CLEAR,
        intensity=WeatherIntensity.NONE,
    ))
    assert ai.clear("bastok")
    assert ai.current("bastok") is None


def test_clear_unknown_returns_false():
    ai = DynamicWeatherAI()
    assert not ai.clear("ghost")


def test_unmapped_combo_returns_neutral():
    """No directive entry should still return a sensible neutral
    directive."""
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="windurst", kind=WeatherKind.AURORA,
        intensity=WeatherIntensity.LIGHT,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.MERCHANT_CARAVAN,
        zone_id="windurst",
    )
    assert not d.take_shelter
    assert d.aggression_mod_pct == 0


def test_night_amplifies_speed_penalty():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="xarcabard", kind=WeatherKind.SNOW,
        intensity=WeatherIntensity.HEAVY,
        is_night=True,
    ))
    d = ai.directive_for(
        actor_kind=ActorKind.MERCHANT_CARAVAN,
        zone_id="xarcabard",
    )
    # Base -50 * 1.2 = -60
    assert d.speed_mod_pct == -60


def test_total_zones_observed():
    ai = DynamicWeatherAI()
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="z1", kind=WeatherKind.CLEAR,
    ))
    ai.observe(snapshot=WeatherSnapshot(
        zone_id="z2", kind=WeatherKind.RAIN,
    ))
    assert ai.total_zones_observed() == 2
