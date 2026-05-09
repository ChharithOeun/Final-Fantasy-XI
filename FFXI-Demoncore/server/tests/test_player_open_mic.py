"""Tests for player_open_mic."""
from __future__ import annotations

from server.player_open_mic import (
    PlayerOpenMicSystem, NightState, PieceType,
)


def _open(s: PlayerOpenMicSystem) -> str:
    return s.open_night(
        venue_id="bastok_inn", audience_size=50,
    )


def _signup_three(
    s: PlayerOpenMicSystem, nid: str,
) -> None:
    s.signup(
        night_id=nid, performer_id="alice",
        performer_skill=70,
        piece_type=PieceType.STORY,
        duration_minutes=5,
    )
    s.signup(
        night_id=nid, performer_id="bob",
        performer_skill=80,
        piece_type=PieceType.POEM,
        duration_minutes=3,
    )
    s.signup(
        night_id=nid, performer_id="cara",
        performer_skill=60,
        piece_type=PieceType.SONG,
        duration_minutes=10,
    )


def test_open_night_happy():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    assert nid is not None


def test_open_night_empty_venue():
    s = PlayerOpenMicSystem()
    assert s.open_night(
        venue_id="", audience_size=50,
    ) is None


def test_open_night_negative_audience():
    s = PlayerOpenMicSystem()
    assert s.open_night(
        venue_id="v", audience_size=-1,
    ) is None


def test_signup_happy():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    sid = s.signup(
        night_id=nid, performer_id="alice",
        performer_skill=70,
        piece_type=PieceType.STORY,
        duration_minutes=5,
    )
    assert sid is not None


def test_signup_invalid_skill():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    assert s.signup(
        night_id=nid, performer_id="alice",
        performer_skill=0,
        piece_type=PieceType.STORY,
        duration_minutes=5,
    ) is None


def test_signup_invalid_duration():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    assert s.signup(
        night_id=nid, performer_id="alice",
        performer_skill=70,
        piece_type=PieceType.STORY,
        duration_minutes=60,
    ) is None


def test_signup_dup_performer_blocked():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    s.signup(
        night_id=nid, performer_id="alice",
        performer_skill=70,
        piece_type=PieceType.STORY,
        duration_minutes=5,
    )
    second = s.signup(
        night_id=nid, performer_id="alice",
        performer_skill=70,
        piece_type=PieceType.SONG,
        duration_minutes=3,
    )
    assert second is None


def test_signup_after_begin_blocked():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    s.begin(night_id=nid)
    assert s.signup(
        night_id=nid, performer_id="late",
        performer_skill=70,
        piece_type=PieceType.STORY,
        duration_minutes=5,
    ) is None


def test_begin_happy():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    assert s.begin(night_id=nid) is True


def test_begin_no_signups_blocked():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    assert s.begin(night_id=nid) is False


def test_perform_next_happy():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    s.begin(night_id=nid)
    tips = s.perform_next(night_id=nid, seed=42)
    assert tips is not None
    assert tips >= 0


def test_perform_next_advances_index():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    s.begin(night_id=nid)
    s.perform_next(night_id=nid, seed=1)
    s.perform_next(night_id=nid, seed=2)
    n = s.night(night_id=nid)
    assert n.next_slot_index == 2


def test_perform_next_after_all_done():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    s.begin(night_id=nid)
    for _ in range(3):
        s.perform_next(night_id=nid, seed=1)
    assert s.perform_next(
        night_id=nid, seed=1,
    ) is None


def test_perform_next_before_begin_blocked():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    assert s.perform_next(
        night_id=nid, seed=42,
    ) is None


def test_song_tips_higher_than_rant():
    """Song bonus +10, rant bonus -10 — same skill,
    same audience, song should pay more."""
    s = PlayerOpenMicSystem()
    nid = _open(s)
    s.signup(
        night_id=nid, performer_id="alice",
        performer_skill=70,
        piece_type=PieceType.SONG,
        duration_minutes=5,
    )
    s.signup(
        night_id=nid, performer_id="bob",
        performer_skill=70,
        piece_type=PieceType.RANT,
        duration_minutes=5,
    )
    s.begin(night_id=nid)
    song_tips = s.perform_next(night_id=nid, seed=5)
    rant_tips = s.perform_next(night_id=nid, seed=5)
    assert song_tips > rant_tips


def test_higher_skill_more_tips():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    s.signup(
        night_id=nid, performer_id="amateur",
        performer_skill=10,
        piece_type=PieceType.POEM,
        duration_minutes=3,
    )
    s.signup(
        night_id=nid, performer_id="master",
        performer_skill=95,
        piece_type=PieceType.POEM,
        duration_minutes=3,
    )
    s.begin(night_id=nid)
    amateur_tips = s.perform_next(night_id=nid, seed=5)
    master_tips = s.perform_next(night_id=nid, seed=5)
    assert master_tips > amateur_tips


def test_end_night_happy():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    s.begin(night_id=nid)
    assert s.end_night(night_id=nid) is True
    assert s.night(
        night_id=nid,
    ).state == NightState.ENDED


def test_end_night_before_begin_blocked():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    assert s.end_night(night_id=nid) is False


def test_slots_listed():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    assert len(s.slots(night_id=nid)) == 3


def test_performer_tips_lookup():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    s.begin(night_id=nid)
    s.perform_next(night_id=nid, seed=5)
    assert s.performer_tips(
        night_id=nid, performer_id="alice",
    ) > 0


def test_performer_tips_unknown():
    s = PlayerOpenMicSystem()
    nid = _open(s)
    _signup_three(s, nid)
    s.begin(night_id=nid)
    s.perform_next(night_id=nid, seed=5)
    assert s.performer_tips(
        night_id=nid, performer_id="ghost",
    ) == 0


def test_unknown_night():
    s = PlayerOpenMicSystem()
    assert s.night(night_id="ghost") is None


def test_enum_counts():
    assert len(list(NightState)) == 3
    assert len(list(PieceType)) == 5
