"""Tests for vr_swimming."""
from __future__ import annotations

from server.vr_swimming import (
    Hand, HandSweep, StrokeKind, VrSwimming,
)


def _good_sweep(t=1000, dur=400):
    return HandSweep(
        backward_z_m=0.5, downward_y_m=0.1,
        duration_ms=dur, timestamp_ms=t,
    )


def test_enter_water_happy():
    s = VrSwimming()
    assert s.enter_water(
        player_id="bob", surface_y=10.0,
    ) is True


def test_enter_water_blank_blocked():
    s = VrSwimming()
    assert s.enter_water(
        player_id="", surface_y=10.0,
    ) is False


def test_exit_water():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    assert s.exit_water(player_id="bob") is True
    assert s.state(player_id="bob") is None


def test_exit_water_unknown():
    s = VrSwimming()
    assert s.exit_water(player_id="ghost") is False


def test_sweep_unknown_player():
    s = VrSwimming()
    out = s.ingest_sweep(
        player_id="ghost", hand=Hand.RIGHT,
        sweep=_good_sweep(),
    )
    assert out is False


def test_sweep_too_small_rejected():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    bad = HandSweep(
        backward_z_m=0.1, downward_y_m=0.1,
        duration_ms=400, timestamp_ms=1000,
    )
    assert s.ingest_sweep(
        player_id="bob", hand=Hand.RIGHT, sweep=bad,
    ) is False


def test_sweep_no_downward_rejected():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    bad = HandSweep(
        backward_z_m=0.5, downward_y_m=0.01,
        duration_ms=400, timestamp_ms=1000,
    )
    assert s.ingest_sweep(
        player_id="bob", hand=Hand.RIGHT, sweep=bad,
    ) is False


def test_sweep_too_long_rejected():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    bad = HandSweep(
        backward_z_m=0.5, downward_y_m=0.1,
        duration_ms=2000, timestamp_ms=1000,
    )
    assert s.ingest_sweep(
        player_id="bob", hand=Hand.RIGHT, sweep=bad,
    ) is False


def test_dog_paddle_first_stroke():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    s.ingest_sweep(
        player_id="bob", hand=Hand.RIGHT,
        sweep=_good_sweep(t=1000),
    )
    state = s.state(player_id="bob")
    assert state.last_stroke_kind == StrokeKind.DOG_PADDLE


def test_freestyle_alternating():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    s.ingest_sweep(
        player_id="bob", hand=Hand.RIGHT,
        sweep=_good_sweep(t=1000),
    )
    s.ingest_sweep(
        player_id="bob", hand=Hand.LEFT,
        sweep=_good_sweep(t=1700),
    )
    # Within 1200ms alternating window after dog paddle
    state = s.state(player_id="bob")
    # Second stroke is FREESTYLE
    assert state.last_stroke_kind == StrokeKind.FREESTYLE


def test_breaststroke_simultaneous():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    s.ingest_sweep(
        player_id="bob", hand=Hand.LEFT,
        sweep=_good_sweep(t=1000),
    )
    s.ingest_sweep(
        player_id="bob", hand=Hand.RIGHT,
        sweep=_good_sweep(t=1100),  # within 250ms
    )
    state = s.state(player_id="bob")
    assert state.last_stroke_kind == StrokeKind.BREASTSTROKE


def test_velocity_increases_with_strokes():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    s.ingest_sweep(
        player_id="bob", hand=Hand.RIGHT,
        sweep=_good_sweep(t=1000),
    )
    v1 = s.state(player_id="bob").forward_velocity_mps
    s.ingest_sweep(
        player_id="bob", hand=Hand.LEFT,
        sweep=_good_sweep(t=1500),
    )
    v2 = s.state(player_id="bob").forward_velocity_mps
    assert v2 > v1


def test_velocity_decays_on_tick():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    s.ingest_sweep(
        player_id="bob", hand=Hand.RIGHT,
        sweep=_good_sweep(t=1000),
    )
    v1 = s.state(player_id="bob").forward_velocity_mps
    s.tick(player_id="bob", elapsed_ms=1000)
    v2 = s.state(player_id="bob").forward_velocity_mps
    assert v2 < v1


def test_velocity_clamps_at_zero():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    s.tick(player_id="bob", elapsed_ms=10000)
    state = s.state(player_id="bob")
    assert state.forward_velocity_mps == 0.0


def test_underwater_detection():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    s.update_head(player_id="bob", head_y=8.0)
    state = s.state(player_id="bob")
    assert state.underwater is True


def test_above_surface_not_underwater():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    s.update_head(player_id="bob", head_y=11.0)
    assert s.state(player_id="bob").underwater is False


def test_reset():
    s = VrSwimming()
    s.enter_water(player_id="bob", surface_y=10.0)
    assert s.reset(player_id="bob") is True
    assert s.state(player_id="bob") is None


def test_reset_unknown():
    s = VrSwimming()
    assert s.reset(player_id="ghost") is False


def test_three_stroke_kinds():
    assert len(list(StrokeKind)) == 3


def test_state_unknown_player():
    s = VrSwimming()
    assert s.state(player_id="ghost") is None
