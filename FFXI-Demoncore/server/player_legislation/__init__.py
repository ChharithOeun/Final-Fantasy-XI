"""Player legislation — bills proposed and voted in a body.

A speaker founds a legislative body and enrolls registered
legislators. Any legislator can propose a bill (title +
body_text). The speaker calls a vote, after which all
legislators may cast yea/nay. The speaker closes the vote
and the bill PASSES if yea > nay (strict majority — ties
fail). Bills carry a sponsor_id and a public yea/nay tally.

Lifecycle (bill)
    PROPOSED      sponsor wrote it; awaiting begin_vote
    VOTING        speaker opened vote; legislators voting
    PASSED        yea > nay; bill enacted
    FAILED        yea <= nay; bill rejected

Public surface
--------------
    BillState enum
    LegislativeBody dataclass (frozen)
    Bill dataclass (frozen)
    PlayerLegislationSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BillState(str, enum.Enum):
    PROPOSED = "proposed"
    VOTING = "voting"
    PASSED = "passed"
    FAILED = "failed"


@dataclasses.dataclass(frozen=True)
class LegislativeBody:
    body_id: str
    speaker_id: str
    name: str


@dataclasses.dataclass(frozen=True)
class Bill:
    bill_id: str
    body_id: str
    sponsor_id: str
    title: str
    body_text: str
    state: BillState
    yea_count: int
    nay_count: int


@dataclasses.dataclass
class _BillState:
    spec: Bill
    # legislator_id -> True (yea) or False (nay)
    votes: dict[str, bool] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class _BodyState:
    spec: LegislativeBody
    legislators: set[str] = dataclasses.field(
        default_factory=set,
    )
    bills: dict[str, _BillState] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerLegislationSystem:
    _bodies: dict[str, _BodyState] = dataclasses.field(
        default_factory=dict,
    )
    _next_body: int = 1
    _next_bill: int = 1

    def found_body(
        self, *, speaker_id: str, name: str,
    ) -> t.Optional[str]:
        if not speaker_id or not name:
            return None
        bid = f"body_{self._next_body}"
        self._next_body += 1
        self._bodies[bid] = _BodyState(
            spec=LegislativeBody(
                body_id=bid, speaker_id=speaker_id,
                name=name,
            ),
        )
        # Speaker is automatically a legislator
        self._bodies[bid].legislators.add(speaker_id)
        return bid

    def enroll_legislator(
        self, *, body_id: str, speaker_id: str,
        legislator_id: str,
    ) -> bool:
        if body_id not in self._bodies:
            return False
        st = self._bodies[body_id]
        if st.spec.speaker_id != speaker_id:
            return False
        if not legislator_id:
            return False
        if legislator_id in st.legislators:
            return False
        st.legislators.add(legislator_id)
        return True

    def propose_bill(
        self, *, body_id: str, sponsor_id: str,
        title: str, body_text: str,
    ) -> t.Optional[str]:
        if body_id not in self._bodies:
            return None
        st = self._bodies[body_id]
        if sponsor_id not in st.legislators:
            return None
        if not title or not body_text:
            return None
        bid = f"bill_{self._next_bill}"
        self._next_bill += 1
        st.bills[bid] = _BillState(
            spec=Bill(
                bill_id=bid, body_id=body_id,
                sponsor_id=sponsor_id, title=title,
                body_text=body_text,
                state=BillState.PROPOSED,
                yea_count=0, nay_count=0,
            ),
        )
        return bid

    def begin_vote(
        self, *, body_id: str, bill_id: str,
        speaker_id: str,
    ) -> bool:
        if body_id not in self._bodies:
            return False
        st = self._bodies[body_id]
        if st.spec.speaker_id != speaker_id:
            return False
        if bill_id not in st.bills:
            return False
        bs = st.bills[bill_id]
        if bs.spec.state != BillState.PROPOSED:
            return False
        bs.spec = dataclasses.replace(
            bs.spec, state=BillState.VOTING,
        )
        return True

    def cast_vote(
        self, *, body_id: str, bill_id: str,
        legislator_id: str, yea: bool,
    ) -> bool:
        if body_id not in self._bodies:
            return False
        st = self._bodies[body_id]
        if legislator_id not in st.legislators:
            return False
        if bill_id not in st.bills:
            return False
        bs = st.bills[bill_id]
        if bs.spec.state != BillState.VOTING:
            return False
        if legislator_id in bs.votes:
            return False
        bs.votes[legislator_id] = yea
        return True

    def close_vote(
        self, *, body_id: str, bill_id: str,
        speaker_id: str,
    ) -> t.Optional[BillState]:
        if body_id not in self._bodies:
            return None
        st = self._bodies[body_id]
        if st.spec.speaker_id != speaker_id:
            return None
        if bill_id not in st.bills:
            return None
        bs = st.bills[bill_id]
        if bs.spec.state != BillState.VOTING:
            return None
        yea = sum(1 for v in bs.votes.values() if v)
        nay = sum(
            1 for v in bs.votes.values() if not v
        )
        if yea > nay:
            new_state = BillState.PASSED
        else:
            new_state = BillState.FAILED
        bs.spec = dataclasses.replace(
            bs.spec, state=new_state,
            yea_count=yea, nay_count=nay,
        )
        return new_state

    def body(
        self, *, body_id: str,
    ) -> t.Optional[LegislativeBody]:
        st = self._bodies.get(body_id)
        return st.spec if st else None

    def bill(
        self, *, body_id: str, bill_id: str,
    ) -> t.Optional[Bill]:
        st = self._bodies.get(body_id)
        if st is None:
            return None
        bs = st.bills.get(bill_id)
        return bs.spec if bs else None

    def legislators(
        self, *, body_id: str,
    ) -> list[str]:
        st = self._bodies.get(body_id)
        if st is None:
            return []
        return sorted(st.legislators)


__all__ = [
    "BillState", "LegislativeBody", "Bill",
    "PlayerLegislationSystem",
]
