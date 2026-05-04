"""Tests for the beastman job unlock quests."""
from __future__ import annotations

from server.beastman_job_availability import (
    BeastmanJobAvailability, JobCode,
)
from server.beastman_job_unlock_quests import (
    BeastmanJobUnlockQuests,
    UnlockChainStep,
)
from server.beastman_playable_races import BeastmanRace


def _avail():
    return BeastmanJobAvailability()


def _yagudo_rdm_steps():
    return (
        UnlockChainStep(
            step_index=0, label="Seek Lamia tutor",
        ),
        UnlockChainStep(
            step_index=1, label="Forge contract",
        ),
        UnlockChainStep(
            step_index=2, label="Trial of Tongues",
        ),
    )


def test_register_chain():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    chain = j.register_chain(
        race=BeastmanRace.YAGUDO,
        job=JobCode.RDM,
        tutor_npc_id="lamia_tutor_1",
        steps=_yagudo_rdm_steps(),
    )
    assert chain is not None


def test_register_no_steps_rejected():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    res = j.register_chain(
        race=BeastmanRace.YAGUDO,
        job=JobCode.RDM,
        tutor_npc_id="x", steps=(),
    )
    assert res is None


def test_register_non_contiguous_rejected():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    bad = (
        UnlockChainStep(step_index=0, label="a"),
        UnlockChainStep(step_index=2, label="c"),
    )
    res = j.register_chain(
        race=BeastmanRace.YAGUDO,
        job=JobCode.RDM,
        tutor_npc_id="x", steps=bad,
    )
    assert res is None


def test_register_double_rejected():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    res = j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="y", steps=_yagudo_rdm_steps(),
    )
    assert res is None


def test_start_chain():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    assert j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )


def test_start_unknown_chain_rejected():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    assert not j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )


def test_start_starter_job_rejected():
    """A STARTER job doesn't need a chain."""
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.WHM,
        tutor_npc_id="x",
        steps=(UnlockChainStep(step_index=0, label="x"),),
    )
    assert not j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.WHM,
    )


def test_double_start_rejected():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    assert not j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )


def test_complete_step_in_order():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    res = j.complete_step(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        step_index=0,
    )
    assert res.accepted


def test_complete_step_out_of_order():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    res = j.complete_step(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        step_index=2,
    )
    assert not res.accepted


def test_complete_chain_after_all_steps():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    for i in range(3):
        j.complete_step(
            player_id="alice",
            race=BeastmanRace.YAGUDO, job=JobCode.RDM,
            step_index=i,
        )
    res = j.complete_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    assert res.accepted


def test_complete_chain_without_steps_rejected():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    res = j.complete_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    assert not res.accepted


def test_unlocked_via_chain():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    for i in range(3):
        j.complete_step(
            player_id="alice",
            race=BeastmanRace.YAGUDO, job=JobCode.RDM,
            step_index=i,
        )
    j.complete_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    assert j.unlocked_via_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )


def test_can_play_starter_without_chain():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    assert j.can_play(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.WHM,
    )


def test_can_play_after_chain_completion():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    for i in range(3):
        j.complete_step(
            player_id="alice",
            race=BeastmanRace.YAGUDO, job=JobCode.RDM,
            step_index=i,
        )
    j.complete_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    assert j.can_play(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )


def test_cannot_play_unstarted_unrelated():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    assert not j.can_play(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )


def test_complete_step_unstarted_chain():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    res = j.complete_step(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        step_index=0,
    )
    assert not res.accepted


def test_total_chains():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    j.register_chain(
        race=BeastmanRace.ORC, job=JobCode.SCH,
        tutor_npc_id="y",
        steps=(UnlockChainStep(step_index=0, label="x"),),
    )
    assert j.total_chains() == 2


def test_per_player_isolation():
    j = BeastmanJobUnlockQuests(job_availability=_avail())
    j.register_chain(
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
        tutor_npc_id="x", steps=_yagudo_rdm_steps(),
    )
    j.start_chain(
        player_id="alice",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
    assert not j.unlocked_via_chain(
        player_id="bob",
        race=BeastmanRace.YAGUDO, job=JobCode.RDM,
    )
