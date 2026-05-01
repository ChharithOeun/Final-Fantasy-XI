"""Notorious Monster spawn windows and time-of-day gates.

NMs are the spice of mid- and high-level FFXI. Each one is tied to
a placeholder mob: kill the placeholder, the timer rolls, and on a
matching tick the NM spawns instead of the placeholder. Some NMs
are gated to night-only or specific Vana'diel hours.

Public surface
--------------
    ToDGate                  enum: ANY / NIGHT / DAY / HOUR_RANGE
    NotoriousMonster         immutable spec
    NM_CATALOG               sample registered NMs
    SpawnTracker             per-(zone, nm) state
    record_placeholder_kill  bumps the eligibility window
    attempt_pop              rolls under deterministic rng_pool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_ENCOUNTER_GEN


class ToDGate(str, enum.Enum):
    ANY = "any"
    NIGHT = "night"      # 20:00 - 5:59 Vana'diel
    DAY = "day"          # 6:00 - 19:59
    HOUR_RANGE = "hour_range"


@dataclasses.dataclass(frozen=True)
class NotoriousMonster:
    nm_id: str
    label: str
    placeholder_id: str           # mob class that "is" the placeholder
    zone_id: str
    level: int
    pop_chance: float             # 0..1 per placeholder kill
    spawn_window_min: int = 0     # eligibility opens N seconds after kill
    spawn_window_max: int = 300   # closes after N seconds (PH respawns)
    tod_gate: ToDGate = ToDGate.ANY
    hour_range: tuple[int, int] = (0, 24)   # only used with HOUR_RANGE

    def __post_init__(self) -> None:
        if not 0.0 <= self.pop_chance <= 1.0:
            raise ValueError("pop_chance must be in [0, 1]")
        if self.spawn_window_min < 0:
            raise ValueError("spawn_window_min must be >= 0")
        if self.spawn_window_max < self.spawn_window_min:
            raise ValueError("spawn_window_max < min")


# Sample catalog — designers add via the data-files pattern later.
NM_CATALOG: tuple[NotoriousMonster, ...] = (
    NotoriousMonster(
        nm_id="leaping_lizzy", label="Leaping Lizzy",
        placeholder_id="rock_lizard", zone_id="south_gustaberg",
        level=23, pop_chance=0.10,
    ),
    NotoriousMonster(
        nm_id="valkurm_emperor", label="Valkurm Emperor",
        placeholder_id="emperor_hornet", zone_id="rolanberry_fields",
        level=25, pop_chance=0.05,
    ),
    NotoriousMonster(
        nm_id="serket", label="Serket",
        placeholder_id="hieracosphinx", zone_id="korroloka_tunnel",
        level=55, pop_chance=0.04,
        tod_gate=ToDGate.NIGHT,
    ),
    NotoriousMonster(
        nm_id="argus", label="Argus",
        placeholder_id="goblin_pathfinder", zone_id="crawlers_nest",
        level=57, pop_chance=0.04,
    ),
    NotoriousMonster(
        nm_id="kreutzet", label="Kreutzet",
        placeholder_id="cliff_hippogryph", zone_id="jugner_forest",
        level=39, pop_chance=0.06,
        tod_gate=ToDGate.HOUR_RANGE, hour_range=(6, 12),
    ),
)

NM_BY_ID: dict[str, NotoriousMonster] = {n.nm_id: n for n in NM_CATALOG}


@dataclasses.dataclass
class SpawnTracker:
    """Per-(zone, nm) state. Tracks the last placeholder kill."""
    last_placeholder_kill_tick: t.Optional[int] = None
    last_pop_attempt_tick: t.Optional[int] = None
    nm_currently_alive: bool = False

    def record_placeholder_kill(self, *, now_tick: int) -> None:
        self.last_placeholder_kill_tick = now_tick

    def is_window_open(
        self, *, nm: NotoriousMonster, now_tick: int,
    ) -> bool:
        if self.last_placeholder_kill_tick is None:
            return False
        if self.nm_currently_alive:
            return False
        elapsed = now_tick - self.last_placeholder_kill_tick
        return nm.spawn_window_min <= elapsed <= nm.spawn_window_max


def _is_night_hour(hour: int) -> bool:
    return hour >= 20 or hour < 6


def tod_gate_open(
    nm: NotoriousMonster, *, vanadiel_hour: int,
) -> bool:
    """Is the NM's time-of-day gate open right now?"""
    if not 0 <= vanadiel_hour < 24:
        raise ValueError(f"vanadiel_hour {vanadiel_hour} out of [0, 24)")
    if nm.tod_gate == ToDGate.ANY:
        return True
    if nm.tod_gate == ToDGate.NIGHT:
        return _is_night_hour(vanadiel_hour)
    if nm.tod_gate == ToDGate.DAY:
        return not _is_night_hour(vanadiel_hour)
    if nm.tod_gate == ToDGate.HOUR_RANGE:
        lo, hi = nm.hour_range
        if lo <= hi:
            return lo <= vanadiel_hour < hi
        # Wraparound (e.g. (22, 4) means 22-23 + 0-3)
        return vanadiel_hour >= lo or vanadiel_hour < hi
    return False


def attempt_pop(
    *,
    nm: NotoriousMonster,
    tracker: SpawnTracker,
    rng_pool: RngPool,
    now_tick: int,
    vanadiel_hour: int,
) -> bool:
    """Roll for the NM to pop. Returns True if it spawns this call.

    Side effects: marks tracker.last_pop_attempt_tick = now_tick;
    on success, marks nm_currently_alive = True.
    """
    tracker.last_pop_attempt_tick = now_tick

    if not tracker.is_window_open(nm=nm, now_tick=now_tick):
        return False
    if not tod_gate_open(nm, vanadiel_hour=vanadiel_hour):
        return False

    rng = rng_pool.stream(STREAM_ENCOUNTER_GEN)
    if rng.random() < nm.pop_chance:
        tracker.nm_currently_alive = True
        return True
    return False


def declare_nm_killed(tracker: SpawnTracker) -> None:
    """Reset tracker when the NM dies (placeholder cycle restarts)."""
    tracker.nm_currently_alive = False
    tracker.last_placeholder_kill_tick = None


__all__ = [
    "ToDGate", "NotoriousMonster",
    "NM_CATALOG", "NM_BY_ID",
    "SpawnTracker",
    "tod_gate_open",
    "attempt_pop",
    "declare_nm_killed",
]
