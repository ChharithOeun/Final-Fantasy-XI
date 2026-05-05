"""Tide cycle clock — global tide drives zone access.

Vana'diel's seas rise and fall on a 24-hour Vana'diel cycle.
The tide doesn't change combat much, but it gates SHALLOWS
zones: at high tide, surface trade lanes flood and become
underwater accessible. At low tide, those same lanes are
walkable beach with surface-only mob encounters. Some zones
only open during specific tide phases.

Tide phases (each lasts 6 Vana'diel hours = 1/4 day):
  RISING   - water creeping in
  HIGH     - peak; submerged lanes accessible to divers
  EBBING   - water pulling out
  LOW      - peak low; shallows exposed; salvage easier

Each ZONE binds to a tide_access policy:
  TIDE_AGNOSTIC      - always accessible
  HIGH_TIDE_ONLY     - only RISING+HIGH (can dive in)
  LOW_TIDE_ONLY      - only EBBING+LOW (walking access)

The cycle is anchored to a TIDE_EPOCH (the first RISING
tide). All future tide queries are derived from the offset
since that epoch.

Public surface
--------------
    TidePhase enum
    TideAccess enum
    TideCycleClock
        .phase_at(now_seconds)       -> TidePhase
        .is_accessible(zone_access, now_seconds)
        .next_phase_change_after(now_seconds) -> int seconds-from-epoch
"""
from __future__ import annotations

import dataclasses
import enum


class TidePhase(str, enum.Enum):
    RISING = "rising"
    HIGH = "high"
    EBBING = "ebbing"
    LOW = "low"


class TideAccess(str, enum.Enum):
    TIDE_AGNOSTIC = "agnostic"
    HIGH_TIDE_ONLY = "high_only"
    LOW_TIDE_ONLY = "low_only"


# 24-hour cycle, 4 phases of 6 hours each.
# (Real-world seconds; callers can map to Vana'diel time
# by passing in Vana'diel-clock seconds.)
_PHASE_LENGTH_SECONDS = 6 * 3_600
_CYCLE_LENGTH_SECONDS = 4 * _PHASE_LENGTH_SECONDS

_PHASE_ORDER: tuple[TidePhase, ...] = (
    TidePhase.RISING,
    TidePhase.HIGH,
    TidePhase.EBBING,
    TidePhase.LOW,
)

_HIGH_TIDE_PHASES = (TidePhase.RISING, TidePhase.HIGH)
_LOW_TIDE_PHASES = (TidePhase.EBBING, TidePhase.LOW)


@dataclasses.dataclass
class TideCycleClock:
    tide_epoch_seconds: int = 0

    def phase_at(self, *, now_seconds: int) -> TidePhase:
        offset = (now_seconds - self.tide_epoch_seconds) % _CYCLE_LENGTH_SECONDS
        if offset < 0:
            offset += _CYCLE_LENGTH_SECONDS
        index = offset // _PHASE_LENGTH_SECONDS
        return _PHASE_ORDER[index]

    def is_accessible(
        self, *, zone_access: TideAccess, now_seconds: int,
    ) -> bool:
        if zone_access == TideAccess.TIDE_AGNOSTIC:
            return True
        phase = self.phase_at(now_seconds=now_seconds)
        if zone_access == TideAccess.HIGH_TIDE_ONLY:
            return phase in _HIGH_TIDE_PHASES
        if zone_access == TideAccess.LOW_TIDE_ONLY:
            return phase in _LOW_TIDE_PHASES
        return False

    def next_phase_change_after(
        self, *, now_seconds: int,
    ) -> int:
        offset = (now_seconds - self.tide_epoch_seconds) % _CYCLE_LENGTH_SECONDS
        if offset < 0:
            offset += _CYCLE_LENGTH_SECONDS
        cycles = (now_seconds - self.tide_epoch_seconds) // _CYCLE_LENGTH_SECONDS
        if (now_seconds - self.tide_epoch_seconds) < 0:
            cycles -= 1
        index = offset // _PHASE_LENGTH_SECONDS
        # next change = epoch + cycles*cycle + (index+1)*phase
        return (
            self.tide_epoch_seconds
            + cycles * _CYCLE_LENGTH_SECONDS
            + (index + 1) * _PHASE_LENGTH_SECONDS
        )

    def time_until_next_phase(
        self, *, now_seconds: int,
    ) -> int:
        return self.next_phase_change_after(
            now_seconds=now_seconds,
        ) - now_seconds


__all__ = [
    "TidePhase", "TideAccess", "TideCycleClock",
]
