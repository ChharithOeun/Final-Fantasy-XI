"""Tests for linkshell voting."""
from __future__ import annotations

from server.linkshell_voting import (
    LinkshellVoting,
    MotionKind,
    MotionStatus,
    Rank,
    Vote,
)


def test_file_motion_succeeds():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.DECLARE_WAR,
        member_count=10,
    )
    assert m is not None
    assert m.status == MotionStatus.OPEN


def test_file_motion_zero_members_rejected():
    lv = LinkshellVoting()
    assert lv.file_motion(
        linkshell_id="ls1", filer_id="x",
        kind=MotionKind.RENAME_LINKSHELL,
        member_count=0,
    ) is None


def test_cast_vote_succeeds():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.DECLARE_WAR,
        member_count=4,
    )
    assert lv.cast_vote(
        motion_id=m.motion_id, voter_id="bob",
        vote=Vote.YEA, rank=Rank.PEARL_HOLDER,
    )


def test_cast_vote_unknown_motion():
    lv = LinkshellVoting()
    assert not lv.cast_vote(
        motion_id="ghost", voter_id="x",
        vote=Vote.YEA, rank=Rank.PEARL_HOLDER,
    )


def test_cast_vote_can_be_changed():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.DECLARE_WAR,
        member_count=4,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="bob",
        vote=Vote.YEA, rank=Rank.PEARL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="bob",
        vote=Vote.NAY, rank=Rank.PEARL_HOLDER,
    )
    out = lv.tally(motion_id=m.motion_id)
    assert out.weighted_nay == 1
    assert out.weighted_yea == 0


def test_tally_no_quorum():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.DECLARE_WAR,
        member_count=10,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="bob",
        vote=Vote.YEA, rank=Rank.LINKSHELL_HOLDER,
    )
    out = lv.tally(motion_id=m.motion_id)
    assert out.status == MotionStatus.NO_QUORUM
    assert out.quorum_required == 5
    assert out.voters_count == 1


def test_tally_passes():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.DECLARE_WAR,
        member_count=4,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="a",
        vote=Vote.YEA, rank=Rank.PEARL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="b",
        vote=Vote.YEA, rank=Rank.PEARL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="c",
        vote=Vote.NAY, rank=Rank.PEARL_HOLDER,
    )
    out = lv.tally(motion_id=m.motion_id)
    assert out.status == MotionStatus.PASSED


def test_tally_fails():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.DECLARE_WAR,
        member_count=4,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="a",
        vote=Vote.NAY, rank=Rank.PEARL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="b",
        vote=Vote.NAY, rank=Rank.PEARL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="c",
        vote=Vote.YEA, rank=Rank.PEARL_HOLDER,
    )
    out = lv.tally(motion_id=m.motion_id)
    assert out.status == MotionStatus.FAILED


def test_tally_tied():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.DECLARE_WAR,
        member_count=4,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="a",
        vote=Vote.YEA, rank=Rank.PEARL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="b",
        vote=Vote.NAY, rank=Rank.PEARL_HOLDER,
    )
    out = lv.tally(motion_id=m.motion_id)
    assert out.status == MotionStatus.TIED


def test_leader_weighted_more():
    """A LINKSHELL_HOLDER vote should outweigh a single
    PEARL_HOLDER 4 to 1."""
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.RENAME_LINKSHELL,
        member_count=2,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="leader",
        vote=Vote.YEA, rank=Rank.LINKSHELL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="rookie",
        vote=Vote.NAY, rank=Rank.PEARL_HOLDER,
    )
    out = lv.tally(motion_id=m.motion_id)
    assert out.weighted_yea == 4
    assert out.weighted_nay == 1
    assert out.status == MotionStatus.PASSED


def test_abstain_doesnt_swing():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.DECLARE_WAR,
        member_count=4,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="a",
        vote=Vote.ABSTAIN, rank=Rank.PEARL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="b",
        vote=Vote.YEA, rank=Rank.PEARL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="c",
        vote=Vote.NAY, rank=Rank.PEARL_HOLDER,
    )
    out = lv.tally(motion_id=m.motion_id)
    assert out.abstain_count == 1
    assert out.status == MotionStatus.TIED


def test_close_motion():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.RENAME_LINKSHELL,
        member_count=2,
    )
    assert lv.close_motion(motion_id=m.motion_id)
    assert lv.get(m.motion_id).status == MotionStatus.CLOSED


def test_close_already_closed_returns_false():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.RENAME_LINKSHELL,
        member_count=2,
    )
    lv.close_motion(motion_id=m.motion_id)
    assert not lv.close_motion(motion_id=m.motion_id)


def test_close_unknown_returns_false():
    lv = LinkshellVoting()
    assert not lv.close_motion(motion_id="ghost")


def test_cast_vote_after_tally_blocked():
    lv = LinkshellVoting()
    m = lv.file_motion(
        linkshell_id="ls1", filer_id="alice",
        kind=MotionKind.DECLARE_WAR,
        member_count=2,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="a",
        vote=Vote.YEA, rank=Rank.LINKSHELL_HOLDER,
    )
    lv.cast_vote(
        motion_id=m.motion_id, voter_id="b",
        vote=Vote.YEA, rank=Rank.PEARL_HOLDER,
    )
    lv.tally(motion_id=m.motion_id)
    # Now PASSED — additional vote should be rejected
    assert not lv.cast_vote(
        motion_id=m.motion_id, voter_id="c",
        vote=Vote.NAY, rank=Rank.PEARL_HOLDER,
    )


def test_tally_unknown_returns_none():
    lv = LinkshellVoting()
    assert lv.tally(motion_id="ghost") is None


def test_total_motions():
    lv = LinkshellVoting()
    lv.file_motion(
        linkshell_id="ls1", filer_id="a",
        kind=MotionKind.DECLARE_WAR,
        member_count=5,
    )
    lv.file_motion(
        linkshell_id="ls1", filer_id="b",
        kind=MotionKind.RENAME_LINKSHELL,
        member_count=5,
    )
    assert lv.total_motions() == 2
