"""Aerial wreck salvage — downed-airship looting.

Mirrors wreck_salvage but with sky-specific behaviour:

- DECAY is faster than underwater (10 minutes vs 1 hour).
  Skies clear quickly; mobs scavenge wrecks before crews
  can mount a full salvage operation.
- SCAVENGER mobs (rocs, sky pirates) automatically chip
  away at cargo over time — even with no crews salvaging.
  set_scavenger_pressure controls how aggressive that is
  per wreck.
- Wrecks remember their CRASH BAND. They can be reached
  from adjacent bands but salvage rate scales by band gap.

Public surface
--------------
    AerialSalvageResult dataclass (frozen)
    AerialWreckSalvage
        .register_wreck(wreck_id, cargo_units, crash_band)
        .set_scavenger_pressure(wreck_id, units_per_second)
        .begin_salvage(crew_id, wreck_id, crew_band, now_seconds)
        .stop_salvage(crew_id, wreck_id)
        .tick(crew_id, wreck_id, crew_band, now_seconds)
            -> AerialSalvageResult
        .units_remaining(wreck_id) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t


# 10 minute decay window
DECAY_SECONDS = 10 * 60
# base rate; band-adjacent crews salvage slower
SALVAGE_RATE_UNITS_PER_SECOND = 0.2
# adjacent-band penalty multiplier
ADJACENT_BAND_PENALTY = 0.5


@dataclasses.dataclass
class _WreckState:
    wreck_id: str
    cargo_remaining: float
    crash_band: int
    decay_starts_at: t.Optional[int] = None
    scavenger_pressure: float = 0.0
    last_scavenger_tick: int = 0
    # crew_id -> last_tick_seconds
    active: dict[str, int] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class AerialSalvageResult:
    accepted: bool
    units_pulled: float = 0.0
    cargo_remaining: int = 0
    wreck_decayed: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class AerialWreckSalvage:
    _wrecks: dict[str, _WreckState] = dataclasses.field(default_factory=dict)

    def register_wreck(
        self, *, wreck_id: str,
        cargo_units: int, crash_band: int,
    ) -> bool:
        if not wreck_id or cargo_units <= 0:
            return False
        if wreck_id in self._wrecks:
            return False
        self._wrecks[wreck_id] = _WreckState(
            wreck_id=wreck_id,
            cargo_remaining=float(cargo_units),
            crash_band=crash_band,
        )
        return True

    def set_scavenger_pressure(
        self, *, wreck_id: str,
        units_per_second: float,
        now_seconds: int = 0,
    ) -> bool:
        w = self._wrecks.get(wreck_id)
        if w is None:
            return False
        w.scavenger_pressure = max(0.0, units_per_second)
        w.last_scavenger_tick = now_seconds
        return True

    def begin_salvage(
        self, *, crew_id: str, wreck_id: str,
        crew_band: int, now_seconds: int,
    ) -> bool:
        w = self._wrecks.get(wreck_id)
        if w is None:
            return False
        if self._is_decayed(w, now_seconds):
            return False
        if w.cargo_remaining <= 0:
            return False
        # band gap > 1 = unreachable
        if abs(crew_band - w.crash_band) > 1:
            return False
        if crew_id in w.active:
            return False
        self._apply_scavenger(w, now_seconds)
        w.active[crew_id] = now_seconds
        if w.decay_starts_at is None:
            w.decay_starts_at = now_seconds
        return True

    def stop_salvage(
        self, *, crew_id: str, wreck_id: str,
    ) -> bool:
        w = self._wrecks.get(wreck_id)
        if w is None or crew_id not in w.active:
            return False
        del w.active[crew_id]
        return True

    def tick(
        self, *, crew_id: str, wreck_id: str,
        crew_band: int, now_seconds: int,
    ) -> AerialSalvageResult:
        w = self._wrecks.get(wreck_id)
        if w is None:
            return AerialSalvageResult(False, reason="unknown wreck")
        if self._is_decayed(w, now_seconds):
            return AerialSalvageResult(
                False, reason="decayed",
                wreck_decayed=True,
                cargo_remaining=int(w.cargo_remaining),
            )
        last = w.active.get(crew_id)
        if last is None:
            return AerialSalvageResult(False, reason="not salvaging")
        # apply scavenger drain since last tick
        self._apply_scavenger(w, now_seconds)
        elapsed = max(0, now_seconds - last)
        n_active = max(1, len(w.active))
        per_crew_rate = SALVAGE_RATE_UNITS_PER_SECOND / n_active
        # adjacent-band penalty
        if crew_band != w.crash_band:
            per_crew_rate *= ADJACENT_BAND_PENALTY
        pulled = min(elapsed * per_crew_rate, w.cargo_remaining)
        w.cargo_remaining = max(0.0, w.cargo_remaining - pulled)
        w.active[crew_id] = now_seconds
        return AerialSalvageResult(
            accepted=True,
            units_pulled=pulled,
            cargo_remaining=int(w.cargo_remaining),
        )

    def units_remaining(self, *, wreck_id: str) -> int:
        w = self._wrecks.get(wreck_id)
        return int(w.cargo_remaining) if w else 0

    # ---

    def _is_decayed(self, w: _WreckState, now_seconds: int) -> bool:
        if w.decay_starts_at is None:
            return False
        return (now_seconds - w.decay_starts_at) >= DECAY_SECONDS

    def _apply_scavenger(self, w: _WreckState, now_seconds: int) -> None:
        if w.scavenger_pressure <= 0:
            w.last_scavenger_tick = now_seconds
            return
        elapsed = max(0, now_seconds - w.last_scavenger_tick)
        drain = elapsed * w.scavenger_pressure
        w.cargo_remaining = max(0.0, w.cargo_remaining - drain)
        w.last_scavenger_tick = now_seconds


__all__ = [
    "AerialSalvageResult", "AerialWreckSalvage",
    "DECAY_SECONDS", "SALVAGE_RATE_UNITS_PER_SECOND",
    "ADJACENT_BAND_PENALTY",
]
