"""Tests for political_offices."""
from __future__ import annotations

from server.political_offices import (
    Office, OfficeKind, PoliticalOffices,
)


def _senator(oid="bastok_senator_1", nation="bastok",
             elected=True):
    return Office(
        office_id=oid, nation=nation,
        kind=OfficeKind.SENATOR,
        title=f"Senator from {nation}",
        is_elected=elected,
    )


def test_register_office():
    p = PoliticalOffices()
    assert p.register_office(_senator()) is True


def test_register_blank_id_blocked():
    p = PoliticalOffices()
    bad = Office(
        office_id="", nation="bastok",
        kind=OfficeKind.SENATOR,
        title="x", is_elected=True,
    )
    assert p.register_office(bad) is False


def test_register_dup_blocked():
    p = PoliticalOffices()
    p.register_office(_senator())
    assert p.register_office(_senator()) is False


def test_install_holder():
    p = PoliticalOffices()
    p.register_office(_senator())
    assert p.install_holder(
        office_id="bastok_senator_1", holder_id="cid",
    ) is True
    assert p.holder(
        office_id="bastok_senator_1",
    ) == "cid"


def test_install_holder_unknown():
    p = PoliticalOffices()
    assert p.install_holder(
        office_id="ghost", holder_id="cid",
    ) is False


def test_install_holder_during_election_blocked():
    p = PoliticalOffices()
    p.register_office(_senator())
    p.open_election(
        office_id="bastok_senator_1",
        candidates=["a", "b"], deadline_day=10,
    )
    assert p.install_holder(
        office_id="bastok_senator_1", holder_id="cid",
    ) is False


def test_open_election():
    p = PoliticalOffices()
    p.register_office(_senator())
    assert p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "bob"],
        deadline_day=10,
    ) is True


def test_open_election_unelected_office_blocked():
    p = PoliticalOffices()
    king = Office(
        office_id="sandy_king", nation="sandy",
        kind=OfficeKind.KING, title="King",
        is_elected=False,
    )
    p.register_office(king)
    assert p.open_election(
        office_id="sandy_king",
        candidates=["alice", "bob"], deadline_day=10,
    ) is False


def test_open_election_one_candidate_blocked():
    p = PoliticalOffices()
    p.register_office(_senator())
    assert p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice"], deadline_day=10,
    ) is False


def test_open_election_dup_candidates_blocked():
    p = PoliticalOffices()
    p.register_office(_senator())
    assert p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "alice"], deadline_day=10,
    ) is False


def test_open_election_already_open_blocked():
    p = PoliticalOffices()
    p.register_office(_senator())
    p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "bob"], deadline_day=10,
    )
    assert p.open_election(
        office_id="bastok_senator_1",
        candidates=["c", "d"], deadline_day=20,
    ) is False


def test_cast_vote():
    p = PoliticalOffices()
    p.register_office(_senator())
    p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "bob"], deadline_day=10,
    )
    assert p.cast_vote(
        voter_id="v1", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="alice",
    ) is True


def test_cast_vote_wrong_nation_blocked():
    p = PoliticalOffices()
    p.register_office(_senator())
    p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "bob"], deadline_day=10,
    )
    assert p.cast_vote(
        voter_id="v1", voter_nation="sandy",
        office_id="bastok_senator_1", candidate="alice",
    ) is False


def test_cast_vote_unknown_candidate_blocked():
    p = PoliticalOffices()
    p.register_office(_senator())
    p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "bob"], deadline_day=10,
    )
    assert p.cast_vote(
        voter_id="v1", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="evil",
    ) is False


def test_cast_double_vote_blocked():
    p = PoliticalOffices()
    p.register_office(_senator())
    p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "bob"], deadline_day=10,
    )
    p.cast_vote(
        voter_id="v1", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="alice",
    )
    assert p.cast_vote(
        voter_id="v1", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="bob",
    ) is False


def test_cast_vote_when_closed_blocked():
    p = PoliticalOffices()
    p.register_office(_senator())
    assert p.cast_vote(
        voter_id="v1", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="alice",
    ) is False


def test_close_election_too_early():
    p = PoliticalOffices()
    p.register_office(_senator())
    p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "bob"], deadline_day=10,
    )
    p.cast_vote(
        voter_id="v1", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="alice",
    )
    out = p.close_election(
        office_id="bastok_senator_1", now_day=5,
    )
    assert out is None


def test_close_election_at_deadline():
    p = PoliticalOffices()
    p.register_office(_senator())
    p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "bob"], deadline_day=10,
    )
    p.cast_vote(
        voter_id="v1", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="alice",
    )
    p.cast_vote(
        voter_id="v2", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="alice",
    )
    p.cast_vote(
        voter_id="v3", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="bob",
    )
    res = p.close_election(
        office_id="bastok_senator_1", now_day=10,
    )
    assert res is not None
    assert res.winner_id == "alice"
    assert res.total_votes == 3
    assert p.holder(
        office_id="bastok_senator_1",
    ) == "alice"


def test_close_election_clears_open_state():
    p = PoliticalOffices()
    p.register_office(_senator())
    p.open_election(
        office_id="bastok_senator_1",
        candidates=["alice", "bob"], deadline_day=10,
    )
    p.cast_vote(
        voter_id="v1", voter_nation="bastok",
        office_id="bastok_senator_1", candidate="alice",
    )
    p.close_election(
        office_id="bastok_senator_1", now_day=10,
    )
    assert p.is_election_open(
        office_id="bastok_senator_1",
    ) is False


def test_offices_in_nation():
    p = PoliticalOffices()
    p.register_office(_senator("a", "bastok"))
    p.register_office(_senator("b", "bastok"))
    p.register_office(_senator("c", "sandy"))
    out = p.offices_in_nation(nation="bastok")
    assert {o.office_id for o in out} == {"a", "b"}


def test_holder_unknown_office():
    p = PoliticalOffices()
    assert p.holder(office_id="ghost") is None


def test_eight_office_kinds():
    assert len(list(OfficeKind)) == 8
