"""Tests for job training (AI mentor apprenticeship)."""
from __future__ import annotations

from server.faction_reputation import PlayerFactionReputation
from server.job_training import (
    ApprenticeshipStatus,
    JobTrainingRegistry,
    MentorProfile,
    MentorTier,
    TrainingSubject,
)


def _master_mentor() -> MentorProfile:
    return MentorProfile(
        mentor_id="cooper_smith",
        faction_id="bastok",
        subject=TrainingSubject.SMITHING,
        tier=MentorTier.MASTER,
        max_apprentices=2,
        grants_signed_recipes=False,
    )


def _grandmaster_mentor() -> MentorProfile:
    return MentorProfile(
        mentor_id="ironhand_grand",
        faction_id="bastok",
        subject=TrainingSubject.SMITHING,
        tier=MentorTier.GRANDMASTER,
        max_apprentices=1,
        grants_signed_recipes=True,
    )


def _rep_friendly() -> PlayerFactionReputation:
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="bastok", value=100)
    return rep


def test_register_mentor_lookup():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    assert reg.mentor("cooper_smith") is not None
    assert reg.total_mentors() == 1


def test_propose_unknown_mentor_rejected():
    reg = JobTrainingRegistry()
    res = reg.propose_apprenticeship(
        player_id="alice", mentor_id="ghost",
        subject=TrainingSubject.SMITHING,
        rep=_rep_friendly(),
    )
    assert not res.accepted


def test_propose_subject_mismatch_rejected():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    res = reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.ALCHEMY,
        rep=_rep_friendly(),
    )
    assert not res.accepted
    assert "subject" in res.reason


def test_propose_low_rep_rejected():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="bastok", value=20)  # NEUTRAL
    res = reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=rep,
    )
    assert not res.accepted
    assert "rep" in res.reason.lower()


def test_propose_friendly_accepted():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    res = reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING,
        rep=_rep_friendly(),
    )
    assert res.accepted
    assert res.apprenticeship.status == ApprenticeshipStatus.PROPOSED


def test_capacity_block_when_full():
    reg = JobTrainingRegistry()
    reg.register_mentor(_grandmaster_mentor())  # 1 slot
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="ironhand_grand",
        subject=TrainingSubject.SMITHING,
        rep=_rep_friendly(),
    )
    rep_b = PlayerFactionReputation(player_id="bob")
    rep_b.set(faction_id="bastok", value=100)
    res = reg.propose_apprenticeship(
        player_id="bob", mentor_id="ironhand_grand",
        subject=TrainingSubject.SMITHING, rep=rep_b,
    )
    assert not res.accepted
    assert "capacity" in res.reason


def test_double_apprentice_with_same_mentor_rejected():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    second = reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    assert not second.accepted


def test_accept_moves_proposed_to_active():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    assert reg.accept(
        player_id="alice", mentor_id="cooper_smith",
    )
    aps = reg.apprenticeships_of_player("alice")
    assert aps[0].status == ApprenticeshipStatus.ACTIVE


def test_accept_unknown_returns_false():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    assert not reg.accept(
        player_id="alice", mentor_id="cooper_smith",
    )


def test_skill_gain_bonus_only_when_active():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    # Bonus is 1.0 when no active apprenticeship
    assert reg.skill_gain_bonus(
        player_id="alice", subject=TrainingSubject.SMITHING,
    ) == 1.0
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    # Still proposed, not active -> no bonus
    assert reg.skill_gain_bonus(
        player_id="alice", subject=TrainingSubject.SMITHING,
    ) == 1.0
    reg.accept(player_id="alice", mentor_id="cooper_smith")
    # Active master -> 1.25x
    assert reg.skill_gain_bonus(
        player_id="alice", subject=TrainingSubject.SMITHING,
    ) == 1.25


def test_skill_gain_bonus_picks_best_tier():
    """If a player has two active apprenticeships in the same
    subject (rare but possible), the better tier wins."""
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    reg.register_mentor(_grandmaster_mentor())
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="ironhand_grand",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.accept(player_id="alice", mentor_id="cooper_smith")
    reg.accept(player_id="alice", mentor_id="ironhand_grand")
    assert reg.skill_gain_bonus(
        player_id="alice", subject=TrainingSubject.SMITHING,
    ) == 1.40


def test_grants_signed_recipes_only_grandmaster():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    reg.register_mentor(_grandmaster_mentor())
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.accept(player_id="alice", mentor_id="cooper_smith")
    assert not reg.grants_signed_for(
        player_id="alice", subject=TrainingSubject.SMITHING,
    )
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="ironhand_grand",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.accept(player_id="alice", mentor_id="ironhand_grand")
    assert reg.grants_signed_for(
        player_id="alice", subject=TrainingSubject.SMITHING,
    )


def test_complete_active_apprenticeship():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.accept(player_id="alice", mentor_id="cooper_smith")
    assert reg.complete(
        player_id="alice", mentor_id="cooper_smith",
    )
    aps = reg.apprenticeships_of_player("alice")
    assert aps[0].status == ApprenticeshipStatus.COMPLETED


def test_dismiss_records_cause():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.accept(player_id="alice", mentor_id="cooper_smith")
    reg.dismiss(
        player_id="alice", mentor_id="cooper_smith",
        cause="forgery",
    )
    aps = reg.apprenticeships_of_player("alice")
    assert aps[0].status == ApprenticeshipStatus.DISMISSED
    assert aps[0].cause == "forgery"


def test_abandon():
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.accept(player_id="alice", mentor_id="cooper_smith")
    reg.abandon(player_id="alice", mentor_id="cooper_smith")
    aps = reg.apprenticeships_of_player("alice")
    assert aps[0].status == ApprenticeshipStatus.ABANDONED


def test_dismissed_apprentice_does_not_block_new_slot():
    """When a mentor dismisses an apprentice, the slot frees up."""
    reg = JobTrainingRegistry()
    reg.register_mentor(_grandmaster_mentor())  # 1 slot
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="ironhand_grand",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.accept(player_id="alice", mentor_id="ironhand_grand")
    reg.dismiss(
        player_id="alice", mentor_id="ironhand_grand",
        cause="not enough effort",
    )
    rep_b = PlayerFactionReputation(player_id="bob")
    rep_b.set(faction_id="bastok", value=100)
    res = reg.propose_apprenticeship(
        player_id="bob", mentor_id="ironhand_grand",
        subject=TrainingSubject.SMITHING, rep=rep_b,
    )
    assert res.accepted


def test_full_lifecycle_alice_journeys_to_grandmaster():
    """Alice apprentices with a master, completes, then graduates
    to a grandmaster's apprenticeship."""
    reg = JobTrainingRegistry()
    reg.register_mentor(_master_mentor())
    reg.register_mentor(_grandmaster_mentor())
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="cooper_smith",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.accept(player_id="alice", mentor_id="cooper_smith")
    assert reg.skill_gain_bonus(
        player_id="alice", subject=TrainingSubject.SMITHING,
    ) == 1.25
    reg.complete(
        player_id="alice", mentor_id="cooper_smith",
    )
    # Now apprentice with grandmaster
    reg.propose_apprenticeship(
        player_id="alice", mentor_id="ironhand_grand",
        subject=TrainingSubject.SMITHING, rep=_rep_friendly(),
    )
    reg.accept(player_id="alice", mentor_id="ironhand_grand")
    assert reg.skill_gain_bonus(
        player_id="alice", subject=TrainingSubject.SMITHING,
    ) == 1.40
    assert reg.grants_signed_for(
        player_id="alice", subject=TrainingSubject.SMITHING,
    )
