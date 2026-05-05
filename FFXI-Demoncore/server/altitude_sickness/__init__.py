"""Altitude sickness — thin-air analogue to oxygen_system.

Going above the MID band (cruise altitude) without gear is
risky. Players accumulate ALTITUDE STRESS at HIGH and
STRATOSPHERE bands; once stress crosses STRESS_HARM_THRESHOLD
they start taking damage (decompression sickness, hypoxia,
disorientation).

Gear stacks the same way oxygen gear does:
    OXYGEN_MASK   — safe to HIGH (no stress accrues at HIGH)
    PRESSURE_SUIT — safe to STRATOSPHERE (no stress at any band)

Climbing too fast also adds STRESS — ascending more than one
band per ASCENT_WINDOW_SECONDS spikes the meter (barotrauma).
Descending below MID clears stress over time.

Public surface
--------------
    AltitudeGear str enum
    AltitudeStatus dataclass (frozen)
    AltitudeSickness
        .register(player_id)
        .equip_gear(player_id, gear)
        .unequip_gear(player_id, gear)
        .set_band(player_id, band, now_seconds)
        .tick(player_id, now_seconds) -> AltitudeStatus
        .is_suffering(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AltitudeGear(str, enum.Enum):
    OXYGEN_MASK = "oxygen_mask"
    PRESSURE_SUIT = "pressure_suit"


# bands above this accrue stress without proper gear
SAFE_BAND_CEILING = 2          # MID
HIGH_BAND = 3
STRATOSPHERE_BAND = 4
LOW_BAND_CEILING = 1           # at LOW or below, stress decays

# per-tick (per-second) stress accrual rates
HIGH_STRESS_PER_SECOND = 0.5
STRATOSPHERE_STRESS_PER_SECOND = 1.5
STRESS_DECAY_PER_SECOND_AT_LOW = 1.0

STRESS_MAX = 100.0
STRESS_HARM_THRESHOLD = 70.0

# barotrauma — ascending too fast
ASCENT_WINDOW_SECONDS = 5
RAPID_ASCENT_STRESS_SPIKE = 25.0


@dataclasses.dataclass
class _Player:
    player_id: str
    gear: set[AltitudeGear] = dataclasses.field(default_factory=set)
    band: int = 0
    last_tick: int = 0
    last_band_change: int = 0
    band_ever_set: bool = False
    stress: float = 0.0


@dataclasses.dataclass(frozen=True)
class AltitudeStatus:
    stress: float
    suffering: bool
    band: int


def _safe_at(band: int, gear: t.Iterable[AltitudeGear]) -> bool:
    if band <= SAFE_BAND_CEILING:
        return True
    if AltitudeGear.PRESSURE_SUIT in gear:
        return True
    if band == HIGH_BAND and AltitudeGear.OXYGEN_MASK in gear:
        return True
    return False


@dataclasses.dataclass
class AltitudeSickness:
    _players: dict[str, _Player] = dataclasses.field(default_factory=dict)

    def register(self, *, player_id: str) -> bool:
        if not player_id or player_id in self._players:
            return False
        self._players[player_id] = _Player(player_id=player_id)
        return True

    def equip_gear(
        self, *, player_id: str, gear: AltitudeGear,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None:
            return False
        p.gear.add(gear)
        return True

    def unequip_gear(
        self, *, player_id: str, gear: AltitudeGear,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None or gear not in p.gear:
            return False
        p.gear.discard(gear)
        return True

    def set_band(
        self, *, player_id: str,
        band: int, now_seconds: int,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None:
            return False
        # advance against the OLD band first
        self._advance(p, now_seconds)
        old_band = p.band
        # rapid-ascent barotrauma: jumping > 1 band in window;
        # only applies after the player's first set_band call,
        # so the initial spawn placement doesn't fire it
        if (
            p.band_ever_set
            and band - old_band > 1
            and (now_seconds - p.last_band_change) <= ASCENT_WINDOW_SECONDS
        ):
            p.stress = min(STRESS_MAX, p.stress + RAPID_ASCENT_STRESS_SPIKE)
        p.band = band
        p.last_band_change = now_seconds
        p.band_ever_set = True
        return True

    def tick(
        self, *, player_id: str, now_seconds: int,
    ) -> t.Optional[AltitudeStatus]:
        p = self._players.get(player_id)
        if p is None:
            return None
        self._advance(p, now_seconds)
        return AltitudeStatus(
            stress=p.stress,
            suffering=p.stress >= STRESS_HARM_THRESHOLD,
            band=p.band,
        )

    def is_suffering(self, *, player_id: str) -> bool:
        p = self._players.get(player_id)
        return bool(p and p.stress >= STRESS_HARM_THRESHOLD)

    def _advance(self, p: _Player, now_seconds: int) -> None:
        elapsed = max(0, now_seconds - p.last_tick)
        p.last_tick = now_seconds
        if elapsed == 0:
            return
        # gear-protected at this band? no stress accrual
        safe = _safe_at(p.band, p.gear)
        if safe:
            # decay only if at LOW band or below
            if p.band <= LOW_BAND_CEILING:
                p.stress = max(
                    0.0, p.stress - elapsed * STRESS_DECAY_PER_SECOND_AT_LOW,
                )
            return
        # unprotected at HIGH or STRATOSPHERE
        if p.band == HIGH_BAND:
            p.stress = min(
                STRESS_MAX, p.stress + elapsed * HIGH_STRESS_PER_SECOND,
            )
        elif p.band == STRATOSPHERE_BAND:
            p.stress = min(
                STRESS_MAX,
                p.stress + elapsed * STRATOSPHERE_STRESS_PER_SECOND,
            )


__all__ = [
    "AltitudeGear", "AltitudeStatus", "AltitudeSickness",
    "SAFE_BAND_CEILING", "HIGH_BAND", "STRATOSPHERE_BAND",
    "LOW_BAND_CEILING", "STRESS_MAX",
    "STRESS_HARM_THRESHOLD",
    "HIGH_STRESS_PER_SECOND",
    "STRATOSPHERE_STRESS_PER_SECOND",
    "STRESS_DECAY_PER_SECOND_AT_LOW",
    "ASCENT_WINDOW_SECONDS",
    "RAPID_ASCENT_STRESS_SPIKE",
]
