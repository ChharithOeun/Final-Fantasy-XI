"""Tests for stream_overlay."""
from __future__ import annotations

from server.stream_overlay import (
    OverlayEventKind, StreamOverlay,
)


def test_record_happy():
    o = StreamOverlay()
    out = o.record(
        session_id="s1", kind=OverlayEventKind.GEAR_CHANGE,
        payload="head: fenrir's stone", timestamp=1000,
    )
    assert out is True


def test_record_blank_session_blocked():
    o = StreamOverlay()
    assert o.record(
        session_id="", kind=OverlayEventKind.GEAR_CHANGE,
        payload="x", timestamp=1000,
    ) is False


def test_record_blank_payload_blocked():
    o = StreamOverlay()
    assert o.record(
        session_id="s1", kind=OverlayEventKind.GEAR_CHANGE,
        payload="  ", timestamp=1000,
    ) is False


def test_record_out_of_order_blocked():
    o = StreamOverlay()
    o.record(
        session_id="s1", kind=OverlayEventKind.SPELL_CAST,
        payload="fire iv", timestamp=2000,
    )
    out = o.record(
        session_id="s1", kind=OverlayEventKind.SPELL_CAST,
        payload="firaja", timestamp=1000,
    )
    assert out is False


def test_recent_returns_in_order():
    o = StreamOverlay()
    for i, payload in enumerate(["a", "b", "c"]):
        o.record(
            session_id="s1",
            kind=OverlayEventKind.JA_USED,
            payload=payload, timestamp=1000 + i,
        )
    out = o.recent(session_id="s1")
    assert [e.payload for e in out] == ["a", "b", "c"]


def test_recent_limit():
    o = StreamOverlay()
    for i in range(5):
        o.record(
            session_id="s1",
            kind=OverlayEventKind.JA_USED,
            payload=f"e{i}", timestamp=1000 + i,
        )
    out = o.recent(session_id="s1", limit=2)
    assert len(out) == 2
    # Last two events
    assert out[0].payload == "e3"
    assert out[1].payload == "e4"


def test_recent_zero_limit_empty():
    o = StreamOverlay()
    o.record(
        session_id="s1", kind=OverlayEventKind.JA_USED,
        payload="x", timestamp=1000,
    )
    assert o.recent(session_id="s1", limit=0) == []


def test_recent_unknown_session_empty():
    o = StreamOverlay()
    assert o.recent(session_id="ghost") == []


def test_buffer_cap_drops_oldest():
    o = StreamOverlay()
    for i in range(120):
        o.record(
            session_id="s1",
            kind=OverlayEventKind.JA_USED,
            payload=f"e{i}", timestamp=1000 + i,
        )
    out = o.recent(session_id="s1", limit=200)
    assert len(out) == 100
    # Oldest 20 events were trimmed
    assert out[0].payload == "e20"
    assert out[-1].payload == "e119"


def test_latest_by_kind_finds_most_recent():
    o = StreamOverlay()
    o.record(
        session_id="s1", kind=OverlayEventKind.SPELL_CAST,
        payload="fire", timestamp=1000,
    )
    o.record(
        session_id="s1", kind=OverlayEventKind.JA_USED,
        payload="conserve mp", timestamp=1100,
    )
    o.record(
        session_id="s1", kind=OverlayEventKind.SPELL_CAST,
        payload="fire iv", timestamp=1200,
    )
    out = o.latest_by_kind(
        session_id="s1", kind=OverlayEventKind.SPELL_CAST,
    )
    assert out.payload == "fire iv"


def test_latest_by_kind_no_match_none():
    o = StreamOverlay()
    o.record(
        session_id="s1", kind=OverlayEventKind.JA_USED,
        payload="x", timestamp=1000,
    )
    out = o.latest_by_kind(
        session_id="s1", kind=OverlayEventKind.HP_TIER,
    )
    assert out is None


def test_latest_by_kind_unknown_session_none():
    o = StreamOverlay()
    out = o.latest_by_kind(
        session_id="ghost",
        kind=OverlayEventKind.JA_USED,
    )
    assert out is None


def test_clear_session():
    o = StreamOverlay()
    for i in range(5):
        o.record(
            session_id="s1",
            kind=OverlayEventKind.JA_USED,
            payload=f"e{i}", timestamp=1000 + i,
        )
    n = o.clear_session(session_id="s1")
    assert n == 5
    assert o.recent(session_id="s1") == []


def test_clear_session_unknown_zero():
    o = StreamOverlay()
    assert o.clear_session(session_id="ghost") == 0


def test_total_events():
    o = StreamOverlay()
    o.record(
        session_id="s1", kind=OverlayEventKind.JA_USED,
        payload="a", timestamp=1000,
    )
    o.record(
        session_id="s2", kind=OverlayEventKind.JA_USED,
        payload="b", timestamp=2000,
    )
    assert o.total_events() == 2


def test_five_event_kinds():
    assert len(list(OverlayEventKind)) == 5
