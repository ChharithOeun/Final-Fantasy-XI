"""Tests for terrain + weather + race modifiers + fomor lighting +
SCH/GEO manipulators + the composer.

Run:  python -m pytest server/tests/test_terrain_weather.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from terrain_weather import (
    DUNGEON_FOMOR_MULTIPLIER,
    EffectiveModifier,
    EnvironmentEffectComposer,
    GeoBubble,
    GeoManipulator,
    LightingState,
    NIGHT_FOMOR_MULTIPLIER,
    RACE_TERRAIN_PROFILES,
    SchManipulator,
    TerrainType,
    WeatherType,
    ZoneEnvironment,
    fomor_lighting_strength,
    race_profile_for,
    weather_elemental_amp,
)
from terrain_weather.composer import WEATHER_SIDE_EFFECTS


# ----------------------------------------------------------------------
# Fomor lighting strength
# ----------------------------------------------------------------------

def test_fomor_daytime_baseline():
    assert fomor_lighting_strength(LightingState.DAYTIME) == 1.0


def test_fomor_nighttime_buff():
    assert fomor_lighting_strength(LightingState.NIGHTTIME) == NIGHT_FOMOR_MULTIPLIER
    assert NIGHT_FOMOR_MULTIPLIER > 1.0


def test_fomor_dungeon_strongest_among_normal():
    """Dungeon = always sunless = 1.35x."""
    assert fomor_lighting_strength(LightingState.DUNGEON) == DUNGEON_FOMOR_MULTIPLIER
    assert DUNGEON_FOMOR_MULTIPLIER > NIGHT_FOMOR_MULTIPLIER


def test_fomor_eternal_night_apex():
    """Dynamis / Sky-of-Eternal-Twilight: 1.50x."""
    assert fomor_lighting_strength(LightingState.ETERNAL_NIGHT) == 1.50


def test_fomor_dawn_dusk_transitional():
    assert fomor_lighting_strength(LightingState.DAWN) == 1.10
    assert fomor_lighting_strength(LightingState.DUSK) == 1.10


# ----------------------------------------------------------------------
# Per-race profiles
# ----------------------------------------------------------------------

def test_all_five_races_present():
    for race in ("hume", "elvaan", "tarutaru", "mithra", "galka"):
        assert race in RACE_TERRAIN_PROFILES


def test_elvaan_strong_in_grassland():
    p = race_profile_for("elvaan")
    assert p.terrain_buffs[TerrainType.GRASSLAND] > 1.0


def test_elvaan_weak_in_swamp():
    p = race_profile_for("elvaan")
    assert p.terrain_buffs[TerrainType.SWAMP] < 1.0


def test_tarutaru_buffed_by_aurora():
    """Wisdom-attuned tarus get a big aurora bonus."""
    p = race_profile_for("tarutaru")
    assert p.weather_buffs[WeatherType.AURORA] >= 1.10


def test_tarutaru_battered_by_heavy_weather():
    p = race_profile_for("tarutaru")
    assert p.weather_buffs[WeatherType.WIND_GALES] < 1.0
    assert p.weather_buffs[WeatherType.BLIZZARD] < 1.0
    assert p.weather_buffs[WeatherType.SANDSTORM] < 1.0


def test_mithra_thrives_in_forest_and_desert():
    p = race_profile_for("mithra")
    assert p.terrain_buffs[TerrainType.FOREST] > 1.0
    assert p.terrain_buffs[TerrainType.DESERT] > 1.0
    # Cold-averse fur
    assert p.terrain_buffs[TerrainType.SNOW] < 1.0


def test_galka_thrives_in_dungeon_and_mountains():
    p = race_profile_for("galka")
    assert p.terrain_buffs[TerrainType.DUNGEON] > 1.0
    assert p.terrain_buffs[TerrainType.MOUNTAINS] > 1.0
    # Heavy = swims poorly
    assert p.terrain_buffs[TerrainType.WATER] < 1.0


def test_hume_balanced_no_big_debuffs():
    """Hume profile has only mild buffs; no terrain debuff < 0.95."""
    p = race_profile_for("hume")
    for terrain, mult in p.terrain_buffs.items():
        assert mult >= 0.95, f"hume should have no big debuffs: {terrain}"


def test_unknown_race_neutral_profile():
    p = race_profile_for("zilart")
    assert p.terrain_buffs == {}
    assert p.weather_buffs == {}


# ----------------------------------------------------------------------
# Weather elemental amp
# ----------------------------------------------------------------------

def test_blizzard_amplifies_ice_dampens_fire():
    assert weather_elemental_amp(WeatherType.BLIZZARD, "ice") == 1.25
    assert weather_elemental_amp(WeatherType.BLIZZARD, "fire") == 0.75


def test_thunder_amplifies_lightning():
    assert weather_elemental_amp(WeatherType.THUNDER, "lightning") == 1.20


def test_aurora_amplifies_light_dampens_dark():
    assert weather_elemental_amp(WeatherType.AURORA, "light") == 1.25
    assert weather_elemental_amp(WeatherType.AURORA, "dark") == 0.75


def test_clear_weather_neutral():
    for el in ("fire", "ice", "water", "lightning", "earth", "wind", "light", "dark"):
        assert weather_elemental_amp(WeatherType.CLEAR, el) == 1.0


def test_intensity_attenuates_amp():
    """50% blizzard intensity halves the deviation."""
    full = weather_elemental_amp(WeatherType.BLIZZARD, "ice", intensity=1.0)
    half = weather_elemental_amp(WeatherType.BLIZZARD, "ice", intensity=0.5)
    # full = 1.25; deviation = 0.25; half-deviation = 0.125; → 1.125
    assert half == pytest.approx(1.125)
    assert full == 1.25


# ----------------------------------------------------------------------
# Composer — race + terrain + weather
# ----------------------------------------------------------------------

def _grassland_clear_day(zone="ronfaure_east") -> ZoneEnvironment:
    return ZoneEnvironment(
        zone_id=zone, terrain=TerrainType.GRASSLAND,
        weather=WeatherType.CLEAR, lighting=LightingState.DAYTIME,
        weather_intensity=1.0,
    )


def _dungeon_clear() -> ZoneEnvironment:
    return ZoneEnvironment(
        zone_id="garlaige_citadel", terrain=TerrainType.DUNGEON,
        weather=WeatherType.CLEAR, lighting=LightingState.DUNGEON,
        weather_intensity=1.0,
    )


def test_composer_neutral_for_hume_clear_grassland():
    """Hume on grassland in clear weather: small race bonus."""
    env = _grassland_clear_day()
    mod = EnvironmentEffectComposer().compose(env=env, race="hume")
    # Hume gets +3% grassland * +3% clear = ~1.06
    assert mod.vitality_mult == pytest.approx(1.0609, abs=0.01)
    assert mod.fomor_strength_mult == 1.0


def test_composer_elvaan_in_swamp_takes_hit():
    env = ZoneEnvironment(
        zone_id="qufim_swamp", terrain=TerrainType.SWAMP,
        weather=WeatherType.FOG, lighting=LightingState.DAYTIME,
        weather_intensity=1.0,
    )
    mod = EnvironmentEffectComposer().compose(env=env, race="elvaan")
    # Elvaan swamp 0.85 * fog 0.95 = 0.8075
    assert mod.vitality_mult < 0.85


def test_composer_galka_in_dungeon_buffed():
    env = _dungeon_clear()
    mod = EnvironmentEffectComposer().compose(env=env, race="galka")
    assert mod.vitality_mult > 1.10


def test_composer_fomor_in_dungeon_extra_strong():
    env = _dungeon_clear()
    mod = EnvironmentEffectComposer().compose(
        env=env, race="hume", is_fomor=True,
    )
    assert mod.fomor_strength_mult == DUNGEON_FOMOR_MULTIPLIER


def test_composer_fomor_at_night_open_world():
    env = ZoneEnvironment(
        zone_id="east_ronfaure", terrain=TerrainType.GRASSLAND,
        weather=WeatherType.CLEAR, lighting=LightingState.NIGHTTIME,
    )
    mod = EnvironmentEffectComposer().compose(
        env=env, race="hume", is_fomor=True,
    )
    assert mod.fomor_strength_mult == NIGHT_FOMOR_MULTIPLIER


def test_composer_fomor_at_daytime_no_lighting_bonus():
    env = _grassland_clear_day()
    mod = EnvironmentEffectComposer().compose(
        env=env, race="hume", is_fomor=True,
    )
    assert mod.fomor_strength_mult == 1.0


def test_composer_blizzard_amp_ice_for_anyone():
    env = ZoneEnvironment(
        zone_id="x", terrain=TerrainType.SNOW, weather=WeatherType.BLIZZARD,
        lighting=LightingState.DAYTIME, weather_intensity=1.0,
    )
    mod = EnvironmentEffectComposer().compose(env=env, race="hume")
    assert mod.elemental_multiplier_for("ice") == 1.25
    assert mod.elemental_multiplier_for("fire") == 0.75


def test_composer_sandstorm_drops_speed_and_accuracy():
    env = ZoneEnvironment(
        zone_id="altepa_desert", terrain=TerrainType.DESERT,
        weather=WeatherType.SANDSTORM, lighting=LightingState.DAYTIME,
        weather_intensity=1.0,
    )
    mod = EnvironmentEffectComposer().compose(env=env, race="hume")
    speed, acc = WEATHER_SIDE_EFFECTS[WeatherType.SANDSTORM]
    assert mod.speed_mult == speed
    assert mod.accuracy_mod == acc


def test_composer_intensity_scales_side_effects():
    """50% sandstorm intensity → halved deviation."""
    env = ZoneEnvironment(
        zone_id="altepa_desert", terrain=TerrainType.DESERT,
        weather=WeatherType.SANDSTORM, lighting=LightingState.DAYTIME,
        weather_intensity=0.5,
    )
    mod = EnvironmentEffectComposer().compose(env=env, race="hume")
    speed_full, acc_full = WEATHER_SIDE_EFFECTS[WeatherType.SANDSTORM]
    # 0.90 → at 0.5 intensity: 1.0 + (0.90 - 1.0) * 0.5 = 0.95
    assert mod.speed_mult == pytest.approx(0.95)
    assert mod.accuracy_mod == pytest.approx(acc_full * 0.5)


# ----------------------------------------------------------------------
# Pull-NM-to-zone scenario
# ----------------------------------------------------------------------

def test_pull_water_nm_into_thunder_zone_amps_lightning():
    """User scenario: pull a water-aligned NM into a thunder zone.
    Lightning damage on the NM gets amplified by the THUNDER weather.
    (Verified via the elemental_mult, which the damage_resolver applies.)"""
    env = ZoneEnvironment(
        zone_id="rolanberry_thunderstorm", terrain=TerrainType.GRASSLAND,
        weather=WeatherType.THUNDER, lighting=LightingState.DAYTIME,
        weather_intensity=1.0,
    )
    mod = EnvironmentEffectComposer().compose(env=env, race="hume")
    # Lightning gets a 1.20x boost just from being in the weather
    assert mod.elemental_multiplier_for("lightning") == 1.20


# ----------------------------------------------------------------------
# SCH manipulator
# ----------------------------------------------------------------------

def test_sch_stormsurge_forces_rain():
    env = _grassland_clear_day()
    sch = SchManipulator()
    ok = sch.cast_strategos(env, spell_name="Stormsurge", now=100)
    assert ok is True
    assert env.weather == WeatherType.RAIN
    assert env.weather_intensity == 1.0


def test_sch_unknown_spell_returns_false():
    env = _grassland_clear_day()
    sch = SchManipulator()
    ok = sch.cast_strategos(env, spell_name="Fireball", now=100)
    assert ok is False
    assert env.weather == WeatherType.CLEAR


def test_sch_thunderstorm_amps_lightning():
    """End-to-end: SCH casts Thunderstorm → composer reads new weather
    → lightning gets the THUNDER amp."""
    env = _grassland_clear_day()
    sch = SchManipulator()
    sch.cast_strategos(env, spell_name="Thunderstorm", now=0)
    mod = EnvironmentEffectComposer().compose(env=env, race="hume")
    assert mod.elemental_multiplier_for("lightning") == 1.20


def test_sch_expiration_restores_default():
    env = _grassland_clear_day()
    sch = SchManipulator()
    sch.cast_strategos(env, spell_name="Stormsurge",
                        now=0, duration_seconds=60)
    # Mid-duration: still raining
    fired = sch.tick_expirations(env, now=30,
                                    default_weather=WeatherType.CLEAR)
    assert fired is False
    assert env.weather == WeatherType.RAIN
    # Expired: restored
    fired = sch.tick_expirations(env, now=70,
                                    default_weather=WeatherType.CLEAR)
    assert fired is True
    assert env.weather == WeatherType.CLEAR


# ----------------------------------------------------------------------
# GEO manipulator
# ----------------------------------------------------------------------

def test_geo_bubble_overrides_terrain_for_inside_unit():
    env = ZoneEnvironment(
        zone_id="east_ronfaure", terrain=TerrainType.GRASSLAND,
        weather=WeatherType.CLEAR, lighting=LightingState.DAYTIME,
        weather_intensity=1.0,
    )
    geo = GeoManipulator()
    geo.cast(env.zone_id, GeoBubble(
        bubble_id="b1", caster_id="geo_player",
        center_xy=(0, 0), radius_cm=500,
        terrain_override=TerrainType.MOUNTAINS,
        elemental_boost=("earth", 1.20),
    ))
    # Galka inside the bubble: gets the mountains+earth boost
    inside_mod = EnvironmentEffectComposer().compose(
        env=env, race="galka", unit_position=(100, 100), geo=geo,
    )
    # Galka mountains buff = 1.10
    assert inside_mod.vitality_mult > 1.05
    assert inside_mod.elemental_multiplier_for("earth") == 1.20

    # Outside the bubble: no override
    outside_mod = EnvironmentEffectComposer().compose(
        env=env, race="galka", unit_position=(2000, 2000), geo=geo,
    )
    assert outside_mod.elemental_multiplier_for("earth") == 1.0


def test_geo_bubble_remove():
    geo = GeoManipulator()
    geo.cast("zone_a", GeoBubble(
        bubble_id="b1", caster_id="geo_player",
        center_xy=(0, 0), radius_cm=500,
    ))
    assert geo.remove("zone_a", "b1") is True
    assert geo.remove("zone_a", "nonexistent") is False


def test_geo_bubble_expires():
    geo = GeoManipulator()
    geo.cast("z", GeoBubble(
        bubble_id="b1", caster_id="x", center_xy=(0, 0),
        radius_cm=500, expires_at=100,
    ))
    # Still active at t=50
    assert geo.tick_expirations(now=50) == 0
    assert geo.bubble_at("z", (0, 0)) is not None
    # Expired at t=200
    assert geo.tick_expirations(now=200) == 1
    assert geo.bubble_at("z", (0, 0)) is None


def test_geo_last_cast_wins_on_overlap():
    """When two bubbles overlap, the most-recently-cast one wins."""
    geo = GeoManipulator()
    geo.cast("z", GeoBubble(
        bubble_id="old", caster_id="x", center_xy=(0, 0), radius_cm=1000,
        terrain_override=TerrainType.GRASSLAND,
    ))
    geo.cast("z", GeoBubble(
        bubble_id="new", caster_id="x", center_xy=(0, 0), radius_cm=500,
        terrain_override=TerrainType.MOUNTAINS,
    ))
    bubble = geo.bubble_at("z", (50, 50))
    assert bubble is not None
    assert bubble.bubble_id == "new"


# ----------------------------------------------------------------------
# Mob counter-strategy: same logic against players
# ----------------------------------------------------------------------

def test_mob_party_gets_same_environmental_buffs():
    """A goblin (treated as 'galka'-ish stone-bodied for terrain) in a
    dungeon: same boost any galka would get. Mob parties using SCH/GEO
    benefit identically. We model this by simply running the same
    composer for the mob unit."""
    env = _dungeon_clear()
    mob_mod = EnvironmentEffectComposer().compose(
        env=env, race="galka", is_fomor=False,
    )
    player_mod = EnvironmentEffectComposer().compose(
        env=env, race="galka", is_fomor=False,
    )
    # Same race + same env = identical modifiers (the engine doesn't
    # discriminate friend/foe by default; the caller chooses race)
    assert mob_mod.vitality_mult == player_mod.vitality_mult


# ----------------------------------------------------------------------
# Integration: pull-NM-debuff scenario
# ----------------------------------------------------------------------

def test_pull_fire_nm_into_blizzard_zone():
    """Full scenario: a fire-aligned NM gets debuffed when pulled into
    a blizzard zone — fire dampens to 0.75x, ice spells against the NM
    amp to 1.25x. Combined 'wrong-weather penalty' is significant."""
    env = ZoneEnvironment(
        zone_id="uleguerand_range", terrain=TerrainType.SNOW,
        weather=WeatherType.BLIZZARD, lighting=LightingState.DAYTIME,
        weather_intensity=1.0,
    )
    mod = EnvironmentEffectComposer().compose(env=env, race="neutral")
    # The NM's fire spells get dampened to 0.75x
    assert mod.elemental_multiplier_for("fire") == 0.75
    # Players casting ice on the NM benefit from the 1.25x
    assert mod.elemental_multiplier_for("ice") == 1.25
    # Combined ratio of 'right vs wrong element under this weather':
    # 1.25 / 0.75 = 1.67x advantage for ice over fire under blizzard
    assert mod.elemental_multiplier_for("ice") / mod.elemental_multiplier_for("fire") == pytest.approx(5/3)
