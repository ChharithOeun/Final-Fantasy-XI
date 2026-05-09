"""Tests for player_comedy_club."""
from __future__ import annotations

from server.player_comedy_club import (
    PlayerComedyClubSystem, SetState,
)


def _set(s: PlayerComedyClubSystem) -> str:
    return s.write_set(
        comedian_id="naji", comedian_skill=70,
        heckle_resistance=50,
    )


def _add_three(
    s: PlayerComedyClubSystem, sid: str,
) -> None:
    s.add_joke(set_id=sid, topic="moogles")
    s.add_joke(set_id=sid, topic="goblins")
    s.add_joke(set_id=sid, topic="tarutaru")


def test_write_set_happy():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    assert sid is not None


def test_write_set_invalid_skill():
    s = PlayerComedyClubSystem()
    assert s.write_set(
        comedian_id="naji", comedian_skill=0,
        heckle_resistance=50,
    ) is None


def test_write_set_invalid_heckle_res():
    s = PlayerComedyClubSystem()
    assert s.write_set(
        comedian_id="naji", comedian_skill=70,
        heckle_resistance=200,
    ) is None


def test_write_set_empty_id():
    s = PlayerComedyClubSystem()
    assert s.write_set(
        comedian_id="", comedian_skill=70,
        heckle_resistance=50,
    ) is None


def test_add_joke_happy():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    jid = s.add_joke(set_id=sid, topic="moogles")
    assert jid is not None


def test_add_joke_empty_topic():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    assert s.add_joke(set_id=sid, topic="") is None


def test_add_joke_after_book_blocked():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    s.book_club(set_id=sid, club_id="bastok_inn")
    assert s.add_joke(
        set_id=sid, topic="late",
    ) is None


def test_book_club_happy():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    assert s.book_club(
        set_id=sid, club_id="bastok_inn",
    ) is True


def test_book_no_jokes_blocked():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    assert s.book_club(
        set_id=sid, club_id="bastok_inn",
    ) is False


def test_perform_happy():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    s.book_club(set_id=sid, club_id="bastok_inn")
    score = s.perform_set(
        set_id=sid, audience_heckle=20,
        performed_day=10,
    )
    assert score is not None
    assert score > 0


def test_perform_decays_freshness():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    s.book_club(set_id=sid, club_id="bastok_inn")
    s.perform_set(
        set_id=sid, audience_heckle=20,
        performed_day=10,
    )
    js = s.jokes(set_id=sid)
    for j in js:
        assert j.freshness < 100


def test_perform_state_set():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    s.book_club(set_id=sid, club_id="bastok_inn")
    s.perform_set(
        set_id=sid, audience_heckle=20,
        performed_day=10,
    )
    spec = s.set(set_id=sid)
    assert spec.state == SetState.PERFORMED
    assert spec.last_log is not None


def test_perform_before_book_blocked():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    assert s.perform_set(
        set_id=sid, audience_heckle=20,
        performed_day=10,
    ) is None


def test_heckle_below_resistance_no_penalty():
    s = PlayerComedyClubSystem()
    sid_a = _set(s)
    _add_three(s, sid_a)
    s.book_club(set_id=sid_a, club_id="x")
    a = s.perform_set(
        set_id=sid_a, audience_heckle=10,
        performed_day=10,
    )
    sid_b = s.write_set(
        comedian_id="naji", comedian_skill=70,
        heckle_resistance=50,
    )
    s.add_joke(set_id=sid_b, topic="moogles")
    s.add_joke(set_id=sid_b, topic="goblins")
    s.add_joke(set_id=sid_b, topic="tarutaru")
    s.book_club(set_id=sid_b, club_id="x")
    b = s.perform_set(
        set_id=sid_b, audience_heckle=49,
        performed_day=10,
    )
    assert a == b


def test_heckle_above_resistance_drops_score():
    s = PlayerComedyClubSystem()
    sid_a = _set(s)
    _add_three(s, sid_a)
    s.book_club(set_id=sid_a, club_id="x")
    quiet = s.perform_set(
        set_id=sid_a, audience_heckle=10,
        performed_day=10,
    )
    sid_b = s.write_set(
        comedian_id="naji", comedian_skill=70,
        heckle_resistance=50,
    )
    s.add_joke(set_id=sid_b, topic="moogles")
    s.add_joke(set_id=sid_b, topic="goblins")
    s.add_joke(set_id=sid_b, topic="tarutaru")
    s.book_club(set_id=sid_b, club_id="x")
    rowdy = s.perform_set(
        set_id=sid_b, audience_heckle=90,
        performed_day=10,
    )
    assert rowdy < quiet


def test_bomb_flagged():
    s = PlayerComedyClubSystem()
    sid = s.write_set(
        comedian_id="weak", comedian_skill=1,
        heckle_resistance=1,
    )
    s.add_joke(set_id=sid, topic="t1", freshness=1)
    s.book_club(set_id=sid, club_id="rowdy")
    s.perform_set(
        set_id=sid, audience_heckle=100,
        performed_day=10,
    )
    spec = s.set(set_id=sid)
    assert spec.last_log.bombed is True


def test_archive_happy():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    s.book_club(set_id=sid, club_id="x")
    s.perform_set(
        set_id=sid, audience_heckle=20,
        performed_day=10,
    )
    assert s.archive_set(set_id=sid) is True
    assert s.set(set_id=sid).state == SetState.ARCHIVED


def test_archive_before_perform_blocked():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    s.book_club(set_id=sid, club_id="x")
    assert s.archive_set(set_id=sid) is False


def test_rebook_happy():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    s.book_club(set_id=sid, club_id="x")
    s.perform_set(
        set_id=sid, audience_heckle=10,
        performed_day=10,
    )
    assert s.re_book(
        set_id=sid, club_id="y",
    ) is True
    assert s.set(set_id=sid).state == SetState.BOOKED


def test_rebook_then_perform_decays_more():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    s.book_club(set_id=sid, club_id="x")
    first = s.perform_set(
        set_id=sid, audience_heckle=10,
        performed_day=10,
    )
    s.re_book(set_id=sid, club_id="y")
    second = s.perform_set(
        set_id=sid, audience_heckle=10,
        performed_day=11,
    )
    # Second performance should score worse — jokes
    # are staler now.
    assert second < first


def test_jokes_listed():
    s = PlayerComedyClubSystem()
    sid = _set(s)
    _add_three(s, sid)
    assert len(s.jokes(set_id=sid)) == 3


def test_unknown_set():
    s = PlayerComedyClubSystem()
    assert s.set(set_id="ghost") is None


def test_enum_count():
    assert len(list(SetState)) == 4
