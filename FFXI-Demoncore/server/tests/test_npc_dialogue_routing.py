"""Tests for npc_dialogue_routing."""
from __future__ import annotations

from server.npc_dialogue_routing import (
    NPCDialogueRoutingSystem,
)


def test_register_happy():
    s = NPCDialogueRoutingSystem()
    assert s.register_variant(
        npc_id="off_volker", faction_key="bastok",
        greeting="Welcome to Bastok!",
        dialogue_tree_id="volker_bastok_v1",
        voice_profile_id="volker_default",
    ) is True


def test_register_blank():
    s = NPCDialogueRoutingSystem()
    assert s.register_variant(
        npc_id="", faction_key="bastok",
        greeting="x", dialogue_tree_id="x",
        voice_profile_id="x",
    ) is False


def test_register_missing_voice():
    s = NPCDialogueRoutingSystem()
    assert s.register_variant(
        npc_id="o", faction_key="bastok",
        greeting="x", dialogue_tree_id="x",
        voice_profile_id="",
    ) is False


def test_default_variant_active():
    s = NPCDialogueRoutingSystem()
    s.register_variant(
        npc_id="off_volker", faction_key="bastok",
        greeting="Welcome to Bastok!",
        dialogue_tree_id="volker_bastok_v1",
        voice_profile_id="volker_default",
        is_default=True,
    )
    v = s.active_variant(npc_id="off_volker")
    assert v.faction_key == "bastok"


def test_swap_after_defection():
    """The killer test: NPC defects, dialogue flips."""
    s = NPCDialogueRoutingSystem()
    s.register_variant(
        npc_id="off_volker", faction_key="bastok",
        greeting="Welcome to Bastok!",
        dialogue_tree_id="volker_bastok_v1",
        voice_profile_id="volker_loyal",
        is_default=True,
    )
    s.register_variant(
        npc_id="off_volker", faction_key="windy",
        greeting="The wind whispers welcome.",
        dialogue_tree_id="volker_windy_v1",
        voice_profile_id="volker_defected",
    )
    s.update_npc_faction(
        npc_id="off_volker", faction_key="windy",
    )
    v = s.active_variant(npc_id="off_volker")
    assert v.faction_key == "windy"
    assert v.greeting == "The wind whispers welcome."


def test_voice_profile_swaps_too():
    s = NPCDialogueRoutingSystem()
    s.register_variant(
        npc_id="o", faction_key="bastok",
        greeting="x", dialogue_tree_id="t1",
        voice_profile_id="loyal_voice",
        is_default=True,
    )
    s.register_variant(
        npc_id="o", faction_key="windy",
        greeting="y", dialogue_tree_id="t2",
        voice_profile_id="exile_voice",
    )
    s.update_npc_faction(
        npc_id="o", faction_key="windy",
    )
    v = s.active_variant(npc_id="o")
    assert v.voice_profile_id == "exile_voice"


def test_missing_variant_falls_back_to_default():
    s = NPCDialogueRoutingSystem()
    s.register_variant(
        npc_id="o", faction_key="bastok",
        greeting="x", dialogue_tree_id="t1",
        voice_profile_id="v1",
        is_default=True,
    )
    s.update_npc_faction(
        npc_id="o", faction_key="sandy",
    )
    v = s.active_variant(npc_id="o")
    assert v is not None
    assert v.faction_key == "bastok"


def test_no_variants_no_active():
    s = NPCDialogueRoutingSystem()
    s.update_npc_faction(
        npc_id="o", faction_key="bastok",
    )
    assert s.active_variant(npc_id="o") is None


def test_no_npc_no_active():
    s = NPCDialogueRoutingSystem()
    assert s.active_variant(
        npc_id="ghost",
    ) is None


def test_no_faction_uses_default():
    s = NPCDialogueRoutingSystem()
    s.register_variant(
        npc_id="o", faction_key="bastok",
        greeting="x", dialogue_tree_id="t1",
        voice_profile_id="v1",
        is_default=True,
    )
    # Never called update_npc_faction; default
    # auto-applied at register time
    v = s.active_variant(npc_id="o")
    assert v.faction_key == "bastok"


def test_has_variant():
    s = NPCDialogueRoutingSystem()
    s.register_variant(
        npc_id="o", faction_key="bastok",
        greeting="x", dialogue_tree_id="t1",
        voice_profile_id="v1",
    )
    assert s.has_variant(
        npc_id="o", faction_key="bastok",
    ) is True
    assert s.has_variant(
        npc_id="o", faction_key="windy",
    ) is False


def test_variants_for():
    s = NPCDialogueRoutingSystem()
    s.register_variant(
        npc_id="o", faction_key="bastok",
        greeting="x", dialogue_tree_id="t1",
        voice_profile_id="v1",
    )
    s.register_variant(
        npc_id="o", faction_key="windy",
        greeting="y", dialogue_tree_id="t2",
        voice_profile_id="v2",
    )
    s.register_variant(
        npc_id="other", faction_key="bastok",
        greeting="z", dialogue_tree_id="t3",
        voice_profile_id="v3",
    )
    out = s.variants_for(npc_id="o")
    assert len(out) == 2


def test_remove_variant():
    s = NPCDialogueRoutingSystem()
    s.register_variant(
        npc_id="o", faction_key="bastok",
        greeting="x", dialogue_tree_id="t1",
        voice_profile_id="v1",
    )
    assert s.remove_variant(
        npc_id="o", faction_key="bastok",
    ) is True


def test_remove_variant_unknown():
    s = NPCDialogueRoutingSystem()
    assert s.remove_variant(
        npc_id="o", faction_key="bastok",
    ) is False


def test_remove_default_clears_default():
    s = NPCDialogueRoutingSystem()
    s.register_variant(
        npc_id="o", faction_key="bastok",
        greeting="x", dialogue_tree_id="t1",
        voice_profile_id="v1",
        is_default=True,
    )
    s.remove_variant(
        npc_id="o", faction_key="bastok",
    )
    # No default, no current set explicitly
    assert s.active_variant(
        npc_id="o",
    ) is None


def test_current_faction():
    s = NPCDialogueRoutingSystem()
    s.update_npc_faction(
        npc_id="o", faction_key="windy",
    )
    assert s.current_faction(
        npc_id="o",
    ) == "windy"


def test_current_faction_unknown():
    s = NPCDialogueRoutingSystem()
    assert s.current_faction(
        npc_id="o",
    ) is None


def test_update_blank_blocked():
    s = NPCDialogueRoutingSystem()
    assert s.update_npc_faction(
        npc_id="", faction_key="bastok",
    ) is False
