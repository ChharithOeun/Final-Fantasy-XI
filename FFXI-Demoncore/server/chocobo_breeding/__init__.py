"""Chocobo breeding — egg, raise, race.

Chocobo lineage: each parent contributes a color "gene"; the child
takes the dominant color via a simple rule (BLACK > YELLOW > GREEN >
BLUE > RED). Stats (speed/stamina/discernment) blend toward the
average of the parents with a small +/- via rng_pool. Race resolution
picks the highest speed across competitors with deterministic ties.

Public surface
--------------
    ChocoboColor enum
    ChocoboStats dataclass
    ChocoboEgg / Chocobo dataclass
    breed(parent_a, parent_b, rng_pool) -> ChocoboEgg
    hatch(egg, name, now_tick) -> Chocobo
    run_race(competitors, rng_pool) -> RaceResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_FOMOR_APPEARANCE


class ChocoboColor(str, enum.Enum):
    YELLOW = "yellow"
    BLUE = "blue"
    RED = "red"
    GREEN = "green"
    BLACK = "black"


# Higher index = more dominant.
_COLOR_RANK: dict[ChocoboColor, int] = {
    ChocoboColor.RED: 1,
    ChocoboColor.BLUE: 2,
    ChocoboColor.GREEN: 3,
    ChocoboColor.YELLOW: 4,
    ChocoboColor.BLACK: 5,
}


@dataclasses.dataclass(frozen=True)
class ChocoboStats:
    speed: int
    stamina: int
    discernment: int

    def __post_init__(self) -> None:
        for name in ("speed", "stamina", "discernment"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")


@dataclasses.dataclass(frozen=True)
class ChocoboEgg:
    egg_id: str
    color: ChocoboColor
    inherited_stats: ChocoboStats
    parent_a_id: str
    parent_b_id: str


@dataclasses.dataclass
class Chocobo:
    chocobo_id: str
    name: str
    color: ChocoboColor
    stats: ChocoboStats
    age_ticks: int = 0


def _dominant_color(
    a: ChocoboColor, b: ChocoboColor,
) -> ChocoboColor:
    if _COLOR_RANK[a] >= _COLOR_RANK[b]:
        return a
    return b


def breed(
    *,
    parent_a: Chocobo, parent_b: Chocobo,
    rng_pool: RngPool, egg_id: str,
    stream_name: str = STREAM_FOMOR_APPEARANCE,
) -> ChocoboEgg:
    """Produce an egg from two parent chocobos.

    Color: dominant ranks, with a 5% mutation chance to bump up by
    one rank if available.
    Stats: midpoint of parents with +/- 5% jitter via rng_pool.
    """
    rng = rng_pool.stream(stream_name)
    color = _dominant_color(parent_a.color, parent_b.color)
    if rng.random() < 0.05:
        cur_rank = _COLOR_RANK[color]
        higher = [c for c, r in _COLOR_RANK.items()
                  if r == cur_rank + 1]
        if higher:
            color = higher[0]

    def _blend(va: int, vb: int) -> int:
        mid = (va + vb) // 2
        # +/- 5% jitter
        jitter = int(mid * 0.05)
        return max(0, mid + rng.randint(-jitter, jitter))

    stats = ChocoboStats(
        speed=_blend(parent_a.stats.speed, parent_b.stats.speed),
        stamina=_blend(parent_a.stats.stamina,
                       parent_b.stats.stamina),
        discernment=_blend(parent_a.stats.discernment,
                            parent_b.stats.discernment),
    )
    return ChocoboEgg(
        egg_id=egg_id, color=color,
        inherited_stats=stats,
        parent_a_id=parent_a.chocobo_id,
        parent_b_id=parent_b.chocobo_id,
    )


def hatch(
    *, egg: ChocoboEgg, chocobo_id: str, name: str,
) -> Chocobo:
    return Chocobo(
        chocobo_id=chocobo_id, name=name,
        color=egg.color, stats=egg.inherited_stats,
        age_ticks=0,
    )


@dataclasses.dataclass(frozen=True)
class RaceResult:
    winner_id: str
    rankings: tuple[str, ...]


def run_race(
    *, competitors: t.Sequence[Chocobo],
    rng_pool: RngPool,
    stream_name: str = STREAM_FOMOR_APPEARANCE,
) -> RaceResult:
    """Resolve a race. Each chocobo gets a final score = speed +
    rng-based 0..stamina/2 jitter; winner is highest score."""
    if not competitors:
        raise ValueError("no competitors")
    rng = rng_pool.stream(stream_name)
    scores: list[tuple[int, str]] = []
    for c in competitors:
        jitter = rng.randint(0, max(1, c.stats.stamina // 2))
        scores.append((c.stats.speed + jitter, c.chocobo_id))
    # Sort highest first; tie broken by chocobo_id ascending
    scores.sort(key=lambda x: (-x[0], x[1]))
    rankings = tuple(s[1] for s in scores)
    return RaceResult(winner_id=rankings[0], rankings=rankings)


__all__ = [
    "ChocoboColor", "ChocoboStats",
    "ChocoboEgg", "Chocobo",
    "breed", "hatch",
    "RaceResult", "run_race",
]
