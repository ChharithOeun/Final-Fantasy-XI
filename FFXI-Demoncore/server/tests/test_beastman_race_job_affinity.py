"""Tests for the beastman race-job affinity."""
from __future__ import annotations

from server.beastman_job_availability import JobCode
from server.beastman_playable_races import BeastmanRace
from server.beastman_race_job_affinity import (
    BeastmanRaceJobAffinity,
    DEFAULT_DAMAGE_HEAL_PCT,
    DEFAULT_FAME_MULTIPLIER,
)


def test_lamia_affinity_jobs():
    a = BeastmanRaceJobAffinity()
    jobs = a.affinity_jobs(race=BeastmanRace.LAMIA)
    expected = {
        JobCode.PUP, JobCode.BST, JobCode.SMN,
        JobCode.BRD, JobCode.GEO, JobCode.DNC,
        JobCode.COR, JobCode.SCH,
    }
    assert set(jobs) == expected


def test_yagudo_affinity_jobs():
    a = BeastmanRaceJobAffinity()
    jobs = a.affinity_jobs(race=BeastmanRace.YAGUDO)
    expected = {
        JobCode.SAM, JobCode.BLU, JobCode.NIN,
        JobCode.MNK, JobCode.PUP, JobCode.BLM,
        JobCode.WHM,
    }
    assert set(jobs) == expected


def test_quadav_affinity_jobs():
    a = BeastmanRaceJobAffinity()
    jobs = a.affinity_jobs(race=BeastmanRace.QUADAV)
    expected = {
        JobCode.WAR, JobCode.PLD, JobCode.DRK,
        JobCode.DRG, JobCode.RUN,
    }
    assert set(jobs) == expected


def test_orc_affinity_jobs():
    a = BeastmanRaceJobAffinity()
    jobs = a.affinity_jobs(race=BeastmanRace.ORC)
    expected = {
        JobCode.THF, JobCode.RDM, JobCode.RNG,
        JobCode.COR, JobCode.WAR, JobCode.MNK,
        JobCode.BST,
    }
    assert set(jobs) == expected


def test_has_affinity():
    a = BeastmanRaceJobAffinity()
    assert a.has_affinity(
        race=BeastmanRace.YAGUDO, job=JobCode.SAM,
    )


def test_no_affinity():
    a = BeastmanRaceJobAffinity()
    assert not a.has_affinity(
        race=BeastmanRace.YAGUDO, job=JobCode.WAR,
    )


def test_bonus_for_affinity_job():
    a = BeastmanRaceJobAffinity()
    bonus = a.bonus_for(
        race=BeastmanRace.LAMIA, job=JobCode.BRD,
    )
    assert bonus.has_bonus
    assert bonus.damage_heal_pct == DEFAULT_DAMAGE_HEAL_PCT
    assert bonus.fame_multiplier == DEFAULT_FAME_MULTIPLIER


def test_bonus_for_non_affinity_job():
    a = BeastmanRaceJobAffinity()
    bonus = a.bonus_for(
        race=BeastmanRace.LAMIA, job=JobCode.WAR,
    )
    assert not bonus.has_bonus
    assert bonus.fame_multiplier == 1.0


def test_quadav_drg_requires_pet():
    a = BeastmanRaceJobAffinity()
    no_pet = a.bonus_for(
        race=BeastmanRace.QUADAV, job=JobCode.DRG,
        pet_active=False,
    )
    assert not no_pet.has_bonus
    with_pet = a.bonus_for(
        race=BeastmanRace.QUADAV, job=JobCode.DRG,
        pet_active=True,
    )
    assert with_pet.has_bonus


def test_quadav_war_no_pet_gate():
    """Non-DRG affinity jobs aren't pet-gated."""
    a = BeastmanRaceJobAffinity()
    bonus = a.bonus_for(
        race=BeastmanRace.QUADAV, job=JobCode.WAR,
        pet_active=False,
    )
    assert bonus.has_bonus


def test_is_pet_gated_drg():
    a = BeastmanRaceJobAffinity()
    assert a.is_pet_gated(
        race=BeastmanRace.QUADAV, job=JobCode.DRG,
    )


def test_is_pet_gated_other():
    a = BeastmanRaceJobAffinity()
    assert not a.is_pet_gated(
        race=BeastmanRace.QUADAV, job=JobCode.WAR,
    )


def test_total_affinity_jobs_count():
    a = BeastmanRaceJobAffinity()
    assert a.total_affinity_jobs(
        race=BeastmanRace.LAMIA,
    ) == 8
    assert a.total_affinity_jobs(
        race=BeastmanRace.YAGUDO,
    ) == 7
    assert a.total_affinity_jobs(
        race=BeastmanRace.QUADAV,
    ) == 5
    assert a.total_affinity_jobs(
        race=BeastmanRace.ORC,
    ) == 7


def test_orc_thf_affinity_present():
    a = BeastmanRaceJobAffinity()
    bonus = a.bonus_for(
        race=BeastmanRace.ORC, job=JobCode.THF,
    )
    assert bonus.has_bonus


def test_orc_smn_no_affinity():
    """Per spec, Orcs don't have SMN."""
    a = BeastmanRaceJobAffinity()
    assert not a.has_affinity(
        race=BeastmanRace.ORC, job=JobCode.SMN,
    )


def test_yagudo_pup_affinity_no_pet_gate():
    """Yagudo PUP isn't pet-gated even though PUP is a pet job."""
    a = BeastmanRaceJobAffinity()
    bonus = a.bonus_for(
        race=BeastmanRace.YAGUDO, job=JobCode.PUP,
        pet_active=False,
    )
    assert bonus.has_bonus


def test_lamia_smn_affinity():
    a = BeastmanRaceJobAffinity()
    assert a.has_affinity(
        race=BeastmanRace.LAMIA, job=JobCode.SMN,
    )


def test_quadav_run_affinity():
    a = BeastmanRaceJobAffinity()
    assert a.has_affinity(
        race=BeastmanRace.QUADAV, job=JobCode.RUN,
    )
