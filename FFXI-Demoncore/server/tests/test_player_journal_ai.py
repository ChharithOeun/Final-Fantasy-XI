"""Tests for the player journal AI."""
from __future__ import annotations

from server.player_journal_ai import (
    DayMood,
    EventCategory,
    EventWeight,
    PlayerJournalAI,
)


def test_ingest_and_compose():
    j = PlayerJournalAI()
    j.ingest_event(
        player_id="alice", kind="boss_kill",
        weight=EventWeight.HUGE_POSITIVE,
        label="Slew Fafnir",
        category=EventCategory.COMBAT,
        day_index=1,
    )
    entry = j.compose_entry(
        player_id="alice", day_index=1,
    )
    assert entry is not None
    assert entry.mood == DayMood.TRIUMPH
    assert "Fafnir" in entry.headline


def test_ingest_empty_kind_rejected():
    j = PlayerJournalAI()
    assert not j.ingest_event(
        player_id="alice", kind="",
        weight=EventWeight.NEUTRAL,
        day_index=1,
    )


def test_no_events_no_entry():
    j = PlayerJournalAI()
    assert j.compose_entry(
        player_id="alice", day_index=1,
    ) is None


def test_setback_for_negative_day():
    j = PlayerJournalAI()
    j.ingest_event(
        player_id="alice", kind="permadeath",
        weight=EventWeight.HUGE_NEGATIVE,
        label="Lost a beloved character",
        category=EventCategory.DEATH,
        day_index=2,
    )
    entry = j.compose_entry(
        player_id="alice", day_index=2,
    )
    assert entry.mood == DayMood.SETBACK


def test_exploration_mood():
    j = PlayerJournalAI()
    for i in range(3):
        j.ingest_event(
            player_id="alice", kind="discovery",
            weight=EventWeight.POSITIVE,
            label="found landmark",
            category=EventCategory.EXPLORE,
            day_index=3,
        )
    entry = j.compose_entry(
        player_id="alice", day_index=3,
    )
    # Score = 30 -> TRIUMPH overrides; lower count
    j2 = PlayerJournalAI(triumph_threshold=999)
    for i in range(3):
        j2.ingest_event(
            player_id="alice", kind="discovery",
            weight=EventWeight.POSITIVE,
            label="found landmark",
            category=EventCategory.EXPLORE,
            day_index=3,
        )
    entry2 = j2.compose_entry(
        player_id="alice", day_index=3,
    )
    assert entry2.mood == DayMood.EXPLORATION


def test_social_mood():
    j = PlayerJournalAI(triumph_threshold=999)
    for _ in range(2):
        j.ingest_event(
            player_id="alice", kind="ls_event",
            weight=EventWeight.POSITIVE,
            label="ls victory",
            category=EventCategory.SOCIAL,
            day_index=4,
        )
    entry = j.compose_entry(
        player_id="alice", day_index=4,
    )
    assert entry.mood == DayMood.SOCIAL


def test_routine_mood_for_low_score():
    j = PlayerJournalAI()
    j.ingest_event(
        player_id="alice", kind="merchant_purchase",
        weight=EventWeight.NEUTRAL,
        label="bought arrows",
        category=EventCategory.CRAFT,
        day_index=5,
    )
    entry = j.compose_entry(
        player_id="alice", day_index=5,
    )
    assert entry.mood == DayMood.ROUTINE


def test_notable_event_picks_highest_magnitude():
    j = PlayerJournalAI()
    j.ingest_event(
        player_id="alice", kind="small",
        weight=EventWeight.POSITIVE,
        label="small win", day_index=6,
    )
    j.ingest_event(
        player_id="alice", kind="huge",
        weight=EventWeight.HUGE_POSITIVE,
        label="HUGE WIN", day_index=6,
    )
    entry = j.compose_entry(
        player_id="alice", day_index=6,
    )
    assert entry.notable_event_label == "HUGE WIN"


def test_score_aggregates():
    j = PlayerJournalAI()
    j.ingest_event(
        player_id="alice", kind="a",
        weight=EventWeight.HUGE_POSITIVE,
        label="a", day_index=7,
    )
    j.ingest_event(
        player_id="alice", kind="b",
        weight=EventWeight.NEGATIVE,
        label="b", day_index=7,
    )
    entry = j.compose_entry(
        player_id="alice", day_index=7,
    )
    # 30 + (-10) = 20
    assert entry.score == 20


def test_entries_for_sorted_by_day():
    j = PlayerJournalAI()
    j.ingest_event(
        player_id="alice", kind="x",
        weight=EventWeight.NEUTRAL,
        label="x", day_index=3,
    )
    j.ingest_event(
        player_id="alice", kind="x",
        weight=EventWeight.NEUTRAL,
        label="x", day_index=1,
    )
    j.ingest_event(
        player_id="alice", kind="x",
        weight=EventWeight.NEUTRAL,
        label="x", day_index=2,
    )
    entries = j.entries_for(player_id="alice")
    days = [e.day_index for e in entries]
    assert days == [1, 2, 3]


def test_per_player_isolation():
    j = PlayerJournalAI()
    j.ingest_event(
        player_id="alice", kind="x",
        weight=EventWeight.NEUTRAL,
        label="x", day_index=1,
    )
    assert j.compose_entry(
        player_id="alice", day_index=1,
    ) is not None
    assert j.compose_entry(
        player_id="bob", day_index=1,
    ) is None


def test_event_count_reported():
    j = PlayerJournalAI()
    for i in range(5):
        j.ingest_event(
            player_id="alice", kind=f"k_{i}",
            weight=EventWeight.NEUTRAL,
            label="x", day_index=8,
        )
    entry = j.compose_entry(
        player_id="alice", day_index=8,
    )
    assert entry.event_count == 5


def test_total_events_per_player():
    j = PlayerJournalAI()
    j.ingest_event(
        player_id="alice", kind="x",
        weight=EventWeight.NEUTRAL,
        label="x", day_index=1,
    )
    j.ingest_event(
        player_id="alice", kind="y",
        weight=EventWeight.NEUTRAL,
        label="y", day_index=2,
    )
    j.ingest_event(
        player_id="bob", kind="z",
        weight=EventWeight.NEUTRAL,
        label="z", day_index=1,
    )
    assert j.total_events(player_id="alice") == 2
    assert j.total_events(player_id="bob") == 1


def test_headline_format_changes_with_mood():
    j = PlayerJournalAI()
    j.ingest_event(
        player_id="alice", kind="boss_kill",
        weight=EventWeight.HUGE_POSITIVE,
        label="kill", day_index=1,
    )
    triumph_entry = j.compose_entry(
        player_id="alice", day_index=1,
    )
    j.ingest_event(
        player_id="alice", kind="death",
        weight=EventWeight.HUGE_NEGATIVE,
        label="death", day_index=2,
    )
    setback_entry = j.compose_entry(
        player_id="alice", day_index=2,
    )
    assert triumph_entry.headline != setback_entry.headline


def test_threshold_constants_ordered():
    from server.player_journal_ai import (
        SETBACK_THRESHOLD, TRIUMPH_THRESHOLD,
    )
    assert SETBACK_THRESHOLD < 0 < TRIUMPH_THRESHOLD
