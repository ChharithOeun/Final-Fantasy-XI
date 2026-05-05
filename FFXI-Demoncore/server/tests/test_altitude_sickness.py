"""Tests for altitude sickness."""
from __future__ import annotations

from server.altitude_sickness import (
    ASCENT_WINDOW_SECONDS,
    AltitudeGear,
    AltitudeSickness,
    HIGH_BAND,
    HIGH_STRESS_PER_SECOND,
    LOW_BAND_CEILING,
    SAFE_BAND_CEILING,
    STRATOSPHERE_BAND,
    STRESS_DECAY_PER_SECOND_AT_LOW,
    STRESS_HARM_THRESHOLD,
)


def test_register_happy():
    s = AltitudeSickness()
    assert s.register(player_id="p1") is True


def test_register_blank():
    s = AltitudeSickness()
    assert s.register(player_id="") is False


def test_register_double_blocked():
    s = AltitudeSickness()
    s.register(player_id="p1")
    assert s.register(player_id="p1") is False


def test_no_stress_at_safe_bands():
    s = AltitudeSickness()
    s.register(player_id="p1")
    s.set_band(player_id="p1", band=SAFE_BAND_CEILING, now_seconds=0)
    status = s.tick(player_id="p1", now_seconds=120)
    assert status.stress == 0.0


def test_stress_accrues_at_high_unprotected():
    s = AltitudeSickness()
    s.register(player_id="p1")
    s.set_band(player_id="p1", band=HIGH_BAND, now_seconds=0)
    status = s.tick(player_id="p1", now_seconds=20)
    assert status.stress > 0


def test_stress_accrues_faster_at_stratosphere():
    s_high = AltitudeSickness()
    s_high.register(player_id="p1")
    s_high.set_band(player_id="p1", band=HIGH_BAND, now_seconds=0)
    h = s_high.tick(player_id="p1", now_seconds=10)
    s_strat = AltitudeSickness()
    s_strat.register(player_id="p2")
    s_strat.set_band(
        player_id="p2", band=STRATOSPHERE_BAND, now_seconds=0,
    )
    sa = s_strat.tick(player_id="p2", now_seconds=10)
    assert sa.stress > h.stress


def test_oxygen_mask_protects_at_high():
    s = AltitudeSickness()
    s.register(player_id="p1")
    s.equip_gear(player_id="p1", gear=AltitudeGear.OXYGEN_MASK)
    s.set_band(player_id="p1", band=HIGH_BAND, now_seconds=0)
    status = s.tick(player_id="p1", now_seconds=120)
    assert status.stress == 0.0


def test_oxygen_mask_does_not_protect_at_stratosphere():
    s = AltitudeSickness()
    s.register(player_id="p1")
    s.equip_gear(player_id="p1", gear=AltitudeGear.OXYGEN_MASK)
    s.set_band(
        player_id="p1", band=STRATOSPHERE_BAND, now_seconds=0,
    )
    status = s.tick(player_id="p1", now_seconds=10)
    assert status.stress > 0


def test_pressure_suit_protects_at_stratosphere():
    s = AltitudeSickness()
    s.register(player_id="p1")
    s.equip_gear(player_id="p1", gear=AltitudeGear.PRESSURE_SUIT)
    s.set_band(
        player_id="p1", band=STRATOSPHERE_BAND, now_seconds=0,
    )
    status = s.tick(player_id="p1", now_seconds=120)
    assert status.stress == 0.0


def test_suffering_at_threshold():
    s = AltitudeSickness()
    s.register(player_id="p1")
    s.set_band(
        player_id="p1", band=STRATOSPHERE_BAND, now_seconds=0,
    )
    # tick long enough to exceed harm threshold
    s.tick(player_id="p1", now_seconds=200)
    assert s.is_suffering(player_id="p1") is True


def test_decay_at_low_band():
    s = AltitudeSickness()
    s.register(player_id="p1")
    # build up stress at HIGH
    s.set_band(player_id="p1", band=HIGH_BAND, now_seconds=0)
    s.tick(player_id="p1", now_seconds=int(STRESS_HARM_THRESHOLD / HIGH_STRESS_PER_SECOND) + 5)
    # descend to LOW
    s.set_band(player_id="p1", band=LOW_BAND_CEILING, now_seconds=200)
    status_before = s.tick(player_id="p1", now_seconds=200)
    s.tick(player_id="p1", now_seconds=300)
    status_after = s.tick(player_id="p1", now_seconds=300)
    assert status_after.stress < status_before.stress


def test_rapid_ascent_spike():
    s = AltitudeSickness()
    s.register(player_id="p1")
    # at GROUND
    s.set_band(player_id="p1", band=0, now_seconds=0)
    # jump to HIGH within window
    s.set_band(player_id="p1", band=HIGH_BAND, now_seconds=2)
    status = s.tick(player_id="p1", now_seconds=2)
    # spike should be applied
    assert status.stress >= 25.0


def test_slow_ascent_no_spike():
    s = AltitudeSickness()
    s.register(player_id="p1")
    s.set_band(player_id="p1", band=0, now_seconds=0)
    # one band per ascent_window — fine
    s.set_band(player_id="p1", band=1, now_seconds=10)
    s.set_band(
        player_id="p1", band=2, now_seconds=20,
    )
    status = s.tick(player_id="p1", now_seconds=20)
    # at MID, no stress accrual at all and no spike
    assert status.stress == 0.0


def test_unequip_strips_protection():
    s = AltitudeSickness()
    s.register(player_id="p1")
    s.equip_gear(player_id="p1", gear=AltitudeGear.OXYGEN_MASK)
    s.set_band(player_id="p1", band=HIGH_BAND, now_seconds=0)
    s.tick(player_id="p1", now_seconds=10)
    s.unequip_gear(player_id="p1", gear=AltitudeGear.OXYGEN_MASK)
    s.tick(player_id="p1", now_seconds=10)
    after = s.tick(player_id="p1", now_seconds=20)
    assert after.stress > 0


def test_unknown_player_returns_none():
    s = AltitudeSickness()
    assert s.tick(player_id="ghost", now_seconds=0) is None
    assert s.is_suffering(player_id="ghost") is False
