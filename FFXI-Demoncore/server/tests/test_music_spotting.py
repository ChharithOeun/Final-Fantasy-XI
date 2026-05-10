"""Tests for music_spotting."""
from __future__ import annotations

import pytest

from server.music_spotting import (
    MusicSpottingSystem,
    SpotCue,
    SpotLayer,
    SpotPlan,
    SpotTrigger,
    populate_default_cues,
)


def _make_cue(
    cue_id="c1",
    trigger=SpotTrigger.ZONE_ENTER,
    stem="music/test.ogg",
    fade_in=1000,
    fade_out=1000,
    layer=SpotLayer.BASE,
    priority=5,
    loop=True,
    zone_id="",
    context_tag="",
):
    return SpotCue(
        cue_id=cue_id,
        trigger_kind=trigger,
        music_stem_uri=stem,
        fade_in_ms=fade_in,
        fade_out_ms=fade_out,
        layer=layer,
        priority=priority,
        loop=loop,
        zone_id=zone_id,
        context_tag=context_tag,
    )


# ---- enum coverage ----

def test_trigger_kinds_at_least_twelve():
    assert len(list(SpotTrigger)) >= 12


def test_layers_eight():
    assert len(list(SpotLayer)) == 8


def test_layer_names_contain_base_and_boss():
    names = {l.name for l in SpotLayer}
    assert "BASE" in names
    assert "BOSS" in names
    assert "VICTORY" in names
    assert "DEFEAT" in names


# ---- register / get ----

def test_register_and_get():
    s = MusicSpottingSystem()
    cue = _make_cue()
    s.register_cue(cue)
    assert s.get_cue("c1") is cue


def test_register_empty_id_raises():
    s = MusicSpottingSystem()
    with pytest.raises(ValueError):
        s.register_cue(_make_cue(cue_id=""))


def test_register_duplicate_raises():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue())
    with pytest.raises(ValueError):
        s.register_cue(_make_cue())


def test_register_priority_out_of_range_low():
    s = MusicSpottingSystem()
    with pytest.raises(ValueError):
        s.register_cue(_make_cue(priority=-1))


def test_register_priority_out_of_range_high():
    s = MusicSpottingSystem()
    with pytest.raises(ValueError):
        s.register_cue(_make_cue(priority=11))


def test_register_negative_fade_in_raises():
    s = MusicSpottingSystem()
    with pytest.raises(ValueError):
        s.register_cue(_make_cue(fade_in=-50))


def test_register_negative_fade_out_raises():
    s = MusicSpottingSystem()
    with pytest.raises(ValueError):
        s.register_cue(_make_cue(fade_out=-50))


def test_register_empty_stem_raises():
    s = MusicSpottingSystem()
    with pytest.raises(ValueError):
        s.register_cue(_make_cue(stem=""))


def test_get_unknown_raises():
    s = MusicSpottingSystem()
    with pytest.raises(KeyError):
        s.get_cue("missing")


# ---- fire ----

def test_fire_returns_plans():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue(zone_id="z1"))
    plans = s.fire(SpotTrigger.ZONE_ENTER, {"zone_id": "z1"})
    assert len(plans) == 1
    assert isinstance(plans[0], SpotPlan)
    assert plans[0].cue_id == "c1"


def test_fire_filters_by_zone():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue("a", zone_id="z1"))
    s.register_cue(_make_cue("b", zone_id="z2"))
    plans = s.fire(SpotTrigger.ZONE_ENTER, {"zone_id": "z1"})
    assert len(plans) == 1
    assert plans[0].cue_id == "a"


def test_fire_no_match_returns_empty():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue(zone_id="z1"))
    plans = s.fire(SpotTrigger.COMBAT_START)
    assert plans == ()


def test_fire_priority_wins_within_layer():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue("low", layer=SpotLayer.COMBAT,
                             trigger=SpotTrigger.COMBAT_START,
                             priority=3))
    s.register_cue(_make_cue("high", layer=SpotLayer.COMBAT,
                             trigger=SpotTrigger.COMBAT_START,
                             priority=8))
    plans = s.fire(SpotTrigger.COMBAT_START)
    ids = {p.cue_id for p in plans}
    assert "high" in ids
    assert "low" not in ids


def test_fire_returns_one_per_layer():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue(
        "combat", layer=SpotLayer.COMBAT,
        trigger=SpotTrigger.COMBAT_START, priority=5,
    ))
    s.register_cue(_make_cue(
        "tension", layer=SpotLayer.TENSION,
        trigger=SpotTrigger.COMBAT_START, priority=4,
    ))
    plans = s.fire(SpotTrigger.COMBAT_START)
    assert len(plans) == 2
    layers = {p.layer for p in plans}
    assert SpotLayer.COMBAT in layers
    assert SpotLayer.TENSION in layers


def test_fire_context_tag_filters():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue(
        "light", trigger=SpotTrigger.COMBAT_START,
        layer=SpotLayer.COMBAT, context_tag="light", priority=5,
    ))
    s.register_cue(_make_cue(
        "heavy", trigger=SpotTrigger.COMBAT_START,
        layer=SpotLayer.COMBAT, context_tag="heavy", priority=7,
    ))
    plans = s.fire(SpotTrigger.COMBAT_START,
                   {"context_tag": "light"})
    ids = {p.cue_id for p in plans}
    assert "light" in ids
    assert "heavy" not in ids


def test_fire_plans_carry_fade_params():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue(
        "x", trigger=SpotTrigger.MAGIC_BURST_FIRED,
        fade_in=42, fade_out=87, layer=SpotLayer.REVEAL_STING,
    ))
    plans = s.fire(SpotTrigger.MAGIC_BURST_FIRED)
    assert plans[0].fade_in_ms == 42
    assert plans[0].fade_out_ms == 87


# ---- currently_playing ----

def test_currently_playing_idle_is_base():
    s = MusicSpottingSystem()
    layers = s.currently_playing("z1", {})
    assert SpotLayer.BASE in layers


def test_currently_playing_tension_on_threat():
    s = MusicSpottingSystem()
    layers = s.currently_playing(
        "z1", {"threat_level": 5, "in_combat": False},
    )
    assert SpotLayer.TENSION in layers
    assert SpotLayer.COMBAT not in layers


def test_currently_playing_combat_replaces_tension():
    s = MusicSpottingSystem()
    layers = s.currently_playing(
        "z1", {"threat_level": 5, "in_combat": True},
    )
    assert SpotLayer.COMBAT in layers
    assert SpotLayer.TENSION not in layers


def test_currently_playing_boss_replaces_combat():
    s = MusicSpottingSystem()
    layers = s.currently_playing(
        "z1",
        {"threat_level": 9, "in_combat": True,
         "is_boss_engaged": True},
    )
    assert SpotLayer.BOSS in layers
    assert SpotLayer.COMBAT not in layers
    assert SpotLayer.TENSION not in layers


def test_currently_playing_base_always_present():
    s = MusicSpottingSystem()
    layers = s.currently_playing(
        "z1",
        {"threat_level": 9, "in_combat": True,
         "is_boss_engaged": True},
    )
    assert SpotLayer.BASE in layers


# ---- transition_to ----

def test_transition_to_returns_plan():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue("c", layer=SpotLayer.BOSS))
    plan = s.transition_to(SpotLayer.BOSS, "c")
    assert plan.cue_id == "c"
    assert plan.layer == SpotLayer.BOSS


def test_transition_to_layer_mismatch_raises():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue("c", layer=SpotLayer.BOSS))
    with pytest.raises(ValueError):
        s.transition_to(SpotLayer.BASE, "c")


def test_transition_to_unknown_cue_raises():
    s = MusicSpottingSystem()
    with pytest.raises(KeyError):
        s.transition_to(SpotLayer.BOSS, "missing")


# ---- all_cues_for_layer ----

def test_all_cues_for_layer_filters():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue("a", layer=SpotLayer.BASE))
    s.register_cue(_make_cue("b", layer=SpotLayer.COMBAT,
                             trigger=SpotTrigger.COMBAT_START))
    cues = s.all_cues_for_layer(SpotLayer.BASE)
    assert len(cues) == 1
    assert cues[0].cue_id == "a"


def test_all_cues_for_layer_empty():
    s = MusicSpottingSystem()
    assert s.all_cues_for_layer(SpotLayer.VICTORY) == ()


# ---- cue_priority_for ----

def test_cue_priority_for_no_cues_zero():
    s = MusicSpottingSystem()
    assert s.cue_priority_for(SpotTrigger.LEVEL_UP) == 0


def test_cue_priority_for_max():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue(
        "a", trigger=SpotTrigger.LEVEL_UP, priority=3,
        layer=SpotLayer.REVEAL_STING,
    ))
    s.register_cue(_make_cue(
        "b", trigger=SpotTrigger.LEVEL_UP, priority=9,
        layer=SpotLayer.REVEAL_STING,
    ))
    assert s.cue_priority_for(SpotTrigger.LEVEL_UP) == 9


# ---- zone_base_cue ----

def test_zone_base_cue_registered():
    s = MusicSpottingSystem()
    s.register_cue(_make_cue(
        "base_z1", zone_id="z1", layer=SpotLayer.BASE,
        trigger=SpotTrigger.ZONE_ENTER,
    ))
    assert s.zone_base_cue("z1") == "base_z1"


def test_zone_base_cue_missing_returns_empty():
    s = MusicSpottingSystem()
    assert s.zone_base_cue("nothing") == ""


# ---- is_sting ----

def test_is_sting_true_for_reveal():
    s = MusicSpottingSystem()
    assert s.is_sting(SpotLayer.REVEAL_STING)


def test_is_sting_true_for_dialogue():
    s = MusicSpottingSystem()
    assert s.is_sting(SpotLayer.DIALOGUE_STING)


def test_is_sting_false_for_base():
    s = MusicSpottingSystem()
    assert not s.is_sting(SpotLayer.BASE)


def test_is_sting_false_for_boss():
    s = MusicSpottingSystem()
    assert not s.is_sting(SpotLayer.BOSS)


# ---- default catalog ----

def test_default_catalog_at_least_thirty():
    s = MusicSpottingSystem()
    n = populate_default_cues(s)
    assert n >= 30


def test_default_catalog_bastok_mines_base():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    assert s.zone_base_cue("bastok_mines") == "base_bastok_mines"


def test_default_catalog_iron_eater_boss():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    plans = s.fire(
        SpotTrigger.BOSS_INTRO_TRIGGER,
        {"context_tag": "iron_eater"},
    )
    assert any(p.cue_id == "boss_iron_eater" for p in plans)


def test_default_catalog_skillchain_light_sting_present():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    plans = s.fire(
        SpotTrigger.SKILLCHAIN_CLOSED,
        {"context_tag": "light"},
    )
    assert any(p.cue_id == "sting_skillchain_light" for p in plans)


def test_default_catalog_mb_sting_present():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    plans = s.fire(SpotTrigger.MAGIC_BURST_FIRED)
    assert any(p.cue_id == "sting_magic_burst" for p in plans)


def test_default_catalog_level_up_high_priority():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    cue = s.get_cue("sting_level_up")
    assert cue.priority >= 8


def test_default_catalog_combat_themes_present():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    for tag in ("light", "medium", "heavy"):
        plans = s.fire(
            SpotTrigger.COMBAT_START,
            {"context_tag": tag},
        )
        assert any(p.layer == SpotLayer.COMBAT for p in plans)


def test_default_catalog_dialogue_stings_three_kinds():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    cues = s.all_cues_for_layer(SpotLayer.DIALOGUE_STING)
    assert len(cues) >= 3


def test_default_catalog_weather_sting():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    plans = s.fire(SpotTrigger.WEATHER_CHANGED)
    assert len(plans) >= 1


def test_default_catalog_loop_flag_on_base():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    cue = s.get_cue("base_bastok_mines")
    assert cue.loop is True


def test_default_catalog_stings_dont_loop():
    s = MusicSpottingSystem()
    populate_default_cues(s)
    cue = s.get_cue("sting_magic_burst")
    assert cue.loop is False
