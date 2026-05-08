"""Tests for vr_eye_tracking."""
from __future__ import annotations

from server.vr_eye_tracking import (
    Entity, GazeSample, VrEyeTracking,
)


def _gaze_forward(t=1000, x=0.0, y=1.5, z=0.0,
                  dx=0.0, dy=0.0, dz=1.0):
    return GazeSample(
        origin_x=x, origin_y=y, origin_z=z,
        dir_x=dx, dir_y=dy, dir_z=dz,
        timestamp_ms=t,
    )


def test_ingest_happy():
    e = VrEyeTracking()
    assert e.ingest(
        player_id="bob", sample=_gaze_forward(),
    ) is True


def test_ingest_blank_player_blocked():
    e = VrEyeTracking()
    assert e.ingest(
        player_id="", sample=_gaze_forward(),
    ) is False


def test_ingest_out_of_order_blocked():
    e = VrEyeTracking()
    e.ingest(player_id="bob", sample=_gaze_forward(t=2000))
    assert e.ingest(
        player_id="bob", sample=_gaze_forward(t=1000),
    ) is False


def test_soft_target_picks_closest_to_gaze():
    e = VrEyeTracking()
    e.ingest(player_id="bob", sample=_gaze_forward())
    # Looking straight forward (z+); two mobs in front.
    # crab at z=10 is dead-on; goblin at z=10,x=2 is offset
    crab = Entity(entity_id="crab_1", x=0, y=1.5, z=10)
    gob = Entity(entity_id="goblin_1", x=2, y=1.5, z=10)
    target = e.soft_target(
        player_id="bob", entities=[gob, crab],
    )
    assert target is not None
    assert target.entity_id == "crab_1"


def test_soft_target_outside_cone_returns_none():
    e = VrEyeTracking()
    e.ingest(player_id="bob", sample=_gaze_forward())
    # Mob is to the side — way outside 8-deg cone
    mob = Entity(entity_id="goblin_1", x=20, y=1.5, z=10)
    target = e.soft_target(
        player_id="bob", entities=[mob],
    )
    assert target is None


def test_soft_target_no_samples_returns_none():
    e = VrEyeTracking()
    crab = Entity(entity_id="crab_1", x=0, y=1.5, z=10)
    target = e.soft_target(
        player_id="bob", entities=[crab],
    )
    assert target is None


def test_eye_contact_dwell_required():
    e = VrEyeTracking()
    npc = Entity(entity_id="cid", x=0, y=1.5, z=5)
    # One sample only — dwell is 0
    e.ingest(player_id="bob", sample=_gaze_forward(t=1000))
    out = e.eye_contact(
        player_id="bob", entities=[npc], now_ms=1100,
    )
    assert out == []


def test_eye_contact_long_enough():
    e = VrEyeTracking()
    npc = Entity(entity_id="cid", x=0, y=1.5, z=5)
    # Multiple samples held looking at NPC for 800ms
    for t in [1000, 1200, 1400, 1600, 1800]:
        e.ingest(player_id="bob", sample=_gaze_forward(t=t))
    out = e.eye_contact(
        player_id="bob", entities=[npc], now_ms=1850,
    )
    assert len(out) == 1
    assert out[0].entity_id == "cid"
    assert out[0].duration_ms >= 600


def test_eye_contact_broken_resets():
    e = VrEyeTracking()
    npc = Entity(entity_id="cid", x=0, y=1.5, z=5)
    # Look at NPC
    e.ingest(player_id="bob", sample=_gaze_forward(t=1000))
    e.ingest(player_id="bob", sample=_gaze_forward(t=1200))
    # Look way away (gaze x+ direction)
    e.ingest(
        player_id="bob",
        sample=_gaze_forward(t=1400, dx=1.0, dz=0.0),
    )
    # Look back, but fresh streak < dwell
    e.ingest(player_id="bob", sample=_gaze_forward(t=1600))
    out = e.eye_contact(
        player_id="bob", entities=[npc], now_ms=1700,
    )
    assert out == []  # broken streak, current too short


def test_set_supported_returns_diff():
    e = VrEyeTracking()
    assert e.set_supported(
        player_id="bob", supported=True,
    ) is True
    # Setting same value returns False (no change)
    assert e.set_supported(
        player_id="bob", supported=True,
    ) is False


def test_set_supported_blank_blocked():
    e = VrEyeTracking()
    assert e.set_supported(
        player_id="", supported=True,
    ) is False


def test_is_supported_default_false():
    e = VrEyeTracking()
    assert e.is_supported(player_id="bob") is False


def test_clear_removes():
    e = VrEyeTracking()
    e.ingest(player_id="bob", sample=_gaze_forward())
    e.set_supported(player_id="bob", supported=True)
    assert e.clear(player_id="bob") is True
    assert e.is_supported(player_id="bob") is False


def test_clear_unknown():
    e = VrEyeTracking()
    assert e.clear(player_id="ghost") is False


def test_history_window_drops_old():
    e = VrEyeTracking()
    e.ingest(player_id="bob", sample=_gaze_forward(t=1000))
    # Sample 3 seconds later — older sample should be
    # outside the 2000ms history window
    e.ingest(player_id="bob", sample=_gaze_forward(t=4000))
    npc = Entity(entity_id="cid", x=0, y=1.5, z=5)
    out = e.eye_contact(
        player_id="bob", entities=[npc], now_ms=4100,
    )
    # Only 1 sample left in buffer -> dwell=0
    assert out == []


def test_soft_target_multiple_picks_smallest():
    e = VrEyeTracking()
    e.ingest(player_id="bob", sample=_gaze_forward())
    a = Entity(entity_id="a", x=0.5, y=1.5, z=10)  # ~3deg
    b = Entity(entity_id="b", x=0.1, y=1.5, z=10)  # ~0.5deg
    c = Entity(entity_id="c", x=1.0, y=1.5, z=10)  # ~5.7deg
    target = e.soft_target(
        player_id="bob", entities=[a, b, c],
    )
    assert target.entity_id == "b"


def test_eye_contact_unknown_player():
    e = VrEyeTracking()
    npc = Entity(entity_id="cid", x=0, y=1.5, z=5)
    out = e.eye_contact(
        player_id="ghost", entities=[npc], now_ms=2000,
    )
    assert out == []
