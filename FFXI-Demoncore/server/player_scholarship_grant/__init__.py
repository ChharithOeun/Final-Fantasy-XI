"""Player scholarship grant — wealthy donors fund students.

Wealthy players or LSes can endow scholarships: a pool of gil
locked toward sponsoring students at registered schools. The
donor sets criteria (course subject, max award per student,
total pool); the grant disburses to qualifying students until
the pool runs dry. Returns to the donor any unused balance
when revoked.

Lifecycle
    OPEN          accepting applications, disbursing
    EXHAUSTED     pool ran dry
    REVOKED       donor pulled remaining funds

Public surface
--------------
    GrantState enum
    Grant dataclass (frozen)
    Award dataclass (frozen)
    PlayerScholarshipGrantSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GrantState(str, enum.Enum):
    OPEN = "open"
    EXHAUSTED = "exhausted"
    REVOKED = "revoked"


@dataclasses.dataclass(frozen=True)
class Grant:
    grant_id: str
    donor_id: str
    name: str
    subject_filter: str       # blank = any subject
    max_award_per_student: int
    pool_gil: int
    disbursed_gil: int
    state: GrantState


@dataclasses.dataclass(frozen=True)
class Award:
    award_id: str
    grant_id: str
    student_id: str
    amount_gil: int
    awarded_day: int
    subject: str


@dataclasses.dataclass
class _GState:
    spec: Grant
    awards: dict[str, Award] = dataclasses.field(
        default_factory=dict,
    )
    student_totals: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerScholarshipGrantSystem:
    _grants: dict[str, _GState] = dataclasses.field(
        default_factory=dict,
    )
    _next_grant: int = 1
    _next_award: int = 1

    def endow_grant(
        self, *, donor_id: str, name: str,
        pool_gil: int, max_award_per_student: int,
        subject_filter: str = "",
    ) -> t.Optional[str]:
        if not donor_id or not name:
            return None
        if pool_gil <= 0:
            return None
        if max_award_per_student <= 0:
            return None
        if max_award_per_student > pool_gil:
            return None
        gid = f"grant_{self._next_grant}"
        self._next_grant += 1
        self._grants[gid] = _GState(
            spec=Grant(
                grant_id=gid, donor_id=donor_id,
                name=name,
                subject_filter=subject_filter,
                max_award_per_student=(
                    max_award_per_student
                ),
                pool_gil=pool_gil, disbursed_gil=0,
                state=GrantState.OPEN,
            ),
        )
        return gid

    def apply_award(
        self, *, grant_id: str, student_id: str,
        subject: str, requested_gil: int,
        awarded_day: int,
    ) -> t.Optional[str]:
        if grant_id not in self._grants:
            return None
        st = self._grants[grant_id]
        if st.spec.state != GrantState.OPEN:
            return None
        if not student_id or student_id == st.spec.donor_id:
            return None
        if requested_gil <= 0:
            return None
        if awarded_day < 0:
            return None
        # Subject filter check
        if (
            st.spec.subject_filter
            and subject != st.spec.subject_filter
        ):
            return None
        # Per-student cap
        prior_total = st.student_totals.get(
            student_id, 0,
        )
        if (
            prior_total + requested_gil
            > st.spec.max_award_per_student
        ):
            return None
        # Pool floor check
        remaining = (
            st.spec.pool_gil - st.spec.disbursed_gil
        )
        if requested_gil > remaining:
            return None
        aid = f"award_{self._next_award}"
        self._next_award += 1
        st.awards[aid] = Award(
            award_id=aid, grant_id=grant_id,
            student_id=student_id,
            amount_gil=requested_gil,
            awarded_day=awarded_day,
            subject=subject,
        )
        st.student_totals[student_id] = (
            prior_total + requested_gil
        )
        new_disbursed = (
            st.spec.disbursed_gil + requested_gil
        )
        new_state = st.spec.state
        if new_disbursed >= st.spec.pool_gil:
            new_state = GrantState.EXHAUSTED
        st.spec = dataclasses.replace(
            st.spec, disbursed_gil=new_disbursed,
            state=new_state,
        )
        return aid

    def revoke(
        self, *, grant_id: str, donor_id: str,
    ) -> t.Optional[int]:
        """Returns the unused gil refunded to the
        donor."""
        if grant_id not in self._grants:
            return None
        st = self._grants[grant_id]
        if st.spec.state != GrantState.OPEN:
            return None
        if st.spec.donor_id != donor_id:
            return None
        refund = (
            st.spec.pool_gil - st.spec.disbursed_gil
        )
        st.spec = dataclasses.replace(
            st.spec, state=GrantState.REVOKED,
        )
        return refund

    def grant(
        self, *, grant_id: str,
    ) -> t.Optional[Grant]:
        st = self._grants.get(grant_id)
        return st.spec if st else None

    def awards_to_student(
        self, *, grant_id: str, student_id: str,
    ) -> int:
        st = self._grants.get(grant_id)
        if st is None:
            return 0
        return st.student_totals.get(student_id, 0)

    def all_awards(
        self, *, grant_id: str,
    ) -> list[Award]:
        st = self._grants.get(grant_id)
        if st is None:
            return []
        return list(st.awards.values())


__all__ = [
    "GrantState", "Grant", "Award",
    "PlayerScholarshipGrantSystem",
]
