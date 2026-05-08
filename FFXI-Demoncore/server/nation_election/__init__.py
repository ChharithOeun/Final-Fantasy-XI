"""Nation election — periodic governor selection.

When a nation_governor's term is approaching its end,
nation_election opens a CAMPAIGN. Candidates declare,
voters cast ballots, the winner is installed.

Lifecycle:
    DECLARED        election announced; candidates may
                    register
    CAMPAIGNING     campaign window open; no voting yet
    POLLING         polls are open; voters may cast
    CLOSED          polls closed, votes being tallied
    CERTIFIED       winner declared, election archived

Voting rules:
    - One vote per voter_id per election (the caller
      determines voter eligibility — citizenship,
      reputation min, etc.)
    - Re-voting is rejected at the data layer
    - A withdrawn candidate's votes are discarded
    - Ties: lowest candidate_id wins (deterministic)

Public surface
--------------
    ElectionState enum
    Candidate dataclass (frozen)
    Election dataclass (frozen)
    NationElectionSystem
        .declare(nation_id, term_days,
                 campaign_open_day, polls_open_day,
                 polls_close_day) -> Optional[str]
        .register_candidate(election_id, candidate_id,
                            platform) -> bool
        .withdraw_candidate(election_id,
                            candidate_id) -> bool
        .open_polls(election_id, now_day) -> bool
        .cast_vote(election_id, voter_id,
                   candidate_id, now_day) -> bool
        .close_polls(election_id, now_day) -> bool
        .certify(election_id, now_day) ->
                 Optional[str]  # winning candidate
        .tally(election_id) -> dict[str, int]
        .election(election_id) -> Optional[Election]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ElectionState(str, enum.Enum):
    DECLARED = "declared"
    CAMPAIGNING = "campaigning"
    POLLING = "polling"
    CLOSED = "closed"
    CERTIFIED = "certified"


@dataclasses.dataclass(frozen=True)
class Candidate:
    candidate_id: str
    platform: str
    withdrawn: bool


@dataclasses.dataclass(frozen=True)
class Election:
    election_id: str
    nation_id: str
    term_days: int
    campaign_open_day: int
    polls_open_day: int
    polls_close_day: int
    state: ElectionState
    winner_id: t.Optional[str]


@dataclasses.dataclass
class _ElState:
    spec: Election
    candidates: dict[str, Candidate] = dataclasses.field(
        default_factory=dict,
    )
    votes: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )  # voter_id -> candidate_id


@dataclasses.dataclass
class NationElectionSystem:
    _elections: dict[str, _ElState] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def declare(
        self, *, nation_id: str, term_days: int,
        campaign_open_day: int, polls_open_day: int,
        polls_close_day: int,
    ) -> t.Optional[str]:
        if not nation_id:
            return None
        if term_days <= 0:
            return None
        if (campaign_open_day < 0
                or polls_open_day < campaign_open_day
                or polls_close_day < polls_open_day):
            return None
        eid = f"elec_{self._next_id}"
        self._next_id += 1
        spec = Election(
            election_id=eid, nation_id=nation_id,
            term_days=term_days,
            campaign_open_day=campaign_open_day,
            polls_open_day=polls_open_day,
            polls_close_day=polls_close_day,
            state=ElectionState.DECLARED,
            winner_id=None,
        )
        self._elections[eid] = _ElState(spec=spec)
        return eid

    def register_candidate(
        self, *, election_id: str, candidate_id: str,
        platform: str,
    ) -> bool:
        if election_id not in self._elections:
            return False
        if not candidate_id:
            return False
        st = self._elections[election_id]
        if st.spec.state not in (
            ElectionState.DECLARED,
            ElectionState.CAMPAIGNING,
        ):
            return False
        if candidate_id in st.candidates:
            return False
        st.candidates[candidate_id] = Candidate(
            candidate_id=candidate_id,
            platform=platform, withdrawn=False,
        )
        if st.spec.state == ElectionState.DECLARED:
            st.spec = dataclasses.replace(
                st.spec,
                state=ElectionState.CAMPAIGNING,
            )
        return True

    def withdraw_candidate(
        self, *, election_id: str,
        candidate_id: str,
    ) -> bool:
        if election_id not in self._elections:
            return False
        st = self._elections[election_id]
        if candidate_id not in st.candidates:
            return False
        if st.spec.state == ElectionState.CERTIFIED:
            return False
        c = st.candidates[candidate_id]
        if c.withdrawn:
            return False
        st.candidates[candidate_id] = (
            dataclasses.replace(c, withdrawn=True)
        )
        return True

    def open_polls(
        self, *, election_id: str, now_day: int,
    ) -> bool:
        if election_id not in self._elections:
            return False
        st = self._elections[election_id]
        if st.spec.state != ElectionState.CAMPAIGNING:
            return False
        if now_day < st.spec.polls_open_day:
            return False
        # Need at least one non-withdrawn candidate
        active = [
            c for c in st.candidates.values()
            if not c.withdrawn
        ]
        if not active:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=ElectionState.POLLING,
        )
        return True

    def cast_vote(
        self, *, election_id: str, voter_id: str,
        candidate_id: str, now_day: int,
    ) -> bool:
        if election_id not in self._elections:
            return False
        if not voter_id:
            return False
        st = self._elections[election_id]
        if st.spec.state != ElectionState.POLLING:
            return False
        if now_day > st.spec.polls_close_day:
            return False
        if candidate_id not in st.candidates:
            return False
        if st.candidates[candidate_id].withdrawn:
            return False
        if voter_id in st.votes:
            return False
        st.votes[voter_id] = candidate_id
        return True

    def close_polls(
        self, *, election_id: str, now_day: int,
    ) -> bool:
        if election_id not in self._elections:
            return False
        st = self._elections[election_id]
        if st.spec.state != ElectionState.POLLING:
            return False
        if now_day < st.spec.polls_close_day:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=ElectionState.CLOSED,
        )
        return True

    def certify(
        self, *, election_id: str, now_day: int,
    ) -> t.Optional[str]:
        if election_id not in self._elections:
            return None
        st = self._elections[election_id]
        if st.spec.state != ElectionState.CLOSED:
            return None
        tally = self.tally(election_id=election_id)
        if not tally:
            return None
        # Highest votes wins; tie broken by lowest
        # candidate_id (deterministic).
        ranked = sorted(
            tally.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
        winner = ranked[0][0]
        st.spec = dataclasses.replace(
            st.spec, state=ElectionState.CERTIFIED,
            winner_id=winner,
        )
        return winner

    def tally(
        self, *, election_id: str,
    ) -> dict[str, int]:
        if election_id not in self._elections:
            return {}
        st = self._elections[election_id]
        out: dict[str, int] = {}
        for cid, c in st.candidates.items():
            if c.withdrawn:
                continue
            out[cid] = 0
        for v_cid in st.votes.values():
            if v_cid in out:
                out[v_cid] += 1
        return out

    def election(
        self, *, election_id: str,
    ) -> t.Optional[Election]:
        if election_id not in self._elections:
            return None
        return self._elections[election_id].spec


__all__ = [
    "ElectionState", "Candidate", "Election",
    "NationElectionSystem",
]
