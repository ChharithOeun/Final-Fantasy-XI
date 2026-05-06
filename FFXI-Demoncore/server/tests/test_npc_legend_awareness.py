"""Tests for npc_legend_awareness."""
from __future__ import annotations

from server.hero_titles import HeroTitleRegistry, TitleTier
from server.npc_legend_awareness import (
    NpcLegendAwareness,
    RecognitionTier,
)


def _setup_titles():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="common", name="Wanderer",
        tier=TitleTier.COMMON,
    )
    r.define_title(
        title_id="rare", name="Adventurer",
        tier=TitleTier.RARE,
    )
    r.define_title(
        title_id="epic", name="Champion",
        tier=TitleTier.EPIC,
    )
    r.define_title(
        title_id="legendary", name="Hero",
        tier=TitleTier.LEGENDARY,
    )
    r.define_title(
        title_id="mythic", name="Demoncore",
        tier=TitleTier.MYTHIC,
    )
    return r


def test_unknown_player_returns_unknown():
    r = _setup_titles()
    a = NpcLegendAwareness()
    out = a.recognize(player_id="ghost", title_registry=r)
    assert out.tier == RecognitionTier.UNKNOWN
    assert out.highest_title_id is None


def test_blank_player_returns_unknown():
    r = _setup_titles()
    a = NpcLegendAwareness()
    out = a.recognize(player_id="", title_registry=r)
    assert out.tier == RecognitionTier.UNKNOWN


def test_rare_title_yields_noted():
    r = _setup_titles()
    r.grant_title(title_id="rare", player_id="alice", granted_at=10)
    a = NpcLegendAwareness()
    out = a.recognize(player_id="alice", title_registry=r)
    assert out.tier == RecognitionTier.NOTED


def test_epic_title_yields_honored():
    r = _setup_titles()
    r.grant_title(title_id="epic", player_id="alice", granted_at=10)
    a = NpcLegendAwareness()
    out = a.recognize(player_id="alice", title_registry=r)
    assert out.tier == RecognitionTier.HONORED


def test_legendary_yields_revered():
    r = _setup_titles()
    r.grant_title(title_id="legendary", player_id="alice", granted_at=10)
    a = NpcLegendAwareness()
    out = a.recognize(player_id="alice", title_registry=r)
    assert out.tier == RecognitionTier.REVERED


def test_mythic_yields_mythical():
    r = _setup_titles()
    r.grant_title(title_id="mythic", player_id="alice", granted_at=10)
    a = NpcLegendAwareness()
    out = a.recognize(player_id="alice", title_registry=r)
    assert out.tier == RecognitionTier.MYTHICAL


def test_highest_title_wins():
    r = _setup_titles()
    r.grant_title(title_id="common", player_id="alice", granted_at=1)
    r.grant_title(title_id="rare", player_id="alice", granted_at=2)
    r.grant_title(title_id="legendary", player_id="alice", granted_at=3)
    a = NpcLegendAwareness()
    out = a.recognize(player_id="alice", title_registry=r)
    assert out.tier == RecognitionTier.REVERED
    assert out.highest_title_id == "legendary"


def test_reaction_phrase_present():
    r = _setup_titles()
    r.grant_title(title_id="mythic", player_id="alice", granted_at=10)
    a = NpcLegendAwareness()
    out = a.recognize(player_id="alice", title_registry=r)
    assert out.reaction_phrase != ""


def test_friendly_at_50_plus():
    r = _setup_titles()
    a = NpcLegendAwareness()
    out = a.recognize(
        player_id="alice", title_registry=r,
        faction_rep_score=75,
    )
    assert out.faction_friendly is True
    assert out.faction_hostile is False


def test_hostile_at_minus_50_or_below():
    r = _setup_titles()
    a = NpcLegendAwareness()
    out = a.recognize(
        player_id="alice", title_registry=r,
        faction_rep_score=-60,
    )
    assert out.faction_hostile is True
    assert out.faction_friendly is False


def test_neutral_zone_neither_friend_nor_foe():
    r = _setup_titles()
    a = NpcLegendAwareness()
    out = a.recognize(
        player_id="alice", title_registry=r,
        faction_rep_score=10,
    )
    assert out.faction_friendly is False
    assert out.faction_hostile is False


def test_common_title_only_still_unknown():
    """COMMON titles aren't enough to be recognized."""
    r = _setup_titles()
    r.grant_title(title_id="common", player_id="alice", granted_at=1)
    a = NpcLegendAwareness()
    out = a.recognize(player_id="alice", title_registry=r)
    assert out.tier == RecognitionTier.UNKNOWN


def test_reaction_phrase_for_each_tier():
    a = NpcLegendAwareness()
    for tier in RecognitionTier:
        phrase = a.reaction_phrase_for(tier=tier)
        assert phrase != ""


def test_total_recognitions_increments():
    r = _setup_titles()
    a = NpcLegendAwareness()
    a.recognize(player_id="a", title_registry=r)
    a.recognize(player_id="b", title_registry=r)
    a.recognize(player_id="c", title_registry=r)
    assert a.total_recognitions() == 3


def test_five_recognition_tiers():
    assert len(list(RecognitionTier)) == 5
