"""Nation council advisory — officers debate motions.

The COUNCIL is a seated body of officers who advise the
governor. Members propose MOTIONS (action proposals)
and other members VOTE for/against, with a stat-weighted
recommendation: each member's vote weight is their
intellect (capped at 100 / 100). The motion's outcome
is decided when the chair calls the vote.

Council seats are limited; the governor (or successor
council) seats officers via SEAT and unseats via UNSEAT.
A motion proposed by a non-seated officer is rejected.

Motion lifecycle:
    PROPOSED        motion filed, awaiting debate
    DEBATING        chair has opened debate;
                    voting allowed
    PASSED          tally passed
    DEFEATED        tally failed
    WITHDRAWN       proposer pulled it before vote

Public surface
--------------
    MotionState enum
    Vote enum
    Seat dataclass (frozen)
    Motion dataclass (frozen)
    NationCouncilAdvisorySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MotionState(str, enum.Enum):
    PROPOSED = "proposed"
    DEBATING = "debating"
    PASSED = "passed"
    DEFEATED = "defeated"
    WITHDRAWN = "withdrawn"


class Vote(str, enum.Enum):
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


@dataclasses.dataclass(frozen=True)
class Seat:
    nation_id: str
    officer_id: str
    intellect: int
    seated_day: int


@dataclasses.dataclass(frozen=True)
class Motion:
    motion_id: str
    nation_id: str
    proposer: str
    title: str
    body: str
    proposed_day: int
    state: MotionState
    weight_for: int
    weight_against: int
    final_decided_day: t.Optional[int]


@dataclasses.dataclass
class _MState:
    spec: Motion
    votes: dict[str, Vote] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class NationCouncilAdvisorySystem:
    _seats: dict[tuple[str, str], Seat] = (
        dataclasses.field(default_factory=dict)
    )
    _seat_caps: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    _motions: dict[str, _MState] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def set_seat_cap(
        self, *, nation_id: str, cap: int,
    ) -> bool:
        if not nation_id:
            return False
        if cap <= 0:
            return False
        self._seat_caps[nation_id] = cap
        return True

    def _seats_in(self, nation_id: str) -> list[Seat]:
        return [
            s for s in self._seats.values()
            if s.nation_id == nation_id
        ]

    def seat(
        self, *, nation_id: str, officer_id: str,
        intellect: int, seated_day: int,
    ) -> bool:
        if not nation_id or not officer_id:
            return False
        if intellect < 1 or intellect > 100:
            return False
        if seated_day < 0:
            return False
        cap = self._seat_caps.get(nation_id, 0)
        if cap <= 0:
            return False
        if (nation_id, officer_id) in self._seats:
            return False
        if len(self._seats_in(nation_id)) >= cap:
            return False
        self._seats[(nation_id, officer_id)] = Seat(
            nation_id=nation_id,
            officer_id=officer_id,
            intellect=intellect,
            seated_day=seated_day,
        )
        return True

    def unseat(
        self, *, nation_id: str, officer_id: str,
    ) -> bool:
        key = (nation_id, officer_id)
        if key not in self._seats:
            return False
        del self._seats[key]
        return True

    def is_seated(
        self, *, nation_id: str, officer_id: str,
    ) -> bool:
        return (nation_id, officer_id) in self._seats

    def propose_motion(
        self, *, nation_id: str, proposer: str,
        title: str, body: str, proposed_day: int,
    ) -> t.Optional[str]:
        if not self.is_seated(
            nation_id=nation_id, officer_id=proposer,
        ):
            return None
        if not title or not body:
            return None
        if proposed_day < 0:
            return None
        mid = f"motion_{self._next_id}"
        self._next_id += 1
        spec = Motion(
            motion_id=mid, nation_id=nation_id,
            proposer=proposer, title=title,
            body=body, proposed_day=proposed_day,
            state=MotionState.PROPOSED,
            weight_for=0, weight_against=0,
            final_decided_day=None,
        )
        self._motions[mid] = _MState(spec=spec)
        return mid

    def open_debate(
        self, *, motion_id: str,
    ) -> bool:
        if motion_id not in self._motions:
            return False
        st = self._motions[motion_id]
        if st.spec.state != MotionState.PROPOSED:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=MotionState.DEBATING,
        )
        return True

    def cast_vote(
        self, *, motion_id: str, voter: str,
        vote: Vote,
    ) -> bool:
        if motion_id not in self._motions:
            return False
        st = self._motions[motion_id]
        if st.spec.state != MotionState.DEBATING:
            return False
        if not self.is_seated(
            nation_id=st.spec.nation_id,
            officer_id=voter,
        ):
            return False
        if voter in st.votes:
            return False
        st.votes[voter] = vote
        return True

    def tally(
        self, *, motion_id: str, now_day: int,
    ) -> t.Optional[MotionState]:
        if motion_id not in self._motions:
            return None
        st = self._motions[motion_id]
        if st.spec.state != MotionState.DEBATING:
            return None
        wf, wa = 0, 0
        for voter, vote in st.votes.items():
            seat_ = self._seats.get(
                (st.spec.nation_id, voter),
            )
            if seat_ is None:
                continue
            if vote == Vote.FOR:
                wf += seat_.intellect
            elif vote == Vote.AGAINST:
                wa += seat_.intellect
        new_state = (
            MotionState.PASSED if wf > wa
            else MotionState.DEFEATED
        )
        st.spec = dataclasses.replace(
            st.spec, state=new_state,
            weight_for=wf, weight_against=wa,
            final_decided_day=now_day,
        )
        return new_state

    def withdraw(
        self, *, motion_id: str, now_day: int,
    ) -> bool:
        if motion_id not in self._motions:
            return False
        st = self._motions[motion_id]
        if st.spec.state not in (
            MotionState.PROPOSED,
            MotionState.DEBATING,
        ):
            return False
        st.spec = dataclasses.replace(
            st.spec, state=MotionState.WITHDRAWN,
            final_decided_day=now_day,
        )
        return True

    def motion(
        self, *, motion_id: str,
    ) -> t.Optional[Motion]:
        if motion_id not in self._motions:
            return None
        return self._motions[motion_id].spec

    def motions_for(
        self, *, nation_id: str,
    ) -> list[Motion]:
        return [
            st.spec for st in self._motions.values()
            if st.spec.nation_id == nation_id
        ]


__all__ = [
    "MotionState", "Vote", "Seat", "Motion",
    "NationCouncilAdvisorySystem",
]
