"""Nation navy — fleet of warships and patrols.

Each nation that can reach water (Bastok via the harbor,
San d'Oria via Selbina, Windurst via Mhaura, plus
beastman cities like Movalpolos coastal) maintains a
NAVY: registry of WARSHIPS, ports, and PATROL ROUTES.

Ships have ship_class (FRIGATE / GALLEON / CUTTER /
IRONCLAD), captain, crew, hull integrity, and an
operational state. They're STATIONED at a port,
PATROLLING a route, or IN_DOCK for repairs.

Ports tie to retail FFXI airship/ferry zones plus new
beastman ports. A ship's home_port is where it returns
for refit and crew rotation.

Public surface
--------------
    ShipClass enum
    ShipState enum
    Ship dataclass (frozen)
    PatrolRoute dataclass (frozen)
    NationNavySystem
        .add_port(port_id, nation_id) -> bool
        .commission_ship(...) -> bool
        .add_route(route_id, port_a, port_b,
                   transit_days) -> bool
        .deploy_ship(ship_id, route_id,
                     now_day) -> bool
        .recall_ship(ship_id, now_day) -> bool
        .take_hull_damage(ship_id, dmg) -> bool
        .repair(ship_id, hp, now_day) -> bool
        .replace_captain(ship_id, captain) -> bool
        .scuttle(ship_id, now_day) -> bool
        .ship(ship_id) -> Optional[Ship]
        .ships_for(nation) -> list[Ship]
        .ships_at(port_id) -> list[Ship]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ShipClass(str, enum.Enum):
    CUTTER = "cutter"
    FRIGATE = "frigate"
    GALLEON = "galleon"
    IRONCLAD = "ironclad"


class ShipState(str, enum.Enum):
    STATIONED = "stationed"
    PATROLLING = "patrolling"
    IN_DOCK = "in_dock"
    SUNK = "sunk"


@dataclasses.dataclass(frozen=True)
class Ship:
    ship_id: str
    nation_id: str
    name: str
    ship_class: ShipClass
    captain: str
    crew: int
    hull_max: int
    hull_current: int
    home_port: str
    current_port: str
    patrol_route: str
    state: ShipState


@dataclasses.dataclass(frozen=True)
class PatrolRoute:
    route_id: str
    port_a: str
    port_b: str
    transit_days: int


@dataclasses.dataclass
class NationNavySystem:
    _ports: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )  # port_id -> nation_id
    _ships: dict[str, Ship] = dataclasses.field(
        default_factory=dict,
    )
    _routes: dict[str, PatrolRoute] = (
        dataclasses.field(default_factory=dict)
    )

    def add_port(
        self, *, port_id: str, nation_id: str,
    ) -> bool:
        if not port_id or not nation_id:
            return False
        if port_id in self._ports:
            return False
        self._ports[port_id] = nation_id
        return True

    def commission_ship(
        self, *, ship_id: str, nation_id: str,
        name: str, ship_class: ShipClass,
        captain: str, crew: int, hull_max: int,
        home_port: str,
    ) -> bool:
        if not ship_id or not nation_id or not name:
            return False
        if not captain:
            return False
        if crew <= 0 or hull_max <= 0:
            return False
        if home_port not in self._ports:
            return False
        if self._ports[home_port] != nation_id:
            return False
        if ship_id in self._ships:
            return False
        self._ships[ship_id] = Ship(
            ship_id=ship_id, nation_id=nation_id,
            name=name, ship_class=ship_class,
            captain=captain, crew=crew,
            hull_max=hull_max,
            hull_current=hull_max,
            home_port=home_port,
            current_port=home_port,
            patrol_route="",
            state=ShipState.STATIONED,
        )
        return True

    def add_route(
        self, *, route_id: str, port_a: str,
        port_b: str, transit_days: int,
    ) -> bool:
        if not route_id:
            return False
        if route_id in self._routes:
            return False
        if port_a == port_b:
            return False
        if (port_a not in self._ports
                or port_b not in self._ports):
            return False
        if transit_days <= 0:
            return False
        self._routes[route_id] = PatrolRoute(
            route_id=route_id, port_a=port_a,
            port_b=port_b, transit_days=transit_days,
        )
        return True

    def deploy_ship(
        self, *, ship_id: str, route_id: str,
        now_day: int,
    ) -> bool:
        if ship_id not in self._ships:
            return False
        if route_id not in self._routes:
            return False
        sh = self._ships[ship_id]
        if sh.state != ShipState.STATIONED:
            return False
        rt = self._routes[route_id]
        # Ship's current port must be on the route
        if sh.current_port not in (rt.port_a, rt.port_b):
            return False
        self._ships[ship_id] = dataclasses.replace(
            sh, patrol_route=route_id,
            state=ShipState.PATROLLING,
        )
        return True

    def recall_ship(
        self, *, ship_id: str, now_day: int,
    ) -> bool:
        if ship_id not in self._ships:
            return False
        sh = self._ships[ship_id]
        if sh.state != ShipState.PATROLLING:
            return False
        self._ships[ship_id] = dataclasses.replace(
            sh, patrol_route="",
            current_port=sh.home_port,
            state=ShipState.STATIONED,
        )
        return True

    def take_hull_damage(
        self, *, ship_id: str, dmg: int,
    ) -> bool:
        if ship_id not in self._ships:
            return False
        if dmg <= 0:
            return False
        sh = self._ships[ship_id]
        if sh.state == ShipState.SUNK:
            return False
        new_hull = max(0, sh.hull_current - dmg)
        if new_hull == 0:
            self._ships[ship_id] = (
                dataclasses.replace(
                    sh, hull_current=0,
                    patrol_route="",
                    state=ShipState.SUNK,
                )
            )
        else:
            new_state = sh.state
            # If badly damaged below 33%, force IN_DOCK
            if (new_hull * 3 < sh.hull_max
                    and sh.state == ShipState.PATROLLING):
                new_state = ShipState.IN_DOCK
            self._ships[ship_id] = (
                dataclasses.replace(
                    sh, hull_current=new_hull,
                    state=new_state,
                )
            )
        return True

    def repair(
        self, *, ship_id: str, hp: int, now_day: int,
    ) -> bool:
        if ship_id not in self._ships:
            return False
        if hp <= 0:
            return False
        sh = self._ships[ship_id]
        if sh.state == ShipState.SUNK:
            return False
        new_hull = min(
            sh.hull_max, sh.hull_current + hp,
        )
        new_state = sh.state
        if (sh.state == ShipState.IN_DOCK
                and new_hull == sh.hull_max):
            new_state = ShipState.STATIONED
        self._ships[ship_id] = dataclasses.replace(
            sh, hull_current=new_hull,
            state=new_state,
        )
        return True

    def replace_captain(
        self, *, ship_id: str, captain: str,
    ) -> bool:
        if ship_id not in self._ships:
            return False
        if not captain:
            return False
        sh = self._ships[ship_id]
        if sh.state == ShipState.SUNK:
            return False
        self._ships[ship_id] = dataclasses.replace(
            sh, captain=captain,
        )
        return True

    def scuttle(
        self, *, ship_id: str, now_day: int,
    ) -> bool:
        if ship_id not in self._ships:
            return False
        sh = self._ships[ship_id]
        if sh.state == ShipState.SUNK:
            return False
        self._ships[ship_id] = dataclasses.replace(
            sh, hull_current=0, patrol_route="",
            state=ShipState.SUNK,
        )
        return True

    def ship(
        self, *, ship_id: str,
    ) -> t.Optional[Ship]:
        return self._ships.get(ship_id)

    def ships_for(
        self, *, nation_id: str,
    ) -> list[Ship]:
        return [
            s for s in self._ships.values()
            if s.nation_id == nation_id
        ]

    def ships_at(
        self, *, port_id: str,
    ) -> list[Ship]:
        return [
            s for s in self._ships.values()
            if (s.current_port == port_id
                and s.state in (ShipState.STATIONED,
                                ShipState.IN_DOCK))
        ]


__all__ = [
    "ShipClass", "ShipState", "Ship", "PatrolRoute",
    "NationNavySystem",
]
