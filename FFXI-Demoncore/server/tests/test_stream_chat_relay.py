"""Tests for stream_chat_relay."""
from __future__ import annotations

from server.stream_chat_relay import StreamChatRelay


def _seed():
    r = StreamChatRelay()
    r.register_session(
        session_id="s1", broadcaster_id="chharith",
    )
    return r


def test_register_session():
    r = StreamChatRelay()
    assert r.register_session(
        session_id="s1", broadcaster_id="chharith",
    ) is True


def test_register_blank_blocked():
    r = StreamChatRelay()
    assert r.register_session(
        session_id="", broadcaster_id="chharith",
    ) is False


def test_send_happy():
    r = _seed()
    out = r.send(
        viewer_id="bob", session_id="s1",
        body="nice solo!", now=1000,
    )
    assert out.success is True


def test_send_blank_ids_blocked():
    r = _seed()
    out = r.send(
        viewer_id="", session_id="s1",
        body="x", now=1000,
    )
    assert out.success is False


def test_send_blank_body_blocked():
    r = _seed()
    out = r.send(
        viewer_id="bob", session_id="s1",
        body="   ", now=1000,
    )
    assert out.success is False
    assert out.reason == "empty_body"


def test_send_too_long_blocked():
    r = _seed()
    out = r.send(
        viewer_id="bob", session_id="s1",
        body="x" * 201, now=1000,
    )
    assert out.success is False
    assert out.reason == "body_too_long"


def test_send_rate_limited():
    r = _seed()
    for i in range(5):
        r.send(
            viewer_id="bob", session_id="s1",
            body=f"msg {i}", now=1000 + i,
        )
    out = r.send(
        viewer_id="bob", session_id="s1",
        body="overflow", now=1010,
    )
    assert out.success is False
    assert out.reason == "rate_limited"


def test_send_rate_limit_window_resets():
    r = _seed()
    for i in range(5):
        r.send(
            viewer_id="bob", session_id="s1",
            body=f"msg {i}", now=1000 + i,
        )
    # 31 seconds later, the window resets
    out = r.send(
        viewer_id="bob", session_id="s1",
        body="fresh", now=1031,
    )
    assert out.success is True


def test_mute_blocks_send():
    r = _seed()
    r.mute(
        broadcaster_id="chharith", viewer_id="bob",
        session_id="s1",
    )
    out = r.send(
        viewer_id="bob", session_id="s1",
        body="hi", now=1000,
    )
    assert out.reason == "muted"


def test_mute_non_owner_blocked():
    r = _seed()
    out = r.mute(
        broadcaster_id="impostor", viewer_id="bob",
        session_id="s1",
    )
    assert out is False


def test_ban_blocks_send():
    r = _seed()
    r.ban(
        broadcaster_id="chharith", viewer_id="bob",
        session_id="s1",
    )
    out = r.send(
        viewer_id="bob", session_id="s1",
        body="hi", now=1000,
    )
    assert out.reason == "banned"


def test_ban_non_owner_blocked():
    r = _seed()
    out = r.ban(
        broadcaster_id="impostor", viewer_id="bob",
        session_id="s1",
    )
    assert out is False


def test_is_muted_query():
    r = _seed()
    assert r.is_muted(
        viewer_id="bob", session_id="s1",
    ) is False
    r.mute(
        broadcaster_id="chharith", viewer_id="bob",
        session_id="s1",
    )
    assert r.is_muted(
        viewer_id="bob", session_id="s1",
    ) is True


def test_is_banned_query():
    r = _seed()
    assert r.is_banned(
        viewer_id="bob", session_id="s1",
    ) is False
    r.ban(
        broadcaster_id="chharith", viewer_id="bob",
        session_id="s1",
    )
    assert r.is_banned(
        viewer_id="bob", session_id="s1",
    ) is True


def test_recent_returns_session_only():
    r = _seed()
    r.register_session(
        session_id="s2", broadcaster_id="rival",
    )
    r.send(
        viewer_id="bob", session_id="s1",
        body="a", now=1000,
    )
    r.send(
        viewer_id="bob", session_id="s2",
        body="b", now=1100,
    )
    out = r.recent(session_id="s1")
    assert len(out) == 1
    assert out[0].body == "a"


def test_recent_zero_limit():
    r = _seed()
    r.send(
        viewer_id="bob", session_id="s1",
        body="x", now=1000,
    )
    assert r.recent(session_id="s1", limit=0) == []


def test_recent_limit_caps():
    r = _seed()
    for i in range(10):
        r.send(
            viewer_id=f"v{i}", session_id="s1",
            body=f"m{i}", now=1000 + i,
        )
    out = r.recent(session_id="s1", limit=3)
    assert len(out) == 3


def test_clear_session():
    r = _seed()
    r.register_session(
        session_id="s2", broadcaster_id="rival",
    )
    r.send(
        viewer_id="bob", session_id="s1",
        body="a", now=1000,
    )
    r.send(
        viewer_id="bob", session_id="s2",
        body="b", now=1100,
    )
    n = r.clear_session(session_id="s1")
    assert n == 1
    assert r.recent(session_id="s1") == []
    assert len(r.recent(session_id="s2")) == 1


def test_total_messages():
    r = _seed()
    r.send(
        viewer_id="bob", session_id="s1",
        body="a", now=1000,
    )
    r.send(
        viewer_id="cara", session_id="s1",
        body="b", now=1010,
    )
    assert r.total_messages() == 2
