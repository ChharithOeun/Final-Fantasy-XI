"""Tests for server_history_log."""
from __future__ import annotations

from server.server_history_log import (
    EventKind,
    QueryFilter,
    ServerHistoryLog,
)


def test_record_happy_returns_id():
    log = ServerHistoryLog()
    eid = log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="Vorrak the Crowned felled by Iron Wing",
        participants=["alice", "bob", "carol"],
        recorded_at=100,
        boss_id="vorrak",
    )
    assert eid == "hist_1"
    assert log.total_entries() == 1


def test_blank_summary_blocked():
    log = ServerHistoryLog()
    eid = log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="",
        participants=["alice"],
        recorded_at=10,
    )
    assert eid == ""
    assert log.total_entries() == 0


def test_no_participants_blocked_for_player_events():
    log = ServerHistoryLog()
    eid = log.record_event(
        kind=EventKind.PERFECT_RUN,
        summary="silent clear",
        participants=[],
        recorded_at=10,
    )
    assert eid == ""


def test_nation_victory_no_participants_ok():
    log = ServerHistoryLog()
    eid = log.record_event(
        kind=EventKind.NATION_VICTORY,
        summary="Bastok reclaims Zeruhn Mines",
        participants=[],
        recorded_at=10,
        region_id="zeruhn",
    )
    assert eid == "hist_1"


def test_expansion_unlock_no_participants_ok():
    log = ServerHistoryLog()
    eid = log.record_event(
        kind=EventKind.EXPANSION_UNLOCK,
        summary="Sea unlocked",
        participants=[],
        recorded_at=10,
    )
    assert eid == "hist_1"


def test_get_by_entry_id():
    log = ServerHistoryLog()
    eid = log.record_event(
        kind=EventKind.SPEED_RECORD,
        summary="Mirahna under 4m",
        participants=["alice"],
        recorded_at=50, boss_id="mirahna", value=237,
    )
    entry = log.get(entry_id=eid)
    assert entry is not None
    assert entry.summary == "Mirahna under 4m"
    assert entry.value == 237


def test_get_missing_returns_none():
    log = ServerHistoryLog()
    assert log.get(entry_id="hist_999") is None


def test_events_for_player_index():
    log = ServerHistoryLog()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="a",
        participants=["alice", "bob"], recorded_at=1,
        boss_id="b1",
    )
    log.record_event(
        kind=EventKind.PERFECT_RUN, summary="b",
        participants=["alice"], recorded_at=2,
        boss_id="b2",
    )
    log.record_event(
        kind=EventKind.SPEED_RECORD, summary="c",
        participants=["carol"], recorded_at=3,
        boss_id="b3",
    )
    alice_events = log.events_for_player(player_id="alice")
    assert len(alice_events) == 2
    bob_events = log.events_for_player(player_id="bob")
    assert len(bob_events) == 1
    nobody = log.events_for_player(player_id="zed")
    assert len(nobody) == 0


def test_events_for_boss_index():
    log = ServerHistoryLog()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="a",
        participants=["alice"], recorded_at=1, boss_id="vorrak",
    )
    log.record_event(
        kind=EventKind.SECOND_KILL, summary="b",
        participants=["bob"], recorded_at=2, boss_id="vorrak",
    )
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="c",
        participants=["carol"], recorded_at=3, boss_id="mirahna",
    )
    vorrak = log.events_for_boss(boss_id="vorrak")
    assert len(vorrak) == 2
    mirahna = log.events_for_boss(boss_id="mirahna")
    assert len(mirahna) == 1


def test_query_filter_by_kind():
    log = ServerHistoryLog()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="a",
        participants=["alice"], recorded_at=1, boss_id="b",
    )
    log.record_event(
        kind=EventKind.PERFECT_RUN, summary="b",
        participants=["alice"], recorded_at=2, boss_id="b",
    )
    out = log.query(qf=QueryFilter(kinds=(EventKind.WORLD_FIRST_KILL,)))
    assert len(out) == 1
    assert out[0].summary == "a"


def test_query_filter_by_boss():
    log = ServerHistoryLog()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="a",
        participants=["alice"], recorded_at=1, boss_id="vorrak",
    )
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="b",
        participants=["alice"], recorded_at=2, boss_id="mirahna",
    )
    out = log.query(qf=QueryFilter(boss_id="mirahna"))
    assert len(out) == 1
    assert out[0].summary == "b"


def test_query_filter_by_participant():
    log = ServerHistoryLog()
    log.record_event(
        kind=EventKind.PERFECT_RUN, summary="a",
        participants=["alice", "bob"], recorded_at=1, boss_id="b",
    )
    log.record_event(
        kind=EventKind.PERFECT_RUN, summary="b",
        participants=["carol"], recorded_at=2, boss_id="b",
    )
    out = log.query(qf=QueryFilter(participant_id="bob"))
    assert len(out) == 1
    assert out[0].summary == "a"


def test_query_filter_by_region():
    log = ServerHistoryLog()
    log.record_event(
        kind=EventKind.NATION_VICTORY, summary="a",
        participants=[], recorded_at=1, region_id="zeruhn",
    )
    log.record_event(
        kind=EventKind.NATION_VICTORY, summary="b",
        participants=[], recorded_at=2, region_id="ronfaure",
    )
    out = log.query(qf=QueryFilter(region_id="ronfaure"))
    assert len(out) == 1


def test_query_since_seconds():
    log = ServerHistoryLog()
    log.record_event(
        kind=EventKind.PERFECT_RUN, summary="a",
        participants=["alice"], recorded_at=10, boss_id="b",
    )
    log.record_event(
        kind=EventKind.PERFECT_RUN, summary="b",
        participants=["alice"], recorded_at=200, boss_id="b",
    )
    out = log.query(qf=QueryFilter(since_seconds=100))
    assert len(out) == 1
    assert out[0].summary == "b"


def test_query_combined_filters():
    log = ServerHistoryLog()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="a",
        participants=["alice"], recorded_at=10, boss_id="vorrak",
    )
    log.record_event(
        kind=EventKind.PERFECT_RUN, summary="b",
        participants=["alice"], recorded_at=20, boss_id="vorrak",
    )
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="c",
        participants=["bob"], recorded_at=30, boss_id="vorrak",
    )
    out = log.query(qf=QueryFilter(
        kinds=(EventKind.WORLD_FIRST_KILL,),
        participant_id="alice",
    ))
    assert len(out) == 1
    assert out[0].summary == "a"


def test_world_firsts_helper():
    log = ServerHistoryLog()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="a",
        participants=["alice"], recorded_at=1, boss_id="vorrak",
    )
    log.record_event(
        kind=EventKind.SECOND_KILL, summary="b",
        participants=["bob"], recorded_at=2, boss_id="vorrak",
    )
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="c",
        participants=["carol"], recorded_at=3, boss_id="mirahna",
    )
    firsts = log.world_firsts()
    assert len(firsts) == 2


def test_entries_are_immutable():
    import dataclasses as _dc
    log = ServerHistoryLog()
    eid = log.record_event(
        kind=EventKind.WORLD_FIRST_KILL, summary="a",
        participants=["alice"], recorded_at=1, boss_id="v",
    )
    entry = log.get(entry_id=eid)
    assert entry is not None
    try:
        entry.summary = "tampered"  # type: ignore
        assert False, "frozen dataclass should reject writes"
    except _dc.FrozenInstanceError:
        pass


def test_blank_participants_filtered():
    log = ServerHistoryLog()
    eid = log.record_event(
        kind=EventKind.PERFECT_RUN,
        summary="filtered run",
        participants=["alice", "", "bob"],
        recorded_at=10, boss_id="b",
    )
    entry = log.get(entry_id=eid)
    assert entry is not None
    assert entry.participants == ("alice", "bob")
