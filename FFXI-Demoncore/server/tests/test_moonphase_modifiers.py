"""Tests for moonphase_modifiers."""
from __future__ import annotations

from server.moonphase_modifiers import MoonPhase, MoonphaseEngine


def test_pld_full_moon_positive():
    e = MoonphaseEngine()
    assert e.modifier_for(job="PLD", phase=MoonPhase.FULL) > 0


def test_nin_full_moon_negative():
    e = MoonphaseEngine()
    assert e.modifier_for(job="NIN", phase=MoonPhase.FULL) < 0


def test_pld_new_moon_negative():
    e = MoonphaseEngine()
    assert e.modifier_for(job="PLD", phase=MoonPhase.NEW) < 0


def test_nin_new_moon_positive():
    e = MoonphaseEngine()
    assert e.modifier_for(job="NIN", phase=MoonPhase.NEW) > 0


def test_neutral_job_zero_at_all_phases():
    e = MoonphaseEngine()
    for phase in MoonPhase:
        assert e.modifier_for(job="BLM", phase=phase) == 0


def test_unknown_job_zero():
    e = MoonphaseEngine()
    assert e.modifier_for(
        job="MADEUPJOB", phase=MoonPhase.FULL,
    ) == 0


def test_blank_job_zero():
    e = MoonphaseEngine()
    assert e.modifier_for(job="", phase=MoonPhase.FULL) == 0


def test_extreme_amplitude_15():
    e = MoonphaseEngine()
    assert e.modifier_for(job="PLD", phase=MoonPhase.FULL) == 15
    assert e.modifier_for(job="PLD", phase=MoonPhase.NEW) == -15


def test_quarter_moons_intermediate():
    e = MoonphaseEngine()
    fq = e.modifier_for(job="PLD", phase=MoonPhase.FIRST_QUARTER)
    full = e.modifier_for(job="PLD", phase=MoonPhase.FULL)
    new = e.modifier_for(job="PLD", phase=MoonPhase.NEW)
    assert new < fq < full


def test_multiplier_for_full_pld():
    e = MoonphaseEngine()
    # +15% → multiplier 1.15
    assert abs(
        e.multiplier_for(job="PLD", phase=MoonPhase.FULL) - 1.15
    ) < 0.001


def test_multiplier_for_new_pld():
    e = MoonphaseEngine()
    assert abs(
        e.multiplier_for(job="PLD", phase=MoonPhase.NEW) - 0.85
    ) < 0.001


def test_multiplier_neutral_is_one():
    e = MoonphaseEngine()
    assert abs(
        e.multiplier_for(job="WHM", phase=MoonPhase.FULL) - 1.0
    ) < 0.001


def test_all_jobs_at_full():
    e = MoonphaseEngine()
    out = e.all_jobs_at(phase=MoonPhase.FULL)
    assert out["PLD"] > 0
    assert out["NIN"] < 0
    assert out["BLM"] == 0


def test_all_jobs_at_new():
    e = MoonphaseEngine()
    out = e.all_jobs_at(phase=MoonPhase.NEW)
    assert out["PLD"] < 0
    assert out["NIN"] > 0


def test_eight_moon_phases():
    assert len(list(MoonPhase)) == 8


def test_light_pct_for_each_phase():
    e = MoonphaseEngine()
    assert e.light_pct_for(phase=MoonPhase.NEW) == 0
    assert e.light_pct_for(phase=MoonPhase.FULL) == 100
    # symmetric
    assert e.light_pct_for(
        phase=MoonPhase.FIRST_QUARTER,
    ) == e.light_pct_for(phase=MoonPhase.LAST_QUARTER)


def test_lowercase_job_normalized():
    e = MoonphaseEngine()
    upper = e.modifier_for(job="PLD", phase=MoonPhase.FULL)
    lower = e.modifier_for(job="pld", phase=MoonPhase.FULL)
    assert upper == lower


def test_thf_drk_match_nin_direction():
    e = MoonphaseEngine()
    for job in ("THF", "DRK"):
        assert e.modifier_for(job=job, phase=MoonPhase.NEW) > 0
        assert e.modifier_for(job=job, phase=MoonPhase.FULL) < 0
