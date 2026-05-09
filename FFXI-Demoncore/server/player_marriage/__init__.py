"""Player marriage — formal pair-bonding with shared assets.

Two players propose, get engaged, marry on a chosen wedding
day, and remain married unless they divorce. Married pairs
have shared mog house access, optional shared inventory, and
an anniversary tracker that drives commemorative bonuses on
each year's wedding day. Divorce splits jointly accumulated
gil 50/50 and revokes shared access.

Lifecycle
    PROPOSED      one party proposed
    ENGAGED       proposal accepted, awaiting wedding day
    MARRIED       wedding day reached
    DIVORCED      assets split, access revoked

Public surface
--------------
    MarriageState enum
    Marriage dataclass (frozen)
    PlayerMarriageSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MarriageState(str, enum.Enum):
    PROPOSED = "proposed"
    ENGAGED = "engaged"
    MARRIED = "married"
    DIVORCED = "divorced"


@dataclasses.dataclass(frozen=True)
class Marriage:
    marriage_id: str
    proposer_id: str
    accepter_id: str
    state: MarriageState
    proposed_day: int
    engaged_day: int
    married_day: int
    wedding_day: int
    shared_inventory: bool
    shared_pool_gil: int
    divorced_day: int


@dataclasses.dataclass
class PlayerMarriageSystem:
    _marriages: dict[str, Marriage] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def propose(
        self, *, proposer_id: str, accepter_id: str,
        wedding_day: int, proposed_day: int,
    ) -> t.Optional[str]:
        if not proposer_id or not accepter_id:
            return None
        if proposer_id == accepter_id:
            return None
        if proposed_day < 0:
            return None
        if wedding_day <= proposed_day:
            return None
        # Block if either party is already in a non-
        # divorced marriage
        for m in self._marriages.values():
            if m.state == MarriageState.DIVORCED:
                continue
            if (
                proposer_id in (
                    m.proposer_id, m.accepter_id,
                )
                or accepter_id in (
                    m.proposer_id, m.accepter_id,
                )
            ):
                return None
        mid = f"marriage_{self._next}"
        self._next += 1
        self._marriages[mid] = Marriage(
            marriage_id=mid, proposer_id=proposer_id,
            accepter_id=accepter_id,
            state=MarriageState.PROPOSED,
            proposed_day=proposed_day,
            engaged_day=0, married_day=0,
            wedding_day=wedding_day,
            shared_inventory=False,
            shared_pool_gil=0, divorced_day=0,
        )
        return mid

    def accept(
        self, *, marriage_id: str, accepter_id: str,
        engaged_day: int,
    ) -> bool:
        if marriage_id not in self._marriages:
            return False
        m = self._marriages[marriage_id]
        if m.state != MarriageState.PROPOSED:
            return False
        if accepter_id != m.accepter_id:
            return False
        if engaged_day < m.proposed_day:
            return False
        self._marriages[marriage_id] = (
            dataclasses.replace(
                m, state=MarriageState.ENGAGED,
                engaged_day=engaged_day,
            )
        )
        return True

    def marry(
        self, *, marriage_id: str, current_day: int,
    ) -> bool:
        if marriage_id not in self._marriages:
            return False
        m = self._marriages[marriage_id]
        if m.state != MarriageState.ENGAGED:
            return False
        if current_day < m.wedding_day:
            return False
        self._marriages[marriage_id] = (
            dataclasses.replace(
                m, state=MarriageState.MARRIED,
                married_day=current_day,
            )
        )
        return True

    def enable_shared_inventory(
        self, *, marriage_id: str, party_id: str,
    ) -> bool:
        if marriage_id not in self._marriages:
            return False
        m = self._marriages[marriage_id]
        if m.state != MarriageState.MARRIED:
            return False
        if party_id not in (
            m.proposer_id, m.accepter_id,
        ):
            return False
        if m.shared_inventory:
            return False
        self._marriages[marriage_id] = (
            dataclasses.replace(
                m, shared_inventory=True,
            )
        )
        return True

    def deposit_pool(
        self, *, marriage_id: str, party_id: str,
        amount_gil: int,
    ) -> bool:
        if marriage_id not in self._marriages:
            return False
        m = self._marriages[marriage_id]
        if m.state != MarriageState.MARRIED:
            return False
        if party_id not in (
            m.proposer_id, m.accepter_id,
        ):
            return False
        if amount_gil <= 0:
            return False
        self._marriages[marriage_id] = (
            dataclasses.replace(
                m, shared_pool_gil=(
                    m.shared_pool_gil + amount_gil
                ),
            )
        )
        return True

    def divorce(
        self, *, marriage_id: str, filer_id: str,
        current_day: int,
    ) -> t.Optional[tuple[int, int]]:
        """Returns (proposer_share, accepter_share)
        from shared pool — split 50/50 with any
        odd remainder going to filer.
        """
        if marriage_id not in self._marriages:
            return None
        m = self._marriages[marriage_id]
        if m.state != MarriageState.MARRIED:
            return None
        if filer_id not in (
            m.proposer_id, m.accepter_id,
        ):
            return None
        half = m.shared_pool_gil // 2
        remainder = m.shared_pool_gil - half * 2
        if filer_id == m.proposer_id:
            proposer_share = half + remainder
            accepter_share = half
        else:
            proposer_share = half
            accepter_share = half + remainder
        self._marriages[marriage_id] = (
            dataclasses.replace(
                m, state=MarriageState.DIVORCED,
                shared_inventory=False,
                shared_pool_gil=0,
                divorced_day=current_day,
            )
        )
        return proposer_share, accepter_share

    def years_married(
        self, *, marriage_id: str, current_day: int,
        days_per_year: int = 365,
    ) -> int:
        if marriage_id not in self._marriages:
            return 0
        m = self._marriages[marriage_id]
        if m.state != MarriageState.MARRIED:
            return 0
        elapsed = current_day - m.married_day
        return max(0, elapsed) // days_per_year

    def is_married(
        self, *, player_id: str,
    ) -> bool:
        for m in self._marriages.values():
            if (
                m.state == MarriageState.MARRIED
                and player_id in (
                    m.proposer_id, m.accepter_id,
                )
            ):
                return True
        return False

    def marriage(
        self, *, marriage_id: str,
    ) -> t.Optional[Marriage]:
        return self._marriages.get(marriage_id)


__all__ = [
    "MarriageState", "Marriage",
    "PlayerMarriageSystem",
]
