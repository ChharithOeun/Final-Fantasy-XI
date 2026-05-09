"""Player lecture hall — booked lectures, audience learning gain.

Distinct from player_concert_hall: this is the academic
counterpart. Scholars book a lecture hall, announce a topic,
and deliver to an audience that pays a small admission and
walks away with skill_gain in the topic's domain. Rare topics
or famous lecturers fill the hall; obscure ones flop. Repeat
attendance of the same lecture by one player gives diminishing
returns.

Lifecycle (per lecture)
    BOOKED       slot reserved
    ANNOUNCED    topic posted, registrations open
    DELIVERED    lecture happened, attendees learned
    CANCELED     pulled before delivery

Public surface
--------------
    LectureState enum
    Lecture dataclass (frozen)
    PlayerLectureHallSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_BASE_GAIN = 5
_REPEAT_GAIN = 1


class LectureState(str, enum.Enum):
    BOOKED = "booked"
    ANNOUNCED = "announced"
    DELIVERED = "delivered"
    CANCELED = "canceled"


@dataclasses.dataclass(frozen=True)
class Lecture:
    lecture_id: str
    hall_id: str
    lecturer_id: str
    topic: str
    lecturer_skill: int        # 1..100
    admission_gil: int
    capacity: int
    state: LectureState
    scheduled_day: int
    attendees_count: int
    revenue_gil: int


@dataclasses.dataclass
class _LState:
    spec: Lecture
    attendees: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerLectureHallSystem:
    _lectures: dict[str, _LState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def book_lecture(
        self, *, hall_id: str, lecturer_id: str,
        topic: str, lecturer_skill: int,
        admission_gil: int, capacity: int,
        scheduled_day: int,
    ) -> t.Optional[str]:
        if not hall_id or not lecturer_id:
            return None
        if not topic:
            return None
        if not 1 <= lecturer_skill <= 100:
            return None
        if admission_gil < 0:
            return None
        if capacity <= 0:
            return None
        if scheduled_day < 0:
            return None
        # No double-booking same hall same day
        for st in self._lectures.values():
            sp = st.spec
            if (
                sp.hall_id == hall_id
                and sp.scheduled_day == scheduled_day
                and sp.state in (
                    LectureState.BOOKED,
                    LectureState.ANNOUNCED,
                )
            ):
                return None
        lid = f"lecture_{self._next}"
        self._next += 1
        spec = Lecture(
            lecture_id=lid, hall_id=hall_id,
            lecturer_id=lecturer_id, topic=topic,
            lecturer_skill=lecturer_skill,
            admission_gil=admission_gil,
            capacity=capacity,
            state=LectureState.BOOKED,
            scheduled_day=scheduled_day,
            attendees_count=0, revenue_gil=0,
        )
        self._lectures[lid] = _LState(spec=spec)
        return lid

    def announce(
        self, *, lecture_id: str,
    ) -> bool:
        if lecture_id not in self._lectures:
            return False
        st = self._lectures[lecture_id]
        if st.spec.state != LectureState.BOOKED:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=LectureState.ANNOUNCED,
        )
        return True

    def register_attendee(
        self, *, lecture_id: str, attendee_id: str,
    ) -> t.Optional[int]:
        """Returns admission gil charged."""
        if lecture_id not in self._lectures:
            return None
        st = self._lectures[lecture_id]
        if st.spec.state != LectureState.ANNOUNCED:
            return None
        if not attendee_id:
            return None
        if attendee_id == st.spec.lecturer_id:
            return None
        if attendee_id in st.attendees:
            return None
        if st.spec.attendees_count >= st.spec.capacity:
            return None
        st.attendees[attendee_id] = 0
        st.spec = dataclasses.replace(
            st.spec,
            attendees_count=(
                st.spec.attendees_count + 1
            ),
            revenue_gil=(
                st.spec.revenue_gil
                + st.spec.admission_gil
            ),
        )
        return st.spec.admission_gil

    def deliver(
        self, *, lecture_id: str,
    ) -> t.Optional[int]:
        """Deliver the lecture. Each attendee gains
        skill: BASE_GAIN + (lecturer_skill // 20)
        the first time, REPEAT_GAIN on subsequent
        attendances of the same topic. Returns
        total skill_gain distributed (sum across
        attendees).
        """
        if lecture_id not in self._lectures:
            return None
        st = self._lectures[lecture_id]
        if st.spec.state != LectureState.ANNOUNCED:
            return None
        per_attendee = (
            _BASE_GAIN + st.spec.lecturer_skill // 20
        )
        total = 0
        for aid in list(st.attendees.keys()):
            prior = st.attendees[aid]
            gain = (
                per_attendee if prior == 0
                else _REPEAT_GAIN
            )
            st.attendees[aid] = prior + gain
            total += gain
        st.spec = dataclasses.replace(
            st.spec, state=LectureState.DELIVERED,
        )
        return total

    def cancel(
        self, *, lecture_id: str,
    ) -> t.Optional[int]:
        """Returns total refund owed to attendees."""
        if lecture_id not in self._lectures:
            return None
        st = self._lectures[lecture_id]
        if st.spec.state not in (
            LectureState.BOOKED,
            LectureState.ANNOUNCED,
        ):
            return None
        refund = st.spec.revenue_gil
        st.spec = dataclasses.replace(
            st.spec, state=LectureState.CANCELED,
        )
        return refund

    def attendee_skill_gain(
        self, *, lecture_id: str, attendee_id: str,
    ) -> int:
        st = self._lectures.get(lecture_id)
        if st is None:
            return 0
        return st.attendees.get(attendee_id, 0)

    def lecture(
        self, *, lecture_id: str,
    ) -> t.Optional[Lecture]:
        st = self._lectures.get(lecture_id)
        return st.spec if st else None


__all__ = [
    "LectureState", "Lecture",
    "PlayerLectureHallSystem",
]
