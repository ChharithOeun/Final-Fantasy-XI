"""Commission board — player-to-player crafting orders.

A buyer who can't craft posts a COMMISSION on the board:
"I want a HQ3 Pellucid Sword. Pay 80,000 gil up front,
60% deposit refundable if you can't deliver in 7 days."
A crafter accepts; the deposit is held in escrow. They
deliver via delivery_box; the buyer claim_delivery()s
and the gil is released.

State machine:
    OPEN              listed; waiting for crafter
    ACCEPTED          a crafter committed; deposit held
    DELIVERED         crafter shipped; awaiting claim
    COMPLETED         buyer claimed; payment released
    CANCELED          buyer canceled before acceptance
                      (full refund) or both agreed to
                      cancel (per-side fees)
    EXPIRED           crafter didn't deliver in time;
                      deposit forfeit (60% refund to
                      buyer, 40% to crafter as
                      cancelation fee)

Public surface
--------------
    State enum
    Commission dataclass (frozen)
    CommissionBoard
        .post(commission, refundable_pct, deposit_gil)
            -> bool
        .accept(commission_id, crafter_id, now_day) -> bool
        .deliver(commission_id, item_id, now_day) -> bool
        .claim_delivery(commission_id, by_buyer_id) -> int
            (returns gil paid to crafter)
        .cancel_open(commission_id, by_buyer_id) -> int
            (returns refunded gil)
        .tick(now_day) -> list[str]   # ids that expired
        .state(commission_id) -> Optional[State]
        .open_listings() -> list[Commission]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class State(str, enum.Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELED = "canceled"
    EXPIRED = "expired"


@dataclasses.dataclass(frozen=True)
class Commission:
    commission_id: str
    buyer_id: str
    template_id: str
    desired_tier: str  # "hq3", "masterwork", etc.
    payment_gil: int
    deposit_gil: int
    refundable_pct: int  # 0..100; refunded if no delivery
    posted_day: int
    deliver_by_day: int


@dataclasses.dataclass
class _CState:
    spec: Commission
    state: State = State.OPEN
    crafter_id: t.Optional[str] = None
    delivered_item_id: t.Optional[str] = None


@dataclasses.dataclass
class CommissionBoard:
    _commissions: dict[str, _CState] = dataclasses.field(
        default_factory=dict,
    )

    def post(
        self, commission: Commission,
    ) -> bool:
        if not commission.commission_id:
            return False
        if not commission.buyer_id:
            return False
        if commission.payment_gil <= 0:
            return False
        if commission.deposit_gil < 0:
            return False
        if commission.deposit_gil > commission.payment_gil:
            return False
        if (commission.refundable_pct < 0
                or commission.refundable_pct > 100):
            return False
        if commission.deliver_by_day <= commission.posted_day:
            return False
        if commission.commission_id in self._commissions:
            return False
        self._commissions[commission.commission_id] = _CState(
            spec=commission,
        )
        return True

    def accept(
        self, *, commission_id: str, crafter_id: str,
        now_day: int,
    ) -> bool:
        if not crafter_id:
            return False
        if commission_id not in self._commissions:
            return False
        st = self._commissions[commission_id]
        if st.state != State.OPEN:
            return False
        if crafter_id == st.spec.buyer_id:
            return False
        if now_day >= st.spec.deliver_by_day:
            return False
        st.crafter_id = crafter_id
        st.state = State.ACCEPTED
        return True

    def deliver(
        self, *, commission_id: str, by_crafter_id: str,
        item_id: str, now_day: int,
    ) -> bool:
        if commission_id not in self._commissions:
            return False
        st = self._commissions[commission_id]
        if st.state != State.ACCEPTED:
            return False
        if st.crafter_id != by_crafter_id:
            return False
        if not item_id:
            return False
        if now_day >= st.spec.deliver_by_day:
            return False
        st.delivered_item_id = item_id
        st.state = State.DELIVERED
        return True

    def claim_delivery(
        self, *, commission_id: str, by_buyer_id: str,
    ) -> t.Optional[int]:
        if commission_id not in self._commissions:
            return None
        st = self._commissions[commission_id]
        if st.state != State.DELIVERED:
            return None
        if by_buyer_id != st.spec.buyer_id:
            return None
        st.state = State.COMPLETED
        return st.spec.payment_gil

    def cancel_open(
        self, *, commission_id: str, by_buyer_id: str,
    ) -> t.Optional[int]:
        if commission_id not in self._commissions:
            return None
        st = self._commissions[commission_id]
        if st.state != State.OPEN:
            return None
        if by_buyer_id != st.spec.buyer_id:
            return None
        st.state = State.CANCELED
        # Full refund — no crafter has committed yet
        return st.spec.payment_gil

    def tick(self, *, now_day: int) -> list[str]:
        expired_ids: list[str] = []
        for cid, st in self._commissions.items():
            if st.state in (State.OPEN, State.ACCEPTED):
                if now_day >= st.spec.deliver_by_day:
                    st.state = State.EXPIRED
                    expired_ids.append(cid)
        return expired_ids

    def state(
        self, *, commission_id: str,
    ) -> t.Optional[State]:
        if commission_id not in self._commissions:
            return None
        return self._commissions[commission_id].state

    def open_listings(self) -> list[Commission]:
        return sorted(
            (st.spec for st in self._commissions.values()
             if st.state == State.OPEN),
            key=lambda c: c.commission_id,
        )

    def expired_refund(
        self, *, commission_id: str,
    ) -> t.Optional[tuple[int, int]]:
        """For an EXPIRED commission, returns
        (buyer_refund, crafter_kept) gil split."""
        if commission_id not in self._commissions:
            return None
        st = self._commissions[commission_id]
        if st.state != State.EXPIRED:
            return None
        pay = st.spec.payment_gil
        refund = pay * st.spec.refundable_pct // 100
        kept = pay - refund
        return (refund, kept)


__all__ = ["State", "Commission", "CommissionBoard"]
