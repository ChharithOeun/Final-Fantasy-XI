"""Player civic office — held position with term & salary.

A civic office is a position that a player holds for a fixed
term (in days) at a fixed salary_per_day_gil. The office is
created once by an organizer and persists through successive
holders. After an election, the elected candidate is appointed
on a specific day; while occupied, the holder accrues unpaid
salary which they collect on demand. Vacating ends the term
early; the office returns to VACANT and can be re-appointed.

Lifecycle
    VACANT      no current holder; ready to be appointed
    OCCUPIED    a holder has been appointed and is accruing
                salary

Public surface
--------------
    OfficeState enum
    CivicOffice dataclass (frozen)
    PlayerCivicOfficeSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class OfficeState(str, enum.Enum):
    VACANT = "vacant"
    OCCUPIED = "occupied"


@dataclasses.dataclass(frozen=True)
class CivicOffice:
    office_id: str
    title: str
    term_days: int
    salary_per_day_gil: int
    state: OfficeState
    holder_id: str
    appointed_day: int
    last_collection_day: int
    salary_paid_lifetime_gil: int


@dataclasses.dataclass
class PlayerCivicOfficeSystem:
    _offices: dict[str, CivicOffice] = (
        dataclasses.field(default_factory=dict)
    )
    _next: int = 1

    def create_office(
        self, *, title: str, term_days: int,
        salary_per_day_gil: int,
    ) -> t.Optional[str]:
        if not title:
            return None
        if term_days <= 0:
            return None
        if salary_per_day_gil <= 0:
            return None
        oid = f"office_{self._next}"
        self._next += 1
        self._offices[oid] = CivicOffice(
            office_id=oid, title=title,
            term_days=term_days,
            salary_per_day_gil=salary_per_day_gil,
            state=OfficeState.VACANT,
            holder_id="", appointed_day=0,
            last_collection_day=0,
            salary_paid_lifetime_gil=0,
        )
        return oid

    def appoint(
        self, *, office_id: str, holder_id: str,
        appointed_day: int,
    ) -> bool:
        if office_id not in self._offices:
            return False
        spec = self._offices[office_id]
        if spec.state != OfficeState.VACANT:
            return False
        if not holder_id:
            return False
        if appointed_day < 0:
            return False
        self._offices[office_id] = dataclasses.replace(
            spec, state=OfficeState.OCCUPIED,
            holder_id=holder_id,
            appointed_day=appointed_day,
            last_collection_day=appointed_day,
        )
        return True

    def collect_salary(
        self, *, office_id: str, holder_id: str,
        current_day: int,
    ) -> t.Optional[int]:
        """Returns gil owed since last collection;
        clamps at term_days from appointment so a
        holder cannot accrue past their term."""
        if office_id not in self._offices:
            return None
        spec = self._offices[office_id]
        if spec.state != OfficeState.OCCUPIED:
            return None
        if spec.holder_id != holder_id:
            return None
        if current_day < spec.last_collection_day:
            return None
        # Cap the effective day at end-of-term
        end_of_term = (
            spec.appointed_day + spec.term_days
        )
        effective_day = min(current_day, end_of_term)
        days_owed = (
            effective_day - spec.last_collection_day
        )
        if days_owed <= 0:
            return 0
        owed = days_owed * spec.salary_per_day_gil
        self._offices[office_id] = dataclasses.replace(
            spec, last_collection_day=effective_day,
            salary_paid_lifetime_gil=(
                spec.salary_paid_lifetime_gil + owed
            ),
        )
        return owed

    def vacate(
        self, *, office_id: str, holder_id: str,
    ) -> bool:
        if office_id not in self._offices:
            return False
        spec = self._offices[office_id]
        if spec.state != OfficeState.OCCUPIED:
            return False
        if spec.holder_id != holder_id:
            return False
        self._offices[office_id] = dataclasses.replace(
            spec, state=OfficeState.VACANT,
            holder_id="",
        )
        return True

    def term_remaining(
        self, *, office_id: str, current_day: int,
    ) -> t.Optional[int]:
        spec = self._offices.get(office_id)
        if spec is None:
            return None
        if spec.state != OfficeState.OCCUPIED:
            return None
        end_of_term = (
            spec.appointed_day + spec.term_days
        )
        return max(0, end_of_term - current_day)

    def office(
        self, *, office_id: str,
    ) -> t.Optional[CivicOffice]:
        return self._offices.get(office_id)


__all__ = [
    "OfficeState", "CivicOffice",
    "PlayerCivicOfficeSystem",
]
