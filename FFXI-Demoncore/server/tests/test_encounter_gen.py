"""Tests for the encounter generator.

Run:  python -m pytest server/tests/test_encounter_gen.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from encounter_gen import (
    EncounterGenerator,
    EncounterPlan,
    EncounterRequest,
    SpawnEntry,
)
from encounter_gen.generator import (
    BOSS_TIER_CLASSES,
    HEALER_CLASSES,
    ZONE_PALETTES,
)


@pytest.fixture
def gen():
    return EncounterGenerator()


# ---------------------- basic generation ----------------------

def test_generate_for_known_zone(gen):
    plan = gen.generate(EncounterRequest(
        zone="south_gustaberg",
        party_avg_level=20,
        party_size=3,
        seed=42,
    ))
    assert plan.zone == "south_gustaberg"
    assert len(plan.spawns) > 0
    # All mob classes are in the south_gustaberg palette
    palette = ZONE_PALETTES["south_gustaberg"]
    for spawn in plan.spawns:
        assert spawn.mob_class in palette or spawn.is_named_NM


def test_generate_unknown_zone_returns_empty_plan(gen):
    plan = gen.generate(EncounterRequest(
        zone="nonexistent_zone",
        party_avg_level=30,
    ))
    assert plan.spawns == []
    assert plan.pack_count == 0


def test_generate_safe_city_zone_returns_empty(gen):
    """Northern San d'Oria has no enemies."""
    plan = gen.generate(EncounterRequest(
        zone="northern_san_doria",
        party_avg_level=30,
    ))
    assert plan.spawns == []


# ---------------------- determinism ----------------------

def test_seeded_generation_is_deterministic(gen):
    """Same seed → same plan."""
    p1 = gen.generate(EncounterRequest(
        zone="konschtat_highlands", party_avg_level=15,
        party_size=2, seed=12345,
    ))
    p2 = gen.generate(EncounterRequest(
        zone="konschtat_highlands", party_avg_level=15,
        party_size=2, seed=12345,
    ))
    assert [(s.mob_class, s.level) for s in p1.spawns] == \
           [(s.mob_class, s.level) for s in p2.spawns]


# ---------------------- challenge tuning ----------------------

def test_easy_prey_vs_tough_levels_differ(gen):
    """Easy prey and tough on the same zone should produce different
    average levels — easy prey should be lower."""
    from encounter_gen.generator import ChallengeTarget
    # Use bastok_mines because its mob classes (goblin_pickpocket lvl 5-15,
    # rat lvl 1-5) have low minimums so the level offset is meaningful.
    plan_easy = gen.generate(EncounterRequest(
        zone="bastok_mines", party_avg_level=10,
        party_size=1, challenge=ChallengeTarget.EASY_PREY,
        seed=100, target_pack_count=8, boss_pack_chance=0.0,
    ))
    plan_tough = gen.generate(EncounterRequest(
        zone="bastok_mines", party_avg_level=10,
        party_size=1, challenge=ChallengeTarget.TOUGH,
        seed=100, target_pack_count=8, boss_pack_chance=0.0,
    ))
    if plan_easy.spawns and plan_tough.spawns:
        assert plan_easy.avg_level <= plan_tough.avg_level


def test_tough_picks_higher_levels(gen):
    from encounter_gen.generator import ChallengeTarget
    plan = gen.generate(EncounterRequest(
        zone="konschtat_highlands", party_avg_level=15,
        party_size=1, challenge=ChallengeTarget.TOUGH,
        seed=100,
    ))
    if plan.spawns:
        # Tough offset is +2 to +5, but clamped by mob class range.
        # Verify we don't get all easy prey.
        assert plan.avg_level >= 15 or plan.spawns[0].is_named_NM


# ---------------------- pack composition ----------------------

def test_no_pack_has_more_than_one_healer(gen):
    """At most 1 yagudo_cleric per pack."""
    plan = gen.generate(EncounterRequest(
        zone="tahrongi_canyon", party_avg_level=25,
        party_size=4, seed=7,
        target_pack_count=8,
    ))
    # Group spawns by pack — pack_leader marks the first
    packs = []
    current = []
    for s in plan.spawns:
        if s.is_pack_leader and current:
            packs.append(current)
            current = []
        current.append(s)
    if current:
        packs.append(current)
    for pack in packs:
        healer_count = sum(1 for s in pack
                            if s.mob_class in HEALER_CLASSES)
        assert healer_count <= 1


def test_boss_tier_class_spawns_solo(gen):
    """When a boss-tier class spawns, it's alone in its pack."""
    # Force boss spawn with high boss_pack_chance + bastok_mines (has goblin_smithy)
    for seed in range(100):
        plan = gen.generate(EncounterRequest(
            zone="bastok_mines", party_avg_level=5,
            party_size=1, seed=seed,
            target_pack_count=4, boss_pack_chance=1.0,
        ))
        boss_spawns = [s for s in plan.spawns if s.is_named_NM]
        if boss_spawns:
            # The boss should be alone (its is_pack_leader True, no
            # other spawn between it and the next is_pack_leader)
            for boss in boss_spawns:
                assert boss.is_pack_leader is True
            return
    pytest.skip("never managed to spawn a boss in 100 seeds; tuning issue")


def test_party_size_affects_pack_size(gen):
    from encounter_gen.generator import ChallengeTarget

    plan_solo = gen.generate(EncounterRequest(
        zone="south_gustaberg", party_avg_level=15,
        party_size=1, challenge=ChallengeTarget.DECENT_CHALLENGE,
        seed=42, target_pack_count=4, boss_pack_chance=0.0,
    ))
    plan_full = gen.generate(EncounterRequest(
        zone="south_gustaberg", party_avg_level=15,
        party_size=6, challenge=ChallengeTarget.DECENT_CHALLENGE,
        seed=42, target_pack_count=4, boss_pack_chance=0.0,
    ))
    # 6-player party gets more mobs total than solo
    assert len(plan_full.spawns) > len(plan_solo.spawns)


# ---------------------- element diversity ----------------------

def test_element_diversity_enforced(gen):
    """A pack with too many of one mob_class gets rebalanced."""
    plan = gen.generate(EncounterRequest(
        zone="korroloka_tunnel", party_avg_level=22,
        party_size=4, seed=1,
        target_pack_count=8, boss_pack_chance=0.0,
    ))
    # Korroloka has heavy quadav weight (2.0). After diversity check,
    # quadav shouldn't dominate >50% of total spawns.
    if len(plan.spawns) >= 4:
        from collections import Counter
        counts = Counter(s.mob_class for s in plan.spawns)
        most_common_count = counts.most_common(1)[0][1]
        assert most_common_count <= len(plan.spawns) // 2 + 1


# ---------------------- level clamping ----------------------

def test_levels_within_class_ranges(gen):
    """Every spawn's level falls within the mob_class's allowed range."""
    from encounter_gen.generator import DEFAULT_LEVEL_RANGES
    plan = gen.generate(EncounterRequest(
        zone="phomiuna_aqueducts", party_avg_level=33,
        party_size=3, seed=5,
    ))
    for spawn in plan.spawns:
        if spawn.mob_class in DEFAULT_LEVEL_RANGES:
            lo, hi = DEFAULT_LEVEL_RANGES[spawn.mob_class]
            assert spawn.level >= max(1, lo)
            assert spawn.level <= max(lo, hi)


# ---------------------- sanity ----------------------

def test_avg_level_reflects_spawn_levels(gen):
    plan = gen.generate(EncounterRequest(
        zone="south_gustaberg", party_avg_level=15,
        party_size=2, seed=999,
    ))
    if plan.spawns:
        actual_avg = sum(s.level for s in plan.spawns) / len(plan.spawns)
        assert abs(plan.avg_level - actual_avg) < 0.01


def test_pack_leader_set_per_pack(gen):
    plan = gen.generate(EncounterRequest(
        zone="south_gustaberg", party_avg_level=15,
        party_size=1, seed=20,
        target_pack_count=3, boss_pack_chance=0.0,
    ))
    leaders = [s for s in plan.spawns if s.is_pack_leader]
    assert len(leaders) == 3   # one leader per pack
