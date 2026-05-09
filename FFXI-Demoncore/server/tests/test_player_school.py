"""Tests for player_school."""
from __future__ import annotations

from server.player_school import (
    PlayerSchoolSystem, SchoolState,
)


def _open_school(
    s: PlayerSchoolSystem,
    name: str = "Bastok Academy",
    founder: str = "naji",
) -> str:
    return s.found_school(
        name=name, founder_id=founder,
    )


def _add_course(
    s: PlayerSchoolSystem, sid: str,
    instructor: str = "professor_naji",
    tuition: int = 1000, capacity: int = 5,
) -> str:
    return s.add_course(
        school_id=sid, subject="alchemy",
        instructor_id=instructor,
        tuition_gil=tuition, capacity=capacity,
    )


def test_found_school_happy():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    assert sid is not None


def test_found_dup_name_blocked():
    s = PlayerSchoolSystem()
    _open_school(s)
    assert s.found_school(
        name="Bastok Academy", founder_id="other",
    ) is None


def test_found_empty_name_blocked():
    s = PlayerSchoolSystem()
    assert s.found_school(
        name="", founder_id="naji",
    ) is None


def test_add_course_happy():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid)
    assert cid is not None


def test_add_course_invalid_tuition():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    assert s.add_course(
        school_id=sid, subject="x",
        instructor_id="i", tuition_gil=0,
        capacity=5,
    ) is None


def test_enroll_happy():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid)
    fee = s.enroll(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    assert fee == 1000


def test_enroll_self_as_instructor_blocked():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid)
    # Instructor can't enroll in own course
    assert s.enroll(
        school_id=sid, course_id=cid,
        student_id="professor_naji",
    ) is None


def test_enroll_dup_blocked():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid)
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    assert s.enroll(
        school_id=sid, course_id=cid,
        student_id="bob",
    ) is None


def test_enroll_capacity():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid, capacity=2)
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="a",
    )
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="b",
    )
    assert s.enroll(
        school_id=sid, course_id=cid,
        student_id="c",
    ) is None


def test_is_enrolled_query():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid)
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    assert s.is_enrolled(
        school_id=sid, course_id=cid,
        student_id="bob",
    ) is True


def test_graduate_happy():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid, tuition=1000)
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    instr_pay, overhead = s.graduate(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    assert instr_pay == 900
    assert overhead == 100


def test_graduate_overhead_accumulates():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid, tuition=1000, capacity=5)
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="a",
    )
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="b",
    )
    s.graduate(
        school_id=sid, course_id=cid,
        student_id="a",
    )
    s.graduate(
        school_id=sid, course_id=cid,
        student_id="b",
    )
    assert s.school(
        school_id=sid,
    ).overhead_gil == 200


def test_graduate_unenrolled_blocked():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid)
    assert s.graduate(
        school_id=sid, course_id=cid,
        student_id="bob",
    ) is None


def test_close_school_returns_overhead():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid, tuition=2000)
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    s.graduate(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    final = s.close_school(
        school_id=sid, founder_id="naji",
    )
    assert final == 200


def test_close_school_wrong_founder_blocked():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    assert s.close_school(
        school_id=sid, founder_id="bob",
    ) is None


def test_actions_after_close_blocked():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    s.close_school(school_id=sid, founder_id="naji")
    assert s.add_course(
        school_id=sid, subject="x",
        instructor_id="i", tuition_gil=100,
        capacity=5,
    ) is None


def test_courses_listing():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    _add_course(s, sid)
    s.add_course(
        school_id=sid, subject="cooking",
        instructor_id="chef",
        tuition_gil=500, capacity=3,
    )
    assert len(s.courses(school_id=sid)) == 2


def test_unknown_school():
    s = PlayerSchoolSystem()
    assert s.school(school_id="ghost") is None


def test_unknown_school_courses_empty():
    s = PlayerSchoolSystem()
    assert s.courses(school_id="ghost") == []


def test_enroll_count_decrements_on_graduate():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid)
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    assert s.courses(
        school_id=sid,
    )[0].enrolled_count == 1
    s.graduate(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    assert s.courses(
        school_id=sid,
    )[0].enrolled_count == 0


def test_re_enroll_after_graduate():
    s = PlayerSchoolSystem()
    sid = _open_school(s)
    cid = _add_course(s, sid)
    s.enroll(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    s.graduate(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    # Bob can take the course again (refresher)
    fee = s.enroll(
        school_id=sid, course_id=cid,
        student_id="bob",
    )
    assert fee == 1000


def test_enum_count():
    assert len(list(SchoolState)) == 2
