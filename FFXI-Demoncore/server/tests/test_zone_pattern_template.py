"""Tests for zone_pattern_template."""
from __future__ import annotations

import dataclasses

import pytest

from server.zone_pattern_template import (
    DEFAULT_TEMPLATES,
    ZoneApplication,
    ZoneArchetype,
    ZonePatternRegistry,
    ZonePatternTemplate,
    archetype_for,
    default_template_for,
)


# ---- enum + defaults ----

def test_archetype_enum_has_six_values():
    assert len(list(ZoneArchetype)) == 6


def test_default_templates_exist_for_every_archetype():
    for a in ZoneArchetype:
        assert a in DEFAULT_TEMPLATES


def test_nation_capital_template_matches_bastok_baseline():
    t = DEFAULT_TEMPLATES[ZoneArchetype.NATION_CAPITAL]
    assert t.dressing_count_target == 32
    assert t.character_roster_size == 11
    assert t.choreography_beats_target == 8


def test_open_field_template_lower_density_than_capital():
    cap = DEFAULT_TEMPLATES[ZoneArchetype.NATION_CAPITAL]
    fld = DEFAULT_TEMPLATES[ZoneArchetype.OPEN_FIELD]
    assert fld.dressing_count_target < cap.dressing_count_target
    assert fld.character_roster_size < cap.character_roster_size


def test_dungeon_default_render_preset_is_cinematic():
    t = DEFAULT_TEMPLATES[ZoneArchetype.DUNGEON_DARK]
    assert t.render_preset_default == "cutscene_cinematic"


def test_endgame_has_highest_priority_one():
    t = DEFAULT_TEMPLATES[ZoneArchetype.ENDGAME_INSTANCE]
    assert t.asset_upgrade_priority == 1


# ---- archetype_for() ----

def test_archetype_for_bastok_markets_is_nation_capital():
    assert (
        archetype_for("bastok_markets")
        == ZoneArchetype.NATION_CAPITAL
    )


def test_archetype_for_selbina_is_outpost_town():
    assert (
        archetype_for("selbina") == ZoneArchetype.OUTPOST_TOWN
    )


def test_archetype_for_pashhow_is_open_field():
    assert (
        archetype_for("pashhow_marshlands")
        == ZoneArchetype.OPEN_FIELD
    )


def test_archetype_for_crawlers_nest_is_dungeon():
    assert (
        archetype_for("crawlers_nest")
        == ZoneArchetype.DUNGEON_DARK
    )


def test_archetype_for_davoi_is_beastman_fortress():
    assert (
        archetype_for("davoi")
        == ZoneArchetype.BEASTMAN_FORTRESS
    )


def test_archetype_for_sky_is_endgame():
    assert (
        archetype_for("sky") == ZoneArchetype.ENDGAME_INSTANCE
    )


def test_archetype_for_unknown_zone_uses_heuristic():
    # name contains 'tunnel' -> dungeon
    assert (
        archetype_for("some_random_tunnel")
        == ZoneArchetype.DUNGEON_DARK
    )


def test_archetype_for_unknown_falls_through_to_open_field():
    assert (
        archetype_for("totally_unknown_field")
        == ZoneArchetype.OPEN_FIELD
    )


def test_archetype_for_empty_raises():
    with pytest.raises(ValueError):
        archetype_for("")


# ---- default_template_for ----

def test_default_template_for_returns_match():
    t = default_template_for(ZoneArchetype.OPEN_FIELD)
    assert t.archetype == ZoneArchetype.OPEN_FIELD


# ---- registry: register, get, all ----

def test_registry_preloads_defaults():
    reg = ZonePatternRegistry()
    assert len(reg.all_templates()) >= 6


def test_register_template_adds_custom():
    reg = ZonePatternRegistry()
    custom = ZonePatternTemplate(
        template_id="tmpl_custom",
        archetype=ZoneArchetype.OPEN_FIELD,
        dressing_count_target=4, character_roster_size=1,
        npc_archetype_mix=(), mob_archetype_mix=(),
        lighting_profile_id="lp_custom",
        atmosphere_preset_id="atm_custom",
        render_preset_default="trailer_master",
        choreography_beats_target=2,
        asset_upgrade_priority=4,
    )
    reg.register_template(custom)
    assert reg.get_template("tmpl_custom") == custom


def test_register_template_empty_id_raises():
    reg = ZonePatternRegistry()
    bad = ZonePatternTemplate(
        template_id="",
        archetype=ZoneArchetype.OPEN_FIELD,
        dressing_count_target=1, character_roster_size=1,
        npc_archetype_mix=(), mob_archetype_mix=(),
        lighting_profile_id="x", atmosphere_preset_id="y",
        render_preset_default="trailer_master",
        choreography_beats_target=1, asset_upgrade_priority=1,
    )
    with pytest.raises(ValueError):
        reg.register_template(bad)


def test_get_template_unknown_raises():
    reg = ZonePatternRegistry()
    with pytest.raises(KeyError):
        reg.get_template("nope")


# ---- apply_template_to ----

def test_apply_template_to_uses_archetype_for_when_unspecified():
    reg = ZonePatternRegistry()
    app = reg.apply_template_to("bastok_markets")
    assert app.archetype == ZoneArchetype.NATION_CAPITAL
    assert app.template_id == "tmpl_nation_capital"


def test_apply_template_to_with_explicit_archetype():
    reg = ZonePatternRegistry()
    app = reg.apply_template_to(
        "some_zone", ZoneArchetype.OPEN_FIELD,
    )
    assert app.archetype == ZoneArchetype.OPEN_FIELD


def test_apply_template_to_zero_progress_when_empty_dep_funcs():
    reg = ZonePatternRegistry()
    app = reg.apply_template_to("bastok_markets")
    assert app.completeness_pct == 0.0


def test_apply_template_to_uses_dep_injected_counters():
    reg = ZonePatternRegistry(
        dressing_count_fn=lambda z: 16,
        roster_count_fn=lambda z: 11,
    )
    app = reg.apply_template_to("bastok_markets")
    # 16/32 = 50%, 11/11 = 100%; mean 75%
    assert app.completeness_pct == 75.0


def test_apply_template_to_caps_at_100():
    reg = ZonePatternRegistry(
        dressing_count_fn=lambda z: 999,
        roster_count_fn=lambda z: 999,
    )
    app = reg.apply_template_to("bastok_markets")
    assert app.completeness_pct == 100.0


def test_apply_template_to_negative_counts_clamped():
    reg = ZonePatternRegistry(
        dressing_count_fn=lambda z: -5,
        roster_count_fn=lambda z: -3,
    )
    app = reg.apply_template_to("bastok_markets")
    assert app.dressing_count_actual == 0
    assert app.roster_count_actual == 0


def test_apply_template_to_empty_zone_raises():
    reg = ZonePatternRegistry()
    with pytest.raises(ValueError):
        reg.apply_template_to("")


def test_apply_template_to_persists_application():
    reg = ZonePatternRegistry()
    reg.apply_template_to("bastok_markets")
    assert reg.application_for("bastok_markets").zone_id \
        == "bastok_markets"


def test_application_for_unknown_raises():
    reg = ZonePatternRegistry()
    with pytest.raises(KeyError):
        reg.application_for("never_seen")


# ---- all_zones_progress / pending / threshold ----

def test_all_zones_progress_returns_dict():
    reg = ZonePatternRegistry(
        dressing_count_fn=lambda z: 16,
        roster_count_fn=lambda z: 11,
    )
    reg.apply_template_to("bastok_markets")
    reg.apply_template_to("south_sandoria")
    prog = reg.all_zones_progress()
    assert prog["bastok_markets"] == 75.0
    assert "south_sandoria" in prog


def test_zones_pending_template_filters_applied():
    reg = ZonePatternRegistry()
    reg.apply_template_to("bastok_markets")
    pending = reg.zones_pending_template((
        "bastok_markets", "south_sandoria", "windurst_woods",
    ))
    assert pending == ("south_sandoria", "windurst_woods")


def test_zones_pending_template_empty_universe():
    reg = ZonePatternRegistry()
    assert reg.zones_pending_template(()) == ()


def test_zones_at_or_above_threshold():
    reg = ZonePatternRegistry(
        dressing_count_fn=lambda z: 32 if z == "a" else 8,
        roster_count_fn=lambda z: 11 if z == "a" else 2,
    )
    reg.apply_template_to("a", ZoneArchetype.NATION_CAPITAL)
    reg.apply_template_to("b", ZoneArchetype.NATION_CAPITAL)
    high = reg.zones_at_or_above(80.0)
    assert "a" in high
    assert "b" not in high


def test_zone_application_dataclass_frozen():
    app = ZoneApplication(
        zone_id="z", archetype=ZoneArchetype.OPEN_FIELD,
        template_id="t", dressing_count_actual=0,
        roster_count_actual=0, completeness_pct=0.0,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        app.completeness_pct = 50.0  # type: ignore


def test_template_dataclass_frozen():
    t = DEFAULT_TEMPLATES[ZoneArchetype.OPEN_FIELD]
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.dressing_count_target = 100  # type: ignore


def test_apply_template_idempotent_overwrites():
    reg = ZonePatternRegistry()
    reg.apply_template_to("bastok_markets")
    reg.apply_template_to(
        "bastok_markets", ZoneArchetype.OPEN_FIELD,
    )
    # Latest application wins.
    assert (
        reg.application_for("bastok_markets").archetype
        == ZoneArchetype.OPEN_FIELD
    )


def test_all_applications_returns_all():
    reg = ZonePatternRegistry()
    reg.apply_template_to("bastok_markets")
    reg.apply_template_to("south_sandoria")
    assert len(reg.all_applications()) == 2


def test_outpost_default_render_preset_trailer_master():
    t = DEFAULT_TEMPLATES[ZoneArchetype.OUTPOST_TOWN]
    assert t.render_preset_default == "trailer_master"
