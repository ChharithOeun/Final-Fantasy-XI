"""Tests for tide cycle clock."""
from __future__ import annotations

from server.tide_cycle_clock import TideAccess, TideCycleClock, TidePhase


def test_phase_at_zero_is_rising():
    c = TideCycleClock(tide_epoch_seconds=0)
    assert c.phase_at(now_seconds=0) == TidePhase.RISING


def test_phase_at_six_hours_is_high():
    c = TideCycleClock(tide_epoch_seconds=0)
    assert c.phase_at(now_seconds=6 * 3_600) == TidePhase.HIGH


def test_phase_at_12_hours_is_ebbing():
    c = TideCycleClock(tide_epoch_seconds=0)
    assert c.phase_at(now_seconds=12 * 3_600) == TidePhase.EBBING


def test_phase_at_18_hours_is_low():
    c = TideCycleClock(tide_epoch_seconds=0)
    assert c.phase_at(now_seconds=18 * 3_600) == TidePhase.LOW


def test_phase_wraps_at_24_hours():
    c = TideCycleClock(tide_epoch_seconds=0)
    assert c.phase_at(now_seconds=24 * 3_600) == TidePhase.RISING


def test_tide_agnostic_always_accessible():
    c = TideCycleClock(tide_epoch_seconds=0)
    for h in (0, 6, 12, 18, 100, 999):
        assert c.is_accessible(
            zone_access=TideAccess.TIDE_AGNOSTIC,
            now_seconds=h * 3_600,
        ) is True


def test_high_tide_only_at_rising_high():
    c = TideCycleClock(tide_epoch_seconds=0)
    assert c.is_accessible(
        zone_access=TideAccess.HIGH_TIDE_ONLY,
        now_seconds=2 * 3_600,
    ) is True
    assert c.is_accessible(
        zone_access=TideAccess.HIGH_TIDE_ONLY,
        now_seconds=8 * 3_600,
    ) is True
    assert c.is_accessible(
        zone_access=TideAccess.HIGH_TIDE_ONLY,
        now_seconds=14 * 3_600,
    ) is False


def test_low_tide_only_at_ebbing_low():
    c = TideCycleClock(tide_epoch_seconds=0)
    assert c.is_accessible(
        zone_access=TideAccess.LOW_TIDE_ONLY,
        now_seconds=14 * 3_600,
    ) is True
    assert c.is_accessible(
        zone_access=TideAccess.LOW_TIDE_ONLY,
        now_seconds=20 * 3_600,
    ) is True
    assert c.is_accessible(
        zone_access=TideAccess.LOW_TIDE_ONLY,
        now_seconds=2 * 3_600,
    ) is False


def test_tide_with_nonzero_epoch():
    # epoch shifted by 3 hours -> phase at hour 3 should be RISING
    c = TideCycleClock(tide_epoch_seconds=3 * 3_600)
    assert c.phase_at(now_seconds=3 * 3_600) == TidePhase.RISING
    assert c.phase_at(now_seconds=9 * 3_600) == TidePhase.HIGH


def test_next_phase_change_within_phase():
    c = TideCycleClock(tide_epoch_seconds=0)
    # at hour 2 (in RISING), next change is hour 6
    assert c.next_phase_change_after(
        now_seconds=2 * 3_600,
    ) == 6 * 3_600


def test_next_phase_change_at_phase_boundary():
    c = TideCycleClock(tide_epoch_seconds=0)
    # at exact phase boundary, next change is one phase later
    assert c.next_phase_change_after(
        now_seconds=6 * 3_600,
    ) == 12 * 3_600


def test_time_until_next_phase():
    c = TideCycleClock(tide_epoch_seconds=0)
    # at hour 4 (in RISING), next change at hour 6 -> 2h away
    assert c.time_until_next_phase(
        now_seconds=4 * 3_600,
    ) == 2 * 3_600


def test_phase_persists_across_cycles():
    c = TideCycleClock(tide_epoch_seconds=0)
    # 48 hours = 2 full cycles -> RISING again
    assert c.phase_at(now_seconds=48 * 3_600) == TidePhase.RISING
    # 50 hours = 2 cycles + 2h -> still RISING
    assert c.phase_at(now_seconds=50 * 3_600) == TidePhase.RISING
