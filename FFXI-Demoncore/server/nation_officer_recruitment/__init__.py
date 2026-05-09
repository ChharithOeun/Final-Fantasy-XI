"""Nation officer recruitment — bidding for free officers.

A FREE OFFICER (one not currently in any nation's
roster — wandering, retired, or freshly graduated from
the academy) can be courted by any nation. Multiple
nations may bid simultaneously; the recruitment closes
when the period ends, and the winning bid (highest gil
+ tie-broken by charisma of the recruiting envoy) gets
the officer.

A free officer has a per-recruitment minimum bid
(reflecting their famed prestige) and may decline
outright if the offered post is beneath them (caller
encodes the rule via min_offer_rank vs offer_rank;
this module just enforces min_bid).

Lifecycle:
    OPEN            recruitment window active
    CLOSED          window ended, winner determined
    CANCELLED       free officer withdrew before close

Public surface
--------------
    RecruitmentState enum
    Bid dataclass (frozen)
    Recruitment dataclass (frozen)
    NationOfficerRecruitmentSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RecruitmentState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclasses.dataclass(frozen=True)
class Bid:
    nation_id: str
    envoy_id: str
    envoy_charisma: int
    gil: int
    placed_day: int


@dataclasses.dataclass(frozen=True)
class Recruitment:
    recruitment_id: str
    free_officer_id: str
    min_bid_gil: int
    opened_day: int
    closes_day: int
    state: RecruitmentState
    winning_nation: str
    winning_gil: int


@dataclasses.dataclass
class _RState:
    spec: Recruitment
    bids: list[Bid] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class NationOfficerRecruitmentSystem:
    _records: dict[str, _RState] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def open(
        self, *, free_officer_id: str,
        min_bid_gil: int, opened_day: int,
        closes_day: int,
    ) -> t.Optional[str]:
        if not free_officer_id:
            return None
        if min_bid_gil < 0:
            return None
        if opened_day < 0:
            return None
        if closes_day <= opened_day:
            return None
        # Block duplicate-OPEN recruitment for same
        # free officer.
        for st in self._records.values():
            if (st.spec.free_officer_id
                    == free_officer_id
                    and st.spec.state
                    == RecruitmentState.OPEN):
                return None
        rid = f"rec_{self._next_id}"
        self._next_id += 1
        spec = Recruitment(
            recruitment_id=rid,
            free_officer_id=free_officer_id,
            min_bid_gil=min_bid_gil,
            opened_day=opened_day,
            closes_day=closes_day,
            state=RecruitmentState.OPEN,
            winning_nation="", winning_gil=0,
        )
        self._records[rid] = _RState(spec=spec)
        return rid

    def place_bid(
        self, *, recruitment_id: str,
        nation_id: str, envoy_id: str,
        envoy_charisma: int, gil: int,
        now_day: int,
    ) -> bool:
        if recruitment_id not in self._records:
            return False
        st = self._records[recruitment_id]
        if st.spec.state != RecruitmentState.OPEN:
            return False
        if not nation_id or not envoy_id:
            return False
        if (envoy_charisma < 1
                or envoy_charisma > 100):
            return False
        if gil < st.spec.min_bid_gil:
            return False
        if now_day < st.spec.opened_day:
            return False
        if now_day > st.spec.closes_day:
            return False
        # Each nation gets ONE active bid; later bids
        # supersede earlier ones — but only if higher.
        prev = next(
            (b for b in st.bids
             if b.nation_id == nation_id),
            None,
        )
        if prev is not None and gil <= prev.gil:
            return False
        if prev is not None:
            st.bids = [
                b for b in st.bids
                if b.nation_id != nation_id
            ]
        st.bids.append(Bid(
            nation_id=nation_id, envoy_id=envoy_id,
            envoy_charisma=envoy_charisma,
            gil=gil, placed_day=now_day,
        ))
        return True

    def close(
        self, *, recruitment_id: str, now_day: int,
    ) -> t.Optional[str]:
        if recruitment_id not in self._records:
            return None
        st = self._records[recruitment_id]
        if st.spec.state != RecruitmentState.OPEN:
            return None
        if now_day < st.spec.closes_day:
            return None
        if not st.bids:
            st.spec = dataclasses.replace(
                st.spec, state=RecruitmentState.CLOSED,
            )
            return None
        # Highest gil; tie -> highest envoy_charisma;
        # tie -> earliest placed_day.
        ranked = sorted(
            st.bids,
            key=lambda b: (
                -b.gil, -b.envoy_charisma,
                b.placed_day,
            ),
        )
        winner = ranked[0]
        st.spec = dataclasses.replace(
            st.spec, state=RecruitmentState.CLOSED,
            winning_nation=winner.nation_id,
            winning_gil=winner.gil,
        )
        return winner.nation_id

    def cancel(
        self, *, recruitment_id: str, now_day: int,
    ) -> bool:
        if recruitment_id not in self._records:
            return False
        st = self._records[recruitment_id]
        if st.spec.state != RecruitmentState.OPEN:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=RecruitmentState.CANCELLED,
        )
        return True

    def recruitment(
        self, *, recruitment_id: str,
    ) -> t.Optional[Recruitment]:
        if recruitment_id not in self._records:
            return None
        return self._records[recruitment_id].spec

    def bids_for(
        self, *, recruitment_id: str,
    ) -> list[Bid]:
        if recruitment_id not in self._records:
            return []
        return list(
            self._records[recruitment_id].bids,
        )

    def open_recruitments(self) -> list[Recruitment]:
        return [
            st.spec for st in self._records.values()
            if st.spec.state == RecruitmentState.OPEN
        ]


__all__ = [
    "RecruitmentState", "Bid", "Recruitment",
    "NationOfficerRecruitmentSystem",
]
