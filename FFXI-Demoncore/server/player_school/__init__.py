"""Player school — establish a school, enroll students, run courses.

Players (or LSes) can found schools, hire instructors, publish
a course catalog, and enroll students. Each course has a
subject, instructor, capacity, and tuition. Students pay
tuition on enrollment; instructors get paid out at graduation.
The school keeps a small overhead cut to cover building
maintenance.

Lifecycle (per school)
    OPEN          accepting students and courses
    CLOSED        retired, no new enrollments

Public surface
--------------
    SchoolState enum
    Course dataclass (frozen)
    School dataclass (frozen)
    PlayerSchoolSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_OVERHEAD_PCT = 10


class SchoolState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclasses.dataclass(frozen=True)
class Course:
    course_id: str
    school_id: str
    subject: str
    instructor_id: str
    tuition_gil: int
    capacity: int
    enrolled_count: int


@dataclasses.dataclass(frozen=True)
class School:
    school_id: str
    name: str
    founder_id: str
    state: SchoolState
    overhead_gil: int


@dataclasses.dataclass
class _SState:
    spec: School
    courses: dict[str, Course] = dataclasses.field(
        default_factory=dict,
    )
    rosters: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerSchoolSystem:
    _schools: dict[str, _SState] = dataclasses.field(
        default_factory=dict,
    )
    _next_school: int = 1
    _next_course: int = 1

    def found_school(
        self, *, name: str, founder_id: str,
    ) -> t.Optional[str]:
        if not name or not founder_id:
            return None
        for st in self._schools.values():
            if st.spec.name == name:
                return None
        sid = f"school_{self._next_school}"
        self._next_school += 1
        self._schools[sid] = _SState(
            spec=School(
                school_id=sid, name=name,
                founder_id=founder_id,
                state=SchoolState.OPEN,
                overhead_gil=0,
            ),
        )
        return sid

    def add_course(
        self, *, school_id: str, subject: str,
        instructor_id: str, tuition_gil: int,
        capacity: int,
    ) -> t.Optional[str]:
        if school_id not in self._schools:
            return None
        st = self._schools[school_id]
        if st.spec.state != SchoolState.OPEN:
            return None
        if not subject or not instructor_id:
            return None
        if tuition_gil <= 0 or capacity <= 0:
            return None
        cid = f"course_{self._next_course}"
        self._next_course += 1
        st.courses[cid] = Course(
            course_id=cid, school_id=school_id,
            subject=subject,
            instructor_id=instructor_id,
            tuition_gil=tuition_gil,
            capacity=capacity, enrolled_count=0,
        )
        st.rosters[cid] = set()
        return cid

    def enroll(
        self, *, school_id: str, course_id: str,
        student_id: str,
    ) -> t.Optional[int]:
        """Returns tuition charged on success."""
        if school_id not in self._schools:
            return None
        st = self._schools[school_id]
        if st.spec.state != SchoolState.OPEN:
            return None
        if course_id not in st.courses:
            return None
        c = st.courses[course_id]
        if not student_id or student_id == c.instructor_id:
            return None
        if student_id in st.rosters[course_id]:
            return None
        if c.enrolled_count >= c.capacity:
            return None
        st.courses[course_id] = dataclasses.replace(
            c, enrolled_count=c.enrolled_count + 1,
        )
        st.rosters[course_id].add(student_id)
        return c.tuition_gil

    def graduate(
        self, *, school_id: str, course_id: str,
        student_id: str,
    ) -> t.Optional[tuple[int, int]]:
        """Pay out: returns (instructor_share,
        school_overhead). Student must be enrolled.
        """
        if school_id not in self._schools:
            return None
        st = self._schools[school_id]
        if st.spec.state != SchoolState.OPEN:
            return None
        if course_id not in st.courses:
            return None
        c = st.courses[course_id]
        if student_id not in st.rosters[course_id]:
            return None
        overhead = (
            c.tuition_gil * _OVERHEAD_PCT // 100
        )
        instructor_share = c.tuition_gil - overhead
        st.rosters[course_id].discard(student_id)
        st.courses[course_id] = dataclasses.replace(
            c, enrolled_count=c.enrolled_count - 1,
        )
        st.spec = dataclasses.replace(
            st.spec, overhead_gil=(
                st.spec.overhead_gil + overhead
            ),
        )
        return instructor_share, overhead

    def close_school(
        self, *, school_id: str, founder_id: str,
    ) -> t.Optional[int]:
        """Returns final overhead gil to founder."""
        if school_id not in self._schools:
            return None
        st = self._schools[school_id]
        if st.spec.state != SchoolState.OPEN:
            return None
        if st.spec.founder_id != founder_id:
            return None
        final = st.spec.overhead_gil
        st.spec = dataclasses.replace(
            st.spec, state=SchoolState.CLOSED,
            overhead_gil=0,
        )
        return final

    def school(
        self, *, school_id: str,
    ) -> t.Optional[School]:
        st = self._schools.get(school_id)
        return st.spec if st else None

    def courses(
        self, *, school_id: str,
    ) -> list[Course]:
        st = self._schools.get(school_id)
        if st is None:
            return []
        return list(st.courses.values())

    def is_enrolled(
        self, *, school_id: str, course_id: str,
        student_id: str,
    ) -> bool:
        st = self._schools.get(school_id)
        if st is None or course_id not in st.rosters:
            return False
        return student_id in st.rosters[course_id]


__all__ = [
    "SchoolState", "Course", "School",
    "PlayerSchoolSystem",
]
