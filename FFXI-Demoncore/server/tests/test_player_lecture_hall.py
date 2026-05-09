"""Tests for player_lecture_hall."""
from __future__ import annotations

from server.player_lecture_hall import (
    PlayerLectureHallSystem, LectureState,
)


def _book(s: PlayerLectureHallSystem) -> str:
    return s.book_lecture(
        hall_id="windy_hall", lecturer_id="naji",
        topic="On the Properties of Mythril",
        lecturer_skill=80, admission_gil=200,
        capacity=20, scheduled_day=10,
    )


def _through_announce(
    s: PlayerLectureHallSystem,
) -> str:
    lid = _book(s)
    s.announce(lecture_id=lid)
    return lid


def test_book_happy():
    s = PlayerLectureHallSystem()
    lid = _book(s)
    assert lid is not None


def test_book_empty_topic_blocked():
    s = PlayerLectureHallSystem()
    assert s.book_lecture(
        hall_id="x", lecturer_id="n", topic="",
        lecturer_skill=50, admission_gil=100,
        capacity=10, scheduled_day=10,
    ) is None


def test_book_invalid_skill_blocked():
    s = PlayerLectureHallSystem()
    assert s.book_lecture(
        hall_id="x", lecturer_id="n", topic="t",
        lecturer_skill=0, admission_gil=100,
        capacity=10, scheduled_day=10,
    ) is None


def test_book_double_booking_blocked():
    s = PlayerLectureHallSystem()
    _book(s)
    assert s.book_lecture(
        hall_id="windy_hall", lecturer_id="other",
        topic="another", lecturer_skill=50,
        admission_gil=100, capacity=10,
        scheduled_day=10,
    ) is None


def test_announce_happy():
    s = PlayerLectureHallSystem()
    lid = _book(s)
    assert s.announce(lecture_id=lid) is True


def test_announce_double_blocked():
    s = PlayerLectureHallSystem()
    lid = _book(s)
    s.announce(lecture_id=lid)
    assert s.announce(lecture_id=lid) is False


def test_register_attendee_happy():
    s = PlayerLectureHallSystem()
    lid = _through_announce(s)
    fee = s.register_attendee(
        lecture_id=lid, attendee_id="bob",
    )
    assert fee == 200


def test_register_lecturer_blocked():
    s = PlayerLectureHallSystem()
    lid = _through_announce(s)
    assert s.register_attendee(
        lecture_id=lid, attendee_id="naji",
    ) is None


def test_register_dup_attendee_blocked():
    s = PlayerLectureHallSystem()
    lid = _through_announce(s)
    s.register_attendee(
        lecture_id=lid, attendee_id="bob",
    )
    assert s.register_attendee(
        lecture_id=lid, attendee_id="bob",
    ) is None


def test_register_capacity_cap():
    s = PlayerLectureHallSystem()
    lid = s.book_lecture(
        hall_id="x", lecturer_id="n",
        topic="t", lecturer_skill=50,
        admission_gil=100, capacity=2,
        scheduled_day=10,
    )
    s.announce(lecture_id=lid)
    s.register_attendee(
        lecture_id=lid, attendee_id="a",
    )
    s.register_attendee(
        lecture_id=lid, attendee_id="b",
    )
    assert s.register_attendee(
        lecture_id=lid, attendee_id="c",
    ) is None


def test_register_before_announce_blocked():
    s = PlayerLectureHallSystem()
    lid = _book(s)
    assert s.register_attendee(
        lecture_id=lid, attendee_id="bob",
    ) is None


def test_revenue_accumulates():
    s = PlayerLectureHallSystem()
    lid = _through_announce(s)
    s.register_attendee(
        lecture_id=lid, attendee_id="a",
    )
    s.register_attendee(
        lecture_id=lid, attendee_id="b",
    )
    assert s.lecture(
        lecture_id=lid,
    ).revenue_gil == 400


def test_deliver_first_time_gain():
    s = PlayerLectureHallSystem()
    lid = _through_announce(s)
    s.register_attendee(
        lecture_id=lid, attendee_id="bob",
    )
    total = s.deliver(lecture_id=lid)
    # 5 base + 80//20 = 4, total = 9 per attendee
    assert total == 9
    assert s.attendee_skill_gain(
        lecture_id=lid, attendee_id="bob",
    ) == 9


def test_deliver_state_set():
    s = PlayerLectureHallSystem()
    lid = _through_announce(s)
    s.register_attendee(
        lecture_id=lid, attendee_id="bob",
    )
    s.deliver(lecture_id=lid)
    assert s.lecture(
        lecture_id=lid,
    ).state == LectureState.DELIVERED


def test_deliver_before_announce_blocked():
    s = PlayerLectureHallSystem()
    lid = _book(s)
    assert s.deliver(lecture_id=lid) is None


def test_cancel_returns_refund():
    s = PlayerLectureHallSystem()
    lid = _through_announce(s)
    s.register_attendee(
        lecture_id=lid, attendee_id="bob",
    )
    s.register_attendee(
        lecture_id=lid, attendee_id="cara",
    )
    refund = s.cancel(lecture_id=lid)
    assert refund == 400


def test_cancel_after_deliver_blocked():
    s = PlayerLectureHallSystem()
    lid = _through_announce(s)
    s.register_attendee(
        lecture_id=lid, attendee_id="bob",
    )
    s.deliver(lecture_id=lid)
    assert s.cancel(lecture_id=lid) is None


def test_higher_lecturer_skill_more_gain():
    s = PlayerLectureHallSystem()
    lid_low = s.book_lecture(
        hall_id="a", lecturer_id="lo",
        topic="t", lecturer_skill=20,
        admission_gil=100, capacity=10,
        scheduled_day=10,
    )
    lid_high = s.book_lecture(
        hall_id="b", lecturer_id="hi",
        topic="t", lecturer_skill=100,
        admission_gil=100, capacity=10,
        scheduled_day=10,
    )
    s.announce(lecture_id=lid_low)
    s.announce(lecture_id=lid_high)
    s.register_attendee(
        lecture_id=lid_low, attendee_id="a",
    )
    s.register_attendee(
        lecture_id=lid_high, attendee_id="b",
    )
    low_total = s.deliver(lecture_id=lid_low)
    high_total = s.deliver(lecture_id=lid_high)
    assert high_total > low_total


def test_attendee_skill_unknown_zero():
    s = PlayerLectureHallSystem()
    lid = _book(s)
    assert s.attendee_skill_gain(
        lecture_id=lid, attendee_id="ghost",
    ) == 0


def test_attendee_skill_unknown_lecture():
    s = PlayerLectureHallSystem()
    assert s.attendee_skill_gain(
        lecture_id="ghost", attendee_id="bob",
    ) == 0


def test_unknown_lecture():
    s = PlayerLectureHallSystem()
    assert s.lecture(lecture_id="ghost") is None


def test_enum_count():
    assert len(list(LectureState)) == 4
