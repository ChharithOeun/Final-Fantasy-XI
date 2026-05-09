"""Tests for npc_quest_anchor."""
from __future__ import annotations

from server.npc_quest_anchor import (
    NPCQuestAnchorSystem,
)


def test_register_happy():
    s = NPCQuestAnchorSystem()
    assert s.register_quest(
        quest_id="volker_lost_sword",
        fallback_role="GIVER",
    ) is True


def test_register_blank():
    s = NPCQuestAnchorSystem()
    assert s.register_quest(
        quest_id="", fallback_role="GIVER",
    ) is False


def test_register_dup_blocked():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    assert s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    ) is False


def test_bind_role():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    assert s.bind_role(
        quest_id="q1", role="GIVER",
        npc_id="off_volker",
    ) is True


def test_bind_replaces_same_role():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    s.bind_role(
        quest_id="q1", role="GIVER", npc_id="a",
    )
    s.bind_role(
        quest_id="q1", role="GIVER", npc_id="b",
    )
    anc = s.anchor(quest_id="q1")
    assert len(anc.bindings) == 1
    assert anc.bindings[0].npc_id == "b"


def test_bind_unknown_quest():
    s = NPCQuestAnchorSystem()
    assert s.bind_role(
        quest_id="ghost", role="GIVER", npc_id="x",
    ) is False


def test_bind_blank_npc():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    assert s.bind_role(
        quest_id="q1", role="GIVER", npc_id="",
    ) is False


def test_unbind_role():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    s.bind_role(
        quest_id="q1", role="GIVER",
        npc_id="off_volker",
    )
    assert s.unbind_role(
        quest_id="q1", role="GIVER",
    ) is True


def test_unbind_unbound_role():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    assert s.unbind_role(
        quest_id="q1", role="GIVER",
    ) is False


def test_resolve_location_via_giver():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    s.bind_role(
        quest_id="q1", role="GIVER",
        npc_id="off_volker",
    )
    loc = s.resolve_quest_location(
        quest_id="q1",
        npc_locations={"off_volker": "windy"},
    )
    assert loc == "windy"


def test_resolve_follows_after_defection():
    """The killer test: NPC moves, location follows."""
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="volker_lost_sword",
        fallback_role="GIVER",
    )
    s.bind_role(
        quest_id="volker_lost_sword",
        role="GIVER", npc_id="off_volker",
    )
    # Pre-defection: Volker in Bastok
    loc_before = s.resolve_quest_location(
        quest_id="volker_lost_sword",
        npc_locations={"off_volker": "bastok"},
    )
    assert loc_before == "bastok"
    # Post-defection: Volker in Windy — same anchor,
    # different npc_locations input
    loc_after = s.resolve_quest_location(
        quest_id="volker_lost_sword",
        npc_locations={"off_volker": "windy"},
    )
    assert loc_after == "windy"


def test_resolve_unknown_quest():
    s = NPCQuestAnchorSystem()
    loc = s.resolve_quest_location(
        quest_id="ghost", npc_locations={},
    )
    assert loc is None


def test_resolve_no_fallback_binding():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    # Bound a different role only
    s.bind_role(
        quest_id="q1", role="WITNESS",
        npc_id="off_witness",
    )
    loc = s.resolve_quest_location(
        quest_id="q1",
        npc_locations={"off_witness": "bastok"},
    )
    assert loc is None


def test_resolve_npc_location_missing():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    s.bind_role(
        quest_id="q1", role="GIVER",
        npc_id="off_volker",
    )
    loc = s.resolve_quest_location(
        quest_id="q1", npc_locations={},
    )
    assert loc is None


def test_quests_for_npc():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    s.register_quest(
        quest_id="q2", fallback_role="GIVER",
    )
    s.register_quest(
        quest_id="q3", fallback_role="GIVER",
    )
    s.bind_role(quest_id="q1", role="GIVER",
                npc_id="off_volker")
    s.bind_role(quest_id="q2", role="WITNESS",
                npc_id="off_volker")
    s.bind_role(quest_id="q3", role="GIVER",
                npc_id="off_naji")
    out = s.quests_for_npc(npc_id="off_volker")
    assert sorted(out) == ["q1", "q2"]


def test_role_npc():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    s.bind_role(
        quest_id="q1", role="GIVER",
        npc_id="off_volker",
    )
    assert s.role_npc(
        quest_id="q1", role="GIVER",
    ) == "off_volker"


def test_role_npc_unknown_role():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    assert s.role_npc(
        quest_id="q1", role="WITNESS",
    ) is None


def test_locked_quest():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="msq_chapter_1",
        fallback_role="GIVER", locked=True,
    )
    assert s.is_locked(
        quest_id="msq_chapter_1",
    ) is True


def test_unlocked_default():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="q1", fallback_role="GIVER",
    )
    assert s.is_locked(quest_id="q1") is False


def test_anchor_unknown():
    s = NPCQuestAnchorSystem()
    assert s.anchor(quest_id="ghost") is None


def test_all_quests():
    s = NPCQuestAnchorSystem()
    s.register_quest(
        quest_id="a", fallback_role="GIVER",
    )
    s.register_quest(
        quest_id="b", fallback_role="GIVER",
    )
    assert len(s.all_quests()) == 2
