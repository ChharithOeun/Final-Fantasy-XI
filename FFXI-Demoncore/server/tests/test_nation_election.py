"""Tests for nation_election."""
from __future__ import annotations

from server.nation_election import (
    NationElectionSystem, ElectionState,
)


def _declare(s, **overrides):
    args = dict(
        nation_id="bastok", term_days=365,
        campaign_open_day=0, polls_open_day=10,
        polls_close_day=20,
    )
    args.update(overrides)
    return s.declare(**args)


def test_declare_happy():
    s = NationElectionSystem()
    assert _declare(s) is not None


def test_declare_blank_nation():
    s = NationElectionSystem()
    assert _declare(s, nation_id="") is None


def test_declare_zero_term():
    s = NationElectionSystem()
    assert _declare(s, term_days=0) is None


def test_declare_inverted_dates():
    s = NationElectionSystem()
    assert _declare(
        s, polls_open_day=20, polls_close_day=10,
    ) is None


def test_register_candidate_happy():
    s = NationElectionSystem()
    eid = _declare(s)
    assert s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform",
    ) is True


def test_register_advances_to_campaigning():
    s = NationElectionSystem()
    eid = _declare(s)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform",
    )
    el = s.election(election_id=eid)
    assert el.state == ElectionState.CAMPAIGNING


def test_register_dup_blocked():
    s = NationElectionSystem()
    eid = _declare(s)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform",
    )
    assert s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform2",
    ) is False


def test_withdraw_candidate():
    s = NationElectionSystem()
    eid = _declare(s)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform",
    )
    assert s.withdraw_candidate(
        election_id=eid, candidate_id="cid",
    ) is True


def test_open_polls_happy():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform",
    )
    assert s.open_polls(
        election_id=eid, now_day=10,
    ) is True


def test_open_polls_too_early():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform",
    )
    assert s.open_polls(
        election_id=eid, now_day=5,
    ) is False


def test_open_polls_no_candidates():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10)
    # No candidates registered - still in DECLARED
    assert s.open_polls(
        election_id=eid, now_day=10,
    ) is False


def test_open_polls_all_withdrawn():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform",
    )
    s.withdraw_candidate(
        election_id=eid, candidate_id="cid",
    )
    assert s.open_polls(
        election_id=eid, now_day=10,
    ) is False


def test_cast_vote_happy():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10,
                   polls_close_day=20)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform",
    )
    s.open_polls(election_id=eid, now_day=10)
    assert s.cast_vote(
        election_id=eid, voter_id="bob",
        candidate_id="cid", now_day=12,
    ) is True


def test_double_vote_blocked():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10,
                   polls_close_day=20)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="reform",
    )
    s.open_polls(election_id=eid, now_day=10)
    s.cast_vote(
        election_id=eid, voter_id="bob",
        candidate_id="cid", now_day=12,
    )
    assert s.cast_vote(
        election_id=eid, voter_id="bob",
        candidate_id="cid", now_day=13,
    ) is False


def test_vote_for_withdrawn_blocked():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10,
                   polls_close_day=20)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="x",
    )
    s.register_candidate(
        election_id=eid, candidate_id="naji",
        platform="y",
    )
    s.open_polls(election_id=eid, now_day=10)
    s.withdraw_candidate(
        election_id=eid, candidate_id="naji",
    )
    assert s.cast_vote(
        election_id=eid, voter_id="bob",
        candidate_id="naji", now_day=12,
    ) is False


def test_vote_after_close_blocked():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10,
                   polls_close_day=20)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="x",
    )
    s.open_polls(election_id=eid, now_day=10)
    assert s.cast_vote(
        election_id=eid, voter_id="bob",
        candidate_id="cid", now_day=21,
    ) is False


def test_close_polls():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10,
                   polls_close_day=20)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="x",
    )
    s.open_polls(election_id=eid, now_day=10)
    assert s.close_polls(
        election_id=eid, now_day=20,
    ) is True


def test_certify_returns_winner():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10,
                   polls_close_day=20)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="x",
    )
    s.register_candidate(
        election_id=eid, candidate_id="naji",
        platform="y",
    )
    s.open_polls(election_id=eid, now_day=10)
    s.cast_vote(
        election_id=eid, voter_id="bob",
        candidate_id="cid", now_day=12,
    )
    s.cast_vote(
        election_id=eid, voter_id="cara",
        candidate_id="cid", now_day=12,
    )
    s.cast_vote(
        election_id=eid, voter_id="dave",
        candidate_id="naji", now_day=13,
    )
    s.close_polls(election_id=eid, now_day=20)
    assert s.certify(
        election_id=eid, now_day=21,
    ) == "cid"


def test_certify_tie_breaks_alphabetical():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10,
                   polls_close_day=20)
    s.register_candidate(
        election_id=eid, candidate_id="alpha",
        platform="x",
    )
    s.register_candidate(
        election_id=eid, candidate_id="beta",
        platform="y",
    )
    s.open_polls(election_id=eid, now_day=10)
    s.cast_vote(
        election_id=eid, voter_id="bob",
        candidate_id="alpha", now_day=12,
    )
    s.cast_vote(
        election_id=eid, voter_id="cara",
        candidate_id="beta", now_day=12,
    )
    s.close_polls(election_id=eid, now_day=20)
    assert s.certify(
        election_id=eid, now_day=21,
    ) == "alpha"


def test_tally():
    s = NationElectionSystem()
    eid = _declare(s, polls_open_day=10,
                   polls_close_day=20)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="x",
    )
    s.open_polls(election_id=eid, now_day=10)
    s.cast_vote(
        election_id=eid, voter_id="bob",
        candidate_id="cid", now_day=12,
    )
    s.cast_vote(
        election_id=eid, voter_id="cara",
        candidate_id="cid", now_day=12,
    )
    out = s.tally(election_id=eid)
    assert out == {"cid": 2}


def test_tally_excludes_withdrawn():
    s = NationElectionSystem()
    eid = _declare(s)
    s.register_candidate(
        election_id=eid, candidate_id="cid",
        platform="x",
    )
    s.withdraw_candidate(
        election_id=eid, candidate_id="cid",
    )
    out = s.tally(election_id=eid)
    assert out == {}


def test_election_unknown():
    s = NationElectionSystem()
    assert s.election(election_id="ghost") is None


def test_enum_count():
    assert len(list(ElectionState)) == 5
