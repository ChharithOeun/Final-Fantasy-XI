"""Player referendum — yes/no constituency vote.

An organizer puts a single yes/no question to a defined
constituency. Voters cast yes or no once before the
voting_close_day. After close, tally returns YES or NO
based on majority — exact ties resolve to TIED. Useful
for ratifying treaties, approving budgets, electing
between two binary options after a candidate election
has narrowed the choice.

Lifecycle
    VOTING        accepting yes/no ballots
    CONCLUDED     tallied; outcome known

Public surface
--------------
    ReferendumState enum
    ReferendumOutcome enum
    Referendum dataclass (frozen)
    PlayerReferendumSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ReferendumState(str, enum.Enum):
    VOTING = "voting"
    CONCLUDED = "concluded"


class ReferendumOutcome(str, enum.Enum):
    YES = "yes"
    NO = "no"
    TIED = "tied"


@dataclasses.dataclass(frozen=True)
class Referendum:
    referendum_id: str
    organizer_id: str
    question: str
    voting_close_day: int
    state: ReferendumState
    outcome: t.Optional[ReferendumOutcome]
    yes_count: int
    no_count: int


@dataclasses.dataclass
class _RState:
    spec: Referendum
    constituency: set[str] = dataclasses.field(
        default_factory=set,
    )
    # voter_id -> bool (True = yes, False = no)
    ballots: dict[str, bool] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerReferendumSystem:
    _refs: dict[str, _RState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def propose(
        self, *, organizer_id: str, question: str,
        voting_close_day: int,
    ) -> t.Optional[str]:
        if not organizer_id or not question:
            return None
        if voting_close_day <= 0:
            return None
        rid = f"ref_{self._next}"
        self._next += 1
        self._refs[rid] = _RState(
            spec=Referendum(
                referendum_id=rid,
                organizer_id=organizer_id,
                question=question,
                voting_close_day=voting_close_day,
                state=ReferendumState.VOTING,
                outcome=None, yes_count=0,
                no_count=0,
            ),
        )
        return rid

    def enroll_constituent(
        self, *, referendum_id: str,
        organizer_id: str, voter_id: str,
        current_day: int,
    ) -> bool:
        if referendum_id not in self._refs:
            return False
        st = self._refs[referendum_id]
        if st.spec.organizer_id != organizer_id:
            return False
        if st.spec.state != ReferendumState.VOTING:
            return False
        if current_day >= st.spec.voting_close_day:
            return False
        if not voter_id:
            return False
        if voter_id in st.constituency:
            return False
        st.constituency.add(voter_id)
        return True

    def cast_yes_no(
        self, *, referendum_id: str, voter_id: str,
        vote_yes: bool, current_day: int,
    ) -> bool:
        if referendum_id not in self._refs:
            return False
        st = self._refs[referendum_id]
        if st.spec.state != ReferendumState.VOTING:
            return False
        if current_day >= st.spec.voting_close_day:
            return False
        if voter_id not in st.constituency:
            return False
        if voter_id in st.ballots:
            return False
        st.ballots[voter_id] = vote_yes
        return True

    def tally(
        self, *, referendum_id: str,
        current_day: int,
    ) -> t.Optional[ReferendumOutcome]:
        if referendum_id not in self._refs:
            return None
        st = self._refs[referendum_id]
        if st.spec.state != ReferendumState.VOTING:
            return None
        if current_day < st.spec.voting_close_day:
            return None
        yes = sum(1 for v in st.ballots.values() if v)
        no = sum(
            1 for v in st.ballots.values() if not v
        )
        if yes > no:
            outcome = ReferendumOutcome.YES
        elif no > yes:
            outcome = ReferendumOutcome.NO
        else:
            outcome = ReferendumOutcome.TIED
        st.spec = dataclasses.replace(
            st.spec, state=ReferendumState.CONCLUDED,
            outcome=outcome, yes_count=yes,
            no_count=no,
        )
        return outcome

    def referendum(
        self, *, referendum_id: str,
    ) -> t.Optional[Referendum]:
        st = self._refs.get(referendum_id)
        return st.spec if st else None

    def constituency(
        self, *, referendum_id: str,
    ) -> list[str]:
        st = self._refs.get(referendum_id)
        if st is None:
            return []
        return sorted(st.constituency)


__all__ = [
    "ReferendumState", "ReferendumOutcome",
    "Referendum", "PlayerReferendumSystem",
]
