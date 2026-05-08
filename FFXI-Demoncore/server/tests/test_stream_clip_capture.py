"""Tests for stream_clip_capture."""
from __future__ import annotations

from server.stream_clip_capture import StreamClipCapture
from server.stream_overlay import (
    OverlayEvent, OverlayEventKind,
)


def _ev(payload, ts, sid="s1",
        kind=OverlayEventKind.JA_USED):
    return OverlayEvent(
        session_id=sid, kind=kind,
        payload=payload, timestamp=ts,
    )


def test_capture_happy():
    c = StreamClipCapture()
    events = [_ev("a", 1000), _ev("b", 1010)]
    out = c.capture(
        clipper_id="bob", session_id="s1",
        title="Maat solo", events=events, now=1020,
    )
    assert out is not None
    assert out.title == "Maat solo"


def test_capture_blank_clipper_blocked():
    c = StreamClipCapture()
    out = c.capture(
        clipper_id="", session_id="s1", title="x",
        events=[], now=1000,
    )
    assert out is None


def test_capture_blank_session_blocked():
    c = StreamClipCapture()
    out = c.capture(
        clipper_id="bob", session_id="", title="x",
        events=[], now=1000,
    )
    assert out is None


def test_capture_default_title_when_blank():
    c = StreamClipCapture()
    out = c.capture(
        clipper_id="bob", session_id="s1", title="",
        events=[], now=1000,
    )
    assert out is not None
    assert out.title.startswith("clip ")


def test_capture_long_title_blocked():
    c = StreamClipCapture()
    out = c.capture(
        clipper_id="bob", session_id="s1",
        title="x" * 81, events=[], now=1000,
    )
    assert out is None


def test_capture_filters_to_30s_window():
    c = StreamClipCapture()
    events = [
        _ev("old", 900),         # outside window
        _ev("recent_a", 980),    # inside
        _ev("recent_b", 1000),   # inside
        _ev("future", 1100),     # > now, dropped
    ]
    out = c.capture(
        clipper_id="bob", session_id="s1", title="t",
        events=events, now=1010,
    )
    assert len(out.events) == 2
    assert all(
        980 <= e.timestamp <= 1010 for e in out.events
    )


def test_capture_filters_other_session():
    c = StreamClipCapture()
    events = [
        _ev("mine", 1000, sid="s1"),
        _ev("theirs", 1000, sid="s2"),
    ]
    out = c.capture(
        clipper_id="bob", session_id="s1", title="t",
        events=events, now=1010,
    )
    assert len(out.events) == 1


def test_capture_rate_limit_60s():
    c = StreamClipCapture()
    c.capture(
        clipper_id="bob", session_id="s1", title="a",
        events=[], now=1000,
    )
    out = c.capture(
        clipper_id="bob", session_id="s1", title="b",
        events=[], now=1030,
    )
    assert out is None


def test_capture_rate_limit_releases_after_60s():
    c = StreamClipCapture()
    c.capture(
        clipper_id="bob", session_id="s1", title="a",
        events=[], now=1000,
    )
    out = c.capture(
        clipper_id="bob", session_id="s1", title="b",
        events=[], now=1061,
    )
    assert out is not None


def test_capture_rate_limit_per_session():
    """Bob can clip session A and session B back-to-back."""
    c = StreamClipCapture()
    c.capture(
        clipper_id="bob", session_id="s1", title="a",
        events=[], now=1000,
    )
    out = c.capture(
        clipper_id="bob", session_id="s2", title="b",
        events=[], now=1010,
    )
    assert out is not None


def test_get_returns_clip():
    c = StreamClipCapture()
    out = c.capture(
        clipper_id="bob", session_id="s1", title="t",
        events=[], now=1000,
    )
    assert c.get(clip_id=out.clip_id) is not None


def test_get_unknown_none():
    c = StreamClipCapture()
    assert c.get(clip_id="ghost") is None


def test_clips_by_sorted_newest_first():
    c = StreamClipCapture()
    c.capture(
        clipper_id="bob", session_id="s1", title="first",
        events=[], now=1000,
    )
    c.capture(
        clipper_id="bob", session_id="s2", title="second",
        events=[], now=2000,
    )
    out = c.clips_by(clipper_id="bob")
    assert out[0].title == "second"


def test_clips_for_session_sorted():
    c = StreamClipCapture()
    c.capture(
        clipper_id="bob", session_id="s1", title="b1",
        events=[], now=1000,
    )
    c.capture(
        clipper_id="cara", session_id="s1", title="c1",
        events=[], now=2000,
    )
    out = c.clips_for_session(session_id="s1")
    assert len(out) == 2
    assert out[0].title == "b1"


def test_delete_owner_only():
    c = StreamClipCapture()
    out = c.capture(
        clipper_id="bob", session_id="s1", title="t",
        events=[], now=1000,
    )
    assert c.delete(
        clip_id=out.clip_id, clipper_id="bob",
    ) is True


def test_delete_non_owner_blocked():
    c = StreamClipCapture()
    out = c.capture(
        clipper_id="bob", session_id="s1", title="t",
        events=[], now=1000,
    )
    assert c.delete(
        clip_id=out.clip_id, clipper_id="impostor",
    ) is False


def test_delete_unknown_clip():
    c = StreamClipCapture()
    assert c.delete(
        clip_id="ghost", clipper_id="bob",
    ) is False


def test_total_clips():
    c = StreamClipCapture()
    c.capture(
        clipper_id="bob", session_id="s1", title="a",
        events=[], now=1000,
    )
    c.capture(
        clipper_id="cara", session_id="s2", title="b",
        events=[], now=2000,
    )
    assert c.total_clips() == 2
