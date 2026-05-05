"""Sonar ping — active reveal vs passive listen.

Underwater there is no line-of-sight; you find each other
by sound. Two modes:

ACTIVE PING
  Emit a ping. Reveals every entity within ACTIVE_RADIUS for
  REVEAL_DURATION seconds. Costs you: anyone within
  PASSIVE_RADIUS (= ACTIVE_RADIUS * 2) hears it and learns
  your position. 30s cooldown so you can't just spam.

PASSIVE LISTEN
  Always-on if the submarine has the passive sonar module
  installed. Hears active pings within passive range and
  reports them as PassiveDetection events. Doesn't reveal
  the listener's own position.

This is the prisoners-dilemma core of underwater PvP — every
ping you fire trades information for exposure. Doctrine
emerges naturally: stealthy hunters listen, panicked
defenders ping.

Public surface
--------------
    SonarContact dataclass (frozen)
    PassiveDetection dataclass (frozen)
    PingResult dataclass (frozen)
    SonarPing
        .register(sub_id, x, y, band, has_passive)
        .update(sub_id, x, y, band)
        .active_ping(sub_id, now_seconds) -> PingResult
        .passive_listen(sub_id) -> tuple[PassiveDetection, ...]
        .last_ping_at(sub_id) -> int or None
"""
from __future__ import annotations

import dataclasses
import math
import typing as t


ACTIVE_RADIUS = 300.0
PASSIVE_RADIUS = ACTIVE_RADIUS * 2.0
PING_COOLDOWN_SECONDS = 30
REVEAL_DURATION_SECONDS = 5
# vertical units per band gap — sound travels poorly across
# thermoclines, so each band is a meaningful distance
BAND_VERTICAL_WEIGHT = 100.0


@dataclasses.dataclass
class _Sub:
    sub_id: str
    x: float
    y: float
    band: int
    has_passive: bool


@dataclasses.dataclass(frozen=True)
class SonarContact:
    sub_id: str
    x: float
    y: float
    band: int
    distance: float


@dataclasses.dataclass(frozen=True)
class PassiveDetection:
    pinger_sub_id: str
    pinger_x: float
    pinger_y: float
    pinger_band: int
    distance: float
    detected_at: int


@dataclasses.dataclass(frozen=True)
class PingResult:
    accepted: bool
    reveals: tuple[SonarContact, ...] = ()
    heard_by: tuple[str, ...] = ()
    reason: t.Optional[str] = None


def _dist(a: _Sub, b: _Sub) -> float:
    # band gap is weighted because sound crosses thermoclines
    # poorly — a few hundred horizontal meters is one thing,
    # a band of cold layer between you and the target is
    # something else. BAND_VERTICAL_WEIGHT calibrates that.
    dz = (a.band - b.band) * BAND_VERTICAL_WEIGHT
    return math.sqrt(
        (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + dz * dz,
    )


@dataclasses.dataclass
class SonarPing:
    _subs: dict[str, _Sub] = dataclasses.field(default_factory=dict)
    _last_ping_at: dict[str, int] = dataclasses.field(default_factory=dict)
    # ring buffer of pings each passive sub has heard; cleared on read
    _pending_passive: dict[str, list[PassiveDetection]] = dataclasses.field(
        default_factory=dict,
    )

    def register(
        self, *, sub_id: str,
        x: float, y: float, band: int,
        has_passive: bool = False,
    ) -> bool:
        if not sub_id:
            return False
        self._subs[sub_id] = _Sub(
            sub_id=sub_id, x=x, y=y, band=band,
            has_passive=has_passive,
        )
        return True

    def update(
        self, *, sub_id: str,
        x: float, y: float, band: int,
    ) -> bool:
        s = self._subs.get(sub_id)
        if s is None:
            return False
        s.x, s.y, s.band = x, y, band
        return True

    def active_ping(
        self, *, sub_id: str, now_seconds: int,
    ) -> PingResult:
        me = self._subs.get(sub_id)
        if me is None:
            return PingResult(False, reason="unknown sub")
        last = self._last_ping_at.get(sub_id)
        if last is not None and (now_seconds - last) < PING_COOLDOWN_SECONDS:
            return PingResult(False, reason="cooldown")
        self._last_ping_at[sub_id] = now_seconds
        reveals: list[SonarContact] = []
        heard_by: list[str] = []
        for other in self._subs.values():
            if other.sub_id == sub_id:
                continue
            d = _dist(me, other)
            if d <= ACTIVE_RADIUS:
                reveals.append(SonarContact(
                    sub_id=other.sub_id,
                    x=other.x, y=other.y, band=other.band,
                    distance=d,
                ))
            if other.has_passive and d <= PASSIVE_RADIUS:
                heard_by.append(other.sub_id)
                self._pending_passive.setdefault(
                    other.sub_id, [],
                ).append(PassiveDetection(
                    pinger_sub_id=sub_id,
                    pinger_x=me.x, pinger_y=me.y,
                    pinger_band=me.band,
                    distance=d, detected_at=now_seconds,
                ))
        return PingResult(
            accepted=True,
            reveals=tuple(reveals),
            heard_by=tuple(heard_by),
        )

    def passive_listen(
        self, *, sub_id: str,
    ) -> tuple[PassiveDetection, ...]:
        pending = self._pending_passive.pop(sub_id, [])
        return tuple(pending)

    def last_ping_at(
        self, *, sub_id: str,
    ) -> t.Optional[int]:
        return self._last_ping_at.get(sub_id)


__all__ = [
    "SonarContact", "PassiveDetection", "PingResult",
    "SonarPing",
    "ACTIVE_RADIUS", "PASSIVE_RADIUS",
    "PING_COOLDOWN_SECONDS", "REVEAL_DURATION_SECONDS",
    "BAND_VERTICAL_WEIGHT",
]
