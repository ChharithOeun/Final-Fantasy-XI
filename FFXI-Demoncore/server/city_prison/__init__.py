"""City prison — holding facility for sentenced players.

When city_court returns GUILTY_PRISON, the prisoner is
incarcerated in the city's PRISON for sentence_value
days. While imprisoned, the player's controllable
actions are restricted (delegated; this module only
tracks state). Time may be reduced via good behavior
or prison labor.

Lifecycle:
    INTAKE        booked, awaiting cell assignment
    SERVING       in cell, accumulating served days
    PAROLE        released early on parole, must
                  check in periodically
    DISCHARGED    sentence served (or pardoned)
    ESCAPED       prisoner broke out (rare event)

A PrisonRecord:
    record_id, prison_id, prisoner_id, case_id (link
    back to court), sentence_days, served_days,
    started_day, ended_day, state.

The system supports:
    - book(prisoner, case, sentence) -> intake
    - assign_cell(record) -> serving
    - tick(now_day) auto-discharges anyone whose
      served_days >= sentence_days
    - apply_good_behavior(record, days) reduces
      sentence
    - request_parole(record, now_day) — eligible at
      half-served-or-more
    - report_in_parole(record, now_day) — keeps
      parole valid
    - mark_escaped(record) — emergency
    - pardon(record) — leader/governor override

Public surface
--------------
    PrisonState enum
    PrisonRecord dataclass (frozen)
    CityPrisonSystem
        .open_prison(prison_id, city, capacity) -> bool
        .book(prison_id, prisoner_id, case_id,
              sentence_days, now_day) -> Optional[str]
        .assign_cell(record_id, now_day) -> bool
        .tick(now_day) -> list[(record_id, PrisonState)]
        .apply_good_behavior(record_id, days) -> bool
        .request_parole(record_id, now_day) -> bool
        .report_in_parole(record_id, now_day) -> bool
        .mark_escaped(record_id, now_day) -> bool
        .pardon(record_id, now_day) -> bool
        .record(record_id) -> Optional[PrisonRecord]
        .records_for(prisoner_id) -> list[PrisonRecord]
        .active_records(prison_id) -> list[PrisonRecord]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PrisonState(str, enum.Enum):
    INTAKE = "intake"
    SERVING = "serving"
    PAROLE = "parole"
    DISCHARGED = "discharged"
    ESCAPED = "escaped"


@dataclasses.dataclass(frozen=True)
class PrisonRecord:
    record_id: str
    prison_id: str
    prisoner_id: str
    case_id: str
    sentence_days: int
    served_days: int
    started_day: int
    last_tick_day: int
    ended_day: t.Optional[int]
    state: PrisonState


@dataclasses.dataclass
class _Prison:
    prison_id: str
    city: str
    capacity: int


@dataclasses.dataclass
class CityPrisonSystem:
    _prisons: dict[str, _Prison] = dataclasses.field(
        default_factory=dict,
    )
    _records: dict[str, PrisonRecord] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def open_prison(
        self, *, prison_id: str, city: str,
        capacity: int,
    ) -> bool:
        if not prison_id or not city:
            return False
        if capacity <= 0:
            return False
        if prison_id in self._prisons:
            return False
        self._prisons[prison_id] = _Prison(
            prison_id=prison_id, city=city,
            capacity=capacity,
        )
        return True

    def _active_count(self, prison_id: str) -> int:
        return sum(
            1 for r in self._records.values()
            if (r.prison_id == prison_id
                and r.state in (PrisonState.INTAKE,
                                PrisonState.SERVING))
        )

    def book(
        self, *, prison_id: str, prisoner_id: str,
        case_id: str, sentence_days: int,
        now_day: int,
    ) -> t.Optional[str]:
        if prison_id not in self._prisons:
            return None
        if not prisoner_id or not case_id:
            return None
        if sentence_days <= 0 or now_day < 0:
            return None
        p = self._prisons[prison_id]
        if self._active_count(prison_id) >= p.capacity:
            return None
        rid = f"prec_{self._next_id}"
        self._next_id += 1
        self._records[rid] = PrisonRecord(
            record_id=rid, prison_id=prison_id,
            prisoner_id=prisoner_id, case_id=case_id,
            sentence_days=sentence_days,
            served_days=0, started_day=now_day,
            last_tick_day=now_day, ended_day=None,
            state=PrisonState.INTAKE,
        )
        return rid

    def assign_cell(
        self, *, record_id: str, now_day: int,
    ) -> bool:
        if record_id not in self._records:
            return False
        r = self._records[record_id]
        if r.state != PrisonState.INTAKE:
            return False
        if now_day < r.started_day:
            return False
        self._records[record_id] = dataclasses.replace(
            r, last_tick_day=now_day,
            state=PrisonState.SERVING,
        )
        return True

    def tick(
        self, *, now_day: int,
    ) -> list[tuple[str, PrisonState]]:
        changes: list[tuple[str, PrisonState]] = []
        for rid, r in list(self._records.items()):
            if r.state != PrisonState.SERVING:
                continue
            if now_day <= r.last_tick_day:
                continue
            elapsed = now_day - r.last_tick_day
            new_served = r.served_days + elapsed
            if new_served >= r.sentence_days:
                self._records[rid] = (
                    dataclasses.replace(
                        r, served_days=r.sentence_days,
                        last_tick_day=now_day,
                        ended_day=now_day,
                        state=PrisonState.DISCHARGED,
                    )
                )
                changes.append(
                    (rid, PrisonState.DISCHARGED),
                )
            else:
                self._records[rid] = (
                    dataclasses.replace(
                        r, served_days=new_served,
                        last_tick_day=now_day,
                    )
                )
        return changes

    def apply_good_behavior(
        self, *, record_id: str, days: int,
    ) -> bool:
        if record_id not in self._records:
            return False
        if days <= 0:
            return False
        r = self._records[record_id]
        if r.state != PrisonState.SERVING:
            return False
        new_sentence = max(
            r.served_days, r.sentence_days - days,
        )
        self._records[record_id] = dataclasses.replace(
            r, sentence_days=new_sentence,
        )
        return True

    def request_parole(
        self, *, record_id: str, now_day: int,
    ) -> bool:
        if record_id not in self._records:
            return False
        r = self._records[record_id]
        if r.state != PrisonState.SERVING:
            return False
        # Eligible at half-served
        if r.served_days * 2 < r.sentence_days:
            return False
        self._records[record_id] = dataclasses.replace(
            r, state=PrisonState.PAROLE,
            last_tick_day=now_day,
        )
        return True

    def report_in_parole(
        self, *, record_id: str, now_day: int,
    ) -> bool:
        if record_id not in self._records:
            return False
        r = self._records[record_id]
        if r.state != PrisonState.PAROLE:
            return False
        # If served_days now >= sentence, discharge
        elapsed = now_day - r.last_tick_day
        new_served = r.served_days + max(0, elapsed)
        if new_served >= r.sentence_days:
            self._records[record_id] = (
                dataclasses.replace(
                    r, served_days=r.sentence_days,
                    last_tick_day=now_day,
                    ended_day=now_day,
                    state=PrisonState.DISCHARGED,
                )
            )
        else:
            self._records[record_id] = (
                dataclasses.replace(
                    r, served_days=new_served,
                    last_tick_day=now_day,
                )
            )
        return True

    def mark_escaped(
        self, *, record_id: str, now_day: int,
    ) -> bool:
        if record_id not in self._records:
            return False
        r = self._records[record_id]
        if r.state not in (
            PrisonState.SERVING, PrisonState.INTAKE,
            PrisonState.PAROLE,
        ):
            return False
        self._records[record_id] = dataclasses.replace(
            r, ended_day=now_day,
            state=PrisonState.ESCAPED,
        )
        return True

    def pardon(
        self, *, record_id: str, now_day: int,
    ) -> bool:
        if record_id not in self._records:
            return False
        r = self._records[record_id]
        if r.state in (
            PrisonState.DISCHARGED, PrisonState.ESCAPED,
        ):
            return False
        self._records[record_id] = dataclasses.replace(
            r, served_days=r.sentence_days,
            ended_day=now_day,
            state=PrisonState.DISCHARGED,
        )
        return True

    def record(
        self, *, record_id: str,
    ) -> t.Optional[PrisonRecord]:
        return self._records.get(record_id)

    def records_for(
        self, *, prisoner_id: str,
    ) -> list[PrisonRecord]:
        return [
            r for r in self._records.values()
            if r.prisoner_id == prisoner_id
        ]

    def active_records(
        self, *, prison_id: str,
    ) -> list[PrisonRecord]:
        return [
            r for r in self._records.values()
            if (r.prison_id == prison_id
                and r.state in (PrisonState.INTAKE,
                                PrisonState.SERVING,
                                PrisonState.PAROLE))
        ]


__all__ = [
    "PrisonState", "PrisonRecord", "CityPrisonSystem",
]
