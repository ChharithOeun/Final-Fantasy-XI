"""Player travel route board — published recommended routes.

A traveler publishes a recommended route between two named
zones, with a list of waypoint zones in between. Other
travelers who walk the route can endorse (it worked) or
flag_dangerous (got attacked or got lost). High-endorsement
routes become RECOMMENDED; high-danger routes become
HAZARDOUS. The publisher can withdraw a route they no longer
stand behind.

Lifecycle (route)
    POSTED        live; collecting endorsements
    RECOMMENDED   5+ endorsements, endorsements > danger
    HAZARDOUS     3+ danger flags, danger > endorsements
    WITHDRAWN     publisher pulled it

Public surface
--------------
    RouteState enum
    TravelRoute dataclass (frozen)
    PlayerTravelRouteBoardSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_RECOMMEND_THRESHOLD = 5
_HAZARD_THRESHOLD = 3


class RouteState(str, enum.Enum):
    POSTED = "posted"
    RECOMMENDED = "recommended"
    HAZARDOUS = "hazardous"
    WITHDRAWN = "withdrawn"


@dataclasses.dataclass(frozen=True)
class TravelRoute:
    route_id: str
    publisher_id: str
    origin_zone: str
    destination_zone: str
    state: RouteState
    endorsement_count: int
    danger_count: int


@dataclasses.dataclass
class _RState:
    spec: TravelRoute
    waypoints: list[str] = dataclasses.field(
        default_factory=list,
    )
    endorsers: set[str] = dataclasses.field(
        default_factory=set,
    )
    danger_flaggers: set[str] = dataclasses.field(
        default_factory=set,
    )


@dataclasses.dataclass
class PlayerTravelRouteBoardSystem:
    _routes: dict[str, _RState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def publish(
        self, *, publisher_id: str,
        origin_zone: str, destination_zone: str,
        waypoints: list[str],
    ) -> t.Optional[str]:
        if not publisher_id:
            return None
        if not origin_zone or not destination_zone:
            return None
        if origin_zone == destination_zone:
            return None
        rid = f"route_{self._next}"
        self._next += 1
        st = _RState(
            spec=TravelRoute(
                route_id=rid,
                publisher_id=publisher_id,
                origin_zone=origin_zone,
                destination_zone=destination_zone,
                state=RouteState.POSTED,
                endorsement_count=0, danger_count=0,
            ),
        )
        st.waypoints = list(waypoints)
        self._routes[rid] = st
        return rid

    def endorse(
        self, *, route_id: str, traveler_id: str,
    ) -> bool:
        if route_id not in self._routes:
            return False
        st = self._routes[route_id]
        if st.spec.state == RouteState.WITHDRAWN:
            return False
        if not traveler_id:
            return False
        if traveler_id == st.spec.publisher_id:
            return False
        if traveler_id in st.endorsers:
            return False
        if traveler_id in st.danger_flaggers:
            return False
        st.endorsers.add(traveler_id)
        self._update_state(st)
        return True

    def flag_dangerous(
        self, *, route_id: str, traveler_id: str,
    ) -> bool:
        if route_id not in self._routes:
            return False
        st = self._routes[route_id]
        if st.spec.state == RouteState.WITHDRAWN:
            return False
        if not traveler_id:
            return False
        if traveler_id == st.spec.publisher_id:
            return False
        if traveler_id in st.endorsers:
            return False
        if traveler_id in st.danger_flaggers:
            return False
        st.danger_flaggers.add(traveler_id)
        self._update_state(st)
        return True

    @staticmethod
    def _update_state(st: _RState) -> None:
        e = len(st.endorsers)
        d = len(st.danger_flaggers)
        if (
            d >= _HAZARD_THRESHOLD and d > e
        ):
            new_state = RouteState.HAZARDOUS
        elif (
            e >= _RECOMMEND_THRESHOLD and e > d
        ):
            new_state = RouteState.RECOMMENDED
        else:
            new_state = RouteState.POSTED
        st.spec = dataclasses.replace(
            st.spec, state=new_state,
            endorsement_count=e, danger_count=d,
        )

    def withdraw(
        self, *, route_id: str, publisher_id: str,
    ) -> bool:
        if route_id not in self._routes:
            return False
        st = self._routes[route_id]
        if st.spec.state == RouteState.WITHDRAWN:
            return False
        if st.spec.publisher_id != publisher_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=RouteState.WITHDRAWN,
        )
        return True

    def route(
        self, *, route_id: str,
    ) -> t.Optional[TravelRoute]:
        st = self._routes.get(route_id)
        return st.spec if st else None

    def waypoints(
        self, *, route_id: str,
    ) -> list[str]:
        st = self._routes.get(route_id)
        if st is None:
            return []
        return list(st.waypoints)

    def routes_to(
        self, *, destination_zone: str,
    ) -> list[TravelRoute]:
        return [
            st.spec for st in self._routes.values()
            if st.spec.destination_zone == destination_zone
        ]

    def recommended_routes(
        self,
    ) -> list[TravelRoute]:
        return [
            st.spec for st in self._routes.values()
            if st.spec.state == RouteState.RECOMMENDED
        ]


__all__ = [
    "RouteState", "TravelRoute",
    "PlayerTravelRouteBoardSystem",
]
