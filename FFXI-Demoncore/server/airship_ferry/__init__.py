"""Airship / ferry — scheduled travel routes with timetables.

Routes are bidirectional pairs (Bastok <-> Jeuno) that depart on
fixed Vana'diel intervals. Boarding requires a ticket purchase
(gil) and sometimes an attunement key item (e.g. Airship Pass).

Public surface
--------------
    Route catalog (ferry/airship)
    Schedule per route (departure offsets within day)
    next_departure(route, now_vanadiel_tick) -> int
    purchase_ticket(...) -> TicketResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


VANADIEL_DAY_SECONDS = 24 * 60 * 60   # one Vana day in seconds
                                       # (we use real-time abstraction)


class TransportKind(str, enum.Enum):
    AIRSHIP = "airship"
    FERRY = "ferry"


@dataclasses.dataclass(frozen=True)
class Route:
    route_id: str
    label: str
    transport_kind: TransportKind
    from_zone: str
    to_zone: str
    fare_gil: int
    travel_seconds: int
    attunement_key_item: str = ""
    departures_per_day: tuple[int, ...] = ()    # offsets from day start


# Sample catalog
ROUTES: tuple[Route, ...] = (
    # Ferry: Selbina <-> Mhaura (every 4 hours real-time)
    Route(
        route_id="ferry_selbina_to_mhaura",
        label="Selbina -> Mhaura",
        transport_kind=TransportKind.FERRY,
        from_zone="selbina", to_zone="mhaura",
        fare_gil=100, travel_seconds=10 * 60,
        departures_per_day=(0, 4 * 3600, 8 * 3600,
                            12 * 3600, 16 * 3600, 20 * 3600),
    ),
    Route(
        route_id="ferry_mhaura_to_selbina",
        label="Mhaura -> Selbina",
        transport_kind=TransportKind.FERRY,
        from_zone="mhaura", to_zone="selbina",
        fare_gil=100, travel_seconds=10 * 60,
        departures_per_day=(2 * 3600, 6 * 3600, 10 * 3600,
                            14 * 3600, 18 * 3600, 22 * 3600),
    ),
    # Airship: Bastok <-> Jeuno
    Route(
        route_id="airship_bastok_to_jeuno",
        label="Bastok -> Jeuno",
        transport_kind=TransportKind.AIRSHIP,
        from_zone="bastok_markets", to_zone="port_jeuno",
        fare_gil=200, travel_seconds=8 * 60,
        attunement_key_item="airship_pass",
        departures_per_day=(0, 30 * 60, 60 * 60, 90 * 60,
                            120 * 60, 150 * 60, 180 * 60,
                            210 * 60),
    ),
    Route(
        route_id="airship_sandy_to_jeuno",
        label="San d'Oria -> Jeuno",
        transport_kind=TransportKind.AIRSHIP,
        from_zone="north_sandoria", to_zone="port_jeuno",
        fare_gil=200, travel_seconds=8 * 60,
        attunement_key_item="airship_pass",
        departures_per_day=(15 * 60, 45 * 60, 75 * 60,
                            105 * 60, 135 * 60, 165 * 60,
                            195 * 60, 225 * 60),
    ),
    Route(
        route_id="airship_windy_to_jeuno",
        label="Windurst -> Jeuno",
        transport_kind=TransportKind.AIRSHIP,
        from_zone="windurst_woods", to_zone="port_jeuno",
        fare_gil=200, travel_seconds=8 * 60,
        attunement_key_item="airship_pass",
        departures_per_day=(20 * 60, 50 * 60, 80 * 60,
                            110 * 60, 140 * 60, 170 * 60,
                            200 * 60, 230 * 60),
    ),
)

ROUTE_BY_ID: dict[str, Route] = {r.route_id: r for r in ROUTES}


def next_departure(
    *, route_id: str, now_tick: int,
) -> t.Optional[int]:
    """Find the next absolute tick at which this route departs.

    Day is rolled by the caller; we compute (now_tick % DAY) and
    pick the next slot, rolling to next day if all gone.
    """
    route = ROUTE_BY_ID.get(route_id)
    if route is None:
        return None
    if not route.departures_per_day:
        return None
    day_start = (now_tick // VANADIEL_DAY_SECONDS) * \
        VANADIEL_DAY_SECONDS
    today_offset = now_tick - day_start
    for slot in route.departures_per_day:
        if slot >= today_offset:
            return day_start + slot
    # Past last slot today — roll to next day
    return day_start + VANADIEL_DAY_SECONDS + \
        route.departures_per_day[0]


@dataclasses.dataclass(frozen=True)
class TicketResult:
    accepted: bool
    route_id: str
    fare_charged: int = 0
    departs_at_tick: t.Optional[int] = None
    arrives_at_tick: t.Optional[int] = None
    reason: t.Optional[str] = None


def purchase_ticket(
    *, route_id: str, player_gil: int,
    completed_quests: tuple[str, ...],
    now_tick: int,
) -> TicketResult:
    route = ROUTE_BY_ID.get(route_id)
    if route is None:
        return TicketResult(
            False, route_id, reason="unknown route",
        )
    if route.attunement_key_item and \
            route.attunement_key_item not in completed_quests:
        return TicketResult(
            False, route_id,
            reason=f"need {route.attunement_key_item}",
        )
    if player_gil < route.fare_gil:
        return TicketResult(
            False, route_id,
            reason=f"need {route.fare_gil} gil",
        )
    departs = next_departure(route_id=route_id, now_tick=now_tick)
    arrives = (
        departs + route.travel_seconds
        if departs is not None else None
    )
    return TicketResult(
        accepted=True, route_id=route_id,
        fare_charged=route.fare_gil,
        departs_at_tick=departs,
        arrives_at_tick=arrives,
    )


__all__ = [
    "VANADIEL_DAY_SECONDS",
    "TransportKind", "Route",
    "ROUTES", "ROUTE_BY_ID",
    "TicketResult",
    "next_departure", "purchase_ticket",
]
