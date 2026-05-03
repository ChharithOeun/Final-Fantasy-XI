"""Trade routes — caravans + supply lines between settlements.

Goods flow between cities along trade routes. Each route has:
* Endpoints (origin / destination settlement)
* Stops (zones it passes through — beastmen lurk in some)
* A frequency (caravans per game-day)
* A goods catalog (what the caravan typically carries)

Caravans dispatch on the route's schedule, traverse stops in
order, and either ARRIVE successfully (delivering goods that
feed npc_economy) or are RAIDED (goods lost, raiders fence them).
The route's RISK level reflects beastmen pressure on its stops;
high-risk routes either get expensive guards or shut down.

Players can ESCORT caravans for pay + reputation. Routes that
players consistently guard reduce their own risk and unlock
discounts in destination shops.

Design
------
This is a STATE module. The orchestrator dispatches caravans;
this module models what they're doing right now and lets other
systems (npc_economy, beastmen_factions, dynamic_quest_gen) read
the state. Faction AI uses raid pressure here to decide whether
to commit forces; merchants use throughput to set prices.

Public surface
--------------
    Settlement enum
    GoodsBundle dataclass — what a caravan carries
    TradeRoute dataclass — definition of a route
    Caravan dataclass — a single in-flight caravan
    CaravanStatus enum (DEPARTING / IN_TRANSIT / ARRIVED / RAIDED)
    TradeRouteRegistry
        .register_route(...) / .route_for(route_id)
        .dispatch(route_id, now)        — spawn a caravan
        .advance(caravan_id, now)       — move to next stop
        .raid(caravan_id, now)          — caravan was hit
        .deliver(caravan_id, now)       — caravan reached endpoint
        .active_caravans()
        .raid_pressure(route_id) -> int — 0..100
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Settlement(str, enum.Enum):
    BASTOK = "bastok"
    SAN_DORIA = "san_doria"
    WINDURST = "windurst"
    JEUNO = "jeuno"
    SELBINA = "selbina"
    MHAURA = "mhaura"
    KAZHAM = "kazham"
    NORG = "norg"
    RABAO = "rabao"
    AHT_URHGAN = "aht_urhgan"


class CaravanStatus(str, enum.Enum):
    DEPARTING = "departing"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    RAIDED = "raided"


# How many games-hours between caravans at each frequency tier.
class Frequency(str, enum.Enum):
    HOURLY = "hourly"           # every 1 game-hour
    BUSY = "busy"               # every 4 game-hours
    DAILY = "daily"              # every 24 game-hours
    WEEKLY = "weekly"            # every 168 game-hours
    SPORADIC = "sporadic"        # caller dispatches manually


_FREQ_HOURS: dict[Frequency, int] = {
    Frequency.HOURLY: 1,
    Frequency.BUSY: 4,
    Frequency.DAILY: 24,
    Frequency.WEEKLY: 168,
    Frequency.SPORADIC: 0,   # manual only
}


@dataclasses.dataclass(frozen=True)
class GoodsBundle:
    """What a caravan typically carries. count is the multiplier
    NPC economy uses when bumping local supply on arrival."""
    item_id: str
    typical_count: int = 50


@dataclasses.dataclass(frozen=True)
class TradeRoute:
    route_id: str
    origin: Settlement
    destination: Settlement
    stops: tuple[str, ...]                 # zone IDs in order
    goods_catalog: tuple[GoodsBundle, ...]
    frequency: Frequency = Frequency.DAILY
    base_risk: int = 10                    # 0..100; bumped by raids


@dataclasses.dataclass
class Caravan:
    caravan_id: str
    route_id: str
    dispatched_at_seconds: float
    current_stop_index: int = 0
    status: CaravanStatus = CaravanStatus.DEPARTING
    raided_at_seconds: t.Optional[float] = None
    arrived_at_seconds: t.Optional[float] = None
    escorting_player_ids: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class DispatchResult:
    accepted: bool
    caravan: t.Optional[Caravan] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class AdvanceResult:
    accepted: bool
    new_status: t.Optional[CaravanStatus] = None
    new_stop_index: int = 0
    reason: t.Optional[str] = None


_RISK_CAP = 100


@dataclasses.dataclass
class TradeRouteRegistry:
    _routes: dict[str, TradeRoute] = dataclasses.field(
        default_factory=dict,
    )
    _caravans: dict[str, Caravan] = dataclasses.field(
        default_factory=dict,
    )
    _route_risk_pressure: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    _next_caravan_id: int = 0
    _last_dispatch_at: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )

    def register_route(self, route: TradeRoute) -> TradeRoute:
        if not route.stops:
            raise ValueError("route must have at least one stop")
        self._routes[route.route_id] = route
        self._route_risk_pressure.setdefault(
            route.route_id, route.base_risk,
        )
        return route

    def route_for(self, route_id: str) -> t.Optional[TradeRoute]:
        return self._routes.get(route_id)

    def dispatch(
        self, *, route_id: str, now_seconds: float,
        escort_player_ids: tuple[str, ...] = (),
    ) -> DispatchResult:
        route = self._routes.get(route_id)
        if route is None:
            return DispatchResult(False, reason="no such route")
        # Frequency gate (skipped for SPORADIC)
        if route.frequency != Frequency.SPORADIC:
            min_gap_seconds = _FREQ_HOURS[route.frequency] * 3600
            last = self._last_dispatch_at.get(route_id)
            if (
                last is not None
                and (now_seconds - last) < min_gap_seconds
            ):
                return DispatchResult(
                    False, reason="dispatch too soon",
                )
        cid = f"caravan_{self._next_caravan_id}"
        self._next_caravan_id += 1
        car = Caravan(
            caravan_id=cid, route_id=route_id,
            dispatched_at_seconds=now_seconds,
            escorting_player_ids=escort_player_ids,
            status=CaravanStatus.DEPARTING,
        )
        self._caravans[cid] = car
        self._last_dispatch_at[route_id] = now_seconds
        return DispatchResult(True, caravan=car)

    def advance(
        self, *, caravan_id: str, now_seconds: float,
    ) -> AdvanceResult:
        car = self._caravans.get(caravan_id)
        if car is None:
            return AdvanceResult(False, reason="no such caravan")
        if car.status in (
            CaravanStatus.ARRIVED, CaravanStatus.RAIDED,
        ):
            return AdvanceResult(
                False, reason=f"already {car.status.value}",
            )
        route = self._routes[car.route_id]
        car.current_stop_index += 1
        if car.current_stop_index >= len(route.stops):
            car.status = CaravanStatus.ARRIVED
            car.arrived_at_seconds = now_seconds
            return AdvanceResult(
                True, new_status=CaravanStatus.ARRIVED,
                new_stop_index=car.current_stop_index,
            )
        car.status = CaravanStatus.IN_TRANSIT
        return AdvanceResult(
            True, new_status=CaravanStatus.IN_TRANSIT,
            new_stop_index=car.current_stop_index,
        )

    def raid(
        self, *, caravan_id: str, now_seconds: float,
        risk_bump: int = 10,
    ) -> AdvanceResult:
        car = self._caravans.get(caravan_id)
        if car is None:
            return AdvanceResult(False, reason="no such caravan")
        if car.status in (
            CaravanStatus.ARRIVED, CaravanStatus.RAIDED,
        ):
            return AdvanceResult(
                False, reason=f"already {car.status.value}",
            )
        car.status = CaravanStatus.RAIDED
        car.raided_at_seconds = now_seconds
        rid = car.route_id
        prev = self._route_risk_pressure.get(rid, 0)
        self._route_risk_pressure[rid] = min(_RISK_CAP, prev + risk_bump)
        return AdvanceResult(True, new_status=CaravanStatus.RAIDED)

    def relieve_pressure(
        self, *, route_id: str, amount: int,
    ) -> int:
        """Player escorts succeeded; risk pressure drops."""
        prev = self._route_risk_pressure.get(route_id, 0)
        new = max(0, prev - amount)
        self._route_risk_pressure[route_id] = new
        return new

    def raid_pressure(self, route_id: str) -> int:
        return self._route_risk_pressure.get(route_id, 0)

    def active_caravans(self) -> tuple[Caravan, ...]:
        return tuple(
            c for c in self._caravans.values()
            if c.status in (
                CaravanStatus.DEPARTING, CaravanStatus.IN_TRANSIT,
            )
        )

    def caravans_on_route(
        self, route_id: str,
    ) -> tuple[Caravan, ...]:
        return tuple(
            c for c in self._caravans.values()
            if c.route_id == route_id
        )

    def total_routes(self) -> int:
        return len(self._routes)


# --------------------------------------------------------------------
# Default route catalog — canonical FFXI overland routes
# --------------------------------------------------------------------
def _build_default_routes() -> tuple[TradeRoute, ...]:
    return (
        TradeRoute(
            route_id="bastok_jeuno_caravan",
            origin=Settlement.BASTOK,
            destination=Settlement.JEUNO,
            stops=(
                "north_gustaberg", "konschtat_highlands",
                "pashhow_marshlands", "rolanberry_fields",
                "lower_jeuno",
            ),
            goods_catalog=(
                GoodsBundle("mythril_ingot", 30),
                GoodsBundle("iron_ore", 60),
                GoodsBundle("smithing_tools", 10),
            ),
            frequency=Frequency.DAILY, base_risk=15,
        ),
        TradeRoute(
            route_id="san_doria_jeuno_caravan",
            origin=Settlement.SAN_DORIA,
            destination=Settlement.JEUNO,
            stops=(
                "east_ronfaure", "la_theine_plateau",
                "jugner_forest", "batallia_downs", "lower_jeuno",
            ),
            goods_catalog=(
                GoodsBundle("oak_lumber", 40),
                GoodsBundle("apple_mint", 50),
                GoodsBundle("noble_wine", 20),
            ),
            frequency=Frequency.DAILY, base_risk=12,
        ),
        TradeRoute(
            route_id="windurst_jeuno_caravan",
            origin=Settlement.WINDURST,
            destination=Settlement.JEUNO,
            stops=(
                "east_sarutabaruta", "tahrongi_canyon",
                "buburimu_peninsula", "meriphataud_mountains",
                "sauromugue_champaign", "lower_jeuno",
            ),
            goods_catalog=(
                GoodsBundle("yagudo_feather", 60),
                GoodsBundle("cotton_thread", 80),
                GoodsBundle("scroll_blank", 20),
            ),
            frequency=Frequency.DAILY, base_risk=15,
        ),
        TradeRoute(
            route_id="selbina_mhaura_ferry",
            origin=Settlement.SELBINA,
            destination=Settlement.MHAURA,
            stops=("buburimu_ferry_dock", "selbina_dock"),
            goods_catalog=(
                GoodsBundle("fish_fresh", 80),
                GoodsBundle("salt_block", 30),
            ),
            frequency=Frequency.HOURLY, base_risk=20,
        ),
        TradeRoute(
            route_id="bastok_san_doria_overland",
            origin=Settlement.BASTOK,
            destination=Settlement.SAN_DORIA,
            stops=(
                "north_gustaberg", "konschtat_highlands",
                "valkurm_dunes", "la_theine_plateau",
                "east_ronfaure",
            ),
            goods_catalog=(
                GoodsBundle("mythril_ingot", 20),
                GoodsBundle("oak_lumber", 30),
            ),
            frequency=Frequency.BUSY, base_risk=25,
        ),
        TradeRoute(
            route_id="jeuno_norg_corsair_run",
            origin=Settlement.JEUNO,
            destination=Settlement.NORG,
            stops=(
                "qufim_island", "lower_delkfutts_tower",
                "behemoths_dominion", "norg_outpost",
            ),
            goods_catalog=(
                GoodsBundle("smuggled_silk", 10),
                GoodsBundle("tenshodo_token", 5),
            ),
            frequency=Frequency.WEEKLY, base_risk=40,
        ),
    )


def seed_default_routes(
    registry: TradeRouteRegistry,
) -> TradeRouteRegistry:
    for r in _build_default_routes():
        registry.register_route(r)
    return registry


__all__ = [
    "Settlement", "CaravanStatus", "Frequency",
    "GoodsBundle", "TradeRoute", "Caravan",
    "DispatchResult", "AdvanceResult",
    "TradeRouteRegistry", "seed_default_routes",
]
