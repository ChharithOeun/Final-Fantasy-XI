"""Wreck salvage — pull cargo from sunken ships.

Naval PvP creates wrecks (via prize_court). Wrecks
register as WRECK landmarks (via seafloor_landmarks). Now
crews can dive on them and pull cargo over time. Each
wreck has a finite cargo_units pool that drains as crews
salvage. Once any crew starts salvaging, a DECAY clock
begins — the wreck rots away after DECAY_SECONDS even if
nobody finishes.

Multiple crews can salvage the same wreck simultaneously.
Each tick, the wreck's per-second yield is split equally
among the active crews. This is the "contested wreck"
mechanic: more crews showing up means everyone gets less.

Public surface
--------------
    Wreck dataclass (frozen)
    SalvageTickResult dataclass (frozen)
    WreckSalvage
        .register_wreck(wreck_id, cargo_units)
        .begin_salvage(crew_id, wreck_id, now_seconds) -> bool
        .stop_salvage(crew_id, wreck_id) -> bool
        .tick(crew_id, wreck_id, now_seconds) -> SalvageTickResult
        .units_remaining(wreck_id) -> int
        .active_crews(wreck_id) -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import typing as t


# wrecks rot away this long after first salvage starts
DECAY_SECONDS = 60 * 60          # 1 hour
SALVAGE_RATE_UNITS_PER_SECOND = 0.1  # 1 unit / 10s solo


@dataclasses.dataclass
class _WreckState:
    wreck_id: str
    cargo_remaining: float
    decay_starts_at: t.Optional[int] = None
    # crew_id -> last_tick_seconds
    active: dict[str, int] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class Wreck:
    wreck_id: str
    cargo_remaining: int
    decay_starts_at: t.Optional[int]


@dataclasses.dataclass(frozen=True)
class SalvageTickResult:
    accepted: bool
    units_pulled: float = 0.0
    cargo_remaining: int = 0
    wreck_decayed: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class WreckSalvage:
    _wrecks: dict[str, _WreckState] = dataclasses.field(default_factory=dict)

    def register_wreck(
        self, *, wreck_id: str, cargo_units: int,
    ) -> bool:
        if not wreck_id or cargo_units <= 0:
            return False
        if wreck_id in self._wrecks:
            return False
        self._wrecks[wreck_id] = _WreckState(
            wreck_id=wreck_id,
            cargo_remaining=float(cargo_units),
        )
        return True

    def begin_salvage(
        self, *, crew_id: str, wreck_id: str,
        now_seconds: int,
    ) -> bool:
        w = self._wrecks.get(wreck_id)
        if w is None:
            return False
        if self._is_decayed(w, now_seconds):
            return False
        if w.cargo_remaining <= 0:
            return False
        if crew_id in w.active:
            return False
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
        now_seconds: int,
    ) -> SalvageTickResult:
        w = self._wrecks.get(wreck_id)
        if w is None:
            return SalvageTickResult(False, reason="unknown wreck")
        if self._is_decayed(w, now_seconds):
            return SalvageTickResult(
                False, reason="decayed",
                wreck_decayed=True,
                cargo_remaining=int(w.cargo_remaining),
            )
        last = w.active.get(crew_id)
        if last is None:
            return SalvageTickResult(False, reason="not salvaging")
        elapsed = max(0, now_seconds - last)
        # share rate equally among active crews
        n_active = max(1, len(w.active))
        per_crew_rate = SALVAGE_RATE_UNITS_PER_SECOND / n_active
        pulled = min(elapsed * per_crew_rate, w.cargo_remaining)
        w.cargo_remaining -= pulled
        w.active[crew_id] = now_seconds
        return SalvageTickResult(
            accepted=True,
            units_pulled=pulled,
            cargo_remaining=int(w.cargo_remaining),
            wreck_decayed=False,
        )

    def units_remaining(
        self, *, wreck_id: str,
    ) -> int:
        w = self._wrecks.get(wreck_id)
        return int(w.cargo_remaining) if w else 0

    def active_crews(
        self, *, wreck_id: str,
    ) -> tuple[str, ...]:
        w = self._wrecks.get(wreck_id)
        return tuple(w.active.keys()) if w else ()

    # ---

    def _is_decayed(
        self, w: _WreckState, now_seconds: int,
    ) -> bool:
        if w.decay_starts_at is None:
            return False
        return (now_seconds - w.decay_starts_at) >= DECAY_SECONDS


__all__ = [
    "Wreck", "SalvageTickResult", "WreckSalvage",
    "DECAY_SECONDS", "SALVAGE_RATE_UNITS_PER_SECOND",
]
