"""Witness system — eyewitness detection of crimes.

In retail FFXI, killing a town NPC just made the city's guards
aggro. In Demoncore, the world is watched. When a player
murders, steals, casts hostile magic in the wrong place, or
pickpockets, EVERY nearby AI entity has a chance to WITNESS the
act. Witnesses don't just trigger flags — they REMEMBER. They
identify the perp by name. They gossip about it.

Distinct from outlaw_system (the consequence — the bounty flag)
and from entity_memory (the storage). This module is the
DETECTION layer:

* Resolves who's in line-of-sight + earshot of the act.
* Computes per-witness identification confidence (full
  identification, partial, didn't-see-the-face).
* Filters witnesses by their personality (a SCHEMER might
  pretend they didn't see; a ZEALOT will report).
* Emits the canonical IdentificationReport that other
  systems consume.

Sensory channel
---------------
Each witness candidate has SIGHT, HEARING, and (rarer) MAGIC
SENSE. A spell cast from across a plaza is heard but not seen,
which gives lower-fidelity ID. A masked perp seen up close
gives PARTIAL ID. Bright daylight + close proximity +
unobstructed gives FULL ID.

Public surface
--------------
    CrimeKind enum
    SensoryChannel enum
    WitnessCandidate dataclass — entity nearby with sensors
    Crime dataclass — what happened
    IdentificationReport dataclass — outcome per witness
    WitnessSystem
        .register_witness(...)
        .observe_crime(...)
        .reports_for(crime_id) -> tuple[IdentificationReport, ...]
        .identifications_of(perp_id) -> tuple[IdentificationReport,...]
        .credible_witnesses(crime_id) — full ID + status==reported
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Sensory ranges in tile units.
SIGHT_BASE_RANGE = 30
HEARING_BASE_RANGE = 20
MAGIC_SENSE_BASE_RANGE = 50

# Confidence thresholds.
FULL_ID_CONFIDENCE = 70
PARTIAL_ID_CONFIDENCE = 35


class CrimeKind(str, enum.Enum):
    MURDER = "murder"                  # killing a peaceful entity
    THEFT = "theft"
    PICKPOCKET = "pickpocket"
    HOSTILE_MAGIC = "hostile_magic"   # casting in safe zone
    VANDALISM = "vandalism"
    ARSON = "arson"
    KIDNAPPING = "kidnapping"
    DESECRATION = "desecration"
    TREASON = "treason"


# How "loud" the crime is on each sensory channel. Modifies the
# witness's effective range.
class SensoryChannel(str, enum.Enum):
    SIGHT = "sight"
    HEARING = "hearing"
    MAGIC = "magic"


_CRIME_VISIBILITY: dict[CrimeKind, dict[SensoryChannel, float]] = {
    CrimeKind.MURDER: {
        SensoryChannel.SIGHT: 1.0, SensoryChannel.HEARING: 0.8,
        SensoryChannel.MAGIC: 0.0,
    },
    CrimeKind.THEFT: {
        SensoryChannel.SIGHT: 0.7, SensoryChannel.HEARING: 0.2,
        SensoryChannel.MAGIC: 0.0,
    },
    CrimeKind.PICKPOCKET: {
        SensoryChannel.SIGHT: 0.4, SensoryChannel.HEARING: 0.0,
        SensoryChannel.MAGIC: 0.0,
    },
    CrimeKind.HOSTILE_MAGIC: {
        SensoryChannel.SIGHT: 0.9, SensoryChannel.HEARING: 0.6,
        SensoryChannel.MAGIC: 1.5,
    },
    CrimeKind.VANDALISM: {
        SensoryChannel.SIGHT: 0.8, SensoryChannel.HEARING: 0.6,
        SensoryChannel.MAGIC: 0.0,
    },
    CrimeKind.ARSON: {
        SensoryChannel.SIGHT: 1.5, SensoryChannel.HEARING: 0.4,
        SensoryChannel.MAGIC: 0.5,
    },
    CrimeKind.KIDNAPPING: {
        SensoryChannel.SIGHT: 0.7, SensoryChannel.HEARING: 1.0,
        SensoryChannel.MAGIC: 0.0,
    },
    CrimeKind.DESECRATION: {
        SensoryChannel.SIGHT: 0.6, SensoryChannel.HEARING: 0.3,
        SensoryChannel.MAGIC: 0.5,
    },
    CrimeKind.TREASON: {
        SensoryChannel.SIGHT: 0.8, SensoryChannel.HEARING: 0.6,
        SensoryChannel.MAGIC: 0.0,
    },
}


class IdentificationLevel(str, enum.Enum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"


class WitnessStatus(str, enum.Enum):
    SAW_AND_REPORTED = "saw_and_reported"
    SAW_BUT_SILENT = "saw_but_silent"   # personality suppresses report
    DID_NOT_SEE = "did_not_see"


@dataclasses.dataclass(frozen=True)
class WitnessCandidate:
    """Entity that might witness a nearby crime."""
    entity_id: str
    position_tile: tuple[int, int]
    sight_range: int = SIGHT_BASE_RANGE
    hearing_range: int = HEARING_BASE_RANGE
    magic_sense_range: int = 0           # 0 = no magic sense
    obstructed: bool = False             # behind a wall etc.
    # Personality flags that affect REPORTING (not detection):
    is_schemer: bool = False
    is_zealot: bool = False
    is_coward: bool = False


@dataclasses.dataclass(frozen=True)
class Crime:
    crime_id: str
    kind: CrimeKind
    perp_id: str
    victim_id: t.Optional[str]
    position_tile: tuple[int, int]
    occurred_at_seconds: float
    perp_disguised: bool = False        # masked / hidden identity


@dataclasses.dataclass(frozen=True)
class IdentificationReport:
    crime_id: str
    witness_id: str
    perp_id: str
    identification_level: IdentificationLevel
    status: WitnessStatus
    confidence: int                     # 0..100
    primary_channel: t.Optional[SensoryChannel]
    notes: str = ""


def _distance(
    a: tuple[int, int], b: tuple[int, int],
) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _channel_confidence(
    *, channel: SensoryChannel, distance: float,
    base_range: int, crime_visibility: float, obstructed: bool,
) -> int:
    """0..100 confidence that this channel picked up the act."""
    if base_range <= 0 or crime_visibility <= 0:
        return 0
    effective_range = base_range * crime_visibility
    if distance >= effective_range:
        return 0
    raw = (1.0 - (distance / effective_range)) * 100.0
    if obstructed and channel == SensoryChannel.SIGHT:
        raw *= 0.3
    return int(round(max(0, min(100, raw))))


def _decide_status(
    *, candidate: WitnessCandidate, crime: Crime,
    confidence: int,
) -> WitnessStatus:
    if confidence == 0:
        return WitnessStatus.DID_NOT_SEE
    # Schemer with low-stakes crime might stay silent
    if candidate.is_schemer and crime.kind in (
        CrimeKind.PICKPOCKET, CrimeKind.THEFT,
    ):
        return WitnessStatus.SAW_BUT_SILENT
    # Coward witnessing a violent crime stays silent
    if candidate.is_coward and crime.kind in (
        CrimeKind.MURDER, CrimeKind.KIDNAPPING,
        CrimeKind.HOSTILE_MAGIC, CrimeKind.ARSON,
    ):
        return WitnessStatus.SAW_BUT_SILENT
    return WitnessStatus.SAW_AND_REPORTED


def _id_level_for_confidence(
    confidence: int, *, perp_disguised: bool,
) -> IdentificationLevel:
    """A disguise caps even high-confidence sightings at PARTIAL."""
    if confidence >= FULL_ID_CONFIDENCE and not perp_disguised:
        return IdentificationLevel.FULL
    if confidence >= PARTIAL_ID_CONFIDENCE:
        return IdentificationLevel.PARTIAL
    if confidence > 0:
        return IdentificationLevel.PARTIAL
    return IdentificationLevel.NONE


@dataclasses.dataclass
class WitnessSystem:
    _candidates: dict[str, WitnessCandidate] = dataclasses.field(
        default_factory=dict,
    )
    _reports_by_crime: dict[
        str, list[IdentificationReport],
    ] = dataclasses.field(default_factory=dict)
    _reports_by_perp: dict[
        str, list[IdentificationReport],
    ] = dataclasses.field(default_factory=dict)

    def register_witness(
        self, candidate: WitnessCandidate,
    ) -> WitnessCandidate:
        self._candidates[candidate.entity_id] = candidate
        return candidate

    def deregister_witness(self, *, entity_id: str) -> bool:
        return self._candidates.pop(entity_id, None) is not None

    def observe_crime(
        self, *, crime: Crime,
    ) -> tuple[IdentificationReport, ...]:
        """Walk every registered witness, compute who saw what."""
        out: list[IdentificationReport] = []
        visibility = _CRIME_VISIBILITY[crime.kind]
        for cand in self._candidates.values():
            distance = _distance(
                cand.position_tile, crime.position_tile,
            )
            # Try each channel; pick the strongest.
            best_conf = 0
            best_channel: t.Optional[SensoryChannel] = None
            for channel in SensoryChannel:
                if channel == SensoryChannel.SIGHT:
                    base = cand.sight_range
                elif channel == SensoryChannel.HEARING:
                    base = cand.hearing_range
                else:
                    base = cand.magic_sense_range
                conf = _channel_confidence(
                    channel=channel, distance=distance,
                    base_range=base,
                    crime_visibility=visibility[channel],
                    obstructed=cand.obstructed,
                )
                if conf > best_conf:
                    best_conf = conf
                    best_channel = channel
            id_level = _id_level_for_confidence(
                best_conf, perp_disguised=crime.perp_disguised,
            )
            status = _decide_status(
                candidate=cand, crime=crime, confidence=best_conf,
            )
            report = IdentificationReport(
                crime_id=crime.crime_id,
                witness_id=cand.entity_id,
                perp_id=crime.perp_id,
                identification_level=id_level,
                status=status,
                confidence=best_conf,
                primary_channel=best_channel,
            )
            out.append(report)
        # Index reports
        self._reports_by_crime[crime.crime_id] = list(out)
        for r in out:
            if r.status == WitnessStatus.SAW_AND_REPORTED:
                self._reports_by_perp.setdefault(
                    r.perp_id, [],
                ).append(r)
        return tuple(out)

    def reports_for(
        self, crime_id: str,
    ) -> tuple[IdentificationReport, ...]:
        return tuple(self._reports_by_crime.get(crime_id, ()))

    def identifications_of(
        self, perp_id: str,
    ) -> tuple[IdentificationReport, ...]:
        return tuple(self._reports_by_perp.get(perp_id, ()))

    def credible_witnesses(
        self, *, crime_id: str,
    ) -> tuple[IdentificationReport, ...]:
        """Witnesses with FULL ID who reported."""
        return tuple(
            r for r in self._reports_by_crime.get(crime_id, [])
            if r.status == WitnessStatus.SAW_AND_REPORTED
            and r.identification_level == IdentificationLevel.FULL
        )

    def total_witnesses(self) -> int:
        return len(self._candidates)


__all__ = [
    "SIGHT_BASE_RANGE", "HEARING_BASE_RANGE",
    "MAGIC_SENSE_BASE_RANGE",
    "FULL_ID_CONFIDENCE", "PARTIAL_ID_CONFIDENCE",
    "CrimeKind", "SensoryChannel",
    "WitnessCandidate", "Crime",
    "IdentificationLevel", "WitnessStatus",
    "IdentificationReport", "WitnessSystem",
]
