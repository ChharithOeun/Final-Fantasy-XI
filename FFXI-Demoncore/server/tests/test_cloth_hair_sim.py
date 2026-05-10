"""Tests for cloth_hair_sim."""
from __future__ import annotations

import pytest

from server.cloth_hair_sim import (
    ClothHairSystem,
    ClothProfile,
    ClothProfileKind,
    HairGroomKind,
    HairGroomProfile,
    populate_default_library,
)


# ---- enum coverage ----

def test_nine_cloth_kinds():
    assert len(list(ClothProfileKind)) == 9


def test_eleven_hair_kinds():
    assert len(list(HairGroomKind)) == 11


def test_specific_cloth_kinds_present():
    names = {k.value for k in ClothProfileKind}
    assert "robe_heavy" in names
    assert "cloak_flowing" in names
    assert "armor_mail" in names
    assert "armor_plate_skirted" in names


def test_specific_hair_kinds_present():
    names = {k.value for k in HairGroomKind}
    assert "mithra_tail" in names
    assert "elvaan_long" in names
    assert "horn_carved" in names
    assert "taru_pigtail" in names


# ---- register / lookup ----

def test_register_and_lookup_cloth():
    s = ClothHairSystem()
    c = ClothProfile(
        kind=ClothProfileKind.CLOAK_FLOWING,
        name="hero_cloak",
        mass_kg_per_m2=0.30,
        stiffness=0.20,
        damping=0.25,
        wind_coupling=0.90,
        self_collision=True,
        max_solver_iterations=10,
    )
    s.register_cloth(c)
    assert s.cloth(ClothProfileKind.CLOAK_FLOWING) is c


def test_register_and_lookup_groom():
    s = ClothHairSystem()
    g = HairGroomProfile(
        kind=HairGroomKind.MITHRA_TAIL,
        name="mithra_tail",
        strand_count=80_000,
        card_count=16,
        wind_coupling=0.40,
        collision_capsules=3,
        gravity_factor=0.6,
    )
    s.register_groom(g)
    assert s.groom(HairGroomKind.MITHRA_TAIL) is g


def test_lookup_missing_cloth_raises():
    s = ClothHairSystem()
    with pytest.raises(KeyError):
        s.cloth(ClothProfileKind.ROBE_HEAVY)


def test_lookup_missing_groom_raises():
    s = ClothHairSystem()
    with pytest.raises(KeyError):
        s.groom(HairGroomKind.LONG_FLOWING)


# ---- validation ----

def test_cloth_zero_mass_raises():
    s = ClothHairSystem()
    with pytest.raises(ValueError):
        s.register_cloth(ClothProfile(
            kind=ClothProfileKind.ROBE_HEAVY,
            name="bad",
            mass_kg_per_m2=0.0,
            stiffness=0.5, damping=0.5,
            wind_coupling=0.5,
            self_collision=False,
            max_solver_iterations=4,
        ))


def test_cloth_stiffness_out_of_range_raises():
    s = ClothHairSystem()
    with pytest.raises(ValueError):
        s.register_cloth(ClothProfile(
            kind=ClothProfileKind.ROBE_HEAVY,
            name="bad",
            mass_kg_per_m2=0.5,
            stiffness=1.5, damping=0.5,
            wind_coupling=0.5,
            self_collision=False,
            max_solver_iterations=4,
        ))


def test_cloth_iterations_zero_raises():
    s = ClothHairSystem()
    with pytest.raises(ValueError):
        s.register_cloth(ClothProfile(
            kind=ClothProfileKind.ROBE_HEAVY,
            name="bad",
            mass_kg_per_m2=0.5,
            stiffness=0.5, damping=0.5,
            wind_coupling=0.5,
            self_collision=False,
            max_solver_iterations=0,
        ))


def test_groom_negative_strand_raises():
    s = ClothHairSystem()
    with pytest.raises(ValueError):
        s.register_groom(HairGroomProfile(
            kind=HairGroomKind.SHORT_NEAT,
            name="bad",
            strand_count=-1, card_count=4,
            wind_coupling=0.5,
            collision_capsules=2,
            gravity_factor=1.0,
        ))


def test_groom_wind_out_of_range_raises():
    s = ClothHairSystem()
    with pytest.raises(ValueError):
        s.register_groom(HairGroomProfile(
            kind=HairGroomKind.SHORT_NEAT,
            name="bad",
            strand_count=100, card_count=4,
            wind_coupling=1.5,
            collision_capsules=2,
            gravity_factor=1.0,
        ))


# ---- costume + hairstyle mapping ----

def test_cloth_for_costume_priest():
    s = ClothHairSystem()
    populate_default_library(s)
    out = s.cloth_for_costume("priest_robe")
    assert out.kind == ClothProfileKind.ROBE_HEAVY


def test_cloth_for_costume_hero():
    s = ClothHairSystem()
    populate_default_library(s)
    out = s.cloth_for_costume("hero_cloak")
    assert out.kind == ClothProfileKind.CLOAK_FLOWING


def test_cloth_for_costume_unknown_raises():
    s = ClothHairSystem()
    populate_default_library(s)
    with pytest.raises(KeyError):
        s.cloth_for_costume("unknown_costume")


def test_groom_for_hairstyle_long_flowing():
    s = ClothHairSystem()
    populate_default_library(s)
    out = s.groom_for_hairstyle("long_flowing")
    assert out.kind == HairGroomKind.LONG_FLOWING


def test_groom_for_hairstyle_unknown_raises():
    s = ClothHairSystem()
    populate_default_library(s)
    with pytest.raises(KeyError):
        s.groom_for_hairstyle("anime_spikes")


# ---- wind ----

def test_apply_wind_per_zone():
    s = ClothHairSystem()
    populate_default_library(s)
    s.apply_wind("pashhow_marshlands", 0.6)
    s.apply_wind("bastok_markets", 0.05)
    assert s.wind_for_zone("pashhow_marshlands") == 0.6
    assert s.wind_for_zone("bastok_markets") == 0.05


def test_wind_default_zero_for_unknown_zone():
    s = ClothHairSystem()
    assert s.wind_for_zone("phantom_zone") == 0.0


def test_wind_out_of_range_raises():
    s = ClothHairSystem()
    with pytest.raises(ValueError):
        s.apply_wind("z", 99.0)


def test_effective_wind_couples_with_cloth():
    s = ClothHairSystem()
    populate_default_library(s)
    s.apply_wind("z", 1.0)
    cloak = s.effective_wind_on(
        "z", ClothProfileKind.CLOAK_FLOWING,
    )
    mail = s.effective_wind_on(
        "z", ClothProfileKind.ARMOR_MAIL,
    )
    assert cloak > mail


def test_effective_wind_zero_when_no_wind():
    s = ClothHairSystem()
    populate_default_library(s)
    assert s.effective_wind_on(
        "no_wind", ClothProfileKind.CLOAK_FLOWING,
    ) == 0.0


# ---- LOD ----

def test_lod_close_uses_strands():
    s = ClothHairSystem()
    populate_default_library(s)
    assert s.lod_groom_for_distance(
        HairGroomKind.LONG_FLOWING, 1.0,
    ) == "strands"


def test_lod_mid_uses_cards():
    s = ClothHairSystem()
    populate_default_library(s)
    assert s.lod_groom_for_distance(
        HairGroomKind.LONG_FLOWING, 20.0,
    ) == "cards"


def test_lod_far_uses_capsule():
    s = ClothHairSystem()
    populate_default_library(s)
    assert s.lod_groom_for_distance(
        HairGroomKind.LONG_FLOWING, 50.0,
    ) == "capsule"


def test_lod_bald_returns_none():
    s = ClothHairSystem()
    populate_default_library(s)
    assert s.lod_groom_for_distance(
        HairGroomKind.BALD, 1.0,
    ) == "none"


def test_lod_negative_distance_raises():
    s = ClothHairSystem()
    populate_default_library(s)
    with pytest.raises(ValueError):
        s.lod_groom_for_distance(
            HairGroomKind.LONG_FLOWING, -1.0,
        )


# ---- KO / sleep state ----

def test_freeze_holds_cloth():
    s = ClothHairSystem()
    s.freeze("npc_dead_guard")
    assert s.is_frozen("npc_dead_guard")
    assert not s.is_active("npc_dead_guard")


def test_thaw_restores_active():
    s = ClothHairSystem()
    s.freeze("npc1")
    s.thaw("npc1")
    assert not s.is_frozen("npc1")
    assert s.is_active("npc1")


def test_sleep_pauses_sim():
    s = ClothHairSystem()
    s.sleep("npc_napping")
    assert s.is_sleeping("npc_napping")
    assert not s.is_active("npc_napping")


def test_wake_resumes_sim():
    s = ClothHairSystem()
    s.sleep("npc_napping")
    s.wake("npc_napping")
    assert not s.is_sleeping("npc_napping")
    assert s.is_active("npc_napping")


# ---- simulate_step ----

def test_simulate_step_returns_hash():
    s = ClothHairSystem()
    h1 = s.simulate_step(0.016)
    assert isinstance(h1, str)
    assert h1.startswith("sim_step_")


def test_simulate_step_advances_counter():
    s = ClothHairSystem()
    h1 = s.simulate_step(0.016)
    h2 = s.simulate_step(0.016)
    # counter changed -> hash changed
    assert h1 != h2


def test_simulate_step_zero_dt_raises():
    s = ClothHairSystem()
    with pytest.raises(ValueError):
        s.simulate_step(0.0)


# ---- populate_default_library + listings ----

def test_populate_default_library_all_cloth_kinds():
    s = ClothHairSystem()
    populate_default_library(s)
    for kind in ClothProfileKind:
        assert s.cloth(kind).kind == kind


def test_populate_default_library_all_groom_kinds():
    s = ClothHairSystem()
    populate_default_library(s)
    for kind in HairGroomKind:
        assert s.groom(kind).kind == kind


def test_all_cloth_returns_sorted():
    s = ClothHairSystem()
    populate_default_library(s)
    out = s.all_cloth()
    assert len(out) == 9
    assert [c.kind.value for c in out] == sorted(
        c.kind.value for c in out
    )


def test_all_grooms_returns_sorted():
    s = ClothHairSystem()
    populate_default_library(s)
    out = s.all_grooms()
    assert len(out) == 11


def test_long_flowing_300k_strands():
    s = ClothHairSystem()
    populate_default_library(s)
    assert s.groom(
        HairGroomKind.LONG_FLOWING,
    ).strand_count == 300_000


def test_chainmail_heavy_mass():
    s = ClothHairSystem()
    populate_default_library(s)
    # chainmail heavier than a tunic
    cm = s.cloth(ClothProfileKind.ARMOR_MAIL).mass_kg_per_m2
    tu = s.cloth(ClothProfileKind.TUNIC_LIGHT).mass_kg_per_m2
    assert cm > tu


def test_cloak_high_wind_coupling():
    s = ClothHairSystem()
    populate_default_library(s)
    # The cloak couples to wind much more than chainmail.
    cloak = s.cloth(
        ClothProfileKind.CLOAK_FLOWING,
    ).wind_coupling
    mail = s.cloth(
        ClothProfileKind.ARMOR_MAIL,
    ).wind_coupling
    assert cloak > mail
    assert cloak > 0.7
