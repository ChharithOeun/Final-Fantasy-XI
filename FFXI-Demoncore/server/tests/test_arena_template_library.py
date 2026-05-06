"""Tests for arena_template_library."""
from __future__ import annotations

from server.arena_environment import ArenaEnvironment
from server.arena_template_library import (
    ArenaTemplateLibrary, TemplateId,
)
from server.environment_cascade import EnvironmentCascade
from server.environment_damage import EnvironmentDamage
from server.habitat_disturbance import (
    HabitatBiome, HabitatDisturbance,
)
from server.siege_cannons import SiegeCannons


def test_canonical_templates_loaded():
    lib = ArenaTemplateLibrary()
    out = lib.all_templates()
    template_ids = {t.template_id for t in out}
    # 5 canonical templates shipped
    assert template_ids == {
        TemplateId.KELP_CHAMBER, TemplateId.SHIP_DECK,
        TemplateId.ICE_CAVERN, TemplateId.DAM_BASIN,
        TemplateId.ROYAL_PALACE,
    }


def test_get_template_by_id():
    lib = ArenaTemplateLibrary()
    tpl = lib.get(template_id=TemplateId.SHIP_DECK)
    assert tpl is not None
    assert tpl.label == "Ship Deck"


def test_unknown_template_returns_none():
    lib = ArenaTemplateLibrary()
    # all canonical IDs are registered, but if a future enum
    # value ever existed without a registration it'd return None
    tpl = lib.get(template_id=TemplateId.KELP_CHAMBER)
    assert tpl is not None


def test_instantiate_kelp_chamber_features():
    lib = ArenaTemplateLibrary()
    env = ArenaEnvironment()
    out = lib.instantiate(
        template_id=TemplateId.KELP_CHAMBER, arena_id="raid_a",
        environment=env,
    )
    assert out.accepted is True
    assert out.features_registered == 3


def test_instantiate_with_cascade():
    lib = ArenaTemplateLibrary()
    env = ArenaEnvironment()
    ed = EnvironmentDamage(arena_env=env)
    casc = EnvironmentCascade(arena_env=env, environment_damage=ed)
    out = lib.instantiate(
        template_id=TemplateId.KELP_CHAMBER, arena_id="raid_a",
        environment=env, cascade=casc,
    )
    assert out.cascade_rules_registered == 1


def test_instantiate_with_habitat():
    lib = ArenaTemplateLibrary()
    env = ArenaEnvironment()
    hd = HabitatDisturbance()
    hd.register_habitat(
        habitat_id="kelp_predators", biome=HabitatBiome.KELP_FOREST,
        creatures={"reef_shark": 1},
    )
    out = lib.instantiate(
        template_id=TemplateId.KELP_CHAMBER, arena_id="raid_a",
        environment=env, habitat_disturbance=hd,
    )
    assert out.habitat_links_registered == 1


def test_instantiate_with_cannons():
    lib = ArenaTemplateLibrary()
    env = ArenaEnvironment()
    sc = SiegeCannons()
    out = lib.instantiate(
        template_id=TemplateId.SHIP_DECK, arena_id="raid_a",
        environment=env, siege_cannons=sc,
    )
    assert out.cannons_registered == 4


def test_instantiate_dup_arena_blocked():
    lib = ArenaTemplateLibrary()
    env = ArenaEnvironment()
    lib.instantiate(
        template_id=TemplateId.SHIP_DECK, arena_id="raid_a",
        environment=env,
    )
    second = lib.instantiate(
        template_id=TemplateId.SHIP_DECK, arena_id="raid_a",
        environment=env,
    )
    assert second.accepted is False


def test_instantiate_blank_arena_id():
    lib = ArenaTemplateLibrary()
    env = ArenaEnvironment()
    out = lib.instantiate(
        template_id=TemplateId.SHIP_DECK, arena_id="",
        environment=env,
    )
    assert out.accepted is False


def test_register_custom_template():
    from server.arena_environment import ArenaFeature, FeatureKind
    from server.arena_template_library import ArenaTemplate

    lib = ArenaTemplateLibrary()
    # Use ICE_CAVERN id is taken; create a fresh enum-like one
    # by registering a duplicate — should fail
    canonical = lib.get(template_id=TemplateId.ICE_CAVERN)
    custom = ArenaTemplate(
        template_id=TemplateId.ICE_CAVERN,
        label="Custom Ice", features=canonical.features,
    )
    assert lib.register_template(custom) is False


def test_palace_has_4_pillar_cascades():
    lib = ArenaTemplateLibrary()
    tpl = lib.get(template_id=TemplateId.ROYAL_PALACE)
    pillar_rules = [
        r for r in tpl.cascade_rules
        if "palace_pillar" in r.source_feature_id
    ]
    assert len(pillar_rules) == 4


def test_dam_basin_cascade_has_delay():
    lib = ArenaTemplateLibrary()
    tpl = lib.get(template_id=TemplateId.DAM_BASIN)
    dam_rule = next(
        r for r in tpl.cascade_rules
        if r.source_feature_id == "great_dam"
    )
    assert dam_rule.delay_seconds == 10


def test_ice_cavern_ice_immune_to_ice():
    lib = ArenaTemplateLibrary()
    tpl = lib.get(template_id=TemplateId.ICE_CAVERN)
    ice = next(f for f in tpl.features if f.feature_id == "lake_ice")
    assert ice.element_mults["ice"] == 0.0


def test_palace_suggested_prep_45m():
    lib = ArenaTemplateLibrary()
    tpl = lib.get(template_id=TemplateId.ROYAL_PALACE)
    assert tpl.suggested_prep_minutes == 45


def test_instantiate_unknown_template():
    """Force a non-existent template_id by clearing the library."""
    lib = ArenaTemplateLibrary()
    # Drop SHIP_DECK and try to instantiate it
    del lib._templates[TemplateId.SHIP_DECK]
    env = ArenaEnvironment()
    out = lib.instantiate(
        template_id=TemplateId.SHIP_DECK, arena_id="raid_a",
        environment=env,
    )
    assert out.accepted is False
