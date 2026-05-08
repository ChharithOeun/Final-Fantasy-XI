"""Tests for spectator_pool."""
from __future__ import annotations

from server.spectator_pool import SpectatorPool
from server.streaming_session import (
    Privacy, StreamingSessionRegistry,
)


def _start(privacy=Privacy.PUBLIC, broadcaster="chharith"):
    r = StreamingSessionRegistry()
    s = r.start(
        broadcaster_id=broadcaster, privacy=privacy,
        started_at=1000,
        linkshell_id=(
            "ls_a" if privacy == Privacy.LINKSHELL_ONLY
            else ""
        ),
    )
    return r, s


def test_join_happy():
    _, s = _start()
    p = SpectatorPool()
    out = p.join(
        viewer_id="bob", session=s,
        can_view_predicate=lambda: True, joined_at=1500,
    )
    assert out.success is True


def test_join_blank_viewer():
    _, s = _start()
    p = SpectatorPool()
    out = p.join(
        viewer_id="", session=s,
        can_view_predicate=lambda: True, joined_at=1500,
    )
    assert out.success is False
    assert out.reason == "viewer_id_required"


def test_join_self_blocked():
    _, s = _start()
    p = SpectatorPool()
    out = p.join(
        viewer_id="chharith", session=s,
        can_view_predicate=lambda: True, joined_at=1500,
    )
    assert out.success is False
    assert out.reason == "self_view"


def test_join_session_ended_blocked():
    r, s = _start()
    r.end(broadcaster_id="chharith", ended_at=2000)
    ended = r._sessions[s.session_id]
    p = SpectatorPool()
    out = p.join(
        viewer_id="bob", session=ended,
        can_view_predicate=lambda: True, joined_at=2500,
    )
    assert out.reason == "session_not_active"


def test_join_privacy_blocked():
    _, s = _start()
    p = SpectatorPool()
    out = p.join(
        viewer_id="bob", session=s,
        can_view_predicate=lambda: False,
        joined_at=1500,
    )
    assert out.reason == "privacy_blocked"


def test_join_idempotent():
    _, s = _start()
    p = SpectatorPool()
    p.join(
        viewer_id="bob", session=s,
        can_view_predicate=lambda: True, joined_at=1500,
    )
    out = p.join(
        viewer_id="bob", session=s,
        can_view_predicate=lambda: True, joined_at=1600,
    )
    assert out.success is True
    assert p.viewer_count(session_id=s.session_id) == 1


def test_join_public_cap_100():
    _, s = _start()
    p = SpectatorPool()
    for i in range(100):
        p.join(
            viewer_id=f"v{i}", session=s,
            can_view_predicate=lambda: True,
            joined_at=1500,
        )
    out = p.join(
        viewer_id="overflow", session=s,
        can_view_predicate=lambda: True, joined_at=1600,
    )
    assert out.success is False
    assert out.reason == "at_capacity"


def test_friends_cap_30():
    _, s = _start(privacy=Privacy.FRIENDS_ONLY)
    p = SpectatorPool()
    for i in range(30):
        p.join(
            viewer_id=f"v{i}", session=s,
            can_view_predicate=lambda: True,
            joined_at=1500,
        )
    out = p.join(
        viewer_id="overflow", session=s,
        can_view_predicate=lambda: True, joined_at=1600,
    )
    assert out.reason == "at_capacity"


def test_linkshell_cap_50():
    _, s = _start(privacy=Privacy.LINKSHELL_ONLY)
    p = SpectatorPool()
    for i in range(50):
        p.join(
            viewer_id=f"v{i}", session=s,
            can_view_predicate=lambda: True,
            joined_at=1500,
        )
    out = p.join(
        viewer_id="overflow", session=s,
        can_view_predicate=lambda: True, joined_at=1600,
    )
    assert out.reason == "at_capacity"


def test_join_auto_leaves_prior_stream():
    r = StreamingSessionRegistry()
    s1 = r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    s2 = r.start(
        broadcaster_id="rival", privacy=Privacy.PUBLIC,
        started_at=1100,
    )
    p = SpectatorPool()
    p.join(
        viewer_id="bob", session=s1,
        can_view_predicate=lambda: True, joined_at=1500,
    )
    p.join(
        viewer_id="bob", session=s2,
        can_view_predicate=lambda: True, joined_at=1600,
    )
    assert p.viewer_count(session_id=s1.session_id) == 0
    assert p.viewer_count(session_id=s2.session_id) == 1


def test_leave_happy():
    _, s = _start()
    p = SpectatorPool()
    p.join(
        viewer_id="bob", session=s,
        can_view_predicate=lambda: True, joined_at=1500,
    )
    assert p.leave(viewer_id="bob") is True
    assert p.viewer_count(session_id=s.session_id) == 0


def test_leave_unknown():
    p = SpectatorPool()
    assert p.leave(viewer_id="ghost") is False


def test_viewers_of_sorted():
    _, s = _start()
    p = SpectatorPool()
    for v in ["zed", "alice", "bob"]:
        p.join(
            viewer_id=v, session=s,
            can_view_predicate=lambda: True,
            joined_at=1500,
        )
    out = p.viewers_of(session_id=s.session_id)
    assert out == ["alice", "bob", "zed"]


def test_viewer_count_zero_unknown():
    p = SpectatorPool()
    assert p.viewer_count(session_id="ghost") == 0


def test_watching_what_returns_session():
    _, s = _start()
    p = SpectatorPool()
    p.join(
        viewer_id="bob", session=s,
        can_view_predicate=lambda: True, joined_at=1500,
    )
    assert p.watching_what(
        viewer_id="bob",
    ) == s.session_id


def test_watching_what_unknown_none():
    p = SpectatorPool()
    assert p.watching_what(viewer_id="ghost") is None


def test_clear_session_ejects_all():
    _, s = _start()
    p = SpectatorPool()
    for v in ["bob", "cara", "dan"]:
        p.join(
            viewer_id=v, session=s,
            can_view_predicate=lambda: True,
            joined_at=1500,
        )
    n = p.clear_session(session_id=s.session_id)
    assert n == 3
    assert p.viewer_count(session_id=s.session_id) == 0
    for v in ["bob", "cara", "dan"]:
        assert p.watching_what(viewer_id=v) is None


def test_total_viewers():
    r = StreamingSessionRegistry()
    s1 = r.start(
        broadcaster_id="chharith", privacy=Privacy.PUBLIC,
        started_at=1000,
    )
    s2 = r.start(
        broadcaster_id="rival", privacy=Privacy.PUBLIC,
        started_at=1100,
    )
    p = SpectatorPool()
    p.join(
        viewer_id="bob", session=s1,
        can_view_predicate=lambda: True, joined_at=1500,
    )
    p.join(
        viewer_id="cara", session=s2,
        can_view_predicate=lambda: True, joined_at=1500,
    )
    assert p.total_viewers() == 2
