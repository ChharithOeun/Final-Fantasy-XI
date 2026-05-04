"""Beastman naval — ships + cross-faction naval lanes.

Beastman cities run their own fleets. Each ship has a NAUTICAL
KIND (Lamia tide-runner, Quadav stoneship, Yagudo wing-craft,
Orc reaver), a CAPACITY (passengers + cargo), a CROSSING RISK
percent (per leg, drives encounter chance with hume navy or
canon pirates), and a MANIFEST that tracks who and what is
aboard.

Ships travel between PORTS — beastman ports + selected
hume-side ports that goblin neutrality opens up. Each LEG (a
port-to-port journey) has its own risk score independent of
the ship.

Public surface
--------------
    NauticalKind enum
    PortKind enum
    Ship dataclass
    Port dataclass
    Leg dataclass
    BoardResult / DepartResult dataclasses
    BeastmanNaval
        .register_port(port_id, kind, zone)
        .register_ship(ship_id, kind, home_port, capacity)
        .register_leg(leg_id, ship_id, from, to, base_risk)
        .board(player_id, ship_id, leg_id, cargo_units)
        .depart(leg_id, now_seconds) -> outcome (success / pirate
                                                 attack / wrecked)
        .ship_manifest(ship_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class NauticalKind(str, enum.Enum):
    LAMIA_TIDE_RUNNER = "lamia_tide_runner"
    QUADAV_STONESHIP = "quadav_stoneship"
    YAGUDO_WING_CRAFT = "yagudo_wing_craft"
    ORC_REAVER = "orc_reaver"
    GOBLIN_TRADER = "goblin_trader"   # neutral


class PortKind(str, enum.Enum):
    BEASTMAN_HOME = "beastman_home"
    HUME_DOCK = "hume_dock"          # opens via goblin neutrality
    NEUTRAL_TRADING = "neutral_trading"


class CrossingOutcome(str, enum.Enum):
    SAFE_ARRIVAL = "safe_arrival"
    PIRATE_ATTACK = "pirate_attack"
    HUME_NAVY_INTERCEPT = "hume_navy_intercept"
    WRECKED = "wrecked"


@dataclasses.dataclass(frozen=True)
class Port:
    port_id: str
    kind: PortKind
    zone_id: str


@dataclasses.dataclass
class Ship:
    ship_id: str
    kind: NauticalKind
    home_port_id: str
    race: t.Optional[BeastmanRace]
    passenger_capacity: int
    cargo_capacity: int
    boarded_passengers: list[str] = dataclasses.field(
        default_factory=list,
    )
    cargo_used: int = 0


@dataclasses.dataclass
class Leg:
    leg_id: str
    ship_id: str
    from_port_id: str
    to_port_id: str
    base_risk_pct: int
    departures_completed: int = 0


@dataclasses.dataclass(frozen=True)
class BoardResult:
    accepted: bool
    ship_id: str
    leg_id: str
    cargo_units: int
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class DepartResult:
    accepted: bool
    leg_id: str
    outcome: CrossingOutcome
    survivors_returned: int = 0
    cargo_lost: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanNaval:
    _ports: dict[str, Port] = dataclasses.field(
        default_factory=dict,
    )
    _ships: dict[str, Ship] = dataclasses.field(
        default_factory=dict,
    )
    _legs: dict[str, Leg] = dataclasses.field(
        default_factory=dict,
    )

    def register_port(
        self, *, port_id: str,
        kind: PortKind,
        zone_id: str,
    ) -> t.Optional[Port]:
        if port_id in self._ports:
            return None
        if not zone_id:
            return None
        p = Port(port_id=port_id, kind=kind, zone_id=zone_id)
        self._ports[port_id] = p
        return p

    def register_ship(
        self, *, ship_id: str,
        kind: NauticalKind,
        home_port_id: str,
        race: t.Optional[BeastmanRace] = None,
        passenger_capacity: int = 12,
        cargo_capacity: int = 200,
    ) -> t.Optional[Ship]:
        if ship_id in self._ships:
            return None
        if home_port_id not in self._ports:
            return None
        if (
            passenger_capacity <= 0
            or cargo_capacity <= 0
        ):
            return None
        s = Ship(
            ship_id=ship_id, kind=kind,
            home_port_id=home_port_id,
            race=race,
            passenger_capacity=passenger_capacity,
            cargo_capacity=cargo_capacity,
        )
        self._ships[ship_id] = s
        return s

    def register_leg(
        self, *, leg_id: str,
        ship_id: str,
        from_port_id: str,
        to_port_id: str,
        base_risk_pct: int,
    ) -> t.Optional[Leg]:
        if leg_id in self._legs:
            return None
        if ship_id not in self._ships:
            return None
        if from_port_id == to_port_id:
            return None
        if (
            from_port_id not in self._ports
            or to_port_id not in self._ports
        ):
            return None
        if not (0 <= base_risk_pct <= 100):
            return None
        leg = Leg(
            leg_id=leg_id, ship_id=ship_id,
            from_port_id=from_port_id,
            to_port_id=to_port_id,
            base_risk_pct=base_risk_pct,
        )
        self._legs[leg_id] = leg
        return leg

    def get_ship(
        self, ship_id: str,
    ) -> t.Optional[Ship]:
        return self._ships.get(ship_id)

    def board(
        self, *, player_id: str,
        ship_id: str,
        leg_id: str,
        cargo_units: int = 0,
    ) -> BoardResult:
        ship = self._ships.get(ship_id)
        leg = self._legs.get(leg_id)
        if ship is None or leg is None:
            return BoardResult(
                False, ship_id=ship_id, leg_id=leg_id,
                cargo_units=cargo_units,
                reason="unknown ship or leg",
            )
        if leg.ship_id != ship_id:
            return BoardResult(
                False, ship_id=ship_id, leg_id=leg_id,
                cargo_units=cargo_units,
                reason="leg not assigned to this ship",
            )
        if cargo_units < 0:
            return BoardResult(
                False, ship_id=ship_id, leg_id=leg_id,
                cargo_units=cargo_units,
                reason="negative cargo",
            )
        if (
            len(ship.boarded_passengers)
            >= ship.passenger_capacity
        ):
            return BoardResult(
                False, ship_id=ship_id, leg_id=leg_id,
                cargo_units=cargo_units,
                reason="passenger capacity full",
            )
        if (
            ship.cargo_used + cargo_units
            > ship.cargo_capacity
        ):
            return BoardResult(
                False, ship_id=ship_id, leg_id=leg_id,
                cargo_units=cargo_units,
                reason="cargo capacity exceeded",
            )
        if player_id in ship.boarded_passengers:
            return BoardResult(
                False, ship_id=ship_id, leg_id=leg_id,
                cargo_units=cargo_units,
                reason="already aboard",
            )
        ship.boarded_passengers.append(player_id)
        ship.cargo_used += cargo_units
        return BoardResult(
            accepted=True,
            ship_id=ship_id, leg_id=leg_id,
            cargo_units=cargo_units,
        )

    def depart(
        self, *, leg_id: str,
        risk_roll_pct: int,
    ) -> DepartResult:
        """Roll the crossing. risk_roll_pct is 0..100 — the
        random or test-injected outcome roll. Below the leg's
        base_risk yields a hostile encounter; the SHIP'S kind
        decides which one."""
        leg = self._legs.get(leg_id)
        if leg is None:
            return DepartResult(
                False, leg_id=leg_id,
                outcome=CrossingOutcome.SAFE_ARRIVAL,
                reason="no such leg",
            )
        if not (0 <= risk_roll_pct <= 100):
            return DepartResult(
                False, leg_id=leg_id,
                outcome=CrossingOutcome.SAFE_ARRIVAL,
                reason="invalid roll",
            )
        ship = self._ships[leg.ship_id]
        passengers = list(ship.boarded_passengers)
        cargo = ship.cargo_used
        leg.departures_completed += 1
        # Empty manifest can still depart — just no cargo loss
        if risk_roll_pct >= leg.base_risk_pct:
            ship.boarded_passengers.clear()
            ship.cargo_used = 0
            return DepartResult(
                accepted=True, leg_id=leg_id,
                outcome=CrossingOutcome.SAFE_ARRIVAL,
                survivors_returned=len(passengers),
            )
        # Hostile encounter
        if leg.base_risk_pct - risk_roll_pct >= 60:
            outcome = CrossingOutcome.WRECKED
            survivors = 0
            cargo_lost = cargo
        elif (
            ship.kind in (
                NauticalKind.LAMIA_TIDE_RUNNER,
                NauticalKind.ORC_REAVER,
            )
        ):
            outcome = CrossingOutcome.HUME_NAVY_INTERCEPT
            survivors = max(0, len(passengers) - 2)
            cargo_lost = min(cargo, cargo // 2)
        else:
            outcome = CrossingOutcome.PIRATE_ATTACK
            survivors = len(passengers)
            cargo_lost = cargo
        ship.boarded_passengers.clear()
        ship.cargo_used = 0
        return DepartResult(
            accepted=True, leg_id=leg_id,
            outcome=outcome,
            survivors_returned=survivors,
            cargo_lost=cargo_lost,
        )

    def ship_manifest(
        self, *, ship_id: str,
    ) -> tuple[tuple[str, ...], int]:
        ship = self._ships.get(ship_id)
        if ship is None:
            return ((), 0)
        return (
            tuple(ship.boarded_passengers),
            ship.cargo_used,
        )

    def total_ports(self) -> int:
        return len(self._ports)

    def total_ships(self) -> int:
        return len(self._ships)

    def total_legs(self) -> int:
        return len(self._legs)


__all__ = [
    "NauticalKind", "PortKind", "CrossingOutcome",
    "Port", "Ship", "Leg",
    "BoardResult", "DepartResult",
    "BeastmanNaval",
]
