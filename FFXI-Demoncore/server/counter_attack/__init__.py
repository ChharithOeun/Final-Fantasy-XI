"""Counter-attack mechanic — MNK / PUP / specific-gear reactions.

When an attacker swings and the defender has counter rate, there's
a chance the defender's hit is *reflected*: the original attack
misses, the defender immediately strikes back with their main
weapon, and gains a small TP bonus. Counters can chain (counter
on a counter is rare but possible — capped to prevent infinite
ping-pong).

Counter sources, additive:
    base job rate (MNK gets innate Counter trait)
    Counterstance JA (MNK active buff, +30%)
    Stormwaker maneuver (PUP automaton stance, +25%)
    Gear/augment rolls (typically +1% to +5%)

A counter still goes through normal attack resolution against
the original attacker — it can miss, crit, etc. — but it does
NOT trigger another counter from the original attacker (no
counter-on-counter ping-pong).

Public surface
--------------
    CounterSource enum
    CounterAttempt dataclass
    base_counter_rate(job, level) -> float
    counter_rate(...) -> float
    roll_counter(rng_pool, ...) -> CounterAttempt
    apply_counter_tp_gain(current_tp) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import STREAM_BOSS_CRITIC, RngPool


# ----- Cap & bonus constants ---------------------------------------------
COUNTER_HARD_CAP = 0.65          # 65% absolute ceiling
COUNTERSTANCE_BONUS = 0.30       # MNK Counterstance JA
STORMWAKER_BONUS = 0.25          # PUP Stormwaker maneuver
COUNTER_TP_GAIN = 50             # TP awarded on successful counter (1/100ths)


class CounterSource(str, enum.Enum):
    INNATE = "innate"
    COUNTERSTANCE = "counterstance"
    STORMWAKER = "stormwaker"
    GEAR = "gear"


# Innate counter rate per job. Most jobs get 0; MNK and PUP get a
# baseline trait at higher levels.
_INNATE_BY_JOB: dict[str, list[tuple[int, float]]] = {
    # job -> [(min_level, rate), ...]  — picked the highest matching tier
    "monk":         [(10, 0.05), (40, 0.10), (75, 0.13), (99, 0.15)],
    "puppetmaster": [(10, 0.03), (50, 0.06), (99, 0.08)],
    "thief":        [(50, 0.02)],   # very small innate via THF traits
}


@dataclasses.dataclass(frozen=True)
class CounterAttempt:
    countered: bool = False
    sources_active: tuple[CounterSource, ...] = ()
    rate: float = 0.0
    tp_gain: int = 0
    reason: t.Optional[str] = None


def base_counter_rate(*, job: str, level: int) -> float:
    """Innate counter rate from job+level. 0 for most jobs."""
    bands = _INNATE_BY_JOB.get(job, [])
    rate = 0.0
    for min_lvl, r in bands:
        if level >= min_lvl:
            rate = r
    return rate


def counter_rate(
    *, job: str, level: int,
    counterstance_active: bool = False,
    stormwaker_active: bool = False,
    gear_bonus: float = 0.0,
) -> float:
    """Aggregate counter rate from all sources."""
    total = base_counter_rate(job=job, level=level)
    if counterstance_active:
        total += COUNTERSTANCE_BONUS
    if stormwaker_active:
        total += STORMWAKER_BONUS
    total += gear_bonus
    return min(total, COUNTER_HARD_CAP)


def active_sources(
    *, job: str, level: int,
    counterstance_active: bool, stormwaker_active: bool,
    gear_bonus: float,
) -> tuple[CounterSource, ...]:
    out: list[CounterSource] = []
    if base_counter_rate(job=job, level=level) > 0:
        out.append(CounterSource.INNATE)
    if counterstance_active:
        out.append(CounterSource.COUNTERSTANCE)
    if stormwaker_active:
        out.append(CounterSource.STORMWAKER)
    if gear_bonus > 0:
        out.append(CounterSource.GEAR)
    return tuple(out)


def roll_counter(
    *, job: str, level: int,
    counterstance_active: bool = False,
    stormwaker_active: bool = False,
    gear_bonus: float = 0.0,
    is_counter_chain: bool = False,
    rng_pool: RngPool,
) -> CounterAttempt:
    """Roll for a counter on an incoming attack. *is_counter_chain*
    is True iff the incoming attack is itself a counter (prevents
    ping-pong)."""
    if is_counter_chain:
        return CounterAttempt(reason="no counter-on-counter")
    rate = counter_rate(
        job=job, level=level,
        counterstance_active=counterstance_active,
        stormwaker_active=stormwaker_active,
        gear_bonus=gear_bonus,
    )
    if rate <= 0:
        return CounterAttempt(rate=0.0, reason="no counter sources")
    rng = rng_pool.stream(STREAM_BOSS_CRITIC)
    if rng.random() < rate:
        return CounterAttempt(
            countered=True,
            sources_active=active_sources(
                job=job, level=level,
                counterstance_active=counterstance_active,
                stormwaker_active=stormwaker_active,
                gear_bonus=gear_bonus,
            ),
            rate=rate,
            tp_gain=COUNTER_TP_GAIN,
        )
    return CounterAttempt(rate=rate)


def apply_counter_tp_gain(current_tp: int, *, cap: int = 3000) -> int:
    """Add COUNTER_TP_GAIN to current_tp, capped."""
    return min(cap, current_tp + COUNTER_TP_GAIN)


__all__ = [
    "COUNTER_HARD_CAP", "COUNTERSTANCE_BONUS",
    "STORMWAKER_BONUS", "COUNTER_TP_GAIN",
    "CounterSource", "CounterAttempt",
    "base_counter_rate", "counter_rate", "active_sources",
    "roll_counter", "apply_counter_tp_gain",
]
