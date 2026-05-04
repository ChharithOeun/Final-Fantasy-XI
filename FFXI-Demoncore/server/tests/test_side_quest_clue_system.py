"""Tests for the side quest clue system."""
from __future__ import annotations

from server.side_quest_clue_system import (
    ClueSourceKind,
    LegibilityTier,
    SideQuestClueSystem,
)


def _seed(s: SideQuestClueSystem):
    s.register_side_quest(
        quest_id="ravens_of_zilart",
        title="The Ravens of Zilart",
        full_description=(
            "Find the four crow-marked stones scattered "
            "across Norvallen."
        ),
        start_npc_id="ferdinand",
    )


def test_register_side_quest():
    s = SideQuestClueSystem()
    _seed(s)
    assert s.total_quests() == 1


def test_double_register_rejected():
    s = SideQuestClueSystem()
    _seed(s)
    second = s.register_side_quest(
        quest_id="ravens_of_zilart", title="x",
    )
    assert second is None


def test_unknown_quest_capture_returns_none():
    s = SideQuestClueSystem()
    assert s.capture_fragment(
        player_id="alice", quest_id="ghost",
        source_kind=ClueSourceKind.POSTER_HIT,
    ) is None


def test_no_fragments_means_hidden():
    s = SideQuestClueSystem()
    _seed(s)
    assert s.legibility_for(
        player_id="alice", quest_id="ravens_of_zilart",
    ) == LegibilityTier.HIDDEN


def test_one_fragment_reaches_smell_tier():
    s = SideQuestClueSystem()
    _seed(s)
    s.capture_fragment(
        player_id="alice", quest_id="ravens_of_zilart",
        source_kind=ClueSourceKind.OVERHEARD_CHATTER,
    )
    assert s.legibility_for(
        player_id="alice", quest_id="ravens_of_zilart",
    ) == LegibilityTier.SMELL


def test_three_fragments_partial_title():
    s = SideQuestClueSystem()
    _seed(s)
    for _ in range(3):
        s.capture_fragment(
            player_id="alice", quest_id="ravens_of_zilart",
            source_kind=ClueSourceKind.POSTER_HIT,
        )
    assert s.legibility_for(
        player_id="alice", quest_id="ravens_of_zilart",
    ) == LegibilityTier.PARTIAL_TITLE


def test_six_fragments_full_legibility():
    s = SideQuestClueSystem()
    _seed(s)
    for _ in range(6):
        s.capture_fragment(
            player_id="alice", quest_id="ravens_of_zilart",
            source_kind=ClueSourceKind.SUBTLE_NPC_HINT,
        )
    assert s.legibility_for(
        player_id="alice", quest_id="ravens_of_zilart",
    ) == LegibilityTier.FULL


def test_weighted_kind_advances_faster():
    s = SideQuestClueSystem()
    _seed(s)
    s.add_fragment_kind(
        quest_id="ravens_of_zilart",
        source_kind=ClueSourceKind.MOB_DROP_NOTE,
        weight=6,
    )
    s.capture_fragment(
        player_id="alice", quest_id="ravens_of_zilart",
        source_kind=ClueSourceKind.MOB_DROP_NOTE,
    )
    # One drop note worth 6 -> FULL
    assert s.legibility_for(
        player_id="alice", quest_id="ravens_of_zilart",
    ) == LegibilityTier.FULL


def test_card_hidden_returns_none():
    s = SideQuestClueSystem()
    _seed(s)
    assert s.card_for(
        player_id="alice", quest_id="ravens_of_zilart",
    ) is None


def test_card_smell_obscures_title():
    s = SideQuestClueSystem()
    _seed(s)
    s.capture_fragment(
        player_id="alice", quest_id="ravens_of_zilart",
        source_kind=ClueSourceKind.OVERHEARD_CHATTER,
    )
    card = s.card_for(
        player_id="alice", quest_id="ravens_of_zilart",
    )
    assert card.title_visible == "???"
    assert card.start_npc_visible is None


def test_card_partial_shows_title_prefix():
    s = SideQuestClueSystem()
    _seed(s)
    for _ in range(3):
        s.capture_fragment(
            player_id="alice", quest_id="ravens_of_zilart",
            source_kind=ClueSourceKind.POSTER_HIT,
        )
    card = s.card_for(
        player_id="alice", quest_id="ravens_of_zilart",
    )
    assert card.title_visible.endswith("...")
    assert card.start_npc_visible is None


def test_card_full_shows_everything():
    s = SideQuestClueSystem()
    _seed(s)
    for _ in range(6):
        s.capture_fragment(
            player_id="alice", quest_id="ravens_of_zilart",
            source_kind=ClueSourceKind.SUBTLE_NPC_HINT,
        )
    card = s.card_for(
        player_id="alice", quest_id="ravens_of_zilart",
    )
    assert card.title_visible == "The Ravens of Zilart"
    assert card.start_npc_visible == "ferdinand"
    assert "crow-marked" in card.body_visible


def test_visible_quests_sorted():
    s = SideQuestClueSystem()
    s.register_side_quest(quest_id="b_quest", title="B")
    s.register_side_quest(quest_id="a_quest", title="A")
    s.capture_fragment(
        player_id="alice", quest_id="b_quest",
        source_kind=ClueSourceKind.POSTER_HIT,
    )
    s.capture_fragment(
        player_id="alice", quest_id="a_quest",
        source_kind=ClueSourceKind.POSTER_HIT,
    )
    cards = s.visible_quests("alice")
    assert [c.quest_id for c in cards] == [
        "a_quest", "b_quest",
    ]


def test_visible_quests_only_visible():
    s = SideQuestClueSystem()
    _seed(s)
    s.register_side_quest(quest_id="other", title="O")
    s.capture_fragment(
        player_id="alice", quest_id="ravens_of_zilart",
        source_kind=ClueSourceKind.POSTER_HIT,
    )
    cards = s.visible_quests("alice")
    assert len(cards) == 1
    assert cards[0].quest_id == "ravens_of_zilart"


def test_per_player_isolation():
    s = SideQuestClueSystem()
    _seed(s)
    s.capture_fragment(
        player_id="alice", quest_id="ravens_of_zilart",
        source_kind=ClueSourceKind.POSTER_HIT,
    )
    assert s.legibility_for(
        player_id="bob", quest_id="ravens_of_zilart",
    ) == LegibilityTier.HIDDEN


def test_add_fragment_kind_unknown():
    s = SideQuestClueSystem()
    assert not s.add_fragment_kind(
        quest_id="ghost",
        source_kind=ClueSourceKind.POSTER_HIT,
        weight=2,
    )


def test_add_fragment_zero_weight_rejected():
    s = SideQuestClueSystem()
    _seed(s)
    assert not s.add_fragment_kind(
        quest_id="ravens_of_zilart",
        source_kind=ClueSourceKind.POSTER_HIT,
        weight=0,
    )


def test_card_unknown_quest_returns_none():
    s = SideQuestClueSystem()
    assert s.card_for(
        player_id="alice", quest_id="ghost",
    ) is None


def test_captured_fragments_count():
    s = SideQuestClueSystem()
    _seed(s)
    for _ in range(2):
        s.capture_fragment(
            player_id="alice", quest_id="ravens_of_zilart",
            source_kind=ClueSourceKind.POSTER_HIT,
        )
    card = s.card_for(
        player_id="alice", quest_id="ravens_of_zilart",
    )
    assert card.captured_fragments == 2
