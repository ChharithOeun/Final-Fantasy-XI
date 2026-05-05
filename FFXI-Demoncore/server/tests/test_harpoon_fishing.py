"""Tests for harpoon fishing."""
from __future__ import annotations

from server.harpoon_fishing import (
    HarpoonFishing,
    SpearKind,
    Stage,
)


def test_total_biomes():
    h = HarpoonFishing()
    assert h.total_biomes() == 4


def test_biome_catch_table_known():
    h = HarpoonFishing()
    table = h.biome_catch_table(biome_id="abyss_trench")
    species = {entry[0] for entry in table}
    assert "abyssal_anglerfish" in species
    assert "trench_lurker" in species


def test_biome_catch_table_unknown_empty():
    h = HarpoonFishing()
    assert h.biome_catch_table(biome_id="ghost") == ()


def test_start_cast_happy():
    h = HarpoonFishing()
    ok = h.start_cast(
        player_id="p",
        biome_id="kelp_labyrinth",
        spear_kind=SpearKind.LONG_HARPOON,
        now_seconds=0,
    )
    assert ok is True
    sess = h.session_for(player_id="p")
    assert sess.stage == Stage.TRACK


def test_start_cast_unknown_biome():
    h = HarpoonFishing()
    ok = h.start_cast(
        player_id="p",
        biome_id="ghost",
        spear_kind=SpearKind.LONG_HARPOON,
        now_seconds=0,
    )
    assert ok is False


def test_start_cast_blank_player():
    h = HarpoonFishing()
    ok = h.start_cast(
        player_id="",
        biome_id="kelp_labyrinth",
        spear_kind=SpearKind.LONG_HARPOON,
        now_seconds=0,
    )
    assert ok is False


def test_thrust_resolves_success():
    h = HarpoonFishing()
    h.start_cast(
        player_id="p",
        biome_id="tideplate_shallows",
        spear_kind=SpearKind.GAFFEHOOK,  # quality 20
        now_seconds=0,
    )
    # blueglass_minnow evasion 5; gaffehook +20; need aim 10+ to clear 25
    r = h.resolve_thrust(
        player_id="p",
        target_species="blueglass_minnow",
        player_aim_skill=10,
        target_evasion=5,
        is_hq_roll=False,
    )
    assert r.accepted is True
    assert r.species == "blueglass_minnow"
    assert r.weight == 2
    assert r.is_hq is False


def test_thrust_hq_inflates_weight():
    h = HarpoonFishing()
    h.start_cast(
        player_id="p",
        biome_id="kelp_labyrinth",
        spear_kind=SpearKind.GAFFEHOOK,
        now_seconds=0,
    )
    r = h.resolve_thrust(
        player_id="p",
        target_species="kelp_eel",
        player_aim_skill=30,
        target_evasion=18,
        is_hq_roll=True,
    )
    # base 18 * 1.5 = 27
    assert r.weight == 27
    assert r.is_hq is True


def test_thrust_fish_escapes():
    h = HarpoonFishing()
    h.start_cast(
        player_id="p",
        biome_id="abyss_trench",
        spear_kind=SpearKind.SHORT_SPEAR,  # quality 5
        now_seconds=0,
    )
    # trench_lurker evasion 55; aim 10 + 5 - 55 = -40 -> escape
    r = h.resolve_thrust(
        player_id="p",
        target_species="trench_lurker",
        player_aim_skill=10,
        target_evasion=55,
        is_hq_roll=False,
    )
    assert r.accepted is True
    assert r.weight == 0
    assert r.reason == "escaped"


def test_thrust_unknown_session():
    h = HarpoonFishing()
    r = h.resolve_thrust(
        player_id="ghost",
        target_species="any",
        player_aim_skill=10,
        target_evasion=10,
        is_hq_roll=False,
    )
    assert r.accepted is False
    assert r.reason == "no session"


def test_thrust_species_not_in_biome():
    h = HarpoonFishing()
    h.start_cast(
        player_id="p",
        biome_id="tideplate_shallows",
        spear_kind=SpearKind.LONG_HARPOON,
        now_seconds=0,
    )
    r = h.resolve_thrust(
        player_id="p",
        target_species="trench_lurker",
        player_aim_skill=100,
        target_evasion=10,
        is_hq_roll=False,
    )
    assert r.accepted is False
    assert r.reason == "species not in biome"


def test_thrust_invalid_metrics():
    h = HarpoonFishing()
    h.start_cast(
        player_id="p",
        biome_id="tideplate_shallows",
        spear_kind=SpearKind.LONG_HARPOON,
        now_seconds=0,
    )
    r = h.resolve_thrust(
        player_id="p",
        target_species="blueglass_minnow",
        player_aim_skill=-1,
        target_evasion=10,
        is_hq_roll=False,
    )
    assert r.accepted is False


def test_session_resets_on_escape():
    h = HarpoonFishing()
    h.start_cast(
        player_id="p",
        biome_id="abyss_trench",
        spear_kind=SpearKind.SHORT_SPEAR,
        now_seconds=0,
    )
    h.resolve_thrust(
        player_id="p",
        target_species="trench_lurker",
        player_aim_skill=0,
        target_evasion=99,
        is_hq_roll=False,
    )
    sess = h.session_for(player_id="p")
    assert sess.stage == Stage.IDLE


def test_session_in_reclaim_after_success():
    h = HarpoonFishing()
    h.start_cast(
        player_id="p",
        biome_id="tideplate_shallows",
        spear_kind=SpearKind.GAFFEHOOK,
        now_seconds=0,
    )
    h.resolve_thrust(
        player_id="p",
        target_species="blueglass_minnow",
        player_aim_skill=20,
        target_evasion=5,
        is_hq_roll=False,
    )
    sess = h.session_for(player_id="p")
    assert sess.stage == Stage.RECLAIM
