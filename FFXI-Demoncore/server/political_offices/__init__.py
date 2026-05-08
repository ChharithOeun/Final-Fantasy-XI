"""Political offices — elected positions per nation.

Each nation (Bastok, San d'Oria, Windurst, Norg, Tavnazia)
has a set of political offices held by NPCs OR PLAYERS.
This module is the registry: which offices exist per
nation, who currently holds them, and the election cycle
that rotates the seat.

Offices we model:
    PRESIDENT       single executive (Bastok)
    KING            single hereditary executive (Sandy)
    STAR_SIBYL      religious-political leader (Windy)
    PIRATE_KING     elective with combat trial (Norg)
    GUARDIAN        appointed defender (Tavnazia)
    SENATOR         legislative seat (multiple per nation,
                    typically 5 per nation)
    GENERAL         military commander
    ADJUDICATOR     judicial seat — handles outlaw rulings

Election cycles vary by office:
    PRESIDENT/SENATOR: 90 game-days, popular vote
    KING: hereditary (no election; succession on death)
    STAR_SIBYL: lifetime (no election)
    PIRATE_KING: combat-trial-triggered
    GENERAL: appointed by the executive (PRESIDENT/KING/etc)
    ADJUDICATOR: appointed by the legislature (SENATORS)

We model the ELECTION as a discrete event:
    open_election(office_id, candidates, voting_window_days)
    cast_vote(voter, office_id, candidate)
    close_election(office_id) -> winner_id

The module enforces:
    - No double votes per voter per election
    - Only voters from the office's nation can vote
    - The CURRENT holder of an office is recorded; close()
      transfers the seat to the winner

Public surface
--------------
    OfficeKind enum
    Office dataclass (frozen)
    ElectionResult dataclass (frozen)
    PoliticalOffices
        .register_office(office) -> bool
        .install_holder(office_id, holder_id) -> bool
        .open_election(office_id, candidates, deadline_day)
            -> bool
        .cast_vote(voter, voter_nation, office_id,
                   candidate) -> bool
        .close_election(office_id, now_day)
            -> Optional[ElectionResult]
        .holder(office_id) -> Optional[str]
        .offices_in_nation(nation) -> list[Office]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class OfficeKind(str, enum.Enum):
    PRESIDENT = "president"
    KING = "king"
    STAR_SIBYL = "star_sibyl"
    PIRATE_KING = "pirate_king"
    GUARDIAN = "guardian"
    SENATOR = "senator"
    GENERAL = "general"
    ADJUDICATOR = "adjudicator"


@dataclasses.dataclass(frozen=True)
class Office:
    office_id: str
    nation: str
    kind: OfficeKind
    title: str  # display name like "Senator from Bastok"
    is_elected: bool


@dataclasses.dataclass(frozen=True)
class ElectionResult:
    office_id: str
    winner_id: str
    vote_counts: tuple[tuple[str, int], ...]
    total_votes: int


@dataclasses.dataclass
class _OfficeState:
    spec: Office
    holder: t.Optional[str] = None
    election_open: bool = False
    election_deadline_day: int = 0
    candidates: list[str] = dataclasses.field(default_factory=list)
    votes: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class PoliticalOffices:
    _offices: dict[str, _OfficeState] = dataclasses.field(
        default_factory=dict,
    )

    def register_office(self, office: Office) -> bool:
        if not office.office_id or not office.nation:
            return False
        if not office.title:
            return False
        if office.office_id in self._offices:
            return False
        self._offices[office.office_id] = _OfficeState(
            spec=office,
        )
        return True

    def install_holder(
        self, *, office_id: str, holder_id: str,
    ) -> bool:
        if not holder_id:
            return False
        if office_id not in self._offices:
            return False
        st = self._offices[office_id]
        if st.election_open:
            return False
        st.holder = holder_id
        return True

    def open_election(
        self, *, office_id: str,
        candidates: t.Sequence[str], deadline_day: int,
    ) -> bool:
        if office_id not in self._offices:
            return False
        st = self._offices[office_id]
        if not st.spec.is_elected:
            return False
        if st.election_open:
            return False
        if len(candidates) < 2:
            return False
        if deadline_day <= 0:
            return False
        if len(set(candidates)) != len(candidates):
            return False
        st.election_open = True
        st.election_deadline_day = deadline_day
        st.candidates = list(candidates)
        st.votes = {}
        return True

    def cast_vote(
        self, *, voter_id: str, voter_nation: str,
        office_id: str, candidate: str,
    ) -> bool:
        if not voter_id or not voter_nation:
            return False
        if office_id not in self._offices:
            return False
        st = self._offices[office_id]
        if not st.election_open:
            return False
        if voter_nation != st.spec.nation:
            return False
        if candidate not in st.candidates:
            return False
        if voter_id in st.votes:
            return False
        st.votes[voter_id] = candidate
        return True

    def close_election(
        self, *, office_id: str, now_day: int,
    ) -> t.Optional[ElectionResult]:
        if office_id not in self._offices:
            return None
        st = self._offices[office_id]
        if not st.election_open:
            return None
        if now_day < st.election_deadline_day:
            return None
        # Tally
        counts: dict[str, int] = {
            c: 0 for c in st.candidates
        }
        for cand in st.votes.values():
            counts[cand] += 1
        if not counts:
            return None
        sorted_counts = sorted(
            counts.items(), key=lambda p: -p[1],
        )
        winner = sorted_counts[0][0]
        result = ElectionResult(
            office_id=office_id,
            winner_id=winner,
            vote_counts=tuple(sorted_counts),
            total_votes=len(st.votes),
        )
        st.holder = winner
        st.election_open = False
        st.candidates = []
        st.votes = {}
        return result

    def holder(
        self, *, office_id: str,
    ) -> t.Optional[str]:
        if office_id not in self._offices:
            return None
        return self._offices[office_id].holder

    def offices_in_nation(
        self, *, nation: str,
    ) -> list[Office]:
        return sorted(
            (st.spec for st in self._offices.values()
             if st.spec.nation == nation),
            key=lambda o: o.office_id,
        )

    def is_election_open(
        self, *, office_id: str,
    ) -> bool:
        if office_id not in self._offices:
            return False
        return self._offices[office_id].election_open


__all__ = [
    "OfficeKind", "Office", "ElectionResult",
    "PoliticalOffices",
]
