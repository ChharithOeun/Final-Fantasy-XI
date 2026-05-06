"""Tests for infamy_titles."""
from __future__ import annotations

from server.infamy_titles import (
    InfamyRegistry,
    InfamyTier,
)


def _setup():
    r = InfamyRegistry()
    r.define_infamy(
        title_id="cheater", name="Caught Cheating",
        tier=InfamyTier.PETTY,
    )
    r.define_infamy(
        title_id="coward", name="The Coward",
        tier=InfamyTier.SHAMEFUL,
        cleanse_quest_id="redemption_quest",
    )
    r.define_infamy(
        title_id="bandit_king", name="Bandit King",
        tier=InfamyTier.NOTORIOUS,
        cleanse_quest_id="absolution",
    )
    r.define_infamy(
        title_id="defiler", name="Defiler of Tombs",
        tier=InfamyTier.INFAMOUS,
    )
    r.define_infamy(
        title_id="kingslayer", name="Kingslayer",
        tier=InfamyTier.BLACK,
    )
    return r


def test_define_infamy_happy():
    r = _setup()
    assert r.total_titles() == 5


def test_define_blank_id_blocked():
    r = InfamyRegistry()
    out = r.define_infamy(
        title_id="", name="X", tier=InfamyTier.PETTY,
    )
    assert out is False


def test_define_blank_name_blocked():
    r = InfamyRegistry()
    out = r.define_infamy(
        title_id="x", name="", tier=InfamyTier.PETTY,
    )
    assert out is False


def test_redefine_blocked():
    r = _setup()
    again = r.define_infamy(
        title_id="cheater", name="dup", tier=InfamyTier.PETTY,
    )
    assert again is False


def test_black_tier_forces_indelible():
    r = _setup()
    td = r.get_title(title_id="kingslayer")
    assert td is not None
    assert td.indelible is True
    assert td.cleanse_quest_id is None


def test_mark_player_happy():
    r = _setup()
    ok = r.mark_player(
        player_id="alice", title_id="cheater",
        marked_at=10, source_entry_id="hist_1",
    )
    assert ok is True
    assert r.total_marks() == 1


def test_mark_unknown_title():
    r = _setup()
    out = r.mark_player(
        player_id="alice", title_id="ghost",
        marked_at=10,
    )
    assert out is False


def test_mark_blank_player():
    r = _setup()
    out = r.mark_player(
        player_id="", title_id="cheater", marked_at=10,
    )
    assert out is False


def test_double_mark_blocked():
    r = _setup()
    r.mark_player(
        player_id="alice", title_id="cheater", marked_at=10,
    )
    again = r.mark_player(
        player_id="alice", title_id="cheater", marked_at=20,
    )
    assert again is False


def test_marks_for_player_index():
    r = _setup()
    r.mark_player(
        player_id="alice", title_id="cheater", marked_at=1,
    )
    r.mark_player(
        player_id="alice", title_id="coward", marked_at=2,
    )
    out = r.marks_for_player(player_id="alice")
    assert len(out) == 2


def test_holders_of_index():
    r = _setup()
    r.mark_player(
        player_id="alice", title_id="cheater", marked_at=10,
    )
    r.mark_player(
        player_id="bob", title_id="cheater", marked_at=20,
    )
    holders = r.holders_of(title_id="cheater")
    assert "alice" in holders
    assert "bob" in holders


def test_player_worst_tier():
    r = _setup()
    r.mark_player(
        player_id="alice", title_id="cheater", marked_at=10,
    )
    r.mark_player(
        player_id="alice", title_id="defiler", marked_at=20,
    )
    assert r.player_worst_tier(player_id="alice") == InfamyTier.INFAMOUS


def test_player_worst_tier_none():
    r = _setup()
    assert r.player_worst_tier(player_id="ghost") is None


def test_cleanse_with_correct_quest():
    r = _setup()
    r.mark_player(
        player_id="alice", title_id="coward", marked_at=10,
    )
    ok = r.cleanse(
        player_id="alice", title_id="coward",
        cleansed_at=100,
        quest_id_used="redemption_quest",
    )
    assert ok is True
    out = r.marks_for_player(player_id="alice")
    assert len(out) == 0


def test_cleanse_wrong_quest_rejected():
    r = _setup()
    r.mark_player(
        player_id="alice", title_id="coward", marked_at=10,
    )
    out = r.cleanse(
        player_id="alice", title_id="coward",
        cleansed_at=100,
        quest_id_used="some_other_quest",
    )
    assert out is False


def test_cleanse_indelible_rejected():
    r = _setup()
    r.mark_player(
        player_id="alice", title_id="kingslayer", marked_at=10,
    )
    out = r.cleanse(
        player_id="alice", title_id="kingslayer",
        cleansed_at=100,
    )
    assert out is False
    # alice still holds it
    assert "alice" in r.holders_of(title_id="kingslayer")


def test_cleanse_unmarked_rejected():
    r = _setup()
    out = r.cleanse(
        player_id="alice", title_id="coward",
        cleansed_at=100, quest_id_used="redemption_quest",
    )
    assert out is False


def test_cleanse_no_quest_required():
    r = _setup()
    # cheater has no cleanse_quest_id; can be cleansed without
    r.mark_player(
        player_id="alice", title_id="cheater", marked_at=10,
    )
    ok = r.cleanse(
        player_id="alice", title_id="cheater",
        cleansed_at=100,
    )
    assert ok is True


def test_cleanse_clears_holders_index():
    r = _setup()
    r.mark_player(
        player_id="alice", title_id="cheater", marked_at=10,
    )
    r.cleanse(
        player_id="alice", title_id="cheater",
        cleansed_at=100,
    )
    holders = r.holders_of(title_id="cheater")
    assert "alice" not in holders


def test_five_infamy_tiers():
    assert len(list(InfamyTier)) == 5


def test_cleanse_unknown_title_rejected():
    r = _setup()
    out = r.cleanse(
        player_id="alice", title_id="ghost",
        cleansed_at=100,
    )
    assert out is False


def test_mark_carries_source():
    r = _setup()
    r.mark_player(
        player_id="alice", title_id="cheater",
        marked_at=42, source_entry_id="hist_99",
    )
    marks = r.marks_for_player(player_id="alice")
    assert marks[0].source_entry_id == "hist_99"
    assert marks[0].marked_at == 42
