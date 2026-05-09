"""Tests for player_wine_tasting_club."""
from __future__ import annotations

from server.player_wine_tasting_club import (
    PlayerWineTastingClubSystem, ClubState,
)


def _found(s: PlayerWineTastingClubSystem) -> str:
    return s.found_club(
        sommelier_id="naji", name="Sangria Society",
        annual_dues_gil=500,
    )


def test_found_happy():
    s = PlayerWineTastingClubSystem()
    assert _found(s) is not None


def test_found_zero_dues_blocked():
    s = PlayerWineTastingClubSystem()
    assert s.found_club(
        sommelier_id="naji", name="x",
        annual_dues_gil=0,
    ) is None


def test_join_happy():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    assert s.join(
        club_id=cid, member_id="bob",
    ) is True


def test_join_sommelier_blocked():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    assert s.join(
        club_id=cid, member_id="naji",
    ) is False


def test_join_dup_blocked():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.join(club_id=cid, member_id="bob")
    assert s.join(
        club_id=cid, member_id="bob",
    ) is False


def test_join_collects_dues():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.join(club_id=cid, member_id="bob")
    s.join(club_id=cid, member_id="cara")
    assert s.club(
        club_id=cid,
    ).dues_collected_gil == 1000


def test_join_closed_blocked():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.close_club(
        club_id=cid, sommelier_id="naji",
    )
    assert s.join(
        club_id=cid, member_id="bob",
    ) is False


def test_host_tasting_happy():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    tid = s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=10,
    )
    assert tid is not None


def test_host_tasting_non_sommelier_blocked():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    assert s.host_tasting(
        club_id=cid, sommelier_id="bob",
        held_day=10,
    ) is None


def test_host_tasting_on_closed_blocked():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.close_club(
        club_id=cid, sommelier_id="naji",
    )
    assert s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=10,
    ) is None


def test_score_wine_happy():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.join(club_id=cid, member_id="bob")
    tid = s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=10,
    )
    assert s.score_wine(
        club_id=cid, tasting_id=tid,
        member_id="bob", wine_label="San d'Oria '85",
        score=88,
    ) is True


def test_score_wine_non_member_blocked():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    tid = s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=10,
    )
    assert s.score_wine(
        club_id=cid, tasting_id=tid,
        member_id="stranger", wine_label="x",
        score=80,
    ) is False


def test_score_wine_dup_blocked():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.join(club_id=cid, member_id="bob")
    tid = s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=10,
    )
    s.score_wine(
        club_id=cid, tasting_id=tid,
        member_id="bob", wine_label="x", score=80,
    )
    assert s.score_wine(
        club_id=cid, tasting_id=tid,
        member_id="bob", wine_label="x", score=70,
    ) is False


def test_score_wine_invalid_score_blocked():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.join(club_id=cid, member_id="bob")
    tid = s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=10,
    )
    assert s.score_wine(
        club_id=cid, tasting_id=tid,
        member_id="bob", wine_label="x",
        score=150,
    ) is False


def test_wine_average_computed():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.join(club_id=cid, member_id="bob")
    s.join(club_id=cid, member_id="cara")
    tid = s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=10,
    )
    s.score_wine(
        club_id=cid, tasting_id=tid,
        member_id="bob", wine_label="x", score=80,
    )
    s.score_wine(
        club_id=cid, tasting_id=tid,
        member_id="cara", wine_label="x", score=70,
    )
    assert s.wine_average(
        club_id=cid, wine_label="x",
    ) == 75.0


def test_wine_average_across_tastings():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.join(club_id=cid, member_id="bob")
    t1 = s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=10,
    )
    t2 = s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=20,
    )
    s.score_wine(
        club_id=cid, tasting_id=t1,
        member_id="bob", wine_label="x", score=80,
    )
    s.score_wine(
        club_id=cid, tasting_id=t2,
        member_id="bob", wine_label="x", score=60,
    )
    assert s.wine_average(
        club_id=cid, wine_label="x",
    ) == 70.0


def test_wine_ranking_sorted():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.join(club_id=cid, member_id="bob")
    tid = s.host_tasting(
        club_id=cid, sommelier_id="naji",
        held_day=10,
    )
    s.score_wine(
        club_id=cid, tasting_id=tid,
        member_id="bob", wine_label="A", score=60,
    )
    s.score_wine(
        club_id=cid, tasting_id=tid,
        member_id="bob", wine_label="B", score=90,
    )
    ranking = s.wine_ranking(club_id=cid)
    assert ranking[0][0] == "B"
    assert ranking[1][0] == "A"


def test_close_club_happy():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    assert s.close_club(
        club_id=cid, sommelier_id="naji",
    ) is True


def test_close_club_non_sommelier_blocked():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    assert s.close_club(
        club_id=cid, sommelier_id="bob",
    ) is False


def test_members_listing():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    s.join(club_id=cid, member_id="bob")
    s.join(club_id=cid, member_id="cara")
    assert s.members(
        club_id=cid,
    ) == ["bob", "cara"]


def test_unknown_club():
    s = PlayerWineTastingClubSystem()
    assert s.club(club_id="ghost") is None


def test_wine_average_no_scores_none():
    s = PlayerWineTastingClubSystem()
    cid = _found(s)
    assert s.wine_average(
        club_id=cid, wine_label="ghost",
    ) is None


def test_enum_count():
    assert len(list(ClubState)) == 2
