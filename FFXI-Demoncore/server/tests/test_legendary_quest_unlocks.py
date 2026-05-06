"""Tests for legendary_quest_unlocks."""
from __future__ import annotations

from server.hero_titles import HeroTitleRegistry, TitleTier
from server.legendary_quest_unlocks import (
    LegendaryQuestUnlocks,
    UnlockMode,
)
from server.npc_legend_awareness import (
    RecognitionResult,
    RecognitionTier,
)


def _setup():
    titles = HeroTitleRegistry()
    titles.define_title(
        title_id="dragonslayer", name="Dragonslayer",
        tier=TitleTier.LEGENDARY,
    )
    titles.define_title(
        title_id="vorraks_bane", name="Vorrak's Bane",
        tier=TitleTier.MYTHIC,
    )
    titles.define_title(
        title_id="oathbreaker", name="Oathbreaker",
        tier=TitleTier.RARE,
    )
    return titles


def _rec(tier: RecognitionTier) -> RecognitionResult:
    return RecognitionResult(
        tier=tier, highest_title_id=None,
        faction_friendly=False, faction_hostile=False,
        reaction_phrase="",
    )


def test_register_gate_happy():
    u = LegendaryQuestUnlocks()
    ok = u.register_gate(
        quest_id="hero_only",
        required_title_ids=["dragonslayer"],
    )
    assert ok is True


def test_register_blank_quest_blocked():
    u = LegendaryQuestUnlocks()
    assert u.register_gate(
        quest_id="", required_title_ids=["x"],
    ) is False


def test_register_all_of_no_titles_blocked():
    u = LegendaryQuestUnlocks()
    assert u.register_gate(
        quest_id="x", required_title_ids=[],
        mode=UnlockMode.ALL_OF,
    ) is False


def test_duplicate_gate_blocked():
    u = LegendaryQuestUnlocks()
    u.register_gate(quest_id="x", required_title_ids=["a"])
    assert u.register_gate(
        quest_id="x", required_title_ids=["b"],
    ) is False


def test_unregistered_quest_default_visible():
    titles = _setup()
    u = LegendaryQuestUnlocks()
    out = u.can_see(
        quest_id="ghost", player_id="alice",
        title_registry=titles,
        recognition=_rec(RecognitionTier.UNKNOWN),
    )
    assert out.visible is True


def test_blank_player_blocked():
    titles = _setup()
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="q", required_title_ids=["dragonslayer"],
    )
    out = u.can_see(
        quest_id="q", player_id="",
        title_registry=titles,
        recognition=_rec(RecognitionTier.MYTHICAL),
    )
    assert out.visible is False


def test_any_of_with_one_match():
    titles = _setup()
    titles.grant_title(
        title_id="dragonslayer", player_id="alice", granted_at=10,
    )
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="q",
        required_title_ids=["dragonslayer", "vorraks_bane"],
        mode=UnlockMode.ANY_OF,
    )
    out = u.can_see(
        quest_id="q", player_id="alice",
        title_registry=titles,
        recognition=_rec(RecognitionTier.REVERED),
    )
    assert out.visible is True


def test_any_of_with_no_match():
    titles = _setup()
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="q",
        required_title_ids=["dragonslayer", "vorraks_bane"],
        mode=UnlockMode.ANY_OF,
    )
    out = u.can_see(
        quest_id="q", player_id="alice",
        title_registry=titles,
        recognition=_rec(RecognitionTier.UNKNOWN),
    )
    assert out.visible is False


def test_all_of_full_match():
    titles = _setup()
    titles.grant_title(
        title_id="dragonslayer", player_id="alice", granted_at=10,
    )
    titles.grant_title(
        title_id="vorraks_bane", player_id="alice", granted_at=20,
    )
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="q",
        required_title_ids=["dragonslayer", "vorraks_bane"],
        mode=UnlockMode.ALL_OF,
    )
    out = u.can_see(
        quest_id="q", player_id="alice",
        title_registry=titles,
        recognition=_rec(RecognitionTier.MYTHICAL),
    )
    assert out.visible is True


def test_all_of_partial_match_fails():
    titles = _setup()
    titles.grant_title(
        title_id="dragonslayer", player_id="alice", granted_at=10,
    )
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="q",
        required_title_ids=["dragonslayer", "vorraks_bane"],
        mode=UnlockMode.ALL_OF,
    )
    out = u.can_see(
        quest_id="q", player_id="alice",
        title_registry=titles,
        recognition=_rec(RecognitionTier.REVERED),
    )
    assert out.visible is False


def test_excluded_title_blocks():
    titles = _setup()
    titles.grant_title(
        title_id="dragonslayer", player_id="alice", granted_at=10,
    )
    titles.grant_title(
        title_id="oathbreaker", player_id="alice", granted_at=20,
    )
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="q",
        required_title_ids=["dragonslayer"],
        excluded_title_ids=["oathbreaker"],
    )
    out = u.can_see(
        quest_id="q", player_id="alice",
        title_registry=titles,
        recognition=_rec(RecognitionTier.REVERED),
    )
    assert out.visible is False


def test_min_recognition_floor():
    titles = _setup()
    titles.grant_title(
        title_id="dragonslayer", player_id="alice", granted_at=10,
    )
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="q",
        required_title_ids=["dragonslayer"],
        min_recognition=RecognitionTier.MYTHICAL,
    )
    # alice has the title but only at REVERED tier
    out = u.can_see(
        quest_id="q", player_id="alice",
        title_registry=titles,
        recognition=_rec(RecognitionTier.REVERED),
    )
    assert out.visible is False


def test_min_recognition_only_no_titles():
    titles = _setup()
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="q", required_title_ids=[],
        min_recognition=RecognitionTier.HONORED,
    )
    out = u.can_see(
        quest_id="q", player_id="alice",
        title_registry=titles,
        recognition=_rec(RecognitionTier.HONORED),
    )
    assert out.visible is True


def test_visible_quests_lists_all_visible():
    titles = _setup()
    titles.grant_title(
        title_id="dragonslayer", player_id="alice", granted_at=10,
    )
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="open_to_anyone", required_title_ids=[],
    )
    u.register_gate(
        quest_id="dragon_quest",
        required_title_ids=["dragonslayer"],
    )
    u.register_gate(
        quest_id="mythic_only",
        required_title_ids=["vorraks_bane"],
    )
    out = u.visible_quests(
        player_id="alice", title_registry=titles,
        recognition=_rec(RecognitionTier.REVERED),
    )
    assert "open_to_anyone" in out
    assert "dragon_quest" in out
    assert "mythic_only" not in out


def test_total_gates():
    u = LegendaryQuestUnlocks()
    u.register_gate(quest_id="a", required_title_ids=["x"])
    u.register_gate(quest_id="b", required_title_ids=["y"])
    assert u.total_gates() == 2


def test_unknown_quest_visible_for_legend():
    titles = _setup()
    u = LegendaryQuestUnlocks()
    out = u.can_see(
        quest_id="unknown", player_id="alice",
        title_registry=titles,
        recognition=_rec(RecognitionTier.MYTHICAL),
    )
    assert out.visible is True


def test_get_gate_returns_registered():
    u = LegendaryQuestUnlocks()
    u.register_gate(
        quest_id="q", required_title_ids=["a"],
    )
    g = u.get_gate(quest_id="q")
    assert g is not None
    assert g.quest_id == "q"
