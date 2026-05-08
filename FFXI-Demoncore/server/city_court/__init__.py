"""City court — judicial system for outlaw trials.

When the outlaw_system flags a player as wanted, and
they're caught (KO'd by guards / bounty hunters), they
are dragged before the city COURT for trial.

A trial:
    1. case opened (charges, evidence, witnesses)
    2. plea entered (guilty / not guilty)
    3. judgement rendered (one of 5 verdicts)
    4. sentence executed (delegated to caller)

Verdicts:
    ACQUITTED        no penalty
    GUILTY_FINE      gil fine (delegated)
    GUILTY_PRISON    prison term (delegated to
                     city_prison)
    GUILTY_EXILE     banished from this city for N days
    GUILTY_DEATH     permadeath sentence (rare —
                     server-broadcast)

Lifecycle states:
    OPENED       case filed, awaiting plea
    PLED         plea entered, awaiting verdict
    JUDGED       verdict rendered, awaiting sentence
    EXECUTED     sentence carried out, case closed

Public surface
--------------
    Verdict enum
    PleaKind enum
    CaseState enum
    CourtCase dataclass (frozen)
    CityCourtSystem
        .file_case(...) -> Optional[str]
        .enter_plea(case_id, plea, now_day) -> bool
        .render_verdict(case_id, verdict, judge_id,
                        now_day) -> bool
        .execute_sentence(case_id, now_day) -> bool
        .case(case_id) -> Optional[CourtCase]
        .cases_for(defendant_id) -> list[CourtCase]
        .open_cases() -> list[CourtCase]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Verdict(str, enum.Enum):
    ACQUITTED = "acquitted"
    GUILTY_FINE = "guilty_fine"
    GUILTY_PRISON = "guilty_prison"
    GUILTY_EXILE = "guilty_exile"
    GUILTY_DEATH = "guilty_death"


class PleaKind(str, enum.Enum):
    GUILTY = "guilty"
    NOT_GUILTY = "not_guilty"


class CaseState(str, enum.Enum):
    OPENED = "opened"
    PLED = "pled"
    JUDGED = "judged"
    EXECUTED = "executed"


@dataclasses.dataclass(frozen=True)
class CourtCase:
    case_id: str
    court_id: str
    defendant_id: str
    charges: tuple[str, ...]
    witnesses: tuple[str, ...]
    bounty_value: int
    plea: t.Optional[PleaKind]
    verdict: t.Optional[Verdict]
    judge_id: t.Optional[str]
    sentence_value: int  # gil fine, prison days, etc.
    filed_day: int
    pled_day: t.Optional[int]
    judged_day: t.Optional[int]
    executed_day: t.Optional[int]
    state: CaseState


@dataclasses.dataclass
class CityCourtSystem:
    _cases: dict[str, CourtCase] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def file_case(
        self, *, court_id: str, defendant_id: str,
        charges: t.Sequence[str], filed_day: int,
        witnesses: t.Sequence[str] = (),
        bounty_value: int = 0,
    ) -> t.Optional[str]:
        if not court_id or not defendant_id:
            return None
        if not charges:
            return None
        if filed_day < 0 or bounty_value < 0:
            return None
        cid = f"case_{self._next_id}"
        self._next_id += 1
        self._cases[cid] = CourtCase(
            case_id=cid, court_id=court_id,
            defendant_id=defendant_id,
            charges=tuple(charges),
            witnesses=tuple(witnesses),
            bounty_value=bounty_value, plea=None,
            verdict=None, judge_id=None,
            sentence_value=0, filed_day=filed_day,
            pled_day=None, judged_day=None,
            executed_day=None,
            state=CaseState.OPENED,
        )
        return cid

    def enter_plea(
        self, *, case_id: str, plea: PleaKind,
        now_day: int,
    ) -> bool:
        if case_id not in self._cases:
            return False
        c = self._cases[case_id]
        if c.state != CaseState.OPENED:
            return False
        if now_day < c.filed_day:
            return False
        # Guilty plea fast-tracks the case but still
        # needs verdict (judge sets sentence value).
        self._cases[case_id] = dataclasses.replace(
            c, plea=plea, pled_day=now_day,
            state=CaseState.PLED,
        )
        return True

    def render_verdict(
        self, *, case_id: str, verdict: Verdict,
        judge_id: str, now_day: int,
        sentence_value: int = 0,
    ) -> bool:
        if case_id not in self._cases:
            return False
        c = self._cases[case_id]
        if c.state != CaseState.PLED:
            return False
        if not judge_id:
            return False
        if sentence_value < 0:
            return False
        self._cases[case_id] = dataclasses.replace(
            c, verdict=verdict, judge_id=judge_id,
            sentence_value=sentence_value,
            judged_day=now_day,
            state=CaseState.JUDGED,
        )
        return True

    def execute_sentence(
        self, *, case_id: str, now_day: int,
    ) -> bool:
        if case_id not in self._cases:
            return False
        c = self._cases[case_id]
        if c.state != CaseState.JUDGED:
            return False
        self._cases[case_id] = dataclasses.replace(
            c, executed_day=now_day,
            state=CaseState.EXECUTED,
        )
        return True

    def case(
        self, *, case_id: str,
    ) -> t.Optional[CourtCase]:
        return self._cases.get(case_id)

    def cases_for(
        self, *, defendant_id: str,
    ) -> list[CourtCase]:
        return [
            c for c in self._cases.values()
            if c.defendant_id == defendant_id
        ]

    def open_cases(self) -> list[CourtCase]:
        return [
            c for c in self._cases.values()
            if c.state != CaseState.EXECUTED
        ]


__all__ = [
    "Verdict", "PleaKind", "CaseState", "CourtCase",
    "CityCourtSystem",
]
