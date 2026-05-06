"""Tests for exploration_journal."""
from __future__ import annotations

from server.exploration_journal import EntryKind, ExplorationJournal


def test_record_happy():
    j = ExplorationJournal()
    ok = j.record(
        player_id="alice", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="ronfaure", zone_id="ronfaure",
        discovered_at=10,
    )
    assert ok is True
    assert j.total_entries() == 1


def test_blank_player_blocked():
    j = ExplorationJournal()
    out = j.record(
        player_id="", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="z", zone_id="z", discovered_at=10,
    )
    assert out is False


def test_blank_ref_blocked():
    j = ExplorationJournal()
    out = j.record(
        player_id="a", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="", zone_id="z", discovered_at=10,
    )
    assert out is False


def test_blank_zone_blocked():
    j = ExplorationJournal()
    out = j.record(
        player_id="a", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="r", zone_id="", discovered_at=10,
    )
    assert out is False


def test_dup_entry_dedup():
    j = ExplorationJournal()
    j.record(
        player_id="alice", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="ronfaure", zone_id="ronfaure",
        discovered_at=10,
    )
    again = j.record(
        player_id="alice", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="ronfaure", zone_id="ronfaure",
        discovered_at=20,
    )
    assert again is False
    assert j.total_entries() == 1


def test_entries_for_player():
    j = ExplorationJournal()
    j.record(
        player_id="alice", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="z1", zone_id="z1", discovered_at=10,
    )
    j.record(
        player_id="alice", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="z2", zone_id="z2", discovered_at=20,
    )
    j.record(
        player_id="bob", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="z3", zone_id="z3", discovered_at=30,
    )
    out = j.entries_for(player_id="alice")
    assert len(out) == 2


def test_entries_for_zone():
    j = ExplorationJournal()
    j.record(
        player_id="alice", kind=EntryKind.LANDMARK_FOUND,
        ref_id="cave_001", zone_id="ronfaure",
        discovered_at=10,
    )
    j.record(
        player_id="alice", kind=EntryKind.LANDMARK_FOUND,
        ref_id="cave_002", zone_id="ronfaure",
        discovered_at=20,
    )
    j.record(
        player_id="alice", kind=EntryKind.LANDMARK_FOUND,
        ref_id="cave_003", zone_id="gustav",
        discovered_at=30,
    )
    out = j.entries_for_zone(
        player_id="alice", zone_id="ronfaure",
    )
    assert len(out) == 2


def test_entries_of_kind():
    j = ExplorationJournal()
    j.record(
        player_id="alice", kind=EntryKind.LANDMARK_FOUND,
        ref_id="lm1", zone_id="z", discovered_at=10,
    )
    j.record(
        player_id="alice", kind=EntryKind.PASSAGE_DISCOVERED,
        ref_id="p1", zone_id="z", discovered_at=20,
    )
    j.record(
        player_id="alice", kind=EntryKind.LANDMARK_FOUND,
        ref_id="lm2", zone_id="z", discovered_at=30,
    )
    landmarks = j.entries_of_kind(
        player_id="alice", kind=EntryKind.LANDMARK_FOUND,
    )
    assert len(landmarks) == 2


def test_has_seen_true():
    j = ExplorationJournal()
    j.record(
        player_id="alice", kind=EntryKind.BOSS_FIRST_SIGHTING,
        ref_id="vorrak", zone_id="z", discovered_at=10,
    )
    assert j.has_seen(
        player_id="alice", kind=EntryKind.BOSS_FIRST_SIGHTING,
        ref_id="vorrak",
    ) is True


def test_has_seen_false():
    j = ExplorationJournal()
    assert j.has_seen(
        player_id="alice", kind=EntryKind.BOSS_FIRST_SIGHTING,
        ref_id="vorrak",
    ) is False


def test_has_seen_per_player():
    j = ExplorationJournal()
    j.record(
        player_id="alice", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="z1", zone_id="z1", discovered_at=10,
    )
    assert j.has_seen(
        player_id="bob", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="z1",
    ) is False


def test_per_kind_per_ref_independent():
    j = ExplorationJournal()
    # same ref_id, different kinds — both record independently
    j.record(
        player_id="alice", kind=EntryKind.LANDMARK_FOUND,
        ref_id="oasis", zone_id="z", discovered_at=10,
    )
    ok = j.record(
        player_id="alice", kind=EntryKind.PILGRIMAGE_DONE,
        ref_id="oasis", zone_id="z", discovered_at=20,
    )
    assert ok is True
    assert j.total_entries() == 2


def test_pilgrimage_done_kind():
    j = ExplorationJournal()
    j.record(
        player_id="alice", kind=EntryKind.PILGRIMAGE_DONE,
        ref_id="hero_path", zone_id="bastok",
        discovered_at=100,
    )
    assert j.has_seen(
        player_id="alice", kind=EntryKind.PILGRIMAGE_DONE,
        ref_id="hero_path",
    ) is True


def test_five_entry_kinds():
    assert len(list(EntryKind)) == 5


def test_entries_for_unknown_player_empty():
    j = ExplorationJournal()
    out = j.entries_for(player_id="ghost")
    assert out == ()


def test_entries_carry_kind_and_ref():
    j = ExplorationJournal()
    j.record(
        player_id="alice", kind=EntryKind.PASSAGE_DISCOVERED,
        ref_id="storm_path", zone_id="ronfaure",
        discovered_at=42,
    )
    entries = j.entries_for(player_id="alice")
    assert entries[0].kind == EntryKind.PASSAGE_DISCOVERED
    assert entries[0].ref_id == "storm_path"
    assert entries[0].discovered_at == 42
