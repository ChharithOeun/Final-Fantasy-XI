"""Tests for hero_titles."""
from __future__ import annotations

from server.hero_titles import (
    HeroTitleRegistry,
    TitleTier,
)


def test_define_title_happy():
    r = HeroTitleRegistry()
    ok = r.define_title(
        title_id="dragonslayer", name="Dragonslayer",
        tier=TitleTier.LEGENDARY,
    )
    assert ok is True
    td = r.get_title(title_id="dragonslayer")
    assert td is not None
    assert td.tier == TitleTier.LEGENDARY


def test_define_blank_id_blocked():
    r = HeroTitleRegistry()
    assert r.define_title(
        title_id="", name="X", tier=TitleTier.COMMON,
    ) is False


def test_define_blank_name_blocked():
    r = HeroTitleRegistry()
    assert r.define_title(
        title_id="x", name="", tier=TitleTier.COMMON,
    ) is False


def test_redefine_blocked():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="x", name="X", tier=TitleTier.COMMON,
    )
    assert r.define_title(
        title_id="x", name="X2", tier=TitleTier.RARE,
    ) is False


def test_grant_title_happy():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="kingslayer", name="Kingslayer",
        tier=TitleTier.MYTHIC,
    )
    ok = r.grant_title(
        title_id="kingslayer", player_id="alice",
        granted_at=100, source_entry_id="hist_42",
    )
    assert ok is True
    assert r.total_grants() == 1


def test_grant_unknown_title_blocked():
    r = HeroTitleRegistry()
    ok = r.grant_title(
        title_id="ghost", player_id="alice",
        granted_at=10,
    )
    assert ok is False


def test_grant_blank_player_blocked():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="x", name="X", tier=TitleTier.COMMON,
    )
    ok = r.grant_title(
        title_id="x", player_id="", granted_at=10,
    )
    assert ok is False


def test_double_grant_to_same_player_blocked():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="x", name="X", tier=TitleTier.COMMON,
    )
    r.grant_title(title_id="x", player_id="alice", granted_at=10)
    again = r.grant_title(
        title_id="x", player_id="alice", granted_at=20,
    )
    assert again is False
    assert r.total_grants() == 1


def test_titles_for_player_index():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="a", name="A", tier=TitleTier.COMMON,
    )
    r.define_title(
        title_id="b", name="B", tier=TitleTier.EPIC,
    )
    r.grant_title(title_id="a", player_id="alice", granted_at=1)
    r.grant_title(title_id="b", player_id="alice", granted_at=2)
    r.grant_title(title_id="a", player_id="bob", granted_at=3)
    alice = r.titles_for_player(player_id="alice")
    assert len(alice) == 2
    bob = r.titles_for_player(player_id="bob")
    assert len(bob) == 1


def test_holders_of_index():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="champion", name="Champion",
        tier=TitleTier.LEGENDARY,
    )
    r.grant_title(title_id="champion", player_id="alice", granted_at=1)
    r.grant_title(title_id="champion", player_id="bob", granted_at=2)
    r.grant_title(title_id="champion", player_id="carol", granted_at=3)
    holders = r.holders_of(title_id="champion")
    assert set(holders) == {"alice", "bob", "carol"}


def test_holders_unique():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="x", name="X", tier=TitleTier.COMMON,
    )
    r.grant_title(title_id="x", player_id="alice", granted_at=1)
    # double-grant blocked but ensure no dup in holders either
    r.grant_title(title_id="x", player_id="alice", granted_at=2)
    holders = r.holders_of(title_id="x")
    assert holders == ("alice",)


def test_player_highest_tier_none():
    r = HeroTitleRegistry()
    assert r.player_highest_tier(player_id="ghost") is None


def test_player_highest_tier_picks_max():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="c", name="C", tier=TitleTier.COMMON,
    )
    r.define_title(
        title_id="r", name="R", tier=TitleTier.RARE,
    )
    r.define_title(
        title_id="m", name="M", tier=TitleTier.MYTHIC,
    )
    r.grant_title(title_id="c", player_id="alice", granted_at=1)
    r.grant_title(title_id="r", player_id="alice", granted_at=2)
    r.grant_title(title_id="m", player_id="alice", granted_at=3)
    assert r.player_highest_tier(player_id="alice") == TitleTier.MYTHIC


def test_player_highest_skips_lower():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="c", name="C", tier=TitleTier.COMMON,
    )
    r.define_title(
        title_id="e", name="E", tier=TitleTier.EPIC,
    )
    r.grant_title(title_id="e", player_id="bob", granted_at=1)
    r.grant_title(title_id="c", player_id="bob", granted_at=2)
    assert r.player_highest_tier(player_id="bob") == TitleTier.EPIC


def test_total_titles_defined():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="a", name="A", tier=TitleTier.COMMON,
    )
    r.define_title(
        title_id="b", name="B", tier=TitleTier.RARE,
    )
    assert r.total_titles_defined() == 2


def test_grant_carries_source_entry_id():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="x", name="X", tier=TitleTier.LEGENDARY,
    )
    r.grant_title(
        title_id="x", player_id="alice",
        granted_at=42, source_entry_id="hist_99",
    )
    grants = r.titles_for_player(player_id="alice")
    assert grants[0].source_entry_id == "hist_99"
    assert grants[0].granted_at == 42


def test_five_tier_ladder():
    assert len(list(TitleTier)) == 5
