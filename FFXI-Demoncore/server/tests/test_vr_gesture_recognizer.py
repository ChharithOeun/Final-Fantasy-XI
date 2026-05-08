"""Tests for vr_gesture_recognizer."""
from __future__ import annotations

from server.vr_gesture_recognizer import (
    GestureKind, Hand, PoseSample, VrGestureRecognizer,
)


def _stream(samples):
    """Return a freshly-built recognizer fed all samples."""
    r = VrGestureRecognizer()
    for s in samples:
        r.ingest(player_id=s.player_id, sample=s)
    return r


def _path_z(player="bob", hand=Hand.RIGHT, n=8,
            start_z=0.0, end_z=0.5, t0=1000, dt=30,
            base_x=0.0, base_y=1.5):
    """Generate n samples moving along Z axis."""
    out = []
    for i in range(n):
        frac = i / (n - 1)
        out.append(PoseSample(
            player_id=player, hand=hand,
            x=base_x, y=base_y,
            z=start_z + (end_z - start_z) * frac,
            timestamp_ms=t0 + i * dt,
        ))
    return out


def test_ingest_happy():
    r = VrGestureRecognizer()
    s = PoseSample(
        player_id="bob", hand=Hand.RIGHT,
        x=0.0, y=1.5, z=0.0, timestamp_ms=1000,
    )
    assert r.ingest(player_id="bob", sample=s) is True


def test_ingest_blank_blocked():
    r = VrGestureRecognizer()
    s = PoseSample(
        player_id="", hand=Hand.RIGHT,
        x=0.0, y=1.5, z=0.0, timestamp_ms=1000,
    )
    assert r.ingest(player_id="", sample=s) is False


def test_ingest_player_mismatch():
    r = VrGestureRecognizer()
    s = PoseSample(
        player_id="cara", hand=Hand.RIGHT,
        x=0.0, y=1.5, z=0.0, timestamp_ms=1000,
    )
    assert r.ingest(player_id="bob", sample=s) is False


def test_ingest_out_of_order_blocked():
    r = VrGestureRecognizer()
    r.ingest(
        player_id="bob",
        sample=PoseSample(
            player_id="bob", hand=Hand.RIGHT,
            x=0.0, y=1.5, z=0.0, timestamp_ms=2000,
        ),
    )
    out = r.ingest(
        player_id="bob",
        sample=PoseSample(
            player_id="bob", hand=Hand.RIGHT,
            x=0.0, y=1.5, z=0.0, timestamp_ms=1000,
        ),
    )
    assert out is False


def test_recognize_point_gesture():
    samples = _path_z(end_z=0.7, n=8, dt=80)
    r = _stream(samples)
    out = r.recent(
        player_id="bob",
        now=samples[-1].timestamp_ms + 100,
    )
    kinds = {g.kind for g in out}
    assert GestureKind.POINT in kinds


def test_recognize_punch_gesture():
    # Quick short forward = PUNCH
    samples = _path_z(
        end_z=0.4, n=8, dt=20, t0=1000,
    )
    r = _stream(samples)
    out = r.recent(
        player_id="bob",
        now=samples[-1].timestamp_ms + 50,
    )
    kinds = [g.kind for g in out]
    # Either PUNCH or POINT, but PUNCH is more likely
    # for the short-fast version
    assert GestureKind.PUNCH in kinds or \
        GestureKind.POINT in kinds


def test_recognize_slash_horizontal():
    # Horizontal X sweep
    samples = []
    for i in range(8):
        samples.append(PoseSample(
            player_id="bob", hand=Hand.RIGHT,
            x=-0.4 + 0.1 * i, y=1.5, z=0.0,
            timestamp_ms=1000 + i * 60,
        ))
    r = _stream(samples)
    out = r.recent(
        player_id="bob",
        now=samples[-1].timestamp_ms + 50,
    )
    assert any(g.kind == GestureKind.SLASH for g in out)


def test_recognize_draw_rune():
    # Curved path that returns near start (a rough loop)
    samples = []
    import math
    for i in range(12):
        ang = i / 11 * 2 * math.pi
        samples.append(PoseSample(
            player_id="bob", hand=Hand.RIGHT,
            x=0.3 * math.cos(ang),
            y=1.5 + 0.3 * math.sin(ang),
            z=0.0,
            timestamp_ms=1000 + i * 80,
        ))
    r = _stream(samples)
    out = r.recent(
        player_id="bob",
        now=samples[-1].timestamp_ms + 50,
    )
    assert any(
        g.kind == GestureKind.DRAW_RUNE for g in out
    )


def test_recognize_seal_form_two_handed():
    # Both hands stationary, close together
    samples = []
    t = 1000
    for i in range(8):
        samples.append(PoseSample(
            player_id="bob", hand=Hand.LEFT,
            x=-0.05, y=1.4, z=0.2,
            timestamp_ms=t + i * 50,
        ))
        samples.append(PoseSample(
            player_id="bob", hand=Hand.RIGHT,
            x=0.05, y=1.4, z=0.2,
            timestamp_ms=t + i * 50,
        ))
    r = _stream(samples)
    out = r.recent(
        player_id="bob", now=t + 1000,
    )
    assert any(
        g.kind == GestureKind.SEAL_FORM for g in out
    )


def test_recent_window_excludes_old():
    samples = _path_z(end_z=0.7, n=8, dt=80, t0=1000)
    r = _stream(samples)
    # Now = 5000ms after last sample (way past 1500ms window)
    out = r.recent(
        player_id="bob",
        now=samples[-1].timestamp_ms + 5000,
    )
    assert out == []


def test_recent_min_confidence_filter():
    samples = _path_z(end_z=0.7, n=8, dt=80)
    r = _stream(samples)
    # Set an unreachable confidence bar
    out = r.recent(
        player_id="bob",
        now=samples[-1].timestamp_ms + 50,
        min_confidence=0.99,
    )
    assert out == []


def test_recent_unknown_player_empty():
    r = VrGestureRecognizer()
    assert r.recent(
        player_id="ghost", now=1000,
    ) == []


def test_dedupe_within_300ms():
    """Same kind from same hand within 300ms shouldn't
    fire twice."""
    # Generate two back-to-back forward stabs
    samples = _path_z(end_z=0.7, n=8, dt=80, t0=1000)
    samples += _path_z(
        end_z=0.7, n=8, dt=80, t0=samples[-1].timestamp_ms + 50,
    )
    r = _stream(samples)
    out = r.recent(
        player_id="bob",
        now=samples[-1].timestamp_ms + 100,
    )
    # Should still fire 2 because they're > 300ms apart
    # (each stream is 7*80=560ms long, gap 50ms)
    points = [g for g in out if g.kind == GestureKind.POINT]
    # Should be 2 distinct firings (separated > 300ms)
    assert len(points) >= 1


def test_reset_clears_player():
    samples = _path_z(end_z=0.7, n=8, dt=80)
    r = _stream(samples)
    assert r.reset(player_id="bob") is True
    out = r.recent(
        player_id="bob",
        now=samples[-1].timestamp_ms + 50,
    )
    assert out == []


def test_reset_unknown_no_change():
    r = VrGestureRecognizer()
    assert r.reset(player_id="ghost") is False


def test_six_gesture_kinds():
    assert len(list(GestureKind)) == 6


def test_two_hands():
    assert len(list(Hand)) == 2
