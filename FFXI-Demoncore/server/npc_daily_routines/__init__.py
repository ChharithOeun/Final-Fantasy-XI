"""NPC daily routines — autonomous AI-driven schedules.

Every NPC in Demoncore is alive. The shopkeeper opens the stall
at dawn, eats lunch with another vendor at noon, closes up at
dusk, drinks at the inn until 1am, sleeps. The patrol guard
walks his beat in 8-hour shifts. The monk meditates at sunrise.

This module is the canonical schedule layer — not the AI itself.
Each NPC has a Schedule made of TimeWindows that bind the NPC
to a Routine (a tagged activity + waypoint + stance). The
orchestrator's per-NPC AI agent reads the active routine each
tick and decides the moment-to-moment behavior (which barrel to
lean against, which player to make eye contact with, when to
wave).

Time
----
Schedules are in Vana'diel hours (0..23, 25 vana-hours = 1 game-
day, but for routine purposes we round to a 24-hour clock matching
the game's day-night cycle). The vana_clock module ticks the
world; this module just answers "given now, what is NPC X
supposed to be doing?".

Public surface
--------------
    Routine enum (canonical activity types)
    Posture enum (how the NPC inhabits the routine)
    TimeWindow dataclass (start_hour, end_hour, routine, waypoint)
    NPCSchedule dataclass — a sorted set of TimeWindows
        .active_window_at(hour) -> TimeWindow | None
        .next_window_at(hour) -> TimeWindow | None
    NPCRoutineRegistry
        .register(npc_id, schedule)
        .active_routine(npc_id, hour) -> ActiveRoutine | None
        .npcs_in_routine(routine, hour)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


HOURS_IN_DAY = 24


class Routine(str, enum.Enum):
    """Canonical activity tags. The AI interprets the tag — these
    don't dictate exact behavior, just the broad mode."""
    SLEEP = "sleep"
    WAKE_BREAKFAST = "wake_breakfast"
    OPEN_SHOP = "open_shop"
    TEND_SHOP = "tend_shop"
    LUNCH = "lunch"
    AFTERNOON_WORK = "afternoon_work"
    CLOSE_SHOP = "close_shop"
    SOCIALIZE = "socialize"        # tavern / plaza chat
    PATROL = "patrol"
    GUARD_POST = "guard_post"
    PRAY = "pray"
    STUDY = "study"
    CRAFT = "craft"
    TRAIN = "train"                # combat training, sparring
    REST = "rest"
    TRAVEL = "travel"              # commuting between waypoints
    ON_CALL = "on_call"            # quest-giver waiting for adventurers


class Posture(str, enum.Enum):
    """How the NPC physically holds the routine."""
    STANDING = "standing"
    SITTING = "sitting"
    LYING = "lying"
    WALKING = "walking"
    RUNNING = "running"
    KNEELING = "kneeling"
    LEANING = "leaning"


@dataclasses.dataclass(frozen=True)
class TimeWindow:
    start_hour: int           # 0..23 (inclusive)
    end_hour: int             # 1..24 (exclusive); supports >24 for wrap
    routine: Routine
    waypoint_id: str          # e.g. "bastok_market_stall_3"
    posture: Posture = Posture.STANDING
    notes: str = ""

    def __post_init__(self) -> None:
        if not (0 <= self.start_hour < HOURS_IN_DAY):
            raise ValueError(
                f"start_hour {self.start_hour} out of range",
            )
        if self.end_hour <= self.start_hour:
            raise ValueError(
                "end_hour must be > start_hour "
                "(use wrap-around helper for crossing midnight)",
            )

    def covers(self, hour: int) -> bool:
        # Allows windows ending past midnight (e.g. end_hour=27)
        normalized = hour % HOURS_IN_DAY
        if self.end_hour <= HOURS_IN_DAY:
            return self.start_hour <= normalized < self.end_hour
        # Wrap window: covers [start..23] AND [0..end-24]
        if normalized >= self.start_hour:
            return True
        return normalized < (self.end_hour - HOURS_IN_DAY)

    @property
    def duration_hours(self) -> int:
        return self.end_hour - self.start_hour


def _check_no_overlap(windows: tuple[TimeWindow, ...]) -> None:
    """Reject schedules with overlapping windows. Wrap windows
    are allowed to span midnight, but two normal windows cannot
    share an hour."""
    sorted_w = sorted(windows, key=lambda w: w.start_hour)
    for i in range(len(sorted_w)):
        for j in range(i + 1, len(sorted_w)):
            a, b = sorted_w[i], sorted_w[j]
            for hour in range(HOURS_IN_DAY):
                if a.covers(hour) and b.covers(hour):
                    raise ValueError(
                        f"overlapping windows at hour {hour}: "
                        f"{a.routine.value} and {b.routine.value}"
                    )


@dataclasses.dataclass
class NPCSchedule:
    npc_id: str
    windows: tuple[TimeWindow, ...] = ()
    allow_gaps: bool = True   # gaps default to "ON_CALL"

    def __post_init__(self) -> None:
        _check_no_overlap(self.windows)

    def active_window_at(self, hour: int) -> t.Optional[TimeWindow]:
        for w in self.windows:
            if w.covers(hour):
                return w
        return None

    def next_window_at(self, hour: int) -> t.Optional[TimeWindow]:
        """Find the next window that STARTS strictly after `hour`
        (in the same day; wraps to next day if none)."""
        normalized = hour % HOURS_IN_DAY
        # Sort by start, then find first start > normalized
        ordered = sorted(self.windows, key=lambda w: w.start_hour)
        for w in ordered:
            if w.start_hour > normalized:
                return w
        # Wrap to first window of next day
        return ordered[0] if ordered else None


@dataclasses.dataclass(frozen=True)
class ActiveRoutine:
    npc_id: str
    routine: Routine
    waypoint_id: str
    posture: Posture
    hours_remaining: int


@dataclasses.dataclass
class NPCRoutineRegistry:
    _schedules: dict[str, NPCSchedule] = dataclasses.field(
        default_factory=dict,
    )

    def register(self, *, schedule: NPCSchedule) -> NPCSchedule:
        self._schedules[schedule.npc_id] = schedule
        return schedule

    def schedule_for(self, npc_id: str) -> t.Optional[NPCSchedule]:
        return self._schedules.get(npc_id)

    def active_routine(
        self, *, npc_id: str, hour: int,
    ) -> t.Optional[ActiveRoutine]:
        sched = self._schedules.get(npc_id)
        if sched is None:
            return None
        w = sched.active_window_at(hour)
        if w is None:
            if sched.allow_gaps:
                # Gap = ON_CALL at last waypoint (or "any")
                return ActiveRoutine(
                    npc_id=npc_id, routine=Routine.ON_CALL,
                    waypoint_id="any", posture=Posture.STANDING,
                    hours_remaining=1,
                )
            return None
        normalized = hour % HOURS_IN_DAY
        if w.end_hour <= HOURS_IN_DAY:
            remaining = w.end_hour - normalized
        else:
            if normalized >= w.start_hour:
                remaining = w.end_hour - normalized
            else:
                remaining = (w.end_hour - HOURS_IN_DAY) - normalized
        return ActiveRoutine(
            npc_id=npc_id, routine=w.routine,
            waypoint_id=w.waypoint_id, posture=w.posture,
            hours_remaining=max(1, remaining),
        )

    def npcs_in_routine(
        self, *, routine: Routine, hour: int,
    ) -> tuple[str, ...]:
        out: list[str] = []
        for npc_id in self._schedules:
            ar = self.active_routine(npc_id=npc_id, hour=hour)
            if ar is not None and ar.routine == routine:
                out.append(npc_id)
        return tuple(out)

    def total_npcs(self) -> int:
        return len(self._schedules)


# --------------------------------------------------------------------
# Built-in archetype schedules (templates the AI authors a tribe of)
# --------------------------------------------------------------------
def shopkeeper_schedule(
    *, npc_id: str, shop_waypoint: str,
    home_waypoint: str, tavern_waypoint: str,
) -> NPCSchedule:
    """Standard FFXI shopkeeper rhythm: sleep -> open shop ->
    lunch -> shop -> close -> tavern -> sleep."""
    return NPCSchedule(
        npc_id=npc_id,
        windows=(
            TimeWindow(0, 6, Routine.SLEEP,
                        home_waypoint, Posture.LYING),
            TimeWindow(6, 7, Routine.WAKE_BREAKFAST,
                        home_waypoint, Posture.SITTING),
            TimeWindow(7, 8, Routine.TRAVEL, shop_waypoint,
                        Posture.WALKING),
            TimeWindow(8, 12, Routine.TEND_SHOP, shop_waypoint),
            TimeWindow(12, 13, Routine.LUNCH, shop_waypoint,
                        Posture.SITTING),
            TimeWindow(13, 18, Routine.TEND_SHOP, shop_waypoint),
            TimeWindow(18, 19, Routine.CLOSE_SHOP, shop_waypoint),
            TimeWindow(19, 22, Routine.SOCIALIZE,
                        tavern_waypoint, Posture.SITTING),
            TimeWindow(22, 24, Routine.TRAVEL, home_waypoint,
                        Posture.WALKING),
        ),
        allow_gaps=False,
    )


def patrol_guard_schedule(
    *, npc_id: str, beat_waypoint: str,
    barracks_waypoint: str,
) -> NPCSchedule:
    """8-hour shift on patrol, then 8 off, then 8 sleep."""
    return NPCSchedule(
        npc_id=npc_id,
        windows=(
            TimeWindow(0, 8, Routine.PATROL, beat_waypoint,
                        Posture.WALKING),
            TimeWindow(8, 12, Routine.REST, barracks_waypoint,
                        Posture.SITTING),
            TimeWindow(12, 16, Routine.TRAIN, barracks_waypoint,
                        Posture.STANDING),
            TimeWindow(16, 24, Routine.SLEEP, barracks_waypoint,
                        Posture.LYING),
        ),
        allow_gaps=False,
    )


__all__ = [
    "HOURS_IN_DAY", "Routine", "Posture",
    "TimeWindow", "NPCSchedule", "ActiveRoutine",
    "NPCRoutineRegistry",
    "shopkeeper_schedule", "patrol_guard_schedule",
]
