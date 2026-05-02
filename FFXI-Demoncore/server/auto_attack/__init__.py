"""Auto-attack — swing timer + delay + double/triple attack rolls.

Each weapon has a base delay (240 = ~4s, 480 = ~8s, etc.). Haste %
shortens delay; Slow % lengthens. Each tick the engine asks "is the
next swing due?" and on yes, rolls double/triple/multi-hit procs
via rng_pool.

Public surface
--------------
    SwingTimer per equipped weapon
        .next_swing_at(now)
        .can_swing(now)
        .swing(rng_pool) -> SwingResult
    next_swing_delay(base_delay, haste_pct, slow_pct)
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.rng_pool import RngPool, STREAM_LOOT_DROPS


# Retail uses delay/60 = seconds at 0% haste. Cap haste at +43% per
# canonical FFXI; we follow that.
HASTE_CAP_PCT = 43


def next_swing_delay(
    *,
    base_delay: int,
    haste_pct: int = 0,
    slow_pct: int = 0,
) -> float:
    """Return the actual swing interval in seconds."""
    if base_delay <= 0:
        raise ValueError("base_delay must be > 0")
    haste_pct = min(haste_pct, HASTE_CAP_PCT)
    haste_pct = max(0, haste_pct)
    slow_pct = max(0, slow_pct)
    # net_speed = 1 - haste% + slow%
    multiplier = max(0.1, 1.0 - haste_pct / 100.0 + slow_pct / 100.0)
    seconds = (base_delay / 60.0) * multiplier
    return max(0.5, seconds)


@dataclasses.dataclass(frozen=True)
class SwingResult:
    landed: bool
    hit_count: int        # 1 = single, 2 = double-attack, etc.
    procs: tuple[str, ...] = ()


@dataclasses.dataclass
class SwingTimer:
    actor_id: str
    base_delay: int                 # weapon delay value
    haste_pct: int = 0
    slow_pct: int = 0
    last_swing_tick: float = 0.0
    double_attack_pct: int = 0
    triple_attack_pct: int = 0

    def interval_seconds(self) -> float:
        return next_swing_delay(
            base_delay=self.base_delay,
            haste_pct=self.haste_pct,
            slow_pct=self.slow_pct,
        )

    def next_swing_at(self) -> float:
        return self.last_swing_tick + self.interval_seconds()

    def can_swing(self, *, now_tick: float) -> bool:
        return now_tick >= self.next_swing_at()

    def swing(
        self, *,
        now_tick: float,
        rng_pool: RngPool,
        stream_name: str = STREAM_LOOT_DROPS,
    ) -> SwingResult:
        if not self.can_swing(now_tick=now_tick):
            return SwingResult(landed=False, hit_count=0)
        rng = rng_pool.stream(stream_name)
        # Roll double / triple attack
        procs: list[str] = []
        hits = 1
        if self.double_attack_pct > 0 and \
                rng.uniform(0, 100) < self.double_attack_pct:
            hits += 1
            procs.append("double_attack")
        if self.triple_attack_pct > 0 and \
                rng.uniform(0, 100) < self.triple_attack_pct:
            hits += 1
            procs.append("triple_attack")
        self.last_swing_tick = now_tick
        return SwingResult(
            landed=True, hit_count=hits, procs=tuple(procs),
        )


__all__ = [
    "HASTE_CAP_PCT",
    "next_swing_delay",
    "SwingResult", "SwingTimer",
]
