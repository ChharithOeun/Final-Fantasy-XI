"""Tests for oral_tradition."""
from __future__ import annotations

from server.oral_tradition import (
    OralTradition,
    StoryAccuracy,
)


def test_seed_story_happy():
    o = OralTradition()
    ok = o.seed_story(
        story_id="vorrak_fall",
        source_entry_id="hist_42",
        summary="Iron Wing brought down Vorrak the Crowned",
        origin_zone_id="ru_lude_gardens",
        started_at=100,
    )
    assert ok is True
    assert o.total_stories() == 1


def test_seed_blank_id_blocked():
    o = OralTradition()
    assert o.seed_story(
        story_id="", source_entry_id=None,
        summary="x", origin_zone_id="z", started_at=10,
    ) is False


def test_seed_blank_summary_blocked():
    o = OralTradition()
    assert o.seed_story(
        story_id="x", source_entry_id=None,
        summary="", origin_zone_id="z", started_at=10,
    ) is False


def test_seed_blank_origin_blocked():
    o = OralTradition()
    assert o.seed_story(
        story_id="x", source_entry_id=None,
        summary="x", origin_zone_id="", started_at=10,
    ) is False


def test_seed_duplicate_blocked():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="a", origin_zone_id="z", started_at=10,
    )
    assert o.seed_story(
        story_id="x", source_entry_id=None,
        summary="b", origin_zone_id="z2", started_at=20,
    ) is False


def test_npc_hears_happy():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="A heroic deed", origin_zone_id="z",
        started_at=10,
    )
    ok = o.npc_hears(
        npc_id="bartender_tom", story_id="x",
        accuracy=StoryAccuracy.CLEAR, heard_at=20,
    )
    assert ok is True


def test_npc_hears_unknown_story():
    o = OralTradition()
    out = o.npc_hears(
        npc_id="tom", story_id="ghost",
        accuracy=StoryAccuracy.CLEAR, heard_at=10,
    )
    assert out is False


def test_npc_hears_blank_npc():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="A", origin_zone_id="z", started_at=10,
    )
    out = o.npc_hears(
        npc_id="", story_id="x",
        accuracy=StoryAccuracy.CLEAR, heard_at=10,
    )
    assert out is False


def test_npc_hears_returns_false_on_repeat():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="A", origin_zone_id="z", started_at=10,
    )
    o.npc_hears(
        npc_id="tom", story_id="x",
        accuracy=StoryAccuracy.GARBLED, heard_at=20,
    )
    out = o.npc_hears(
        npc_id="tom", story_id="x",
        accuracy=StoryAccuracy.GARBLED, heard_at=30,
    )
    assert out is False


def test_npc_hears_upgrades_accuracy():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="A", origin_zone_id="z", started_at=10,
    )
    o.npc_hears(
        npc_id="tom", story_id="x",
        accuracy=StoryAccuracy.GARBLED, heard_at=20,
    )
    o.npc_hears(
        npc_id="tom", story_id="x",
        accuracy=StoryAccuracy.FIRSTHAND, heard_at=30,
    )
    kn = o.what_does_npc_know(npc_id="tom", story_id="x")
    assert kn is not None
    assert kn.accuracy == StoryAccuracy.FIRSTHAND


def test_npc_hears_does_not_downgrade():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="A", origin_zone_id="z", started_at=10,
    )
    o.npc_hears(
        npc_id="tom", story_id="x",
        accuracy=StoryAccuracy.CLEAR, heard_at=20,
    )
    o.npc_hears(
        npc_id="tom", story_id="x",
        accuracy=StoryAccuracy.GARBLED, heard_at=30,
    )
    kn = o.what_does_npc_know(npc_id="tom", story_id="x")
    assert kn is not None
    assert kn.accuracy == StoryAccuracy.CLEAR


def test_what_does_npc_know_unknown():
    o = OralTradition()
    out = o.what_does_npc_know(npc_id="nobody", story_id="x")
    assert out is None


def test_npcs_who_know_index():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="A", origin_zone_id="z", started_at=10,
    )
    o.npc_hears(
        npc_id="a", story_id="x",
        accuracy=StoryAccuracy.CLEAR, heard_at=20,
    )
    o.npc_hears(
        npc_id="b", story_id="x",
        accuracy=StoryAccuracy.EMBELLISHED, heard_at=30,
    )
    npcs = o.npcs_who_know(story_id="x")
    assert "a" in npcs
    assert "b" in npcs


def test_retell_firsthand_includes_summary():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="Vorrak fell at dusk",
        origin_zone_id="z", started_at=10,
    )
    o.npc_hears(
        npc_id="alice", story_id="x",
        accuracy=StoryAccuracy.FIRSTHAND, heard_at=20,
    )
    text = o.retell(npc_id="alice", story_id="x")
    assert text is not None
    assert "Vorrak fell at dusk" in text
    assert "I was there" in text


def test_retell_garbled_softens_claim():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="something happened",
        origin_zone_id="z", started_at=10,
    )
    o.npc_hears(
        npc_id="bob", story_id="x",
        accuracy=StoryAccuracy.GARBLED, heard_at=20,
    )
    text = o.retell(npc_id="bob", story_id="x")
    assert text is not None
    assert "Could be true" in text or "many mouths" in text


def test_retell_unknown_returns_none():
    o = OralTradition()
    out = o.retell(npc_id="ghost", story_id="x")
    assert out is None


def test_retell_each_accuracy_distinct():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id=None,
        summary="X", origin_zone_id="z", started_at=10,
    )
    o.npc_hears(
        npc_id="a", story_id="x",
        accuracy=StoryAccuracy.FIRSTHAND, heard_at=10,
    )
    o.npc_hears(
        npc_id="b", story_id="x",
        accuracy=StoryAccuracy.CLEAR, heard_at=10,
    )
    o.npc_hears(
        npc_id="c", story_id="x",
        accuracy=StoryAccuracy.EMBELLISHED, heard_at=10,
    )
    o.npc_hears(
        npc_id="d", story_id="x",
        accuracy=StoryAccuracy.GARBLED, heard_at=10,
    )
    rs = {
        o.retell(npc_id=npc, story_id="x")
        for npc in "abcd"
    }
    # all four should produce different strings
    assert len(rs) == 4


def test_get_story_returns_seed():
    o = OralTradition()
    o.seed_story(
        story_id="x", source_entry_id="hist_1",
        summary="A", origin_zone_id="z", started_at=10,
    )
    s = o.get_story(story_id="x")
    assert s is not None
    assert s.source_entry_id == "hist_1"


def test_four_accuracy_levels():
    assert len(list(StoryAccuracy)) == 4
