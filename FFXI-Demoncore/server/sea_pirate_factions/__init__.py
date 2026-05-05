"""Sea pirate factions — surface pirate fleets that prey on ships.

The undersea expansion finally justifies the surface myth: ships
were going missing because pirates were taking them and (often)
the deep was eating the survivors. This module catalogs the
named pirate FLEETS that haunt specific naval lanes, each with
a flagship boss, a hunting ground, and a typical plunder profile.

Factions:
  TANGLED_FLAG        - opportunist freebooters; lowest threat
  CORSAIRS_OF_BRINE   - sanctioned privateers turned rogue
  SUNKEN_CROWN        - cult fleet allied with sirens
  DROWNED_PRINCES     - undead/fomor pirate captains; abyssal

Each fleet has a SHIP MANIFEST (named flagship + escorts), a
ZONE_TERRITORY (overlaps with airship_ferry lanes), and a
PLUNDER_PROFILE (gil + cargo + sometimes crew abductions —
those abductions feed the missing_ship_registry).

Public surface
--------------
    PirateFleet enum
    Threat enum         LOW / MID / HIGH / ABYSSAL
    PlunderKind enum    GIL_ONLY / GIL_AND_CARGO / FULL_TAKE_ABDUCT
    FleetProfile dataclass
    SeaPirateFactions
        .register_sighting(fleet, zone_id, now_seconds)
        .recent_sightings(fleet, since_seconds)
        .resolve_encounter(fleet, naval_strength,
                           pirate_strength_roll)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PirateFleet(str, enum.Enum):
    TANGLED_FLAG = "tangled_flag"
    CORSAIRS_OF_BRINE = "corsairs_of_brine"
    SUNKEN_CROWN = "sunken_crown"
    DROWNED_PRINCES = "drowned_princes"


class Threat(str, enum.Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    ABYSSAL = "abyssal"


class PlunderKind(str, enum.Enum):
    GIL_ONLY = "gil_only"
    GIL_AND_CARGO = "gil_and_cargo"
    FULL_TAKE_ABDUCT = "full_take_abduct"


class EncounterOutcome(str, enum.Enum):
    NAVY_REPELS = "navy_repels"
    PIRATES_BOARD = "pirates_board"
    SHIP_LOST = "ship_lost"


@dataclasses.dataclass(frozen=True)
class FleetProfile:
    fleet: PirateFleet
    threat: Threat
    flagship: str
    escort_count: int
    plunder: PlunderKind
    primary_zone_id: str
    description: str = ""


_PROFILES: dict[PirateFleet, FleetProfile] = {
    PirateFleet.TANGLED_FLAG: FleetProfile(
        fleet=PirateFleet.TANGLED_FLAG,
        threat=Threat.LOW,
        flagship="rusted_starboard",
        escort_count=2,
        plunder=PlunderKind.GIL_ONLY,
        primary_zone_id="tideplate_shallows",
        description="Rag-tag freebooters; loud and sloppy.",
    ),
    PirateFleet.CORSAIRS_OF_BRINE: FleetProfile(
        fleet=PirateFleet.CORSAIRS_OF_BRINE,
        threat=Threat.MID,
        flagship="emerald_sovereign",
        escort_count=3,
        plunder=PlunderKind.GIL_AND_CARGO,
        primary_zone_id="kelp_labyrinth",
        description="Rogue privateers; disciplined raids.",
    ),
    PirateFleet.SUNKEN_CROWN: FleetProfile(
        fleet=PirateFleet.SUNKEN_CROWN,
        threat=Threat.HIGH,
        flagship="black_lullaby",
        escort_count=4,
        plunder=PlunderKind.FULL_TAKE_ABDUCT,
        primary_zone_id="wreckage_graveyard",
        description="Cult fleet — sirens guide them, abductees feed "
                    "the deep.",
    ),
    PirateFleet.DROWNED_PRINCES: FleetProfile(
        fleet=PirateFleet.DROWNED_PRINCES,
        threat=Threat.ABYSSAL,
        flagship="hollow_admiral",
        escort_count=6,
        plunder=PlunderKind.FULL_TAKE_ABDUCT,
        primary_zone_id="abyss_trench",
        description="Undead captains; their hulls bleed black water.",
    ),
}


@dataclasses.dataclass
class _Sighting:
    fleet: PirateFleet
    zone_id: str
    seen_at: int


@dataclasses.dataclass(frozen=True)
class EncounterResult:
    accepted: bool
    fleet: PirateFleet
    outcome: EncounterOutcome
    plunder: PlunderKind = PlunderKind.GIL_ONLY
    abducted: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SeaPirateFactions:
    _sightings: list[_Sighting] = dataclasses.field(default_factory=list)

    def profile_for(
        self, *, fleet: PirateFleet,
    ) -> t.Optional[FleetProfile]:
        return _PROFILES.get(fleet)

    def register_sighting(
        self, *, fleet: PirateFleet,
        zone_id: str,
        now_seconds: int,
    ) -> bool:
        if fleet not in _PROFILES or not zone_id:
            return False
        self._sightings.append(
            _Sighting(fleet=fleet, zone_id=zone_id, seen_at=now_seconds)
        )
        return True

    def recent_sightings(
        self, *, fleet: PirateFleet,
        since_seconds: int,
    ) -> tuple[_Sighting, ...]:
        return tuple(
            s for s in self._sightings
            if s.fleet == fleet and s.seen_at >= since_seconds
        )

    def resolve_encounter(
        self, *, fleet: PirateFleet,
        naval_strength: int,
        pirate_strength_roll: int,
    ) -> EncounterResult:
        prof = _PROFILES.get(fleet)
        if prof is None:
            return EncounterResult(
                False, fleet, EncounterOutcome.SHIP_LOST,
                reason="unknown fleet",
            )
        if naval_strength < 0 or pirate_strength_roll < 0:
            return EncounterResult(
                False, fleet, EncounterOutcome.SHIP_LOST,
                reason="invalid strength",
            )
        # Outcome resolution
        if naval_strength > pirate_strength_roll:
            return EncounterResult(
                accepted=True, fleet=fleet,
                outcome=EncounterOutcome.NAVY_REPELS,
            )
        # naval loses; FULL_TAKE_ABDUCT escalates to SHIP_LOST when
        # the gap is severe (>=50% short)
        gap = pirate_strength_roll - naval_strength
        if (
            prof.plunder == PlunderKind.FULL_TAKE_ABDUCT
            and gap >= max(1, naval_strength // 2)
        ):
            return EncounterResult(
                accepted=True, fleet=fleet,
                outcome=EncounterOutcome.SHIP_LOST,
                plunder=prof.plunder,
                abducted=True,
            )
        return EncounterResult(
            accepted=True, fleet=fleet,
            outcome=EncounterOutcome.PIRATES_BOARD,
            plunder=prof.plunder,
            abducted=(prof.plunder == PlunderKind.FULL_TAKE_ABDUCT),
        )

    def total_fleets(self) -> int:
        return len(_PROFILES)


__all__ = [
    "PirateFleet", "Threat", "PlunderKind", "EncounterOutcome",
    "FleetProfile", "EncounterResult",
    "SeaPirateFactions",
]
