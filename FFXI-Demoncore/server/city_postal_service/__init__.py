"""City postal service — inter-city mail relay.

The delivery_box module already handles instant
player-to-player mail. The CITY POSTAL SERVICE adds a
canonical, in-world layer on top: official mail moves
between CITIES through real POST OFFICES, with delivery
delays that depend on route distance, weight, and
postage paid.

A POST OFFICE per city accepts inbound mail and queues
outgoing mail. Posted parcels travel along established
ROUTES (chains of intermediate cities). A parcel's
expected delivery is sum_of_route_legs(days) +/- weather
penalty.

In addition, the service supports REGISTERED MAIL —
guaranteed-or-refund — at higher postage cost. Lost mail
(if any leg's caravan is ambushed) shows up as LOST
state.

Public surface
--------------
    ParcelClass enum (LETTER / PARCEL / FREIGHT /
                      REGISTERED)
    ParcelState enum (POSTED / IN_TRANSIT / DELIVERED /
                      LOST / REFUNDED)
    PostalRoute dataclass (frozen)
    Parcel dataclass (frozen)
    CityPostalService
        .open_office(city) -> bool
        .add_route(from_city, to_city,
                   transit_days) -> bool
        .post_parcel(from_city, to_city, sender,
                     recipient, weight, parcel_class,
                     postage_paid, posted_day) ->
                     Optional[str]
        .tick(now_day) -> list[(parcel_id, ParcelState)]
        .mark_lost(parcel_id, leg_at_city) -> bool
        .refund(parcel_id) -> int  # gil refunded
        .parcel(parcel_id) -> Optional[Parcel]
        .inbox(city) -> list[Parcel]
        .outbox(city) -> list[Parcel]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_REQUIRED_POSTAGE = {
    "letter": 50,
    "parcel": 200,
    "freight": 1_000,
    "registered": 5_000,
}


class ParcelClass(str, enum.Enum):
    LETTER = "letter"
    PARCEL = "parcel"
    FREIGHT = "freight"
    REGISTERED = "registered"


class ParcelState(str, enum.Enum):
    POSTED = "posted"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    LOST = "lost"
    REFUNDED = "refunded"


@dataclasses.dataclass(frozen=True)
class PostalRoute:
    from_city: str
    to_city: str
    transit_days: int


@dataclasses.dataclass(frozen=True)
class Parcel:
    parcel_id: str
    from_city: str
    to_city: str
    sender: str
    recipient: str
    weight: int
    parcel_class: ParcelClass
    postage_paid: int
    posted_day: int
    expected_delivery_day: int
    delivered_day: t.Optional[int]
    lost_at_city: t.Optional[str]
    state: ParcelState


@dataclasses.dataclass
class CityPostalService:
    _offices: set[str] = dataclasses.field(
        default_factory=set,
    )
    _routes: dict[tuple[str, str], int] = (
        dataclasses.field(default_factory=dict)
    )
    _parcels: dict[str, Parcel] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def open_office(self, *, city: str) -> bool:
        if not city:
            return False
        if city in self._offices:
            return False
        self._offices.add(city)
        return True

    def add_route(
        self, *, from_city: str, to_city: str,
        transit_days: int,
    ) -> bool:
        if not from_city or not to_city:
            return False
        if from_city == to_city:
            return False
        if transit_days <= 0:
            return False
        if (from_city not in self._offices
                or to_city not in self._offices):
            return False
        self._routes[(from_city, to_city)] = transit_days
        return True

    def post_parcel(
        self, *, from_city: str, to_city: str,
        sender: str, recipient: str, weight: int,
        parcel_class: ParcelClass, postage_paid: int,
        posted_day: int,
    ) -> t.Optional[str]:
        if (from_city, to_city) not in self._routes:
            return None
        if not sender or not recipient:
            return None
        if weight <= 0 or postage_paid < 0:
            return None
        if posted_day < 0:
            return None
        required = _REQUIRED_POSTAGE[
            parcel_class.value
        ]
        if postage_paid < required:
            return None
        transit = self._routes[(from_city, to_city)]
        pid = f"prcl_{self._next_id}"
        self._next_id += 1
        self._parcels[pid] = Parcel(
            parcel_id=pid, from_city=from_city,
            to_city=to_city, sender=sender,
            recipient=recipient, weight=weight,
            parcel_class=parcel_class,
            postage_paid=postage_paid,
            posted_day=posted_day,
            expected_delivery_day=(
                posted_day + transit
            ),
            delivered_day=None, lost_at_city=None,
            state=ParcelState.POSTED,
        )
        return pid

    def tick(
        self, *, now_day: int,
    ) -> list[tuple[str, ParcelState]]:
        changes: list[tuple[str, ParcelState]] = []
        for pid, p in list(self._parcels.items()):
            if p.state == ParcelState.POSTED:
                if now_day > p.posted_day:
                    self._parcels[pid] = (
                        dataclasses.replace(
                            p, state=ParcelState.IN_TRANSIT,
                        )
                    )
                    changes.append(
                        (pid, ParcelState.IN_TRANSIT),
                    )
                    p = self._parcels[pid]
            if p.state == ParcelState.IN_TRANSIT:
                if now_day >= p.expected_delivery_day:
                    self._parcels[pid] = (
                        dataclasses.replace(
                            p, delivered_day=now_day,
                            state=ParcelState.DELIVERED,
                        )
                    )
                    changes.append(
                        (pid, ParcelState.DELIVERED),
                    )
        return changes

    def mark_lost(
        self, *, parcel_id: str, leg_at_city: str,
    ) -> bool:
        if parcel_id not in self._parcels:
            return False
        p = self._parcels[parcel_id]
        if p.state not in (
            ParcelState.POSTED, ParcelState.IN_TRANSIT,
        ):
            return False
        self._parcels[parcel_id] = dataclasses.replace(
            p, lost_at_city=leg_at_city,
            state=ParcelState.LOST,
        )
        return True

    def refund(self, *, parcel_id: str) -> int:
        if parcel_id not in self._parcels:
            return 0
        p = self._parcels[parcel_id]
        if p.state != ParcelState.LOST:
            return 0
        # Only REGISTERED gets refunds; others "tough
        # luck" (caller's policy for non-registered).
        if p.parcel_class != ParcelClass.REGISTERED:
            return 0
        self._parcels[parcel_id] = dataclasses.replace(
            p, state=ParcelState.REFUNDED,
        )
        return p.postage_paid

    def parcel(
        self, *, parcel_id: str,
    ) -> t.Optional[Parcel]:
        return self._parcels.get(parcel_id)

    def inbox(self, *, city: str) -> list[Parcel]:
        return [
            p for p in self._parcels.values()
            if (p.to_city == city
                and p.state == ParcelState.DELIVERED)
        ]

    def outbox(self, *, city: str) -> list[Parcel]:
        return [
            p for p in self._parcels.values()
            if (p.from_city == city
                and p.state in (ParcelState.POSTED,
                                ParcelState.IN_TRANSIT))
        ]


__all__ = [
    "ParcelClass", "ParcelState", "PostalRoute",
    "Parcel", "CityPostalService",
]
