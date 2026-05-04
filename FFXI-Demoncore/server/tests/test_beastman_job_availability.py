"""Tests for beastman job availability."""
from __future__ import annotations

from server.beastman_job_availability import (
    BeastmanJobAvailability,
    JobAvailabilityKind,
    JobCode,
)
from server.beastman_playable_races import BeastmanRace


def test_yagudo_starter_jobs():
    j = BeastmanJobAvailability()
    assert j.availability_kind(
        race=BeastmanRace.YAGUDO, job=JobCode.WHM,
    ) == JobAvailabilityKind.STARTER
    assert j.availability_kind(
        race=BeastmanRace.YAGUDO, job=JobCode.MNK,
    ) == JobAvailabilityKind.STARTER


def test_quadav_blm_starter():
    j = BeastmanJobAvailability()
    assert j.availability_kind(
        race=BeastmanRace.QUADAV, job=JobCode.BLM,
    ) == JobAvailabilityKind.STARTER


def test_lamia_thf_starter():
    j = BeastmanJobAvailability()
    assert j.availability_kind(
        race=BeastmanRace.LAMIA, job=JobCode.THF,
    ) == JobAvailabilityKind.STARTER


def test_orc_war_starter():
    j = BeastmanJobAvailability()
    assert j.availability_kind(
        race=BeastmanRace.ORC, job=JobCode.WAR,
    ) == JobAvailabilityKind.STARTER


def test_yagudo_brd_extended():
    j = BeastmanJobAvailability()
    assert j.availability_kind(
        race=BeastmanRace.YAGUDO, job=JobCode.BRD,
    ) == JobAvailabilityKind.EXTENDED


def test_quadav_geo_extended():
    j = BeastmanJobAvailability()
    assert j.availability_kind(
        race=BeastmanRace.QUADAV, job=JobCode.GEO,
    ) == JobAvailabilityKind.EXTENDED


def test_yagudo_blm_forbidden():
    j = BeastmanJobAvailability()
    assert j.availability_kind(
        race=BeastmanRace.YAGUDO, job=JobCode.BLM,
    ) == JobAvailabilityKind.FORBIDDEN


def test_orc_smn_forbidden():
    """Orcs don't get spirit-summoner; canon match."""
    j = BeastmanJobAvailability()
    assert j.availability_kind(
        race=BeastmanRace.ORC, job=JobCode.SMN,
    ) == JobAvailabilityKind.FORBIDDEN


def test_can_change_to_starter():
    j = BeastmanJobAvailability()
    assert j.can_change_to(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
    )


def test_cannot_change_to_extended_without_unlock():
    j = BeastmanJobAvailability()
    assert not j.can_change_to(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )


def test_complete_unlock_quest_extended():
    j = BeastmanJobAvailability()
    assert j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )
    assert j.has_unlocked(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )


def test_complete_unlock_starter_rejected():
    j = BeastmanJobAvailability()
    assert not j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.WHM,
    )


def test_complete_unlock_forbidden_rejected():
    j = BeastmanJobAvailability()
    assert not j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BLM,
    )


def test_complete_unlock_double_rejected():
    j = BeastmanJobAvailability()
    j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )
    assert not j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )


def test_can_change_after_unlock():
    j = BeastmanJobAvailability()
    j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )
    assert j.can_change_to(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )


def test_cannot_change_to_forbidden():
    j = BeastmanJobAvailability()
    assert not j.can_change_to(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BLM,
    )


def test_unlock_per_race_isolation():
    j = BeastmanJobAvailability()
    j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )
    # alice has no orc unlock
    assert not j.has_unlocked(
        player_id="alice", race=BeastmanRace.ORC,
        job=JobCode.SAM,
    )


def test_available_jobs_combined():
    j = BeastmanJobAvailability()
    yagudo_jobs = j.available_jobs(
        race=BeastmanRace.YAGUDO,
    )
    assert JobCode.WHM in yagudo_jobs
    assert JobCode.MNK in yagudo_jobs
    assert JobCode.BRD in yagudo_jobs
    assert JobCode.NIN in yagudo_jobs
    assert JobCode.BLM not in yagudo_jobs


def test_all_unlocked_for():
    j = BeastmanJobAvailability()
    j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )
    j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.NIN,
    )
    unlocked = j.all_unlocked_for(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )
    assert set(unlocked) == {JobCode.BRD, JobCode.NIN}


def test_total_unlocks_per_player():
    j = BeastmanJobAvailability()
    j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.YAGUDO,
        job=JobCode.BRD,
    )
    j.complete_unlock_quest(
        player_id="alice", race=BeastmanRace.ORC,
        job=JobCode.SAM,
    )
    assert j.total_unlocks(player_id="alice") == 2
