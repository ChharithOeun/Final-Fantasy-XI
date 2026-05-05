"""Tests for crew recruit board."""
from __future__ import annotations

from server.crew_recruit_board import (
    CrewRecruitBoard,
    DEFAULT_POSTING_DURATION,
    MAX_ACTIVE_APPLICATIONS,
    PostingFlag,
)


def test_post_happy():
    b = CrewRecruitBoard()
    r = b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=50,
        preferred_role="WAR", blurb="join us",
        now_seconds=0,
    )
    assert r.accepted is True
    assert r.posting_id is not None


def test_post_blank_ids():
    b = CrewRecruitBoard()
    r = b.post(
        charter_id="", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=0,
        preferred_role="any", blurb="x", now_seconds=0,
    )
    assert r.accepted is False


def test_post_bad_level():
    b = CrewRecruitBoard()
    r = b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=150,
        preferred_role="WAR", blurb="x", now_seconds=0,
    )
    assert r.accepted is False


def test_browse_includes_active():
    b = CrewRecruitBoard()
    b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=0,
        preferred_role="any", blurb="x", now_seconds=0,
    )
    out = b.browse(now_seconds=10)
    assert len(out) == 1


def test_browse_filters_by_flag():
    b = CrewRecruitBoard()
    b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=0,
        preferred_role="any", blurb="x", now_seconds=0,
    )
    b.post(
        charter_id="c2", captain_id="cap2",
        flag=PostingFlag.MERCHANT, min_level=0,
        preferred_role="any", blurb="y", now_seconds=0,
    )
    out = b.browse(
        filter_flag=PostingFlag.MERCHANT, now_seconds=10,
    )
    assert len(out) == 1
    assert out[0].flag == PostingFlag.MERCHANT


def test_browse_filters_max_level():
    b = CrewRecruitBoard()
    b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=80,
        preferred_role="any", blurb="x", now_seconds=0,
    )
    out = b.browse(max_level=50, now_seconds=10)
    assert len(out) == 0


def test_browse_excludes_expired():
    b = CrewRecruitBoard()
    b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=0,
        preferred_role="any", blurb="x", now_seconds=0,
        duration_seconds=10,
    )
    out = b.browse(now_seconds=20)
    assert len(out) == 0


def test_apply_happy():
    b = CrewRecruitBoard()
    r = b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=0,
        preferred_role="any", blurb="x", now_seconds=0,
    )
    pid = r.posting_id
    a = b.apply(player_id="p1", posting_id=pid, now_seconds=10)
    assert a.accepted is True


def test_apply_unknown_posting():
    b = CrewRecruitBoard()
    a = b.apply(player_id="p1", posting_id="ghost", now_seconds=0)
    assert a.accepted is False


def test_apply_to_expired_posting():
    b = CrewRecruitBoard()
    r = b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=0,
        preferred_role="any", blurb="x",
        now_seconds=0, duration_seconds=10,
    )
    a = b.apply(
        player_id="p1", posting_id=r.posting_id, now_seconds=20,
    )
    assert a.accepted is False


def test_apply_duplicate_blocked():
    b = CrewRecruitBoard()
    r = b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=0,
        preferred_role="any", blurb="x", now_seconds=0,
    )
    pid = r.posting_id
    b.apply(player_id="p1", posting_id=pid, now_seconds=10)
    a = b.apply(player_id="p1", posting_id=pid, now_seconds=20)
    assert a.accepted is False


def test_apply_active_cap():
    b = CrewRecruitBoard()
    posts = []
    for i in range(MAX_ACTIVE_APPLICATIONS + 1):
        r = b.post(
            charter_id=f"c{i}", captain_id="cap",
            flag=PostingFlag.PIRATE, min_level=0,
            preferred_role="any", blurb="x", now_seconds=0,
        )
        posts.append(r.posting_id)
    # apply to MAX
    for pid in posts[:MAX_ACTIVE_APPLICATIONS]:
        a = b.apply(
            player_id="p1", posting_id=pid, now_seconds=10,
        )
        assert a.accepted is True
    # next one fails
    a = b.apply(
        player_id="p1", posting_id=posts[-1], now_seconds=10,
    )
    assert a.accepted is False
    assert a.reason == "active app cap"


def test_applications_for_charter():
    b = CrewRecruitBoard()
    r = b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=0,
        preferred_role="any", blurb="x", now_seconds=0,
    )
    b.apply(
        player_id="p1", posting_id=r.posting_id, now_seconds=10,
    )
    apps = b.applications_for(charter_id="c1")
    assert len(apps) == 1
    assert apps[0].player_id == "p1"


def test_withdraw_application():
    b = CrewRecruitBoard()
    r = b.post(
        charter_id="c1", captain_id="cap",
        flag=PostingFlag.PIRATE, min_level=0,
        preferred_role="any", blurb="x", now_seconds=0,
    )
    pid = r.posting_id
    b.apply(player_id="p1", posting_id=pid, now_seconds=10)
    ok = b.withdraw_application(player_id="p1", posting_id=pid)
    assert ok is True
    apps = b.applications_for(charter_id="c1")
    assert len(apps) == 0


def test_withdraw_unknown():
    b = CrewRecruitBoard()
    ok = b.withdraw_application(player_id="p", posting_id="ghost")
    assert ok is False
