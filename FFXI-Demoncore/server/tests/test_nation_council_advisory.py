"""Tests for nation_council_advisory."""
from __future__ import annotations

from server.nation_council_advisory import (
    NationCouncilAdvisorySystem, MotionState, Vote,
)


def _setup(s):
    s.set_seat_cap(nation_id="bastok", cap=5)


def test_set_cap_happy():
    s = NationCouncilAdvisorySystem()
    assert s.set_seat_cap(
        nation_id="bastok", cap=5,
    ) is True


def test_set_cap_zero_blocked():
    s = NationCouncilAdvisorySystem()
    assert s.set_seat_cap(
        nation_id="bastok", cap=0,
    ) is False


def test_seat_happy():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    assert s.seat(
        nation_id="bastok", officer_id="off_volker",
        intellect=80, seated_day=10,
    ) is True


def test_seat_no_cap():
    s = NationCouncilAdvisorySystem()
    assert s.seat(
        nation_id="bastok", officer_id="o",
        intellect=80, seated_day=10,
    ) is False


def test_seat_invalid_intellect():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    assert s.seat(
        nation_id="bastok", officer_id="o",
        intellect=120, seated_day=10,
    ) is False


def test_seat_dup_blocked():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok",
           officer_id="off_volker", intellect=80,
           seated_day=10)
    assert s.seat(
        nation_id="bastok", officer_id="off_volker",
        intellect=80, seated_day=11,
    ) is False


def test_seat_cap_full_blocked():
    s = NationCouncilAdvisorySystem()
    s.set_seat_cap(nation_id="bastok", cap=2)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    s.seat(nation_id="bastok", officer_id="b",
           intellect=80, seated_day=10)
    assert s.seat(
        nation_id="bastok", officer_id="c",
        intellect=80, seated_day=10,
    ) is False


def test_unseat_happy():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok",
           officer_id="off_volker", intellect=80,
           seated_day=10)
    assert s.unseat(
        nation_id="bastok", officer_id="off_volker",
    ) is True


def test_unseat_unknown():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    assert s.unseat(
        nation_id="bastok", officer_id="ghost",
    ) is False


def test_propose_motion_happy():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok",
           officer_id="off_volker", intellect=80,
           seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="off_volker",
        title="Raise the navy budget",
        body="Increase by 25%.", proposed_day=20,
    )
    assert mid is not None


def test_propose_unseated_blocked():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    mid = s.propose_motion(
        nation_id="bastok", proposer="ghost",
        title="x", body="y", proposed_day=20,
    )
    assert mid is None


def test_propose_blank():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="o",
           intellect=80, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="o",
        title="", body="x", proposed_day=20,
    )
    assert mid is None


def test_open_debate():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="o",
           intellect=80, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="o",
        title="x", body="y", proposed_day=20,
    )
    assert s.open_debate(motion_id=mid) is True


def test_cast_vote_happy():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    s.seat(nation_id="bastok", officer_id="b",
           intellect=70, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    s.open_debate(motion_id=mid)
    assert s.cast_vote(
        motion_id=mid, voter="b", vote=Vote.FOR,
    ) is True


def test_vote_when_proposed_blocked():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    s.seat(nation_id="bastok", officer_id="b",
           intellect=70, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    assert s.cast_vote(
        motion_id=mid, voter="b", vote=Vote.FOR,
    ) is False


def test_double_vote_blocked():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    s.seat(nation_id="bastok", officer_id="b",
           intellect=70, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    s.open_debate(motion_id=mid)
    s.cast_vote(motion_id=mid, voter="b",
                vote=Vote.FOR)
    assert s.cast_vote(
        motion_id=mid, voter="b", vote=Vote.AGAINST,
    ) is False


def test_unseated_voter_blocked():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    s.open_debate(motion_id=mid)
    assert s.cast_vote(
        motion_id=mid, voter="ghost", vote=Vote.FOR,
    ) is False


def test_tally_passes():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    s.seat(nation_id="bastok", officer_id="b",
           intellect=70, seated_day=10)
    s.seat(nation_id="bastok", officer_id="c",
           intellect=60, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    s.open_debate(motion_id=mid)
    s.cast_vote(motion_id=mid, voter="a",
                vote=Vote.FOR)
    s.cast_vote(motion_id=mid, voter="b",
                vote=Vote.FOR)
    s.cast_vote(motion_id=mid, voter="c",
                vote=Vote.AGAINST)
    res = s.tally(motion_id=mid, now_day=22)
    assert res == MotionState.PASSED


def test_tally_defeats():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=50, seated_day=10)
    s.seat(nation_id="bastok", officer_id="b",
           intellect=90, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    s.open_debate(motion_id=mid)
    s.cast_vote(motion_id=mid, voter="a",
                vote=Vote.FOR)
    s.cast_vote(motion_id=mid, voter="b",
                vote=Vote.AGAINST)
    res = s.tally(motion_id=mid, now_day=22)
    assert res == MotionState.DEFEATED


def test_abstain_doesnt_count():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    s.seat(nation_id="bastok", officer_id="b",
           intellect=99, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    s.open_debate(motion_id=mid)
    s.cast_vote(motion_id=mid, voter="a",
                vote=Vote.FOR)
    s.cast_vote(motion_id=mid, voter="b",
                vote=Vote.ABSTAIN)
    s.tally(motion_id=mid, now_day=22)
    m = s.motion(motion_id=mid)
    assert m.weight_for == 80
    assert m.weight_against == 0


def test_tally_when_proposed_blocked():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    res = s.tally(motion_id=mid, now_day=22)
    assert res is None


def test_withdraw_proposed():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    assert s.withdraw(
        motion_id=mid, now_day=21,
    ) is True


def test_withdraw_after_pass_blocked():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    mid = s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    s.open_debate(motion_id=mid)
    s.cast_vote(motion_id=mid, voter="a",
                vote=Vote.FOR)
    s.tally(motion_id=mid, now_day=22)
    assert s.withdraw(
        motion_id=mid, now_day=23,
    ) is False


def test_motions_for_nation():
    s = NationCouncilAdvisorySystem()
    _setup(s)
    s.set_seat_cap(nation_id="windy", cap=3)
    s.seat(nation_id="bastok", officer_id="a",
           intellect=80, seated_day=10)
    s.seat(nation_id="windy", officer_id="b",
           intellect=70, seated_day=10)
    s.propose_motion(
        nation_id="bastok", proposer="a",
        title="x", body="y", proposed_day=20,
    )
    s.propose_motion(
        nation_id="windy", proposer="b",
        title="z", body="w", proposed_day=20,
    )
    out = s.motions_for(nation_id="bastok")
    assert len(out) == 1


def test_motion_unknown():
    s = NationCouncilAdvisorySystem()
    assert s.motion(motion_id="ghost") is None


def test_enum_counts():
    assert len(list(MotionState)) == 5
    assert len(list(Vote)) == 3
