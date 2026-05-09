"""Tests for player_travelogue."""
from __future__ import annotations

from server.player_travelogue import (
    PlayerTravelogueSystem, TravelogueState,
)


def _begin(s: PlayerTravelogueSystem) -> str:
    return s.begin(
        writer_id="alice", title="My Travels",
    )


def _published(s: PlayerTravelogueSystem) -> str:
    tid = _begin(s)
    s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=1,
        prose="Set out at dawn.",
    )
    s.publish(travelogue_id=tid, writer_id="alice")
    return tid


def test_begin_happy():
    s = PlayerTravelogueSystem()
    assert _begin(s) is not None


def test_begin_empty_title_blocked():
    s = PlayerTravelogueSystem()
    assert s.begin(
        writer_id="alice", title="",
    ) is None


def test_add_entry_happy():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    assert s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=1, prose="x",
    ) is True


def test_add_entry_wrong_writer_blocked():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    assert s.add_entry(
        travelogue_id=tid, writer_id="bob",
        zone="bastok", day=1, prose="x",
    ) is False


def test_add_entry_chronological_blocked():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=10, prose="x",
    )
    # Earlier day not allowed
    assert s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=5, prose="y",
    ) is False


def test_add_entry_same_day_ok():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=5, prose="x",
    )
    assert s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=5, prose="y",
    ) is True


def test_add_entry_empty_prose_blocked():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    assert s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=1, prose="",
    ) is False


def test_publish_happy():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=1, prose="x",
    )
    assert s.publish(
        travelogue_id=tid, writer_id="alice",
    ) is True


def test_publish_empty_blocked():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    assert s.publish(
        travelogue_id=tid, writer_id="alice",
    ) is False


def test_add_entry_after_publish_blocked():
    s = PlayerTravelogueSystem()
    tid = _published(s)
    assert s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=10, prose="late",
    ) is False


def test_postscript_happy():
    s = PlayerTravelogueSystem()
    tid = _published(s)
    assert s.add_postscript(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=2,
        prose="Returning home.",
    ) is True


def test_postscript_marked_as_postscript():
    s = PlayerTravelogueSystem()
    tid = _published(s)
    s.add_postscript(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=2, prose="ps",
    )
    entries = s.entries(travelogue_id=tid)
    assert entries[-1].is_postscript is True


def test_postscript_on_draft_blocked():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    assert s.add_postscript(
        travelogue_id=tid, writer_id="alice",
        zone="x", day=1, prose="ps",
    ) is False


def test_like_happy():
    s = PlayerTravelogueSystem()
    tid = _published(s)
    assert s.like(
        travelogue_id=tid, reader_id="bob",
    ) is True


def test_like_writer_self_blocked():
    s = PlayerTravelogueSystem()
    tid = _published(s)
    assert s.like(
        travelogue_id=tid, reader_id="alice",
    ) is False


def test_like_dup_blocked():
    s = PlayerTravelogueSystem()
    tid = _published(s)
    s.like(travelogue_id=tid, reader_id="bob")
    assert s.like(
        travelogue_id=tid, reader_id="bob",
    ) is False


def test_like_draft_blocked():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    assert s.like(
        travelogue_id=tid, reader_id="bob",
    ) is False


def test_like_count_tracked():
    s = PlayerTravelogueSystem()
    tid = _published(s)
    s.like(travelogue_id=tid, reader_id="b")
    s.like(travelogue_id=tid, reader_id="c")
    s.like(travelogue_id=tid, reader_id="d")
    assert s.travelogue(
        travelogue_id=tid,
    ).likes == 3


def test_archive_happy():
    s = PlayerTravelogueSystem()
    tid = _published(s)
    assert s.archive(
        travelogue_id=tid, writer_id="alice",
    ) is True


def test_archive_wrong_writer_blocked():
    s = PlayerTravelogueSystem()
    tid = _published(s)
    assert s.archive(
        travelogue_id=tid, writer_id="bob",
    ) is False


def test_entries_listing():
    s = PlayerTravelogueSystem()
    tid = _begin(s)
    s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="bastok", day=1, prose="x",
    )
    s.add_entry(
        travelogue_id=tid, writer_id="alice",
        zone="zulkheim", day=2, prose="y",
    )
    assert len(s.entries(travelogue_id=tid)) == 2


def test_by_writer_listing():
    s = PlayerTravelogueSystem()
    _begin(s)
    s.begin(writer_id="alice", title="Other Trip")
    assert len(s.by_writer(writer_id="alice")) == 2


def test_unknown_travelogue():
    s = PlayerTravelogueSystem()
    assert s.travelogue(
        travelogue_id="ghost",
    ) is None


def test_state_count():
    assert len(list(TravelogueState)) == 3
