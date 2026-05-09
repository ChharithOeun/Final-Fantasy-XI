"""Player concert hall — book a venue, sell tickets, perform.

Bards (and any other player) can rent a concert hall slot,
sell tickets to passersby, and perform a set list. Performance
score is deterministic from performer_skill + set_size + venue
prestige + variance. Ticket revenue and stage fame are paid
out at PERFORMED. Cancelations refund tickets at half value.

Lifecycle
    BOOKED       slot reserved, no tickets yet
    ON_SALE      tickets selling
    PERFORMED    show happened, payouts settled
    CANCELED     show pulled, tickets refunded

Public surface
--------------
    ConcertState enum
    Hall dataclass (frozen)
    Ticket dataclass (frozen)
    Concert dataclass (frozen)
    PlayerConcertHallSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_REFUND_PCT = 50  # half-refund on cancellation


class ConcertState(str, enum.Enum):
    BOOKED = "booked"
    ON_SALE = "on_sale"
    PERFORMED = "performed"
    CANCELED = "canceled"


@dataclasses.dataclass(frozen=True)
class Hall:
    hall_id: str
    name: str
    capacity: int
    prestige: int  # 1..100, multiplies ticket price


@dataclasses.dataclass(frozen=True)
class Ticket:
    ticket_id: str
    concert_id: str
    buyer_id: str
    price_paid_gil: int


@dataclasses.dataclass(frozen=True)
class Concert:
    concert_id: str
    hall_id: str
    performer_id: str
    performer_skill: int
    setlist_size: int
    ticket_price_gil: int
    scheduled_day: int
    state: ConcertState
    tickets_sold: int
    revenue_gil: int
    performance_score: int
    fame_earned: int


@dataclasses.dataclass
class _CState:
    spec: Concert
    tickets: dict[str, Ticket] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerConcertHallSystem:
    _halls: dict[str, Hall] = dataclasses.field(
        default_factory=dict,
    )
    _concerts: dict[str, _CState] = dataclasses.field(
        default_factory=dict,
    )
    _next_concert: int = 1
    _next_ticket: int = 1

    def register_hall(
        self, *, hall_id: str, name: str,
        capacity: int, prestige: int,
    ) -> bool:
        if not hall_id or not name:
            return False
        if hall_id in self._halls:
            return False
        if capacity <= 0 or capacity > 5000:
            return False
        if not 1 <= prestige <= 100:
            return False
        self._halls[hall_id] = Hall(
            hall_id=hall_id, name=name,
            capacity=capacity, prestige=prestige,
        )
        return True

    def book_concert(
        self, *, hall_id: str, performer_id: str,
        performer_skill: int, setlist_size: int,
        ticket_price_gil: int, scheduled_day: int,
    ) -> t.Optional[str]:
        if hall_id not in self._halls:
            return None
        if not performer_id:
            return None
        if not 1 <= performer_skill <= 100:
            return None
        if setlist_size < 1 or setlist_size > 30:
            return None
        if ticket_price_gil <= 0:
            return None
        if scheduled_day < 0:
            return None
        # No double-booking same hall same day
        for st in self._concerts.values():
            sp = st.spec
            if (sp.hall_id == hall_id
                    and sp.scheduled_day == scheduled_day
                    and sp.state in (
                        ConcertState.BOOKED,
                        ConcertState.ON_SALE,
                    )):
                return None
        cid = f"concert_{self._next_concert}"
        self._next_concert += 1
        spec = Concert(
            concert_id=cid, hall_id=hall_id,
            performer_id=performer_id,
            performer_skill=performer_skill,
            setlist_size=setlist_size,
            ticket_price_gil=ticket_price_gil,
            scheduled_day=scheduled_day,
            state=ConcertState.BOOKED,
            tickets_sold=0, revenue_gil=0,
            performance_score=0, fame_earned=0,
        )
        self._concerts[cid] = _CState(spec=spec)
        return cid

    def open_sales(self, *, concert_id: str) -> bool:
        if concert_id not in self._concerts:
            return False
        st = self._concerts[concert_id]
        if st.spec.state != ConcertState.BOOKED:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=ConcertState.ON_SALE,
        )
        return True

    def buy_ticket(
        self, *, concert_id: str, buyer_id: str,
    ) -> t.Optional[str]:
        if concert_id not in self._concerts:
            return None
        st = self._concerts[concert_id]
        if st.spec.state != ConcertState.ON_SALE:
            return None
        if not buyer_id or buyer_id == st.spec.performer_id:
            return None
        hall = self._halls[st.spec.hall_id]
        if st.spec.tickets_sold >= hall.capacity:
            return None
        # Repeat buyers allowed (different ticket each).
        tid = f"ticket_{self._next_ticket}"
        self._next_ticket += 1
        st.tickets[tid] = Ticket(
            ticket_id=tid, concert_id=concert_id,
            buyer_id=buyer_id,
            price_paid_gil=st.spec.ticket_price_gil,
        )
        st.spec = dataclasses.replace(
            st.spec,
            tickets_sold=st.spec.tickets_sold + 1,
            revenue_gil=(
                st.spec.revenue_gil
                + st.spec.ticket_price_gil
            ),
        )
        return tid

    def perform(
        self, *, concert_id: str, seed: int,
    ) -> t.Optional[int]:
        if concert_id not in self._concerts:
            return None
        st = self._concerts[concert_id]
        if st.spec.state != ConcertState.ON_SALE:
            return None
        hall = self._halls[st.spec.hall_id]
        variance = (seed % 21) - 10  # -10..+10
        score = (
            st.spec.performer_skill
            + st.spec.setlist_size * 3
            + hall.prestige // 2
            + variance
        )
        score = max(0, score)
        # Fame scales with score and audience.
        fame = (
            score
            * st.spec.tickets_sold
            // max(1, hall.capacity)
        )
        st.spec = dataclasses.replace(
            st.spec, state=ConcertState.PERFORMED,
            performance_score=score, fame_earned=fame,
        )
        return score

    def cancel(
        self, *, concert_id: str,
    ) -> t.Optional[int]:
        if concert_id not in self._concerts:
            return None
        st = self._concerts[concert_id]
        if st.spec.state not in (
            ConcertState.BOOKED, ConcertState.ON_SALE,
        ):
            return None
        refund_total = (
            st.spec.revenue_gil * _REFUND_PCT // 100
        )
        st.spec = dataclasses.replace(
            st.spec, state=ConcertState.CANCELED,
        )
        return refund_total

    def concert(
        self, *, concert_id: str,
    ) -> t.Optional[Concert]:
        st = self._concerts.get(concert_id)
        return st.spec if st else None

    def hall(
        self, *, hall_id: str,
    ) -> t.Optional[Hall]:
        return self._halls.get(hall_id)

    def tickets(
        self, *, concert_id: str,
    ) -> list[Ticket]:
        st = self._concerts.get(concert_id)
        if st is None:
            return []
        return list(st.tickets.values())


__all__ = [
    "ConcertState", "Hall", "Ticket", "Concert",
    "PlayerConcertHallSystem",
]
