"""Tests for player_referendum."""
from __future__ import annotations

from server.player_referendum import (
    PlayerReferendumSystem, ReferendumState,
    ReferendumOutcome,
)


def _propose(s: PlayerReferendumSystem) -> str:
    return s.propose(
        organizer_id="naji",
        question="Ratify the Bastok-Sandy treaty?",
        voting_close_day=20,
    )


def _ready(s: PlayerReferendumSystem) -> str:
    rid = _propose(s)
    for v in ("a", "b", "c"):
        s.enroll_constituent(
            referendum_id=rid, organizer_id="naji",
            voter_id=v, current_day=5,
        )
    return rid


def test_propose_happy():
    s = PlayerReferendumSystem()
    assert _propose(s) is not None


def test_propose_zero_close_blocked():
    s = PlayerReferendumSystem()
    assert s.propose(
        organizer_id="naji", question="x",
        voting_close_day=0,
    ) is None


def test_propose_empty_question_blocked():
    s = PlayerReferendumSystem()
    assert s.propose(
        organizer_id="naji", question="",
        voting_close_day=20,
    ) is None


def test_enroll_constituent_happy():
    s = PlayerReferendumSystem()
    rid = _propose(s)
    assert s.enroll_constituent(
        referendum_id=rid, organizer_id="naji",
        voter_id="a", current_day=5,
    ) is True


def test_enroll_wrong_organizer_blocked():
    s = PlayerReferendumSystem()
    rid = _propose(s)
    assert s.enroll_constituent(
        referendum_id=rid, organizer_id="bob",
        voter_id="a", current_day=5,
    ) is False


def test_enroll_after_close_blocked():
    s = PlayerReferendumSystem()
    rid = _propose(s)
    assert s.enroll_constituent(
        referendum_id=rid, organizer_id="naji",
        voter_id="a", current_day=25,
    ) is False


def test_enroll_dup_blocked():
    s = PlayerReferendumSystem()
    rid = _propose(s)
    s.enroll_constituent(
        referendum_id=rid, organizer_id="naji",
        voter_id="a", current_day=5,
    )
    assert s.enroll_constituent(
        referendum_id=rid, organizer_id="naji",
        voter_id="a", current_day=6,
    ) is False


def test_cast_yes_no_happy():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    assert s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=True, current_day=10,
    ) is True


def test_cast_non_constituent_blocked():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    assert s.cast_yes_no(
        referendum_id=rid, voter_id="stranger",
        vote_yes=True, current_day=10,
    ) is False


def test_cast_after_close_blocked():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    assert s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=True, current_day=25,
    ) is False


def test_cast_dup_blocked():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=True, current_day=10,
    )
    assert s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=False, current_day=11,
    ) is False


def test_tally_yes_majority():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=True, current_day=10,
    )
    s.cast_yes_no(
        referendum_id=rid, voter_id="b",
        vote_yes=True, current_day=10,
    )
    s.cast_yes_no(
        referendum_id=rid, voter_id="c",
        vote_yes=False, current_day=10,
    )
    outcome = s.tally(
        referendum_id=rid, current_day=21,
    )
    assert outcome == ReferendumOutcome.YES


def test_tally_no_majority():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=False, current_day=10,
    )
    s.cast_yes_no(
        referendum_id=rid, voter_id="b",
        vote_yes=False, current_day=10,
    )
    s.cast_yes_no(
        referendum_id=rid, voter_id="c",
        vote_yes=True, current_day=10,
    )
    outcome = s.tally(
        referendum_id=rid, current_day=21,
    )
    assert outcome == ReferendumOutcome.NO


def test_tally_tie():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=True, current_day=10,
    )
    s.cast_yes_no(
        referendum_id=rid, voter_id="b",
        vote_yes=False, current_day=10,
    )
    outcome = s.tally(
        referendum_id=rid, current_day=21,
    )
    assert outcome == ReferendumOutcome.TIED


def test_tally_before_close_blocked():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=True, current_day=10,
    )
    assert s.tally(
        referendum_id=rid, current_day=15,
    ) is None


def test_tally_twice_blocked():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=True, current_day=10,
    )
    s.tally(referendum_id=rid, current_day=21)
    assert s.tally(
        referendum_id=rid, current_day=22,
    ) is None


def test_yes_no_counts_recorded():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    s.cast_yes_no(
        referendum_id=rid, voter_id="a",
        vote_yes=True, current_day=10,
    )
    s.cast_yes_no(
        referendum_id=rid, voter_id="b",
        vote_yes=True, current_day=10,
    )
    s.cast_yes_no(
        referendum_id=rid, voter_id="c",
        vote_yes=False, current_day=10,
    )
    s.tally(referendum_id=rid, current_day=21)
    spec = s.referendum(referendum_id=rid)
    assert spec.yes_count == 2
    assert spec.no_count == 1
    assert spec.state == ReferendumState.CONCLUDED


def test_constituency_listing():
    s = PlayerReferendumSystem()
    rid = _ready(s)
    assert s.constituency(
        referendum_id=rid,
    ) == ["a", "b", "c"]


def test_unknown_referendum():
    s = PlayerReferendumSystem()
    assert s.referendum(
        referendum_id="ghost",
    ) is None


def test_state_count():
    assert len(list(ReferendumState)) == 2


def test_outcome_count():
    assert len(list(ReferendumOutcome)) == 3


def test_propose_empty_organizer_blocked():
    s = PlayerReferendumSystem()
    assert s.propose(
        organizer_id="", question="x",
        voting_close_day=20,
    ) is None
