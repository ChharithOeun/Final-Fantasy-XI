"""Wandering caravans — itinerant merchants moving zone-to-zone.

Static vendors are convenient but boring. A caravan is an
NPC vendor that travels along a route, stopping in each
zone for a tour duration before moving on. Their stock
includes RARE items not sold by city vendors — exotic
incense from Norg, beastman crafts traded over borders,
forgotten spell scrolls, low-stock relics. If you miss
their visit, you wait for them to come around again.

A Caravan has:
    caravan_id      stable identifier
    name            "Wabe-Fendi's Wandering Wares"
    route           ordered list of (zone_id, hours_stay)
                    pairs that loop forever
    stock           list of CaravanItem (item_id +
                    base_price + max_supply + restock_per_visit)

Per-tick scheduler:
    advance(now_hour) — for each caravan, computes which
    stop they're currently at given total elapsed hours
    modulo total route length.

Active stock at a stop is a per-(caravan, zone, visit)
counter — supply gets restocked at the START of a visit
to its restock_per_visit value (capped at max_supply).
Players buy items, supply ticks down. When the caravan
moves on the per-visit counter is gone — next visit's
stock is its own.

Public surface
--------------
    CaravanStop dataclass (frozen)
    CaravanItem dataclass (frozen)
    Caravan dataclass (frozen)
    StockSnapshot dataclass (frozen)
    WanderingCaravans
        .register_caravan(caravan) -> bool
        .advance(now_hour) -> None
        .current_zone(caravan_id) -> Optional[str]
        .stock_at(caravan_id, zone_id) -> list[StockSnapshot]
        .buy(player_id, caravan_id, item_id, quantity)
            -> Optional[int]    # gil cost or None on fail
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class CaravanStop:
    zone_id: str
    hours_stay: int


@dataclasses.dataclass(frozen=True)
class CaravanItem:
    item_id: str
    base_price_gil: int
    max_supply: int
    restock_per_visit: int


@dataclasses.dataclass(frozen=True)
class Caravan:
    caravan_id: str
    name: str
    route: tuple[CaravanStop, ...]
    stock: tuple[CaravanItem, ...]


@dataclasses.dataclass(frozen=True)
class StockSnapshot:
    item_id: str
    price_gil: int
    available: int


@dataclasses.dataclass
class _CaravanState:
    spec: Caravan
    current_index: int = 0
    last_visit_index: t.Optional[int] = None
    last_loop_count: int = -1
    # item_id -> remaining for the active visit
    visit_supply: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class WanderingCaravans:
    _caravans: dict[str, _CaravanState] = dataclasses.field(
        default_factory=dict,
    )

    def register_caravan(self, caravan: Caravan) -> bool:
        if not caravan.caravan_id or not caravan.name:
            return False
        if not caravan.route:
            return False
        if any(s.hours_stay <= 0 for s in caravan.route):
            return False
        if any(
            i.max_supply <= 0
            or i.restock_per_visit <= 0
            or i.restock_per_visit > i.max_supply
            or i.base_price_gil < 0
            for i in caravan.stock
        ):
            return False
        if caravan.caravan_id in self._caravans:
            return False
        self._caravans[caravan.caravan_id] = _CaravanState(
            spec=caravan,
        )
        return True

    def advance(self, *, now_hour: int) -> None:
        for state in self._caravans.values():
            total = sum(
                s.hours_stay for s in state.spec.route
            )
            if total <= 0:
                continue
            loop_count = now_hour // total
            t_in_loop = now_hour % total
            idx = 0
            cumulative = 0
            for i, stop in enumerate(state.spec.route):
                if t_in_loop < cumulative + stop.hours_stay:
                    idx = i
                    break
                cumulative += stop.hours_stay
            state.current_index = idx
            # If we entered a new stop OR a new loop of
            # the same stop, restock
            if (state.last_visit_index != idx
                    or state.last_loop_count != loop_count):
                state.last_visit_index = idx
                state.last_loop_count = loop_count
                state.visit_supply = {
                    item.item_id: min(
                        item.max_supply,
                        item.restock_per_visit,
                    )
                    for item in state.spec.stock
                }

    def current_zone(
        self, *, caravan_id: str,
    ) -> t.Optional[str]:
        if caravan_id not in self._caravans:
            return None
        state = self._caravans[caravan_id]
        if state.last_visit_index is None:
            return None
        return state.spec.route[
            state.last_visit_index
        ].zone_id

    def stock_at(
        self, *, caravan_id: str, zone_id: str,
    ) -> list[StockSnapshot]:
        if self.current_zone(caravan_id=caravan_id) != zone_id:
            return []
        state = self._caravans[caravan_id]
        return [
            StockSnapshot(
                item_id=item.item_id,
                price_gil=item.base_price_gil,
                available=state.visit_supply.get(
                    item.item_id, 0,
                ),
            )
            for item in state.spec.stock
        ]

    def buy(
        self, *, player_id: str, caravan_id: str,
        item_id: str, quantity: int,
    ) -> t.Optional[int]:
        if not player_id or quantity <= 0:
            return None
        if caravan_id not in self._caravans:
            return None
        state = self._caravans[caravan_id]
        if state.last_visit_index is None:
            return None
        item = next(
            (i for i in state.spec.stock if i.item_id == item_id),
            None,
        )
        if item is None:
            return None
        avail = state.visit_supply.get(item_id, 0)
        if avail < quantity:
            return None
        state.visit_supply[item_id] = avail - quantity
        return item.base_price_gil * quantity


__all__ = [
    "CaravanStop", "CaravanItem", "Caravan",
    "StockSnapshot", "WanderingCaravans",
]
