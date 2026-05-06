"""Tests for deep weapons."""
from __future__ import annotations

from server.deep_weapons import (
    ForgeStage,
    DeepWeapons,
)


def _complete_first_four(m: DeepWeapons, player_id: str):
    for stage in [
        ForgeStage.BLUEPRINT_RECOVERY,
        ForgeStage.HUNDRED_WRECKS,
        ForgeStage.DROWNED_KING_KILL,
        ForgeStage.MASTER_SYNTHESIS,
    ]:
        m.complete_stage(
            player_id=player_id, stage=stage,
            trait_name=stage.name,
            trait_description=stage.name + " trait",
            now_seconds=stage.value * 1000,
        )


def test_start_forge_happy():
    m = DeepWeapons()
    assert m.start_forge(
        player_id="p1", weapon_kind="lance", now_seconds=0,
    ) is True


def test_start_forge_blank_player():
    m = DeepWeapons()
    assert m.start_forge(
        player_id="", weapon_kind="lance", now_seconds=0,
    ) is False


def test_start_forge_blank_kind():
    m = DeepWeapons()
    assert m.start_forge(
        player_id="p1", weapon_kind="", now_seconds=0,
    ) is False


def test_one_deep_per_player():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    assert m.start_forge(
        player_id="p1", weapon_kind="staff", now_seconds=10,
    ) is False


def test_complete_stage_order_required():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    # try to skip to stage 3
    ok = m.complete_stage(
        player_id="p1", stage=ForgeStage.DROWNED_KING_KILL,
        trait_name="X", trait_description="Y",
        now_seconds=100,
    )
    assert ok is False


def test_complete_stage_in_order():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    ok = m.complete_stage(
        player_id="p1", stage=ForgeStage.BLUEPRINT_RECOVERY,
        trait_name="X", trait_description="Y",
        now_seconds=100,
    )
    assert ok is True


def test_complete_stage_unknown_player():
    m = DeepWeapons()
    ok = m.complete_stage(
        player_id="ghost", stage=ForgeStage.BLUEPRINT_RECOVERY,
        trait_name="X", trait_description="Y", now_seconds=100,
    )
    assert ok is False


def test_complete_stage_inscription_blocked():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    ok = m.complete_stage(
        player_id="p1", stage=ForgeStage.NAME_INSCRIPTION,
        trait_name="X", trait_description="Y", now_seconds=100,
    )
    assert ok is False


def test_inscribe_name_after_four_stages():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    _complete_first_four(m, "p1")
    ok = m.inscribe_name(
        player_id="p1", rune_name="Tide", now_seconds=5000,
    )
    assert ok is True


def test_inscribe_name_too_early():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    m.complete_stage(
        player_id="p1", stage=ForgeStage.BLUEPRINT_RECOVERY,
        trait_name="X", trait_description="Y", now_seconds=100,
    )
    ok = m.inscribe_name(
        player_id="p1", rune_name="Tide", now_seconds=200,
    )
    assert ok is False


def test_inscribe_name_blank():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    _complete_first_four(m, "p1")
    ok = m.inscribe_name(
        player_id="p1", rune_name="", now_seconds=5000,
    )
    assert ok is False


def test_inscribe_name_too_long():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    _complete_first_four(m, "p1")
    ok = m.inscribe_name(
        player_id="p1", rune_name="a" * 17, now_seconds=5000,
    )
    assert ok is False


def test_inscribe_name_double_blocked():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    _complete_first_four(m, "p1")
    m.inscribe_name(player_id="p1", rune_name="Tide", now_seconds=5000)
    ok = m.inscribe_name(
        player_id="p1", rune_name="Wave", now_seconds=6000,
    )
    assert ok is False


def test_weapon_for_returns_complete_data():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    _complete_first_four(m, "p1")
    m.inscribe_name(player_id="p1", rune_name="Tide", now_seconds=5000)
    w = m.weapon_for(player_id="p1")
    assert w is not None
    assert w.weapon_kind == "lance"
    assert w.inscribed_name == "Tide"
    assert len(w.traits) == 5


def test_weapon_for_unknown():
    m = DeepWeapons()
    assert m.weapon_for(player_id="ghost") is None


def test_stage_of_progression():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    assert m.stage_of(player_id="p1") == ForgeStage.BLUEPRINT_RECOVERY
    m.complete_stage(
        player_id="p1", stage=ForgeStage.BLUEPRINT_RECOVERY,
        trait_name="X", trait_description="Y", now_seconds=100,
    )
    assert m.stage_of(player_id="p1") == ForgeStage.HUNDRED_WRECKS


def test_stage_of_complete_returns_none():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    _complete_first_four(m, "p1")
    m.inscribe_name(player_id="p1", rune_name="Tide", now_seconds=5000)
    assert m.stage_of(player_id="p1") is None


def test_stage_of_unknown():
    m = DeepWeapons()
    assert m.stage_of(player_id="ghost") is None


def test_traits_of_grows():
    m = DeepWeapons()
    m.start_forge(player_id="p1", weapon_kind="lance", now_seconds=0)
    assert len(m.traits_of(player_id="p1")) == 0
    m.complete_stage(
        player_id="p1", stage=ForgeStage.BLUEPRINT_RECOVERY,
        trait_name="X", trait_description="Y", now_seconds=100,
    )
    assert len(m.traits_of(player_id="p1")) == 1
