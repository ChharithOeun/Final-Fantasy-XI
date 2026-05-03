"""Tests for the LFG group recruit board."""
from __future__ import annotations

from server.group_recruit_board import (
    ApplicationStatus,
    GroupRecruitBoard,
    ObjectiveTag,
    PostStatus,
    RoleSlot,
)


def test_post_listing_succeeds():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice",
        slots=(RoleSlot.TANK, RoleSlot.HEALER, RoleSlot.DPS),
        level_min=50, level_max=60,
        objective=ObjectiveTag.XP,
    )
    assert p is not None
    assert p.status == PostStatus.OPEN


def test_post_no_slots_rejected():
    b = GroupRecruitBoard()
    assert b.post_listing(
        captain_id="alice", slots=(),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    ) is None


def test_post_invalid_level_range_rejected():
    b = GroupRecruitBoard()
    assert b.post_listing(
        captain_id="a", slots=(RoleSlot.TANK,),
        level_min=10, level_max=5,
        objective=ObjectiveTag.XP,
    ) is None


def test_one_open_post_per_captain():
    b = GroupRecruitBoard()
    b.post_listing(
        captain_id="alice", slots=(RoleSlot.TANK,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    second = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.NM,
    )
    assert second is None


def test_browse_filter_by_objective():
    b = GroupRecruitBoard()
    b.post_listing(
        captain_id="a", slots=(RoleSlot.TANK,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    b.post_listing(
        captain_id="b", slots=(RoleSlot.TANK,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.NM,
    )
    nm_posts = b.browse(objective=ObjectiveTag.NM)
    assert len(nm_posts) == 1
    assert nm_posts[0].objective == ObjectiveTag.NM


def test_browse_filter_by_level():
    b = GroupRecruitBoard()
    b.post_listing(
        captain_id="a", slots=(RoleSlot.TANK,),
        level_min=70, level_max=75,
        objective=ObjectiveTag.NM,
    )
    assert b.browse(level=50) == ()
    assert len(b.browse(level=72)) == 1


def test_browse_filter_by_role_open():
    b = GroupRecruitBoard()
    b.post_listing(
        captain_id="a",
        slots=(RoleSlot.TANK, RoleSlot.HEALER),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    healer_posts = b.browse(role_open=RoleSlot.HEALER)
    assert len(healer_posts) == 1


def test_apply_succeeds():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=50, level_max=70,
        objective=ObjectiveTag.NM,
    )
    res = b.apply_to(
        applicant_id="bob", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=60,
    )
    assert res.accepted


def test_apply_captain_rejected():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    res = b.apply_to(
        applicant_id="alice", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=50,
    )
    assert not res.accepted


def test_apply_level_outside_band_rejected():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=70, level_max=75,
        objective=ObjectiveTag.NM,
    )
    res = b.apply_to(
        applicant_id="bob", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=50,
    )
    assert not res.accepted
    assert "outside band" in res.reason


def test_apply_role_not_in_post():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    res = b.apply_to(
        applicant_id="bob", post_id=p.post_id,
        requested_role=RoleSlot.TANK,
        applicant_level=50,
    )
    assert not res.accepted
    assert "not in post" in res.reason


def test_apply_role_already_filled():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    res1 = b.apply_to(
        applicant_id="bob", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=50,
    )
    b.accept(
        post_id=p.post_id,
        application_id=res1.application.application_id,
    )
    res2 = b.apply_to(
        applicant_id="carol", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=50,
    )
    assert not res2.accepted


def test_double_apply_pending_rejected():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    b.apply_to(
        applicant_id="bob", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=50,
    )
    res2 = b.apply_to(
        applicant_id="bob", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=50,
    )
    assert not res2.accepted
    assert "already applied" in res2.reason


def test_accept_fills_slot():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    res = b.apply_to(
        applicant_id="bob", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=50,
    )
    out = b.accept(
        post_id=p.post_id,
        application_id=res.application.application_id,
    )
    assert out.accepted
    assert out.post_full


def test_accept_partial_keeps_open():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice",
        slots=(RoleSlot.TANK, RoleSlot.HEALER),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    res = b.apply_to(
        applicant_id="bob", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=50,
    )
    out = b.accept(
        post_id=p.post_id,
        application_id=res.application.application_id,
    )
    assert not out.post_full
    assert b.get(p.post_id).status == PostStatus.OPEN


def test_reject_application():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    res = b.apply_to(
        applicant_id="bob", post_id=p.post_id,
        requested_role=RoleSlot.HEALER,
        applicant_level=50,
    )
    assert b.reject(
        post_id=p.post_id,
        application_id=res.application.application_id,
    )
    app = b._applications[res.application.application_id]
    assert app.status == ApplicationStatus.REJECTED


def test_close_post():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    assert b.close(post_id=p.post_id)
    assert b.get(p.post_id).status == PostStatus.CLOSED


def test_expire_check():
    b = GroupRecruitBoard()
    p = b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
        posted_at_seconds=0.0,
        expires_at_seconds=100.0,
    )
    expired = b.expire_check(now_seconds=200.0)
    assert p.post_id in expired
    assert b.get(p.post_id).status == PostStatus.EXPIRED


def test_expire_check_keeps_fresh():
    b = GroupRecruitBoard()
    b.post_listing(
        captain_id="alice", slots=(RoleSlot.HEALER,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
        posted_at_seconds=0.0,
        expires_at_seconds=200.0,
    )
    expired = b.expire_check(now_seconds=100.0)
    assert expired == ()


def test_total_posts():
    b = GroupRecruitBoard()
    b.post_listing(
        captain_id="a", slots=(RoleSlot.TANK,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.XP,
    )
    b.post_listing(
        captain_id="b", slots=(RoleSlot.TANK,),
        level_min=1, level_max=99,
        objective=ObjectiveTag.NM,
    )
    assert b.total_posts() == 2
