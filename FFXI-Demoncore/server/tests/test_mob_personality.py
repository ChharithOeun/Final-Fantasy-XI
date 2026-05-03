"""Tests for per-mob personality vectors."""
from __future__ import annotations

import random

import pytest

from server.mob_personality import (
    DEFAULT_ARCHETYPES,
    PersonalityRegistry,
    PersonalityTrait,
    PersonalityVector,
    describe,
    roll_personality,
)


def test_default_vector_is_neutral():
    v = PersonalityVector()
    for trait in PersonalityTrait:
        assert v.get(trait) == 0.5


def test_vector_rejects_out_of_range():
    with pytest.raises(ValueError):
        PersonalityVector(aggression=1.5)
    with pytest.raises(ValueError):
        PersonalityVector(courage=-0.1)


def test_vector_get_returns_value():
    v = PersonalityVector(aggression=0.9, cunning=0.1)
    assert v.get(PersonalityTrait.AGGRESSION) == 0.9
    assert v.get(PersonalityTrait.CUNNING) == 0.1


def test_archetypes_cover_major_families():
    expected = {
        "yagudo_initiate", "yagudo_acolyte", "orc_warlord",
        "goblin_smithy", "skeleton_warrior", "tonberry_pilgrim",
        "sahagin_swordsman", "bee_soldier", "psychomancer",
    }
    assert expected.issubset(DEFAULT_ARCHETYPES.keys())


def test_roll_personality_deterministic_with_seeded_rng():
    arch = DEFAULT_ARCHETYPES["orc_warlord"]
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    v1 = roll_personality(archetype=arch, rng=rng_a)
    v2 = roll_personality(archetype=arch, rng=rng_b)
    assert v1 == v2


def test_roll_personality_clamps_to_unit_range():
    """Even with extreme jitter, traits stay in [0, 1]."""
    from server.mob_personality import MobPersonalityArchetype
    arch = MobPersonalityArchetype(
        archetype_id="test", label="t",
        baseline=PersonalityVector(aggression=0.05),
        jitter=2.0,
    )
    rng = random.Random(0)
    v = roll_personality(archetype=arch, rng=rng)
    for trait in PersonalityTrait:
        val = v.get(trait)
        assert 0.0 <= val <= 1.0


def test_roll_personality_jitters_around_baseline():
    """100 rolls should give a distribution centered near baseline."""
    arch = DEFAULT_ARCHETYPES["yagudo_acolyte"]
    rng = random.Random(7)
    samples = [
        roll_personality(archetype=arch, rng=rng)
        for _ in range(100)
    ]
    avg_aggression = sum(s.aggression for s in samples) / 100
    # Baseline 0.65 +/- 0.15 jitter -> mean should land near 0.65
    assert 0.55 < avg_aggression < 0.75


def test_describe_berserker():
    v = PersonalityVector(
        aggression=0.95, courage=0.95, cunning=0.2,
    )
    tags = describe(v)
    assert "berserker" in tags
    assert "brawler" in tags


def test_describe_coward():
    v = PersonalityVector(courage=0.1, aggression=0.3)
    tags = describe(v)
    assert "coward" in tags


def test_describe_schemer_vs_traitor():
    schemer = PersonalityVector(
        cunning=0.9, aggression=0.4, loyalty=0.8,
    )
    traitor = PersonalityVector(
        cunning=0.85, loyalty=0.2, aggression=0.5,
    )
    assert "schemer" in describe(schemer)
    assert "traitor" in describe(traitor)


def test_describe_guardian():
    v = PersonalityVector(territoriality=0.9, loyalty=0.85)
    assert "guardian" in describe(v)


def test_describe_zealot():
    v = PersonalityVector(loyalty=0.95, courage=0.85)
    assert "zealot" in describe(v)


def test_describe_neutral_vector_no_tags():
    v = PersonalityVector()  # all 0.5
    tags = describe(v)
    assert tags == ()


def test_registry_assign_and_lookup():
    reg = PersonalityRegistry()
    v = PersonalityVector(aggression=0.8)
    reg.assign(mob_id="orc_42", vector=v)
    assert reg.vector_for("orc_42") == v
    assert reg.total() == 1


def test_registry_unknown_mob_returns_none():
    reg = PersonalityRegistry()
    assert reg.vector_for("ghost") is None


def test_registry_assign_from_archetype():
    reg = PersonalityRegistry()
    rng = random.Random(123)
    v = reg.assign_from_archetype(
        mob_id="orc_warlord_1", archetype_id="orc_warlord", rng=rng,
    )
    # Orc warlord baseline: aggression=0.85, jitter=0.15
    # So aggression should be in [0.7, 1.0]
    assert v.aggression >= 0.7
    assert v.aggression <= 1.0


def test_skeleton_low_jitter_uniformity():
    """Skeletons have jitter=0.05 — they're nearly identical."""
    arch = DEFAULT_ARCHETYPES["skeleton_warrior"]
    rng = random.Random(5)
    samples = [
        roll_personality(archetype=arch, rng=rng)
        for _ in range(50)
    ]
    aggressions = [s.aggression for s in samples]
    spread = max(aggressions) - min(aggressions)
    # spread bounded by 2 * jitter = 0.1
    assert spread <= 0.11


def test_full_lifecycle_two_mobs_feel_different():
    """Two same-class mobs rolled with the same archetype but
    different RNG seeds should have distinguishable vectors."""
    reg = PersonalityRegistry()
    reg.assign_from_archetype(
        mob_id="yagudo_a", archetype_id="yagudo_acolyte",
        rng=random.Random(100),
    )
    reg.assign_from_archetype(
        mob_id="yagudo_b", archetype_id="yagudo_acolyte",
        rng=random.Random(200),
    )
    va = reg.vector_for("yagudo_a")
    vb = reg.vector_for("yagudo_b")
    # At least one trait should differ
    differs = any(
        abs(va.get(t) - vb.get(t)) > 0.01
        for t in PersonalityTrait
    )
    assert differs
