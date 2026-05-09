"""Player jury selection — empanel jurors and finalize verdict.

A pool of registered jurors is maintained globally. When a
case needs a jury, empanel_jury picks the first N pool members
not currently sitting on another active jury. Each empaneled
juror submits a single guilty/not_guilty verdict; finalize_
verdict tallies and returns the majority. Ties resolve to
NOT_GUILTY (presumption of innocence). Once finalized, jurors
return to the pool and become available for future cases.

Lifecycle (case)
    EMPANELED        jury seated; awaiting verdicts
    DELIBERATING     all verdicts in; awaiting finalize
    FINALIZED        majority verdict rendered
    DISCHARGED       finalized; jurors free again

Public surface
--------------
    CaseState enum
    JuryVerdict enum
    JuryCase dataclass (frozen)
    PlayerJurySelectionSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_JURY = 3
_MAX_JURY = 12


class CaseState(str, enum.Enum):
    EMPANELED = "empaneled"
    DELIBERATING = "deliberating"
    FINALIZED = "finalized"


class JuryVerdict(str, enum.Enum):
    GUILTY = "guilty"
    NOT_GUILTY = "not_guilty"


@dataclasses.dataclass(frozen=True)
class JuryCase:
    case_id: str
    lawsuit_id: str
    state: CaseState
    final_verdict: t.Optional[JuryVerdict]
    guilty_count: int
    not_guilty_count: int


@dataclasses.dataclass
class _JCState:
    spec: JuryCase
    jurors: list[str] = dataclasses.field(
        default_factory=list,
    )
    # juror_id -> True (guilty) or False (not_guilty)
    verdicts: dict[str, bool] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerJurySelectionSystem:
    _pool: set[str] = dataclasses.field(
        default_factory=set,
    )
    _busy: set[str] = dataclasses.field(
        default_factory=set,
    )
    _cases: dict[str, _JCState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def enroll_juror(
        self, *, juror_id: str,
    ) -> bool:
        if not juror_id:
            return False
        if juror_id in self._pool:
            return False
        self._pool.add(juror_id)
        return True

    def empanel_jury(
        self, *, lawsuit_id: str,
        requested_size: int,
    ) -> t.Optional[str]:
        if not lawsuit_id:
            return None
        if not _MIN_JURY <= requested_size <= _MAX_JURY:
            return None
        # First N pool members not currently busy
        available = sorted(self._pool - self._busy)
        if len(available) < requested_size:
            return None
        chosen = available[:requested_size]
        cid = f"case_{self._next}"
        self._next += 1
        st = _JCState(
            spec=JuryCase(
                case_id=cid, lawsuit_id=lawsuit_id,
                state=CaseState.EMPANELED,
                final_verdict=None, guilty_count=0,
                not_guilty_count=0,
            ),
        )
        st.jurors = list(chosen)
        for j in chosen:
            self._busy.add(j)
        self._cases[cid] = st
        return cid

    def submit_verdict(
        self, *, case_id: str, juror_id: str,
        guilty: bool,
    ) -> bool:
        if case_id not in self._cases:
            return False
        st = self._cases[case_id]
        if st.spec.state != CaseState.EMPANELED:
            return False
        if juror_id not in st.jurors:
            return False
        if juror_id in st.verdicts:
            return False
        st.verdicts[juror_id] = guilty
        if len(st.verdicts) == len(st.jurors):
            st.spec = dataclasses.replace(
                st.spec,
                state=CaseState.DELIBERATING,
            )
        return True

    def finalize_verdict(
        self, *, case_id: str,
    ) -> t.Optional[JuryVerdict]:
        if case_id not in self._cases:
            return None
        st = self._cases[case_id]
        if st.spec.state != CaseState.DELIBERATING:
            return None
        guilty = sum(
            1 for v in st.verdicts.values() if v
        )
        not_g = sum(
            1 for v in st.verdicts.values() if not v
        )
        if guilty > not_g:
            verdict = JuryVerdict.GUILTY
        else:
            # Ties resolve to NOT_GUILTY
            verdict = JuryVerdict.NOT_GUILTY
        st.spec = dataclasses.replace(
            st.spec, state=CaseState.FINALIZED,
            final_verdict=verdict,
            guilty_count=guilty,
            not_guilty_count=not_g,
        )
        # Discharge jurors back to pool
        for j in st.jurors:
            self._busy.discard(j)
        return verdict

    def case(
        self, *, case_id: str,
    ) -> t.Optional[JuryCase]:
        st = self._cases.get(case_id)
        return st.spec if st else None

    def jurors(
        self, *, case_id: str,
    ) -> list[str]:
        st = self._cases.get(case_id)
        if st is None:
            return []
        return list(st.jurors)

    def pool_size(self) -> int:
        return len(self._pool)

    def available_count(self) -> int:
        return len(self._pool - self._busy)


__all__ = [
    "CaseState", "JuryVerdict", "JuryCase",
    "PlayerJurySelectionSystem",
]
