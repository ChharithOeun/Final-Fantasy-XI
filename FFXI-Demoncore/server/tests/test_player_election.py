"""Tests for player_election."""
from __future__ import annotations

from server.player_election import (
    PlayerElectionSystem, ElectionState,
)


def _announce(
    s: PlayerElectionSystem,
) -> str:
    return s.announce(
        organizer_id="naji",
        position_title="Bastok Magistrate",
        registration_close_day=10,
        voting_close_day=20,
    )


def _ready_to_vote(
    s: PlayerElectionSystem,
) -> str:
    """Set up election with 2 candidates and 3 voters,
    advance to VOTING phase."""
    eid = _announce(s)
    s.register_candidate(
        election_id=eid, candidate_id="alice",
        current_day=5,
    )
    s.register_candidate(
        election_id=eid, candidate_id="bob",
        current_day=5,
    )
    for v in ("v1", "v2", "v3"):
        s.enroll_voter(
            election_id=eid, organizer_id="naji",
            voter_id=v, current_day=5,
        )
    return eid


def test_announce_happy():
    s = PlayerElectionSystem()
    assert _announce(s) is not None


def test_announce_voting_before_reg_blocked():
    s = PlayerElectionSystem()
    assert s.announce(
        organizer_id="naji", position_title="x",
        registration_close_day=20,
        voting_close_day=10,
    ) is None


def test_announce_zero_reg_blocked():
    s = PlayerElectionSystem()
    assert s.announce(
        organizer_id="naji", position_title="x",
        registration_close_day=0,
        voting_close_day=10,
    ) is None


def test_register_candidate_happy():
    s = PlayerElectionSystem()
    eid = _announce(s)
    assert s.register_candidate(
        election_id=eid, candidate_id="alice",
        current_day=5,
    ) is True


def test_register_candidate_dup_blocked():
    s = PlayerElectionSystem()
    eid = _announce(s)
    s.register_candidate(
        election_id=eid, candidate_id="alice",
        current_day=5,
    )
    assert s.register_candidate(
        election_id=eid, candidate_id="alice",
        current_day=6,
    ) is False


def test_register_after_close_blocked():
    s = PlayerElectionSystem()
    eid = _announce(s)
    assert s.register_candidate(
        election_id=eid, candidate_id="late",
        current_day=15,
    ) is False


def test_enroll_voter_happy():
    s = PlayerElectionSystem()
    eid = _announce(s)
    assert s.enroll_voter(
        election_id=eid, organizer_id="naji",
        voter_id="v1", current_day=5,
    ) is True


def test_enroll_voter_wrong_organizer_blocked():
    s = PlayerElectionSystem()
    eid = _announce(s)
    assert s.enroll_voter(
        election_id=eid, organizer_id="bob",
        voter_id="v1", current_day=5,
    ) is False


def test_enroll_voter_dup_blocked():
    s = PlayerElectionSystem()
    eid = _announce(s)
    s.enroll_voter(
        election_id=eid, organizer_id="naji",
        voter_id="v1", current_day=5,
    )
    assert s.enroll_voter(
        election_id=eid, organizer_id="naji",
        voter_id="v1", current_day=6,
    ) is False


def test_cast_ballot_happy():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    assert s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="alice", current_day=12,
    ) is True


def test_cast_ballot_before_voting_blocked():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    # Day 5 is before reg_close (10) — still in REG
    assert s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="alice", current_day=5,
    ) is False


def test_cast_ballot_after_voting_close_blocked():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    assert s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="alice", current_day=25,
    ) is False


def test_cast_ballot_non_voter_blocked():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    assert s.cast_ballot(
        election_id=eid, voter_id="stranger",
        candidate_id="alice", current_day=12,
    ) is False


def test_cast_ballot_non_candidate_blocked():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    assert s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="ghost", current_day=12,
    ) is False


def test_cast_ballot_dup_blocked():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="alice", current_day=12,
    )
    assert s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="bob", current_day=13,
    ) is False


def test_tally_happy():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="alice", current_day=12,
    )
    s.cast_ballot(
        election_id=eid, voter_id="v2",
        candidate_id="alice", current_day=13,
    )
    s.cast_ballot(
        election_id=eid, voter_id="v3",
        candidate_id="bob", current_day=14,
    )
    winner = s.tally(
        election_id=eid, current_day=21,
    )
    assert winner == "alice"
    assert s.election(
        election_id=eid,
    ).state == ElectionState.CONCLUDED


def test_tally_before_voting_close_blocked():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="alice", current_day=12,
    )
    assert s.tally(
        election_id=eid, current_day=15,
    ) is None


def test_tally_no_votes_returns_none():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    assert s.tally(
        election_id=eid, current_day=21,
    ) is None


def test_tally_tiebreak_by_registration_order():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    # 1 vote each — tie. Alice registered first.
    s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="alice", current_day=12,
    )
    s.cast_ballot(
        election_id=eid, voter_id="v2",
        candidate_id="bob", current_day=13,
    )
    assert s.tally(
        election_id=eid, current_day=21,
    ) == "alice"


def test_tally_twice_blocked():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="alice", current_day=12,
    )
    s.tally(election_id=eid, current_day=21)
    assert s.tally(
        election_id=eid, current_day=22,
    ) is None


def test_vote_count():
    s = PlayerElectionSystem()
    eid = _ready_to_vote(s)
    s.cast_ballot(
        election_id=eid, voter_id="v1",
        candidate_id="alice", current_day=12,
    )
    s.cast_ballot(
        election_id=eid, voter_id="v2",
        candidate_id="alice", current_day=13,
    )
    assert s.vote_count(
        election_id=eid, candidate_id="alice",
    ) == 2


def test_unknown_election():
    s = PlayerElectionSystem()
    assert s.election(
        election_id="ghost",
    ) is None


def test_enum_count():
    assert len(list(ElectionState)) == 3
