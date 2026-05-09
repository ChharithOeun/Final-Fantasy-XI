"""Player election — multi-candidate vote with eligible roll.

An organizer announces an election for a named position with
two day-thresholds: registration_close_day (after which no
new candidates) and voting_close_day (after which tally can
fire). The organizer enrolls eligible voters; candidates
self-register during the registration phase. Voters cast a
single ballot during the voting phase. tally returns the
winning candidate; ties resolve by registration order
(earlier candidates beat later ones).

Lifecycle
    REGISTRATION   accepting candidates & voter enrollment
    VOTING         registration closed; ballots accepted
    CONCLUDED      tally complete; winner recorded

Public surface
--------------
    ElectionState enum
    Election dataclass (frozen)
    PlayerElectionSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ElectionState(str, enum.Enum):
    REGISTRATION = "registration"
    VOTING = "voting"
    CONCLUDED = "concluded"


@dataclasses.dataclass(frozen=True)
class Election:
    election_id: str
    organizer_id: str
    position_title: str
    registration_close_day: int
    voting_close_day: int
    state: ElectionState
    winner_id: str


@dataclasses.dataclass
class _EState:
    spec: Election
    candidates: list[str] = dataclasses.field(
        default_factory=list,
    )
    voters: set[str] = dataclasses.field(
        default_factory=set,
    )
    # voter_id -> candidate_id
    ballots: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerElectionSystem:
    _elections: dict[str, _EState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def _advance(
        self, st: _EState, current_day: int,
    ) -> None:
        """Lazy state advance; never goes back."""
        spec = st.spec
        if (
            spec.state == ElectionState.REGISTRATION
            and current_day >= spec.registration_close_day
        ):
            st.spec = dataclasses.replace(
                spec, state=ElectionState.VOTING,
            )

    def announce(
        self, *, organizer_id: str, position_title: str,
        registration_close_day: int,
        voting_close_day: int,
    ) -> t.Optional[str]:
        if not organizer_id or not position_title:
            return None
        if registration_close_day <= 0:
            return None
        if voting_close_day <= registration_close_day:
            return None
        eid = f"elect_{self._next}"
        self._next += 1
        self._elections[eid] = _EState(
            spec=Election(
                election_id=eid,
                organizer_id=organizer_id,
                position_title=position_title,
                registration_close_day=(
                    registration_close_day
                ),
                voting_close_day=voting_close_day,
                state=ElectionState.REGISTRATION,
                winner_id="",
            ),
        )
        return eid

    def register_candidate(
        self, *, election_id: str, candidate_id: str,
        current_day: int,
    ) -> bool:
        if election_id not in self._elections:
            return False
        st = self._elections[election_id]
        self._advance(st, current_day)
        if st.spec.state != ElectionState.REGISTRATION:
            return False
        if not candidate_id:
            return False
        if candidate_id in st.candidates:
            return False
        st.candidates.append(candidate_id)
        return True

    def enroll_voter(
        self, *, election_id: str, organizer_id: str,
        voter_id: str, current_day: int,
    ) -> bool:
        if election_id not in self._elections:
            return False
        st = self._elections[election_id]
        if st.spec.organizer_id != organizer_id:
            return False
        self._advance(st, current_day)
        if st.spec.state == ElectionState.CONCLUDED:
            return False
        if not voter_id:
            return False
        if voter_id in st.voters:
            return False
        st.voters.add(voter_id)
        return True

    def cast_ballot(
        self, *, election_id: str, voter_id: str,
        candidate_id: str, current_day: int,
    ) -> bool:
        if election_id not in self._elections:
            return False
        st = self._elections[election_id]
        self._advance(st, current_day)
        if st.spec.state != ElectionState.VOTING:
            return False
        if current_day >= st.spec.voting_close_day:
            return False
        if voter_id not in st.voters:
            return False
        if candidate_id not in st.candidates:
            return False
        if voter_id in st.ballots:
            return False
        st.ballots[voter_id] = candidate_id
        return True

    def tally(
        self, *, election_id: str, current_day: int,
    ) -> t.Optional[str]:
        if election_id not in self._elections:
            return None
        st = self._elections[election_id]
        if current_day < st.spec.voting_close_day:
            return None
        if st.spec.state == ElectionState.CONCLUDED:
            return None
        if not st.ballots:
            return None
        counts: dict[str, int] = {}
        for cand in st.ballots.values():
            counts[cand] = counts.get(cand, 0) + 1
        # Tie-break: earlier candidate wins
        max_votes = max(counts.values())
        for cand in st.candidates:
            if counts.get(cand, 0) == max_votes:
                winner = cand
                break
        st.spec = dataclasses.replace(
            st.spec, state=ElectionState.CONCLUDED,
            winner_id=winner,
        )
        return winner

    def election(
        self, *, election_id: str,
    ) -> t.Optional[Election]:
        st = self._elections.get(election_id)
        return st.spec if st else None

    def candidates(
        self, *, election_id: str,
    ) -> list[str]:
        st = self._elections.get(election_id)
        if st is None:
            return []
        return list(st.candidates)

    def voters(
        self, *, election_id: str,
    ) -> list[str]:
        st = self._elections.get(election_id)
        if st is None:
            return []
        return sorted(st.voters)

    def vote_count(
        self, *, election_id: str, candidate_id: str,
    ) -> int:
        st = self._elections.get(election_id)
        if st is None:
            return 0
        return sum(
            1 for c in st.ballots.values()
            if c == candidate_id
        )


__all__ = [
    "ElectionState", "Election",
    "PlayerElectionSystem",
]
