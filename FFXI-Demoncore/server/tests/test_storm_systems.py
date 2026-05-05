"""Tests for storm systems."""
from __future__ import annotations

from server.storm_systems import (
    HOURS_PER_PHASE,
    StormPhase,
    StormSystems,
    TOTAL_CYCLE_HOURS,
)


def test_register_zone_happy():
    s = StormSystems()
    assert s.register_zone(zone_id="bastok") is True


def test_register_zone_blank():
    s = StormSystems()
    assert s.register_zone(zone_id="") is False


def test_phase_at_unknown_zone():
    s = StormSystems()
    assert s.phase_at(zone_id="ghost", now_game_hours=0) is None


def test_phase_clear_at_zero():
    s = StormSystems()
    s.register_zone(zone_id="bastok", storm_seed_offset=0)
    assert s.phase_at(zone_id="bastok", now_game_hours=0) == StormPhase.CLEAR


def test_phase_progression():
    s = StormSystems()
    s.register_zone(zone_id="bastok", storm_seed_offset=0)
    assert s.phase_at(
        zone_id="bastok", now_game_hours=HOURS_PER_PHASE,
    ) == StormPhase.CIRRUS
    assert s.phase_at(
        zone_id="bastok", now_game_hours=HOURS_PER_PHASE * 2,
    ) == StormPhase.BUILDING
    assert s.phase_at(
        zone_id="bastok", now_game_hours=HOURS_PER_PHASE * 3,
    ) == StormPhase.THUNDERHEAD
    assert s.phase_at(
        zone_id="bastok", now_game_hours=HOURS_PER_PHASE * 4,
    ) == StormPhase.SUPERCELL


def test_phase_wraps():
    s = StormSystems()
    s.register_zone(zone_id="bastok", storm_seed_offset=0)
    assert s.phase_at(
        zone_id="bastok", now_game_hours=TOTAL_CYCLE_HOURS,
    ) == StormPhase.CLEAR


def test_seed_offsets_zones():
    s = StormSystems()
    s.register_zone(zone_id="bastok", storm_seed_offset=0)
    s.register_zone(
        zone_id="norg", storm_seed_offset=HOURS_PER_PHASE * 3,
    )
    # at hour 0: bastok=CLEAR, norg=THUNDERHEAD
    assert s.phase_at(zone_id="bastok", now_game_hours=0) == StormPhase.CLEAR
    assert s.phase_at(zone_id="norg", now_game_hours=0) == StormPhase.THUNDERHEAD


def test_is_band_unsafe_clear():
    s = StormSystems()
    s.register_zone(zone_id="bastok")
    assert s.is_band_unsafe(
        zone_id="bastok", band=3, now_game_hours=0,
    ) is False


def test_is_band_unsafe_thunderhead_mid_high():
    s = StormSystems()
    s.register_zone(zone_id="bastok", storm_seed_offset=0)
    th_hour = HOURS_PER_PHASE * 3
    assert s.is_band_unsafe(
        zone_id="bastok", band=2, now_game_hours=th_hour,
    ) is True
    assert s.is_band_unsafe(
        zone_id="bastok", band=3, now_game_hours=th_hour,
    ) is True
    assert s.is_band_unsafe(
        zone_id="bastok", band=4, now_game_hours=th_hour,
    ) is False


def test_is_band_unsafe_supercell_includes_strat():
    s = StormSystems()
    s.register_zone(zone_id="bastok", storm_seed_offset=0)
    sc_hour = HOURS_PER_PHASE * 4
    assert s.is_band_unsafe(
        zone_id="bastok", band=4, now_game_hours=sc_hour,
    ) is True


def test_lightning_risk_zero_on_clear():
    s = StormSystems()
    s.register_zone(zone_id="bastok")
    assert s.lightning_risk(
        zone_id="bastok", band=3, now_game_hours=0,
    ) == 0


def test_lightning_risk_increases_through_phases():
    s = StormSystems()
    s.register_zone(zone_id="bastok", storm_seed_offset=0)
    building = s.lightning_risk(
        zone_id="bastok", band=3,
        now_game_hours=HOURS_PER_PHASE * 2,
    )
    thunder = s.lightning_risk(
        zone_id="bastok", band=3,
        now_game_hours=HOURS_PER_PHASE * 3,
    )
    super_ = s.lightning_risk(
        zone_id="bastok", band=3,
        now_game_hours=HOURS_PER_PHASE * 4,
    )
    assert building < thunder < super_


def test_lightning_risk_unknown_zone():
    s = StormSystems()
    assert s.lightning_risk(
        zone_id="ghost", band=3, now_game_hours=0,
    ) == 0


def test_is_band_unsafe_unknown_zone_safe():
    s = StormSystems()
    assert s.is_band_unsafe(
        zone_id="ghost", band=3, now_game_hours=0,
    ) is False


def test_lightning_risk_low_band_zero():
    s = StormSystems()
    s.register_zone(zone_id="bastok", storm_seed_offset=0)
    # at SUPERCELL, band 0 (GROUND) and 1 (LOW) have no risk
    sc_hour = HOURS_PER_PHASE * 4
    assert s.lightning_risk(
        zone_id="bastok", band=0, now_game_hours=sc_hour,
    ) == 0
    assert s.lightning_risk(
        zone_id="bastok", band=1, now_game_hours=sc_hour,
    ) == 0
