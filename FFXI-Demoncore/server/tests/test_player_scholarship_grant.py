"""Tests for player_scholarship_grant."""
from __future__ import annotations

from server.player_scholarship_grant import (
    PlayerScholarshipGrantSystem, GrantState,
)


def _endow(
    s: PlayerScholarshipGrantSystem,
    pool: int = 10000, per: int = 2000,
    subject: str = "",
) -> str:
    return s.endow_grant(
        donor_id="naji", name="The Naji Foundation",
        pool_gil=pool, max_award_per_student=per,
        subject_filter=subject,
    )


def test_endow_happy():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s)
    assert gid is not None


def test_endow_zero_pool_blocked():
    s = PlayerScholarshipGrantSystem()
    assert s.endow_grant(
        donor_id="x", name="n", pool_gil=0,
        max_award_per_student=100,
    ) is None


def test_endow_per_student_above_pool_blocked():
    s = PlayerScholarshipGrantSystem()
    assert s.endow_grant(
        donor_id="x", name="n", pool_gil=1000,
        max_award_per_student=2000,
    ) is None


def test_endow_empty_donor_blocked():
    s = PlayerScholarshipGrantSystem()
    assert s.endow_grant(
        donor_id="", name="n", pool_gil=1000,
        max_award_per_student=100,
    ) is None


def test_apply_award_happy():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s)
    aid = s.apply_award(
        grant_id=gid, student_id="bob",
        subject="alchemy", requested_gil=1000,
        awarded_day=10,
    )
    assert aid is not None


def test_apply_donor_self_blocked():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s)
    assert s.apply_award(
        grant_id=gid, student_id="naji",
        subject="alchemy", requested_gil=500,
        awarded_day=10,
    ) is None


def test_apply_subject_filter_blocks_off_topic():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s, subject="alchemy")
    assert s.apply_award(
        grant_id=gid, student_id="bob",
        subject="cooking", requested_gil=1000,
        awarded_day=10,
    ) is None


def test_apply_subject_filter_passes_match():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s, subject="alchemy")
    assert s.apply_award(
        grant_id=gid, student_id="bob",
        subject="alchemy", requested_gil=1000,
        awarded_day=10,
    ) is not None


def test_apply_per_student_cap():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s, per=2000)
    s.apply_award(
        grant_id=gid, student_id="bob",
        subject="x", requested_gil=1500,
        awarded_day=10,
    )
    # Bob already has 1500; another 600 would exceed
    # 2000 cap
    assert s.apply_award(
        grant_id=gid, student_id="bob",
        subject="x", requested_gil=600,
        awarded_day=11,
    ) is None


def test_apply_pool_floor():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s, pool=1000, per=600)
    s.apply_award(
        grant_id=gid, student_id="a",
        subject="x", requested_gil=600,
        awarded_day=10,
    )
    # 600 used, 400 remaining; can't disburse 500
    assert s.apply_award(
        grant_id=gid, student_id="b",
        subject="x", requested_gil=500,
        awarded_day=10,
    ) is None


def test_apply_exhausts_pool():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s, pool=1000, per=600)
    s.apply_award(
        grant_id=gid, student_id="a",
        subject="x", requested_gil=600,
        awarded_day=10,
    )
    s.apply_award(
        grant_id=gid, student_id="b",
        subject="x", requested_gil=400,
        awarded_day=10,
    )
    assert s.grant(
        grant_id=gid,
    ).state == GrantState.EXHAUSTED


def test_apply_after_exhaust_blocked():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s, pool=1000, per=600)
    s.apply_award(
        grant_id=gid, student_id="a",
        subject="x", requested_gil=600,
        awarded_day=10,
    )
    s.apply_award(
        grant_id=gid, student_id="b",
        subject="x", requested_gil=400,
        awarded_day=10,
    )
    assert s.apply_award(
        grant_id=gid, student_id="c",
        subject="x", requested_gil=100,
        awarded_day=11,
    ) is None


def test_apply_zero_requested_blocked():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s)
    assert s.apply_award(
        grant_id=gid, student_id="bob",
        subject="x", requested_gil=0,
        awarded_day=10,
    ) is None


def test_revoke_returns_unused():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s, pool=10000)
    s.apply_award(
        grant_id=gid, student_id="bob",
        subject="x", requested_gil=2000,
        awarded_day=10,
    )
    refund = s.revoke(
        grant_id=gid, donor_id="naji",
    )
    assert refund == 8000


def test_revoke_wrong_donor_blocked():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s)
    assert s.revoke(
        grant_id=gid, donor_id="bob",
    ) is None


def test_revoke_after_exhaust_blocked():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s, pool=1000, per=1000)
    s.apply_award(
        grant_id=gid, student_id="bob",
        subject="x", requested_gil=1000,
        awarded_day=10,
    )
    assert s.revoke(
        grant_id=gid, donor_id="naji",
    ) is None


def test_apply_after_revoke_blocked():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s)
    s.revoke(grant_id=gid, donor_id="naji")
    assert s.apply_award(
        grant_id=gid, student_id="bob",
        subject="x", requested_gil=500,
        awarded_day=10,
    ) is None


def test_awards_to_student_lookup():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s)
    s.apply_award(
        grant_id=gid, student_id="bob",
        subject="x", requested_gil=500,
        awarded_day=10,
    )
    s.apply_award(
        grant_id=gid, student_id="bob",
        subject="x", requested_gil=300,
        awarded_day=11,
    )
    assert s.awards_to_student(
        grant_id=gid, student_id="bob",
    ) == 800


def test_all_awards_listing():
    s = PlayerScholarshipGrantSystem()
    gid = _endow(s)
    s.apply_award(
        grant_id=gid, student_id="bob",
        subject="x", requested_gil=500,
        awarded_day=10,
    )
    s.apply_award(
        grant_id=gid, student_id="cara",
        subject="x", requested_gil=500,
        awarded_day=11,
    )
    assert len(s.all_awards(grant_id=gid)) == 2


def test_unknown_grant():
    s = PlayerScholarshipGrantSystem()
    assert s.grant(grant_id="ghost") is None


def test_unknown_grant_zero_awards():
    s = PlayerScholarshipGrantSystem()
    assert s.awards_to_student(
        grant_id="ghost", student_id="bob",
    ) == 0


def test_enum_count():
    assert len(list(GrantState)) == 3
