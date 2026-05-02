"""Airship / ferry — scheduled travel routes with timetables + encounters.

Routes are bidirectional pairs (Bastok <-> Jeuno) that depart on
fixed Vana'diel intervals. Boarding requires a ticket purchase
(gil) and sometimes an attunement key item (e.g. Airship Pass).

Voyages roll an encounter on departure — most are NORMAL, but
ferries can be attacked by Pirates (day-biased) or Fomors (night-
biased), and airships can be attacked by Sky Pirates (day-biased)
or rogue Automatons (night-biased). Players who stay inside are
safe from death, but if the threat is not repelled the ferry
shipwrecks (or airship crash-lands) at a route-specific dropoff
zone with a 10% gil loss; players have to walk/run the rest of
the way to the destination.

Public surface
--------------
    Route catalog (ferry/airship)
    next_departure(route, now_vanadiel_tick) -> int
    purchase_ticket(...) -> TicketResult
    EncounterKind enum
    roll_encounter(transport, is_night, rng_pool) -> EncounterKind
    random_party_comp(kind, avg_level, rng_pool) -> EnemyParty
    resolve_voyage(route, encounter_kind, repelled, rng_pool)
        -> VoyageOutcome
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_ENCOUNTER_GEN


VANADIEL_DAY_SECONDS = 24 * 60 * 60   # one Vana day in seconds
                                       # (we use real-time abstraction)

# 10% gil loss when wrecked/crashed and the players have to walk.
GIL_LOSS_ON_CRASH_PCT = 10


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
    # Mid-route zones the vessel can be downed at if a threat
    # isn't repelled. Players spawn at one of these on crash.
    dropoff_zones: tuple[str, ...] = ()


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
        dropoff_zones=("buburimu_peninsula", "tahrongi_canyon"),
    ),
    Route(
        route_id="ferry_mhaura_to_selbina",
        label="Mhaura -> Selbina",
        transport_kind=TransportKind.FERRY,
        from_zone="mhaura", to_zone="selbina",
        fare_gil=100, travel_seconds=10 * 60,
        departures_per_day=(2 * 3600, 6 * 3600, 10 * 3600,
                            14 * 3600, 18 * 3600, 22 * 3600),
        dropoff_zones=("buburimu_peninsula", "tahrongi_canyon"),
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
        dropoff_zones=("pashhow_marshlands", "rolanberry_fields"),
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
        dropoff_zones=("jugner_forest", "batallia_downs"),
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
        dropoff_zones=("sauromugue_champaign", "meriphataud_mountains"),
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


# -- voyage encounters ----------------------------------------------

class EncounterKind(str, enum.Enum):
    """What's happening on this voyage."""
    NORMAL = "normal"
    FERRY_PIRATES = "ferry_pirates"
    FERRY_FOMORS = "ferry_fomors"
    SKY_PIRATES = "sky_pirates"
    AUTOMATONS = "automatons"


# Day/night encounter probability tables (sum to 1.0)
_DAY_FERRY_PROBS: tuple[tuple[EncounterKind, float], ...] = (
    (EncounterKind.NORMAL,         0.70),
    (EncounterKind.FERRY_PIRATES,  0.25),
    (EncounterKind.FERRY_FOMORS,   0.05),
)
_NIGHT_FERRY_PROBS: tuple[tuple[EncounterKind, float], ...] = (
    (EncounterKind.NORMAL,         0.70),
    (EncounterKind.FERRY_PIRATES,  0.05),
    (EncounterKind.FERRY_FOMORS,   0.25),
)
_DAY_AIRSHIP_PROBS: tuple[tuple[EncounterKind, float], ...] = (
    (EncounterKind.NORMAL,       0.70),
    (EncounterKind.SKY_PIRATES,  0.25),
    (EncounterKind.AUTOMATONS,   0.05),
)
_NIGHT_AIRSHIP_PROBS: tuple[tuple[EncounterKind, float], ...] = (
    (EncounterKind.NORMAL,       0.70),
    (EncounterKind.SKY_PIRATES,  0.05),
    (EncounterKind.AUTOMATONS,   0.25),
)


# Random party-comp pools per threat kind
_PIRATE_JOBS = ("warrior", "thief", "ranger", "monk", "corsair")
_PIRATE_NAMES = (
    "Pirate Cutthroat", "Pirate Gunner", "Pirate Quartermaster",
    "Pirate Boatswain", "Pirate Captain", "Pirate Bilge Rat",
)
_FOMOR_JOBS = ("warrior", "monk", "white_mage", "black_mage",
                "ninja", "samurai", "thief", "red_mage", "ranger")
_FOMOR_NAMES = (
    "Fomor Warrior", "Fomor Monk", "Fomor Mage",
    "Fomor Sentinel", "Fomor Reaper", "Fomor Ranger",
    "Fomor Mystic",
)
_SKY_PIRATE_JOBS = ("ranger", "thief", "corsair", "warrior", "monk")
_SKY_PIRATE_NAMES = (
    "Sky Pirate Lookout", "Sky Pirate Fencer",
    "Sky Pirate Gunslinger", "Sky Pirate Marauder",
    "Sky Pirate Captain",
)
_AUTOMATON_JOBS = ("puppetmaster",)   # all PUP-style
_AUTOMATON_NAMES = (
    "Combat Automaton", "Healing Automaton",
    "Spellbinder Automaton", "Sentinel Automaton",
    "Striker Automaton", "Rogue Automaton",
)


@dataclasses.dataclass(frozen=True)
class EnemyPartyMember:
    name: str
    job: str
    level: int


@dataclasses.dataclass(frozen=True)
class EnemyParty:
    kind: EncounterKind
    members: tuple[EnemyPartyMember, ...]
    avg_level: int


def is_night_hour(vanadiel_hour: int) -> bool:
    """20:00 - 5:59 inclusive is night."""
    return vanadiel_hour >= 20 or vanadiel_hour < 6


def roll_encounter(
    *,
    transport_kind: TransportKind,
    is_night: bool,
    rng_pool: RngPool,
    stream_name: str = STREAM_ENCOUNTER_GEN,
) -> EncounterKind:
    """Pick which encounter happens this voyage."""
    if transport_kind == TransportKind.FERRY:
        table = _NIGHT_FERRY_PROBS if is_night else _DAY_FERRY_PROBS
    else:
        table = _NIGHT_AIRSHIP_PROBS if is_night else _DAY_AIRSHIP_PROBS
    rng = rng_pool.stream(stream_name)
    roll = rng.random()
    cum = 0.0
    for kind, prob in table:
        cum += prob
        if roll < cum:
            return kind
    return EncounterKind.NORMAL


def random_party_comp(
    *,
    kind: EncounterKind,
    avg_level: int,
    rng_pool: RngPool,
    stream_name: str = STREAM_ENCOUNTER_GEN,
) -> EnemyParty:
    """Build a random party of 3-6 members for the given threat."""
    if kind == EncounterKind.NORMAL:
        return EnemyParty(kind=kind, members=(), avg_level=0)
    rng = rng_pool.stream(stream_name)
    if kind == EncounterKind.FERRY_PIRATES:
        jobs, names = _PIRATE_JOBS, _PIRATE_NAMES
    elif kind == EncounterKind.FERRY_FOMORS:
        jobs, names = _FOMOR_JOBS, _FOMOR_NAMES
    elif kind == EncounterKind.SKY_PIRATES:
        jobs, names = _SKY_PIRATE_JOBS, _SKY_PIRATE_NAMES
    elif kind == EncounterKind.AUTOMATONS:
        jobs, names = _AUTOMATON_JOBS, _AUTOMATON_NAMES
    else:
        return EnemyParty(kind=kind, members=(), avg_level=0)
    member_count = rng.randint(3, 6)
    members: list[EnemyPartyMember] = []
    for _ in range(member_count):
        job = rng.choice(jobs)
        lvl = max(1, avg_level + rng.randint(-3, 3))
        name = rng.choice(names)
        members.append(EnemyPartyMember(name=name, job=job, level=lvl))
    realized_avg = sum(m.level for m in members) // len(members)
    return EnemyParty(
        kind=kind, members=tuple(members), avg_level=realized_avg,
    )


@dataclasses.dataclass(frozen=True)
class VoyageOutcome:
    encounter_kind: EncounterKind
    enemy_party: t.Optional[EnemyParty]
    repelled: bool
    arrived_at_destination: bool
    final_zone: str
    gil_loss_pct: int


def resolve_voyage(
    *,
    route_id: str,
    encounter_kind: EncounterKind,
    enemy_party: t.Optional[EnemyParty],
    repelled: bool,
    rng_pool: RngPool,
    stream_name: str = STREAM_ENCOUNTER_GEN,
) -> VoyageOutcome:
    """Compute the voyage's final outcome.

    NORMAL -> safe arrival, no party.
    Threat repelled -> safe arrival.
    Threat not repelled -> wreck/crash at a route dropoff zone,
                           10% gil loss.

    Players who STAYED INSIDE during the encounter never die — that
    safety contract is enforced by the caller (encounter logic);
    this resolver just packages the outcome.
    """
    route = ROUTE_BY_ID.get(route_id)
    if route is None:
        return VoyageOutcome(
            encounter_kind=encounter_kind,
            enemy_party=None, repelled=False,
            arrived_at_destination=False,
            final_zone="",
            gil_loss_pct=0,
        )

    if encounter_kind == EncounterKind.NORMAL:
        return VoyageOutcome(
            encounter_kind=encounter_kind,
            enemy_party=None, repelled=True,
            arrived_at_destination=True,
            final_zone=route.to_zone,
            gil_loss_pct=0,
        )

    if repelled:
        return VoyageOutcome(
            encounter_kind=encounter_kind,
            enemy_party=enemy_party, repelled=True,
            arrived_at_destination=True,
            final_zone=route.to_zone,
            gil_loss_pct=0,
        )

    # Wreck / crash — pick a dropoff zone.
    if route.dropoff_zones:
        rng = rng_pool.stream(stream_name)
        dropoff = rng.choice(list(route.dropoff_zones))
    else:
        # Fallback: drop at origin if no dropoff zones registered
        dropoff = route.from_zone

    return VoyageOutcome(
        encounter_kind=encounter_kind,
        enemy_party=enemy_party, repelled=False,
        arrived_at_destination=False,
        final_zone=dropoff,
        gil_loss_pct=GIL_LOSS_ON_CRASH_PCT,
    )


__all__ = [
    "VANADIEL_DAY_SECONDS", "GIL_LOSS_ON_CRASH_PCT",
    "TransportKind", "Route",
    "ROUTES", "ROUTE_BY_ID",
    "TicketResult",
    "next_departure", "purchase_ticket",
    "EncounterKind",
    "EnemyPartyMember", "EnemyParty",
    "is_night_hour",
    "roll_encounter", "random_party_comp",
    "VoyageOutcome", "resolve_voyage",
]
