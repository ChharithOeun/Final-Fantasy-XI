"""Tests for foley_library."""
from __future__ import annotations

import pytest

from server.foley_library import (
    FoleyEntry,
    FoleyKind,
    FoleyLibrary,
    Gait,
    Surface,
    populate_default_library,
)


# ---- enum coverage ----

def test_surface_count_at_least_seventeen():
    assert len(list(Surface)) >= 17


def test_gait_count_five_races():
    assert len(list(Gait)) == 5


def test_foley_kind_includes_footstep_and_sword_draw():
    names = {k.name for k in FoleyKind}
    assert "FOOTSTEP" in names
    assert "SWORD_DRAW" in names
    assert "ARMOR_PLATE_JINGLE" in names


def test_foley_kind_count_at_least_seventeen():
    assert len(list(FoleyKind)) >= 17


# ---- register ----

def test_register_simple_interaction():
    lib = FoleyLibrary()
    lib.register_foley(
        "uncork", FoleyKind.BOTTLE_UNCORK,
        sample_uris=("a.ogg",),
    )
    assert lib.entry_count() == 1


def test_register_footstep_requires_surface():
    lib = FoleyLibrary()
    with pytest.raises(ValueError):
        lib.register_foley(
            "f", FoleyKind.FOOTSTEP,
            sample_uris=("a.ogg",),
            gait=Gait.HUME_NORMAL,
        )


def test_register_footstep_requires_gait():
    lib = FoleyLibrary()
    with pytest.raises(ValueError):
        lib.register_foley(
            "f", FoleyKind.FOOTSTEP,
            sample_uris=("a.ogg",),
            surface=Surface.WOOD,
        )


def test_register_empty_id_raises():
    lib = FoleyLibrary()
    with pytest.raises(ValueError):
        lib.register_foley(
            "", FoleyKind.SWORD_DRAW, ("a.ogg",),
        )


def test_register_no_samples_raises():
    lib = FoleyLibrary()
    with pytest.raises(ValueError):
        lib.register_foley(
            "x", FoleyKind.SWORD_DRAW, sample_uris=(),
        )


def test_register_duplicate_raises():
    lib = FoleyLibrary()
    lib.register_foley(
        "x", FoleyKind.SWORD_DRAW, ("a.ogg",),
    )
    with pytest.raises(ValueError):
        lib.register_foley(
            "x", FoleyKind.SWORD_DRAW, ("b.ogg",),
        )


def test_get_entry_unknown_raises():
    lib = FoleyLibrary()
    with pytest.raises(KeyError):
        lib.get_entry("missing")


def test_get_entry_returns_frozen():
    import dataclasses
    lib = FoleyLibrary()
    lib.register_foley(
        "x", FoleyKind.SWORD_DRAW, ("a.ogg",),
    )
    e = lib.get_entry("x")
    assert isinstance(e, FoleyEntry)
    # frozen dataclass should reject mutation
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.foley_id = "y"  # type: ignore[misc]


# ---- pick_footstep ----

def test_pick_footstep_returns_sample():
    lib = FoleyLibrary()
    lib.register_foley(
        "f1", FoleyKind.FOOTSTEP,
        sample_uris=("a.ogg", "b.ogg"),
        surface=Surface.WOOD, gait=Gait.HUME_NORMAL,
    )
    s = lib.pick_footstep(Surface.WOOD, Gait.HUME_NORMAL)
    assert s in ("a.ogg", "b.ogg")


def test_pick_footstep_round_robins():
    lib = FoleyLibrary()
    lib.register_foley(
        "f1", FoleyKind.FOOTSTEP,
        sample_uris=("a.ogg", "b.ogg", "c.ogg"),
        surface=Surface.STONE_DRY, gait=Gait.GALKA_HEAVY,
    )
    samples = [
        lib.pick_footstep(Surface.STONE_DRY, Gait.GALKA_HEAVY)
        for _ in range(6)
    ]
    # Round-robin gives us each sample twice in 6 picks.
    assert samples.count("a.ogg") == 2
    assert samples.count("b.ogg") == 2
    assert samples.count("c.ogg") == 2


def test_pick_footstep_unknown_combo_raises():
    lib = FoleyLibrary()
    with pytest.raises(KeyError):
        lib.pick_footstep(Surface.MARBLE, Gait.MITHRA_PROWL)


def test_pick_footstep_different_surfaces_isolated():
    lib = FoleyLibrary()
    lib.register_foley(
        "f1", FoleyKind.FOOTSTEP,
        sample_uris=("wood_a.ogg",),
        surface=Surface.WOOD, gait=Gait.HUME_NORMAL,
    )
    lib.register_foley(
        "f2", FoleyKind.FOOTSTEP,
        sample_uris=("metal_a.ogg",),
        surface=Surface.METAL_GRATED, gait=Gait.HUME_NORMAL,
    )
    s1 = lib.pick_footstep(Surface.WOOD, Gait.HUME_NORMAL)
    s2 = lib.pick_footstep(
        Surface.METAL_GRATED, Gait.HUME_NORMAL,
    )
    assert s1 == "wood_a.ogg"
    assert s2 == "metal_a.ogg"


# ---- foley_for_action ----

def test_foley_for_action_sword_draw_no_costume():
    lib = FoleyLibrary()
    populate_default_library(lib)
    samples = lib.foley_for_action("sword_draw")
    assert len(samples) == 1


def test_foley_for_action_sword_draw_with_plate():
    lib = FoleyLibrary()
    populate_default_library(lib)
    samples = lib.foley_for_action("sword_draw", "plate")
    # primary + plate jingle overlay
    assert len(samples) == 2


def test_foley_for_action_axe_heft_with_plate():
    lib = FoleyLibrary()
    populate_default_library(lib)
    samples = lib.foley_for_action("axe_heft", "plate_armor")
    assert len(samples) == 2


def test_foley_for_action_axe_with_leather():
    lib = FoleyLibrary()
    populate_default_library(lib)
    samples = lib.foley_for_action("axe_heft", "leather")
    assert len(samples) == 2


def test_foley_for_action_axe_with_cloth():
    lib = FoleyLibrary()
    populate_default_library(lib)
    samples = lib.foley_for_action("axe_heft", "cloth")
    assert len(samples) == 2


def test_foley_for_action_chest_open_no_overlay():
    lib = FoleyLibrary()
    populate_default_library(lib)
    samples = lib.foley_for_action("open_chest", "plate")
    # chest_open is not a body-movement action; plate
    # overlay should NOT apply.
    assert len(samples) == 1


def test_foley_for_action_unknown_raises():
    lib = FoleyLibrary()
    populate_default_library(lib)
    with pytest.raises(KeyError):
        lib.foley_for_action("levitate")


def test_foley_for_action_unknown_costume_no_overlay():
    lib = FoleyLibrary()
    populate_default_library(lib)
    samples = lib.foley_for_action("sword_draw", "fur_pajamas")
    assert len(samples) == 1


# ---- foleys_for_surface ----

def test_foleys_for_surface_returns_all_gaits():
    lib = FoleyLibrary()
    populate_default_library(lib)
    foleys = lib.foleys_for_surface(Surface.WOOD)
    # 5 gaits per surface
    assert len(foleys) == 5


def test_foleys_for_surface_empty():
    lib = FoleyLibrary()
    foleys = lib.foleys_for_surface(Surface.SAND)
    assert foleys == ()


# ---- gaits_for_race ----

def test_gaits_for_race_galka():
    lib = FoleyLibrary()
    assert lib.gaits_for_race("galka") == (Gait.GALKA_HEAVY,)


def test_gaits_for_race_taru_alias():
    lib = FoleyLibrary()
    assert lib.gaits_for_race("taru") == (Gait.TARU_LIGHT,)


def test_gaits_for_race_tarutaru():
    lib = FoleyLibrary()
    assert lib.gaits_for_race("tarutaru") == (Gait.TARU_LIGHT,)


def test_gaits_for_race_mithra():
    lib = FoleyLibrary()
    assert lib.gaits_for_race("Mithra") == (Gait.MITHRA_PROWL,)


def test_gaits_for_race_elvaan():
    lib = FoleyLibrary()
    assert lib.gaits_for_race("elvaan") == (
        Gait.ELVAAN_LONG_STRIDE,
    )


def test_gaits_for_race_unknown_returns_empty():
    lib = FoleyLibrary()
    assert lib.gaits_for_race("dragon") == ()


# ---- all_kinds ----

def test_all_kinds_is_sorted_and_unique():
    lib = FoleyLibrary()
    populate_default_library(lib)
    kinds = lib.all_kinds()
    # sorted by enum value
    assert list(kinds) == sorted(kinds, key=lambda k: k.value)
    # unique
    assert len(set(kinds)) == len(kinds)


# ---- default catalog ----

def test_default_library_count_is_correct():
    lib = FoleyLibrary()
    n = populate_default_library(lib)
    # 17 surfaces * 5 gaits = 85 footstep entries +
    # 16 interaction kinds = 101.
    assert n == 17 * 5 + 16


def test_default_library_has_all_surface_gait_combos():
    lib = FoleyLibrary()
    populate_default_library(lib)
    # Sanity: pick a footstep on every surface for one gait.
    for surface in Surface:
        s = lib.pick_footstep(surface, Gait.HUME_NORMAL)
        assert s.endswith(".ogg")


def test_default_library_galka_heavy_has_samples():
    lib = FoleyLibrary()
    populate_default_library(lib)
    s = lib.pick_footstep(Surface.SNOW, Gait.GALKA_HEAVY)
    assert "snow" in s
    assert "galka_heavy" in s


def test_default_library_taru_light_marsh():
    lib = FoleyLibrary()
    populate_default_library(lib)
    s = lib.pick_footstep(Surface.MARSH_SQUELCH, Gait.TARU_LIGHT)
    assert "marsh" in s


def test_default_library_inventory_open_one_sample():
    lib = FoleyLibrary()
    populate_default_library(lib)
    e = lib.get_entry("inventory_open")
    assert len(e.sample_uris) == 1


def test_default_library_eating_crunch_three_samples():
    lib = FoleyLibrary()
    populate_default_library(lib)
    e = lib.get_entry("eating_crunch")
    assert len(e.sample_uris) == 3


def test_default_library_each_footstep_has_4_variants():
    lib = FoleyLibrary()
    populate_default_library(lib)
    for surface in Surface:
        for gait in Gait:
            e = lib.get_entry(
                f"foot_{surface.value}_{gait.value}",
            )
            assert len(e.sample_uris) == 4
