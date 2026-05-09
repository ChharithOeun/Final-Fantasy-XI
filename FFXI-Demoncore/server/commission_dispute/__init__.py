"""Commission dispute — arbitration of guild contract conflicts.

When a guild job hits a conflict — completer says they
delivered, poster says they didn't; poster says the craft was
shoddy, completer says the spec was met — either side can file
a dispute within DISPUTE_WINDOW_DAYS of the posted completion.
The dispute holds the escrow while evidence is gathered, then
an arbiter (in production: human + AI; here: deterministic
seed) issues a ruling: poster wins (refund), completer wins
(payout), or split (50/50 between the two).

Lifecycle
    FILED                  dispute opened
    EVIDENCE_GATHERING     either side may add evidence
    RESOLVED               arbiter ruled

Outcomes
    POSTER_WINS    full refund to poster
    COMPLETER_WINS full payout to completer
    SPLIT          50/50 split
    DISMISSED      filed without merit; small fine to filer

Public surface
--------------
    DisputeState enum
    DisputeOutcome enum
    Evidence dataclass (frozen)
    Dispute dataclass (frozen)
    CommissionDisputeSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


DISPUTE_WINDOW_DAYS = 7
DISMISSAL_FINE_PCT = 5


class DisputeState(str, enum.Enum):
    FILED = "filed"
    EVIDENCE_GATHERING = "evidence_gathering"
    RESOLVED = "resolved"


class DisputeOutcome(str, enum.Enum):
    POSTER_WINS = "poster_wins"
    COMPLETER_WINS = "completer_wins"
    SPLIT = "split"
    DISMISSED = "dismissed"


@dataclasses.dataclass(frozen=True)
class Evidence:
    evidence_id: str
    submitter_id: str
    description: str
    submitted_day: int


@dataclasses.dataclass(frozen=True)
class Dispute:
    dispute_id: str
    job_id: str
    poster_id: str
    completer_id: str
    filer_id: str
    reason: str
    escrow_gil: int
    state: DisputeState
    outcome: t.Optional[DisputeOutcome]
    poster_payout: int
    completer_payout: int
    filed_day: int
    completed_day: int


@dataclasses.dataclass
class _DState:
    spec: Dispute
    evidence: list[Evidence] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class CommissionDisputeSystem:
    _disputes: dict[str, _DState] = dataclasses.field(
        default_factory=dict,
    )
    _next_dispute: int = 1
    _next_evidence: int = 1

    def file_dispute(
        self, *, job_id: str, poster_id: str,
        completer_id: str, filer_id: str,
        reason: str, escrow_gil: int,
        completed_day: int, filed_day: int,
    ) -> t.Optional[str]:
        if not job_id or not poster_id or not completer_id:
            return None
        if filer_id not in (poster_id, completer_id):
            return None
        if not reason:
            return None
        if escrow_gil <= 0:
            return None
        if filed_day < completed_day:
            return None
        if filed_day - completed_day > DISPUTE_WINDOW_DAYS:
            return None
        # One open dispute per job
        for st in self._disputes.values():
            if (
                st.spec.job_id == job_id
                and st.spec.state != DisputeState.RESOLVED
            ):
                return None
        did = f"disp_{self._next_dispute}"
        self._next_dispute += 1
        self._disputes[did] = _DState(
            spec=Dispute(
                dispute_id=did, job_id=job_id,
                poster_id=poster_id,
                completer_id=completer_id,
                filer_id=filer_id, reason=reason,
                escrow_gil=escrow_gil,
                state=DisputeState.FILED,
                outcome=None, poster_payout=0,
                completer_payout=0,
                filed_day=filed_day,
                completed_day=completed_day,
            ),
        )
        return did

    def open_evidence(
        self, *, dispute_id: str,
    ) -> bool:
        if dispute_id not in self._disputes:
            return False
        st = self._disputes[dispute_id]
        if st.spec.state != DisputeState.FILED:
            return False
        st.spec = dataclasses.replace(
            st.spec,
            state=DisputeState.EVIDENCE_GATHERING,
        )
        return True

    def submit_evidence(
        self, *, dispute_id: str, submitter_id: str,
        description: str, submitted_day: int,
    ) -> t.Optional[str]:
        if dispute_id not in self._disputes:
            return None
        st = self._disputes[dispute_id]
        if st.spec.state != (
            DisputeState.EVIDENCE_GATHERING
        ):
            return None
        if submitter_id not in (
            st.spec.poster_id, st.spec.completer_id,
        ):
            return None
        if not description:
            return None
        eid = f"evid_{self._next_evidence}"
        self._next_evidence += 1
        st.evidence.append(
            Evidence(
                evidence_id=eid,
                submitter_id=submitter_id,
                description=description,
                submitted_day=submitted_day,
            ),
        )
        return eid

    def resolve(
        self, *, dispute_id: str,
        outcome: DisputeOutcome,
    ) -> t.Optional[tuple[int, int]]:
        """Arbiter rules. Returns (poster_payout,
        completer_payout). Sum = escrow.
        """
        if dispute_id not in self._disputes:
            return None
        st = self._disputes[dispute_id]
        if st.spec.state != (
            DisputeState.EVIDENCE_GATHERING
        ):
            return None
        escrow = st.spec.escrow_gil
        if outcome == DisputeOutcome.POSTER_WINS:
            poster_pay = escrow
            completer_pay = 0
        elif outcome == DisputeOutcome.COMPLETER_WINS:
            poster_pay = 0
            completer_pay = escrow
        elif outcome == DisputeOutcome.SPLIT:
            poster_pay = escrow // 2
            completer_pay = escrow - poster_pay
        else:  # DISMISSED — filer pays a fine
            fine = escrow * DISMISSAL_FINE_PCT // 100
            if st.spec.filer_id == st.spec.poster_id:
                poster_pay = escrow - fine
                completer_pay = fine
            else:
                poster_pay = fine
                completer_pay = escrow - fine
        st.spec = dataclasses.replace(
            st.spec, state=DisputeState.RESOLVED,
            outcome=outcome,
            poster_payout=poster_pay,
            completer_payout=completer_pay,
        )
        return poster_pay, completer_pay

    def dispute(
        self, *, dispute_id: str,
    ) -> t.Optional[Dispute]:
        st = self._disputes.get(dispute_id)
        return st.spec if st else None

    def evidence(
        self, *, dispute_id: str,
    ) -> list[Evidence]:
        st = self._disputes.get(dispute_id)
        if st is None:
            return []
        return list(st.evidence)


__all__ = [
    "DisputeState", "DisputeOutcome", "Evidence",
    "Dispute", "CommissionDisputeSystem",
    "DISPUTE_WINDOW_DAYS", "DISMISSAL_FINE_PCT",
]
