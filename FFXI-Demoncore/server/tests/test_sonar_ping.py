"""Tests for sonar ping."""
from __future__ import annotations

from server.sonar_ping import (
    ACTIVE_RADIUS,
    PASSIVE_RADIUS,
    PING_COOLDOWN_SECONDS,
    SonarPing,
)


def test_register_happy():
    s = SonarPing()
    ok = s.register(sub_id="sub1", x=0, y=0, band=2, has_passive=False)
    assert ok is True


def test_register_blank_id():
    s = SonarPing()
    ok = s.register(sub_id="", x=0, y=0, band=2)
    assert ok is False


def test_active_ping_reveals_close():
    s = SonarPing()
    s.register(sub_id="me", x=0, y=0, band=2)
    s.register(sub_id="them", x=100, y=0, band=2)
    r = s.active_ping(sub_id="me", now_seconds=0)
    assert r.accepted is True
    assert len(r.reveals) == 1
    assert r.reveals[0].sub_id == "them"


def test_active_ping_does_not_reveal_far():
    s = SonarPing()
    s.register(sub_id="me", x=0, y=0, band=2)
    s.register(sub_id="them", x=ACTIVE_RADIUS + 50, y=0, band=2)
    r = s.active_ping(sub_id="me", now_seconds=0)
    assert r.accepted is True
    assert len(r.reveals) == 0


def test_active_ping_unknown_sub():
    s = SonarPing()
    r = s.active_ping(sub_id="ghost", now_seconds=0)
    assert r.accepted is False


def test_active_ping_cooldown_blocks():
    s = SonarPing()
    s.register(sub_id="me", x=0, y=0, band=2)
    s.active_ping(sub_id="me", now_seconds=0)
    r = s.active_ping(sub_id="me", now_seconds=10)
    assert r.accepted is False
    assert r.reason == "cooldown"


def test_active_ping_after_cooldown_works():
    s = SonarPing()
    s.register(sub_id="me", x=0, y=0, band=2)
    s.active_ping(sub_id="me", now_seconds=0)
    r = s.active_ping(
        sub_id="me", now_seconds=PING_COOLDOWN_SECONDS + 1,
    )
    assert r.accepted is True


def test_passive_hears_active_ping():
    s = SonarPing()
    s.register(sub_id="hunter", x=0, y=0, band=2, has_passive=True)
    s.register(sub_id="loud", x=400, y=0, band=2, has_passive=False)
    s.active_ping(sub_id="loud", now_seconds=10)
    detections = s.passive_listen(sub_id="hunter")
    assert len(detections) == 1
    assert detections[0].pinger_sub_id == "loud"
    assert detections[0].detected_at == 10


def test_passive_does_not_hear_too_far():
    s = SonarPing()
    s.register(sub_id="hunter", x=0, y=0, band=2, has_passive=True)
    s.register(
        sub_id="loud",
        x=PASSIVE_RADIUS + 100, y=0, band=2,
        has_passive=False,
    )
    s.active_ping(sub_id="loud", now_seconds=10)
    detections = s.passive_listen(sub_id="hunter")
    assert len(detections) == 0


def test_passive_listen_clears_buffer():
    s = SonarPing()
    s.register(sub_id="hunter", x=0, y=0, band=2, has_passive=True)
    s.register(sub_id="loud", x=100, y=0, band=2)
    s.active_ping(sub_id="loud", now_seconds=10)
    first = s.passive_listen(sub_id="hunter")
    assert len(first) == 1
    second = s.passive_listen(sub_id="hunter")
    assert len(second) == 0


def test_non_passive_listener_hears_nothing():
    s = SonarPing()
    s.register(sub_id="deaf", x=0, y=0, band=2, has_passive=False)
    s.register(sub_id="loud", x=100, y=0, band=2)
    s.active_ping(sub_id="loud", now_seconds=10)
    detections = s.passive_listen(sub_id="deaf")
    assert len(detections) == 0


def test_heard_by_only_includes_passive_subs():
    s = SonarPing()
    s.register(sub_id="me", x=0, y=0, band=2)
    s.register(sub_id="passive_listener", x=200, y=0, band=2, has_passive=True)
    s.register(sub_id="deaf", x=200, y=0, band=2, has_passive=False)
    r = s.active_ping(sub_id="me", now_seconds=0)
    assert "passive_listener" in r.heard_by
    assert "deaf" not in r.heard_by


def test_update_position_changes_distance():
    s = SonarPing()
    s.register(sub_id="me", x=0, y=0, band=2)
    s.register(sub_id="them", x=ACTIVE_RADIUS + 50, y=0, band=2)
    # initially out of range
    r = s.active_ping(sub_id="me", now_seconds=0)
    assert len(r.reveals) == 0
    # move them closer
    s.update(sub_id="them", x=50, y=0, band=2)
    r = s.active_ping(sub_id="me", now_seconds=PING_COOLDOWN_SECONDS + 1)
    assert len(r.reveals) == 1


def test_update_unknown_returns_false():
    s = SonarPing()
    ok = s.update(sub_id="ghost", x=0, y=0, band=0)
    assert ok is False


def test_last_ping_at_tracked():
    s = SonarPing()
    s.register(sub_id="me", x=0, y=0, band=2)
    assert s.last_ping_at(sub_id="me") is None
    s.active_ping(sub_id="me", now_seconds=42)
    assert s.last_ping_at(sub_id="me") == 42


def test_band_separation_increases_distance():
    s = SonarPing()
    # right at the edge of active radius horizontally
    s.register(sub_id="me", x=0, y=0, band=2)
    s.register(sub_id="them", x=ACTIVE_RADIUS - 1, y=0, band=2)
    r = s.active_ping(sub_id="me", now_seconds=0)
    assert len(r.reveals) == 1
    # now put them several bands away — should drop out
    s.update(sub_id="them", x=ACTIVE_RADIUS - 1, y=0, band=4)  # ABYSSAL
    r = s.active_ping(
        sub_id="me", now_seconds=PING_COOLDOWN_SECONDS + 1,
    )
    # band gap of 2 adds vertical distance, so total > ACTIVE_RADIUS
    # should reveal nothing now
    assert len(r.reveals) == 0
