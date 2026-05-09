"""Player apprentice — formal mentor/apprentice bonds.

Players who teach earn rep. Players who learn earn
faster. This module formalizes the BOND: a senior
player swears as MENTOR, a junior as APPRENTICE; both
grant explicit consent. While bonded, mentor receives
TEACHING_REP and the apprentice receives an XP_BONUS
multiplier (caller-applied).

Bonds end one of three ways:
    GRADUATED   apprentice hits a level threshold;
                both parties get a final reward
    DISSOLVED   either party amicably ends; lesser
                rewards
    ABANDONED   the apprentice goes silent for too
                long; mentor takes a small rep hit

Public surface
--------------
    BondState enum
    EndReason enum
    ApprenticeBond dataclass (frozen)
    PlayerApprenticeSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_GRADUATION_REP = 200
_DISSOLVED_REP = 50
_ABANDONED_REP_PENALTY = -25


class BondState(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    GRADUATED = "graduated"
    DISSOLVED = "dissolved"
    ABANDONED = "abandoned"


class EndReason(str, enum.Enum):
    LEVEL_THRESHOLD = "level_threshold"
    MUTUAL_AGREEMENT = "mutual_agreement"
    MENTOR_RELEASED = "mentor_released"
    APPRENTICE_RELEASED = "apprentice_released"
    INACTIVITY = "inactivity"


@dataclasses.dataclass(frozen=True)
class ApprenticeBond:
    bond_id: str
    mentor_id: str
    apprentice_id: str
    proposed_day: int
    accepted_day: t.Optional[int]
    ended_day: t.Optional[int]
    end_reason: t.Optional[EndReason]
    state: BondState
    mentor_rep_delta: int


@dataclasses.dataclass
class PlayerApprenticeSystem:
    _bonds: dict[str, ApprenticeBond] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def propose(
        self, *, mentor_id: str,
        apprentice_id: str, proposed_day: int,
    ) -> t.Optional[str]:
        if not mentor_id or not apprentice_id:
            return None
        if mentor_id == apprentice_id:
            return None
        if proposed_day < 0:
            return None
        # Block parallel active/proposed bond for
        # the same apprentice (one mentor at a time)
        for b in self._bonds.values():
            if b.apprentice_id == apprentice_id:
                if b.state in (
                    BondState.PROPOSED,
                    BondState.ACTIVE,
                ):
                    return None
        bid = f"appr_{self._next_id}"
        self._next_id += 1
        self._bonds[bid] = ApprenticeBond(
            bond_id=bid, mentor_id=mentor_id,
            apprentice_id=apprentice_id,
            proposed_day=proposed_day,
            accepted_day=None, ended_day=None,
            end_reason=None,
            state=BondState.PROPOSED,
            mentor_rep_delta=0,
        )
        return bid

    def accept(
        self, *, bond_id: str, now_day: int,
    ) -> bool:
        if bond_id not in self._bonds:
            return False
        b = self._bonds[bond_id]
        if b.state != BondState.PROPOSED:
            return False
        if now_day < b.proposed_day:
            return False
        self._bonds[bond_id] = dataclasses.replace(
            b, state=BondState.ACTIVE,
            accepted_day=now_day,
        )
        return True

    def graduate(
        self, *, bond_id: str, now_day: int,
    ) -> bool:
        if bond_id not in self._bonds:
            return False
        b = self._bonds[bond_id]
        if b.state != BondState.ACTIVE:
            return False
        self._bonds[bond_id] = dataclasses.replace(
            b, state=BondState.GRADUATED,
            ended_day=now_day,
            end_reason=EndReason.LEVEL_THRESHOLD,
            mentor_rep_delta=_GRADUATION_REP,
        )
        return True

    def dissolve(
        self, *, bond_id: str, now_day: int,
        reason: EndReason,
    ) -> bool:
        if bond_id not in self._bonds:
            return False
        if reason not in (
            EndReason.MUTUAL_AGREEMENT,
            EndReason.MENTOR_RELEASED,
            EndReason.APPRENTICE_RELEASED,
        ):
            return False
        b = self._bonds[bond_id]
        if b.state not in (
            BondState.PROPOSED,
            BondState.ACTIVE,
        ):
            return False
        delta = (
            _DISSOLVED_REP
            if (b.state == BondState.ACTIVE
                and reason
                == EndReason.MUTUAL_AGREEMENT)
            else 0
        )
        self._bonds[bond_id] = dataclasses.replace(
            b, state=BondState.DISSOLVED,
            ended_day=now_day, end_reason=reason,
            mentor_rep_delta=delta,
        )
        return True

    def abandon(
        self, *, bond_id: str, now_day: int,
    ) -> bool:
        if bond_id not in self._bonds:
            return False
        b = self._bonds[bond_id]
        if b.state != BondState.ACTIVE:
            return False
        self._bonds[bond_id] = dataclasses.replace(
            b, state=BondState.ABANDONED,
            ended_day=now_day,
            end_reason=EndReason.INACTIVITY,
            mentor_rep_delta=_ABANDONED_REP_PENALTY,
        )
        return True

    def active_bond_for_apprentice(
        self, *, apprentice_id: str,
    ) -> t.Optional[ApprenticeBond]:
        for b in self._bonds.values():
            if (b.apprentice_id == apprentice_id
                    and b.state == BondState.ACTIVE):
                return b
        return None

    def bonds_for_mentor(
        self, *, mentor_id: str,
    ) -> list[ApprenticeBond]:
        return [
            b for b in self._bonds.values()
            if b.mentor_id == mentor_id
        ]

    def total_mentor_rep(
        self, *, mentor_id: str,
    ) -> int:
        return sum(
            b.mentor_rep_delta
            for b in self._bonds.values()
            if b.mentor_id == mentor_id
        )

    def bond(
        self, *, bond_id: str,
    ) -> t.Optional[ApprenticeBond]:
        return self._bonds.get(bond_id)


__all__ = [
    "BondState", "EndReason", "ApprenticeBond",
    "PlayerApprenticeSystem",
]
