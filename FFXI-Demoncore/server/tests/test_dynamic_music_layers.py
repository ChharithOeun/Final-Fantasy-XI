"""Tests for dynamic_music_layers."""
from __future__ import annotations

import pytest

from server.dynamic_music_layers import (
    CombatState,
    DynamicMusicLayerSystem,
    LayerKind,
    MusicLayer,
    SILENT_DB,
    StingEvent,
    populate_default_layers,
)


def _layer(
    lid="l1",
    kind=LayerKind.EXPLORATION,
    zone_id="",
    stem="music/x.ogg",
    gain=-6.0,
    lc=40.0,
    hc=16000.0,
):
    return MusicLayer(
        layer_id=lid, kind=kind, zone_id=zone_id,
        stem_uri=stem, gain_db_default=gain,
        low_cut_hz=lc, high_cut_hz=hc,
    )


def _state(
    pid="p1", in_combat=False, threat=0.0,
    near=999.0, boss=False, mb=False, low_hp=False,
):
    return CombatState(
        player_id=pid,
        in_combat=in_combat,
        threat_level=threat,
        nearest_threat_distance_m=near,
        is_boss_engaged=boss,
        magic_burst_recent=mb,
        party_below_25pct_hp=low_hp,
    )


# ---- enums ----

def test_layer_kind_count_ten():
    assert len(list(LayerKind)) == 10


def test_sting_event_includes_skillchain_kinds():
    names = {e.name for e in StingEvent}
    assert "MAGIC_BURST" in names
    assert "SKILLCHAIN_LIGHT" in names
    assert "SKILLCHAIN_DARKNESS" in names
    assert "CRITICAL_HEALTH" in names


# ---- register ----

def test_register_layer():
    s = DynamicMusicLayerSystem()
    s.register_layer(_layer())
    assert s.layer_count() == 1


def test_register_empty_id():
    s = DynamicMusicLayerSystem()
    with pytest.raises(ValueError):
        s.register_layer(_layer(lid=""))


def test_register_empty_stem():
    s = DynamicMusicLayerSystem()
    with pytest.raises(ValueError):
        s.register_layer(_layer(stem=""))


def test_register_high_cut_below_low_cut():
    s = DynamicMusicLayerSystem()
    with pytest.raises(ValueError):
        s.register_layer(_layer(lc=2000.0, hc=1000.0))


def test_register_gain_too_loud():
    s = DynamicMusicLayerSystem()
    with pytest.raises(ValueError):
        s.register_layer(_layer(gain=20.0))


def test_register_duplicate():
    s = DynamicMusicLayerSystem()
    s.register_layer(_layer())
    with pytest.raises(ValueError):
        s.register_layer(_layer())


def test_get_layer_unknown_raises():
    s = DynamicMusicLayerSystem()
    with pytest.raises(KeyError):
        s.get_layer("missing")


# ---- resolve_layer ----

def test_resolve_layer_global_default():
    s = DynamicMusicLayerSystem()
    s.register_layer(_layer(
        "g_explore", kind=LayerKind.EXPLORATION,
    ))
    layer = s.resolve_layer(LayerKind.EXPLORATION, "any")
    assert layer is not None
    assert layer.layer_id == "g_explore"


def test_resolve_layer_zone_override_beats_global():
    s = DynamicMusicLayerSystem()
    s.register_layer(_layer(
        "g_explore", kind=LayerKind.EXPLORATION,
    ))
    s.register_layer(_layer(
        "z_explore", kind=LayerKind.EXPLORATION, zone_id="z1",
    ))
    layer = s.resolve_layer(LayerKind.EXPLORATION, "z1")
    assert layer.layer_id == "z_explore"


def test_resolve_layer_missing_returns_none():
    s = DynamicMusicLayerSystem()
    assert s.resolve_layer(LayerKind.BOSS, "any") is None


# ---- target_gains: idle ----

def test_target_gains_idle_plays_exploration():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains("any_zone", _state())
    assert g[LayerKind.EXPLORATION] > SILENT_DB
    assert g[LayerKind.COMBAT_LIGHT] == SILENT_DB
    assert g[LayerKind.BOSS] == SILENT_DB


def test_target_gains_idle_with_town_day_layer():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains("bastok_markets", _state(),
                       time_of_day="day")
    # town_day layer present globally; town zone wins it.
    assert g[LayerKind.TOWN_DAY] > SILENT_DB


def test_target_gains_idle_town_night_at_night():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains("bastok_markets", _state(),
                       time_of_day="night")
    assert g[LayerKind.TOWN_NIGHT] > SILENT_DB


def test_target_gains_idle_mog_house_zone():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains("mog_house_bastok", _state())
    assert g[LayerKind.MOG_HOUSE] > SILENT_DB
    assert g[LayerKind.EXPLORATION] == SILENT_DB


# ---- target_gains: tension ----

def test_target_gains_tension_at_threat_3():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains(
        "z", _state(threat=3.0, in_combat=False),
    )
    assert g[LayerKind.TENSION] > SILENT_DB
    assert g[LayerKind.EXPLORATION] == SILENT_DB
    assert g[LayerKind.COMBAT_LIGHT] == SILENT_DB


def test_target_gains_no_tension_below_threshold():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains("z", _state(threat=2.0))
    assert g[LayerKind.TENSION] == SILENT_DB


# ---- target_gains: combat light ----

def test_target_gains_combat_light_when_in_combat():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains(
        "z", _state(in_combat=True, threat=4.0),
    )
    assert g[LayerKind.COMBAT_LIGHT] > SILENT_DB
    assert g[LayerKind.TENSION] == SILENT_DB


def test_target_gains_combat_light_silences_exploration():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains(
        "z", _state(in_combat=True, threat=4.0),
    )
    assert g[LayerKind.EXPLORATION] == SILENT_DB


# ---- target_gains: combat heavy ----

def test_target_gains_combat_heavy_at_threat_7():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains(
        "z", _state(in_combat=True, threat=7.0),
    )
    assert g[LayerKind.COMBAT_HEAVY] > SILENT_DB
    assert g[LayerKind.COMBAT_LIGHT] == SILENT_DB


def test_target_gains_combat_heavy_at_threat_10():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains(
        "z", _state(in_combat=True, threat=10.0),
    )
    assert g[LayerKind.COMBAT_HEAVY] > SILENT_DB


# ---- target_gains: boss ----

def test_target_gains_boss_overrides_combat():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains(
        "z",
        _state(in_combat=True, threat=10.0, boss=True),
    )
    assert g[LayerKind.BOSS] > SILENT_DB
    assert g[LayerKind.COMBAT_HEAVY] == SILENT_DB
    assert g[LayerKind.COMBAT_LIGHT] == SILENT_DB


def test_target_gains_boss_overrides_tension():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    g = s.target_gains(
        "z",
        _state(in_combat=False, threat=4.0, boss=True),
    )
    assert g[LayerKind.BOSS] > SILENT_DB
    assert g[LayerKind.TENSION] == SILENT_DB


def test_target_gains_zone_specific_boss_layer():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    # Verify that bastok_markets gets iron_eater_boss layer
    layer = s.resolve_layer(LayerKind.BOSS, "bastok_markets")
    assert layer.layer_id == "iron_eater_boss"


# ---- transition_to ----

def test_transition_combat_start():
    s = DynamicMusicLayerSystem()
    out = s.transition_to("combat_start")
    assert out == (LayerKind.COMBAT_LIGHT,)


def test_transition_combat_end_win():
    s = DynamicMusicLayerSystem()
    out = s.transition_to("combat_end", won=True)
    assert out == (LayerKind.VICTORY,)


def test_transition_combat_end_loss():
    s = DynamicMusicLayerSystem()
    out = s.transition_to("combat_end", won=False)
    assert out == (LayerKind.DEFEAT,)


def test_transition_boss_engage():
    s = DynamicMusicLayerSystem()
    out = s.transition_to("boss_engage")
    assert out == (LayerKind.BOSS,)


def test_transition_death():
    s = DynamicMusicLayerSystem()
    out = s.transition_to("death")
    assert out == (LayerKind.DEFEAT,)


def test_transition_zone_enter():
    s = DynamicMusicLayerSystem()
    out = s.transition_to("zone_enter")
    assert out == (LayerKind.EXPLORATION,)


def test_transition_mog_house_enter():
    s = DynamicMusicLayerSystem()
    out = s.transition_to("mog_house_enter")
    assert out == (LayerKind.MOG_HOUSE,)


def test_transition_unknown_raises():
    s = DynamicMusicLayerSystem()
    with pytest.raises(ValueError):
        s.transition_to("invalid_event")


# ---- should_play_sting ----

def test_should_play_sting_mb_when_burst_recent():
    s = DynamicMusicLayerSystem()
    assert s.should_play_sting(
        StingEvent.MAGIC_BURST, _state(mb=True),
    )


def test_should_play_sting_mb_when_no_state_default_true():
    s = DynamicMusicLayerSystem()
    assert s.should_play_sting(StingEvent.MAGIC_BURST)


def test_should_play_sting_mb_when_no_burst_false():
    s = DynamicMusicLayerSystem()
    assert not s.should_play_sting(
        StingEvent.MAGIC_BURST, _state(mb=False),
    )


def test_should_play_sting_critical_when_low_hp():
    s = DynamicMusicLayerSystem()
    assert s.should_play_sting(
        StingEvent.CRITICAL_HEALTH, _state(low_hp=True),
    )


def test_should_play_sting_critical_when_full_hp_false():
    s = DynamicMusicLayerSystem()
    assert not s.should_play_sting(
        StingEvent.CRITICAL_HEALTH, _state(low_hp=False),
    )


def test_should_play_sting_critical_no_state_false():
    s = DynamicMusicLayerSystem()
    assert not s.should_play_sting(
        StingEvent.CRITICAL_HEALTH,
    )


def test_should_play_sting_skillchain_always_true():
    s = DynamicMusicLayerSystem()
    assert s.should_play_sting(StingEvent.SKILLCHAIN_LIGHT)
    assert s.should_play_sting(StingEvent.SKILLCHAIN_DARKNESS)


# ---- all_layers_for_zone ----

def test_all_layers_for_zone_returns_zone_overrides():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    layers = s.all_layers_for_zone("bastok_markets")
    ids = {l.layer_id for l in layers}
    assert "bastok_markets_combat_light" in ids
    # The global combat_light is masked by the zone one.
    assert "global_combat_light" not in ids
    # Other globals still appear.
    assert "global_exploration" in ids


def test_all_layers_for_zone_unknown_returns_globals_only():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    layers = s.all_layers_for_zone("unknown_zone")
    ids = {l.layer_id for l in layers}
    assert "global_exploration" in ids
    assert "global_combat_light" in ids
    assert "bastok_markets_combat_light" not in ids


# ---- default catalog ----

def test_default_catalog_has_all_kinds():
    s = DynamicMusicLayerSystem()
    populate_default_layers(s)
    for kind in LayerKind:
        layer = s.resolve_layer(kind, "")
        assert layer is not None


def test_default_catalog_count_at_least_twelve():
    s = DynamicMusicLayerSystem()
    n = populate_default_layers(s)
    assert n >= 12
