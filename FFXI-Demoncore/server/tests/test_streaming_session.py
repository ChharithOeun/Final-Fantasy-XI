"""Tests for streaming_session."""
from __future__ import annotations

from server.streaming_session import (
    Privacy, SessionStatus, StreamingSessionRegistry,
)


def test_start_happy():
    r = StreamingSessionRegistry()
    s = r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    assert s is not None
    assert s.status == SessionStatus.ACTIVE


def test_start_blank_blocked():
    r = StreamingSessionRegistry()
    assert r.start(
        broadcaster_id="", privacy=Privacy.PUBLIC,
        started_at=1000,
    ) is None


def test_start_linkshell_requires_id():
    r = StreamingSessionRegistry()
    assert r.start(
        broadcaster_id="chharith",
        privacy=Privacy.LINKSHELL_ONLY,
        started_at=1000,
    ) is None


def test_start_linkshell_with_id_ok():
    r = StreamingSessionRegistry()
    s = r.start(
        broadcaster_id="chharith",
        privacy=Privacy.LINKSHELL_ONLY,
        linkshell_id="ls_alpha", started_at=1000,
    )
    assert s.linkshell_id == "ls_alpha"


def test_start_friends_ignores_linkshell_id():
    r = StreamingSessionRegistry()
    s = r.start(
        broadcaster_id="chharith",
        privacy=Privacy.FRIENDS_ONLY,
        linkshell_id="ls_alpha", started_at=1000,
    )
    assert s.linkshell_id == ""


def test_start_idempotent_returns_existing():
    r = StreamingSessionRegistry()
    s1 = r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    s2 = r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=2000,
    )
    assert s1.session_id == s2.session_id


def test_unique_session_ids_per_broadcaster_after_end():
    r = StreamingSessionRegistry()
    s1 = r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    r.end(broadcaster_id="chharith", ended_at=2000)
    s2 = r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=3000,
    )
    assert s1.session_id != s2.session_id


def test_end_marks_terminal():
    r = StreamingSessionRegistry()
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    assert r.end(
        broadcaster_id="chharith", ended_at=2000,
    ) is True
    assert r.session_for(broadcaster_id="chharith") is None


def test_end_unknown_broadcaster():
    r = StreamingSessionRegistry()
    assert r.end(
        broadcaster_id="ghost", ended_at=2000,
    ) is False


def test_heartbeat_updates_activity():
    r = StreamingSessionRegistry()
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    assert r.heartbeat(
        broadcaster_id="chharith", now=2000,
    ) is True
    s = r.session_for(broadcaster_id="chharith")
    assert s.last_activity_at == 2000


def test_heartbeat_clock_skew_rejected():
    r = StreamingSessionRegistry()
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=2000,
    )
    out = r.heartbeat(
        broadcaster_id="chharith", now=1000,
    )
    assert out is False


def test_heartbeat_no_session_false():
    r = StreamingSessionRegistry()
    assert r.heartbeat(
        broadcaster_id="chharith", now=1000,
    ) is False


def test_session_for_returns_active():
    r = StreamingSessionRegistry()
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    s = r.session_for(broadcaster_id="chharith")
    assert s is not None


def test_session_for_unknown_none():
    r = StreamingSessionRegistry()
    assert r.session_for(broadcaster_id="ghost") is None


def test_live_sessions_lists_active():
    r = StreamingSessionRegistry()
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    r.start(
        broadcaster_id="bob", privacy=Privacy.PUBLIC,
        started_at=2000,
    )
    out = r.live_sessions()
    assert len(out) == 2
    # Newest first
    assert out[0].broadcaster_id == "bob"


def test_live_excludes_ended():
    r = StreamingSessionRegistry()
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    r.end(broadcaster_id="chharith", ended_at=2000)
    assert r.live_sessions() == []


def test_reap_idle_zero_when_fresh():
    r = StreamingSessionRegistry()
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    n = r.reap_idle(now=1500)
    assert n == 0


def test_reap_idle_ends_stale():
    r = StreamingSessionRegistry()
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    # 31 minutes later, no heartbeat
    n = r.reap_idle(now=1000 + 31 * 60)
    assert n == 1
    assert r.session_for(
        broadcaster_id="chharith",
    ) is None


def test_total_sessions_persists_history():
    r = StreamingSessionRegistry()
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    r.end(broadcaster_id="chharith", ended_at=2000)
    r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=3000,
    )
    assert r.total_sessions() == 2


def test_three_privacy_levels():
    assert len(list(Privacy)) == 3


def test_two_session_statuses():
    assert len(list(SessionStatus)) == 2
