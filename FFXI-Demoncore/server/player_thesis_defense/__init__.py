"""Player thesis defense — formal academic credential.

The capstone of player education: a public defense before
3-7 examiners. Candidate submits thesis, registers
examiners, and on defense day each examiner submits a
score 0..100. Pass requires majority of examiners scoring
>= 60. Pass earns the candidate the THESIS_DEFENDED title
plus academic_credential_score; failure can be re-attempted
after a cooldown.

Lifecycle
    DRAFT             candidate writing
    SUBMITTED         examiners assigned, awaiting defense
    DEFENDED          scoring complete, result known
    FAILED_AWAITING   too few passing scores; can retry

Public surface
--------------
    ThesisState enum
    Verdict enum
    Thesis dataclass (frozen)
    ExaminerScore dataclass (frozen)
    PlayerThesisDefenseSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_PASS_THRESHOLD = 60
_MIN_EXAMINERS = 3
_MAX_EXAMINERS = 7
_RETRY_COOLDOWN_DAYS = 30


class ThesisState(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    DEFENDED = "defended"
    FAILED_AWAITING = "failed_awaiting"


class Verdict(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclasses.dataclass(frozen=True)
class ExaminerScore:
    examiner_id: str
    score: int


@dataclasses.dataclass(frozen=True)
class Thesis:
    thesis_id: str
    candidate_id: str
    title: str
    field: str
    state: ThesisState
    verdict: t.Optional[Verdict]
    examiner_count: int
    average_score: int
    last_defense_day: int


@dataclasses.dataclass
class _TState:
    spec: Thesis
    examiners: list[str] = dataclasses.field(
        default_factory=list,
    )
    scores: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerThesisDefenseSystem:
    _theses: dict[str, _TState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def begin_thesis(
        self, *, candidate_id: str, title: str,
        field: str,
    ) -> t.Optional[str]:
        if not candidate_id or not title or not field:
            return None
        tid = f"thesis_{self._next}"
        self._next += 1
        self._theses[tid] = _TState(
            spec=Thesis(
                thesis_id=tid,
                candidate_id=candidate_id,
                title=title, field=field,
                state=ThesisState.DRAFT,
                verdict=None, examiner_count=0,
                average_score=0,
                last_defense_day=0,
            ),
        )
        return tid

    def add_examiner(
        self, *, thesis_id: str, examiner_id: str,
    ) -> bool:
        if thesis_id not in self._theses:
            return False
        st = self._theses[thesis_id]
        if st.spec.state != ThesisState.DRAFT:
            return False
        if not examiner_id:
            return False
        if examiner_id == st.spec.candidate_id:
            return False
        if examiner_id in st.examiners:
            return False
        if len(st.examiners) >= _MAX_EXAMINERS:
            return False
        st.examiners.append(examiner_id)
        return True

    def submit(
        self, *, thesis_id: str, candidate_id: str,
    ) -> bool:
        if thesis_id not in self._theses:
            return False
        st = self._theses[thesis_id]
        if st.spec.state != ThesisState.DRAFT:
            return False
        if st.spec.candidate_id != candidate_id:
            return False
        if len(st.examiners) < _MIN_EXAMINERS:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=ThesisState.SUBMITTED,
            examiner_count=len(st.examiners),
        )
        return True

    def submit_score(
        self, *, thesis_id: str, examiner_id: str,
        score: int,
    ) -> bool:
        if thesis_id not in self._theses:
            return False
        st = self._theses[thesis_id]
        if st.spec.state != ThesisState.SUBMITTED:
            return False
        if examiner_id not in st.examiners:
            return False
        if examiner_id in st.scores:
            return False
        if not 0 <= score <= 100:
            return False
        st.scores[examiner_id] = score
        return True

    def render_verdict(
        self, *, thesis_id: str, defense_day: int,
    ) -> t.Optional[Verdict]:
        if thesis_id not in self._theses:
            return None
        st = self._theses[thesis_id]
        if st.spec.state != ThesisState.SUBMITTED:
            return None
        if len(st.scores) != len(st.examiners):
            return None
        if defense_day < 0:
            return None
        passing = sum(
            1 for v in st.scores.values()
            if v >= _PASS_THRESHOLD
        )
        majority = len(st.examiners) // 2 + 1
        avg = (
            sum(st.scores.values())
            // len(st.scores)
        )
        if passing >= majority:
            verdict = Verdict.PASS
            new_state = ThesisState.DEFENDED
        else:
            verdict = Verdict.FAIL
            new_state = ThesisState.FAILED_AWAITING
        st.spec = dataclasses.replace(
            st.spec, state=new_state,
            verdict=verdict, average_score=avg,
            last_defense_day=defense_day,
        )
        return verdict

    def retry(
        self, *, thesis_id: str,
        candidate_id: str, current_day: int,
    ) -> bool:
        """Reopen a failed defense for re-attempt
        after the cooldown."""
        if thesis_id not in self._theses:
            return False
        st = self._theses[thesis_id]
        if st.spec.state != ThesisState.FAILED_AWAITING:
            return False
        if st.spec.candidate_id != candidate_id:
            return False
        elapsed = current_day - st.spec.last_defense_day
        if elapsed < _RETRY_COOLDOWN_DAYS:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=ThesisState.DRAFT,
            verdict=None, average_score=0,
        )
        st.scores.clear()
        return True

    def thesis(
        self, *, thesis_id: str,
    ) -> t.Optional[Thesis]:
        st = self._theses.get(thesis_id)
        return st.spec if st else None

    def examiners(
        self, *, thesis_id: str,
    ) -> list[str]:
        st = self._theses.get(thesis_id)
        if st is None:
            return []
        return list(st.examiners)


__all__ = [
    "ThesisState", "Verdict", "Thesis",
    "ExaminerScore", "PlayerThesisDefenseSystem",
]
