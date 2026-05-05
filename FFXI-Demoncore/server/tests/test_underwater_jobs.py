"""Tests for underwater jobs."""
from __future__ import annotations

from server.underwater_jobs import UnderwaterJob, UnderwaterJobsRegistry


def test_two_jobs():
    r = UnderwaterJobsRegistry()
    assert r.total_jobs() == 2


def test_tidemage_profile():
    r = UnderwaterJobsRegistry()
    p = r.profile_for(job=UnderwaterJob.TIDEMAGE)
    assert p.primary_stat == "INT"
    assert p.prereq_job == "BLM"
    assert p.prereq_level == 30


def test_spear_diver_profile():
    r = UnderwaterJobsRegistry()
    p = r.profile_for(job=UnderwaterJob.SPEAR_DIVER)
    assert p.primary_stat == "STR"
    assert p.prereq_job == "DRG"


def test_unlock_tidemage_basic():
    r = UnderwaterJobsRegistry()
    res = r.unlock_for(
        player_id="kraw",
        job=UnderwaterJob.TIDEMAGE,
        prereq_job="BLM",
        prereq_level=30,
        completed_trial_id="tidemage_initiation",
    )
    assert res.accepted


def test_unlock_wrong_prereq_job():
    r = UnderwaterJobsRegistry()
    res = r.unlock_for(
        player_id="kraw",
        job=UnderwaterJob.TIDEMAGE,
        prereq_job="WAR",
        prereq_level=30,
        completed_trial_id="tidemage_initiation",
    )
    assert not res.accepted


def test_unlock_low_level():
    r = UnderwaterJobsRegistry()
    res = r.unlock_for(
        player_id="kraw",
        job=UnderwaterJob.TIDEMAGE,
        prereq_job="BLM",
        prereq_level=15,
        completed_trial_id="tidemage_initiation",
    )
    assert not res.accepted


def test_unlock_wrong_trial():
    r = UnderwaterJobsRegistry()
    res = r.unlock_for(
        player_id="kraw",
        job=UnderwaterJob.TIDEMAGE,
        prereq_job="BLM",
        prereq_level=30,
        completed_trial_id="ghost_trial",
    )
    assert not res.accepted


def test_unlock_double_blocked():
    r = UnderwaterJobsRegistry()
    r.unlock_for(
        player_id="kraw",
        job=UnderwaterJob.TIDEMAGE,
        prereq_job="BLM",
        prereq_level=30,
        completed_trial_id="tidemage_initiation",
    )
    res = r.unlock_for(
        player_id="kraw",
        job=UnderwaterJob.TIDEMAGE,
        prereq_job="BLM",
        prereq_level=99,
        completed_trial_id="tidemage_initiation",
    )
    assert not res.accepted


def test_is_unlocked():
    r = UnderwaterJobsRegistry()
    assert not r.is_unlocked(
        player_id="kraw", job=UnderwaterJob.TIDEMAGE,
    )
    r.unlock_for(
        player_id="kraw",
        job=UnderwaterJob.TIDEMAGE,
        prereq_job="BLM",
        prereq_level=30,
        completed_trial_id="tidemage_initiation",
    )
    assert r.is_unlocked(
        player_id="kraw", job=UnderwaterJob.TIDEMAGE,
    )


def test_swim_mastery_bonus():
    r = UnderwaterJobsRegistry()
    bonus = r.swim_mastery_bonus(job=UnderwaterJob.TIDEMAGE)
    assert bonus["breath_drain_pct"] == -50
    assert bonus["pressure_tier_skip"] == 1


def test_unlock_spear_diver():
    r = UnderwaterJobsRegistry()
    res = r.unlock_for(
        player_id="kraw",
        job=UnderwaterJob.SPEAR_DIVER,
        prereq_job="DRG",
        prereq_level=30,
        completed_trial_id="spear_diver_initiation",
    )
    assert res.accepted


def test_per_player_isolation():
    r = UnderwaterJobsRegistry()
    r.unlock_for(
        player_id="alice",
        job=UnderwaterJob.TIDEMAGE,
        prereq_job="BLM",
        prereq_level=30,
        completed_trial_id="tidemage_initiation",
    )
    assert not r.is_unlocked(
        player_id="bob", job=UnderwaterJob.TIDEMAGE,
    )


def test_signature_abilities():
    r = UnderwaterJobsRegistry()
    tm = r.profile_for(job=UnderwaterJob.TIDEMAGE)
    sd = r.profile_for(job=UnderwaterJob.SPEAR_DIVER)
    assert tm.signature_ability == "summon_tide"
    assert sd.signature_ability == "deep_plunge"


def test_weapons():
    r = UnderwaterJobsRegistry()
    tm = r.profile_for(job=UnderwaterJob.TIDEMAGE)
    sd = r.profile_for(job=UnderwaterJob.SPEAR_DIVER)
    assert "staff" in tm.weapon_kinds
    assert "harpoon" in sd.weapon_kinds
