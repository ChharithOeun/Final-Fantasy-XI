"""Tests for the player chronicle."""
from __future__ import annotations

from server.player_chronicle import (
    ChronicleEventKind,
    ChronicleRegistry,
)


def test_record_event():
    reg = ChronicleRegistry()
    e = reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NM_KILL,
        summary="slew Zerde",
        details="at Crag of Mea",
        now_seconds=100.0,
    )
    assert e.player_id == "alice"
    assert e.summary == "slew Zerde"
    assert reg.total("alice") == 1


def test_for_player_lists_in_order():
    reg = ChronicleRegistry()
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NM_KILL,
        summary="slew Zerde",
    )
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.BOSS_KILL,
        summary="defeated Maat",
    )
    entries = reg.for_player("alice")
    assert len(entries) == 2
    assert entries[0].summary == "slew Zerde"
    assert entries[1].summary == "defeated Maat"


def test_by_kind_filters():
    reg = ChronicleRegistry()
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NM_KILL,
        summary="slew Zerde",
    )
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NM_KILL,
        summary="slew Argus",
    )
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.LEVEL_MILESTONE,
        summary="reached lvl 50",
    )
    nm = reg.by_kind(
        player_id="alice", kind=ChronicleEventKind.NM_KILL,
    )
    assert len(nm) == 2


def test_isolated_per_player():
    reg = ChronicleRegistry()
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NM_KILL,
        summary="slew Zerde",
    )
    reg.record(
        player_id="bob",
        kind=ChronicleEventKind.NM_KILL,
        summary="slew Argus",
    )
    a = reg.for_player("alice")
    b = reg.for_player("bob")
    assert len(a) == 1
    assert len(b) == 1
    assert a[0].summary != b[0].summary


def test_unknown_player_empty():
    reg = ChronicleRegistry()
    assert reg.for_player("ghost") == ()
    assert reg.total("ghost") == 0


def test_last_n_returns_recent():
    reg = ChronicleRegistry()
    for i in range(10):
        reg.record(
            player_id="alice",
            kind=ChronicleEventKind.NM_KILL,
            summary=f"kill {i}",
        )
    last3 = reg.last_n(player_id="alice", n=3)
    assert len(last3) == 3
    assert last3[0].summary == "kill 7"
    assert last3[2].summary == "kill 9"


def test_last_n_zero_returns_empty():
    reg = ChronicleRegistry()
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NM_KILL,
        summary="x",
    )
    assert reg.last_n(player_id="alice", n=0) == ()


def test_last_n_more_than_total():
    reg = ChronicleRegistry()
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NM_KILL,
        summary="x",
    )
    last100 = reg.last_n(player_id="alice", n=100)
    assert len(last100) == 1


def test_recent_summary_renders_lines():
    reg = ChronicleRegistry()
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NM_KILL,
        summary="slew Zerde",
    )
    summary = reg.recent_summary(player_id="alice", top_n=5)
    assert "nm_kill" in summary
    assert "slew Zerde" in summary


def test_recent_summary_empty_message():
    reg = ChronicleRegistry()
    s = reg.recent_summary(player_id="ghost")
    assert "no recorded deeds" in s


def test_has_event_kind():
    reg = ChronicleRegistry()
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.PERMADEATH,
        summary="fell at Sky",
    )
    assert reg.has_event_kind(
        player_id="alice",
        kind=ChronicleEventKind.PERMADEATH,
    )
    assert not reg.has_event_kind(
        player_id="alice",
        kind=ChronicleEventKind.SERVER_FIRST,
    )


def test_full_lifecycle_alice_chronicle():
    """Alice levels, kills NMs, completes a chain, dies. Each
    entry surfaces in the chronicle and recent_summary picks
    the latest."""
    reg = ChronicleRegistry()
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.LEVEL_MILESTONE,
        summary="reached lvl 50",
        now_seconds=100.0,
    )
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NM_KILL,
        summary="slew Zerde",
        now_seconds=200.0,
    )
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.QUEST_CHAIN_COMPLETE,
        summary="completed Steel Republic",
        now_seconds=300.0,
    )
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.NEW_TITLE,
        summary="title_steel_hero",
        now_seconds=300.0,
    )
    reg.record(
        player_id="alice",
        kind=ChronicleEventKind.PERMADEATH,
        summary="fell at the Crystal War",
        now_seconds=10000.0,
    )
    assert reg.total("alice") == 5
    summary = reg.recent_summary(player_id="alice", top_n=3)
    assert "permadeath" in summary
    assert "Crystal War" in summary
    assert reg.has_event_kind(
        player_id="alice",
        kind=ChronicleEventKind.PERMADEATH,
    )
