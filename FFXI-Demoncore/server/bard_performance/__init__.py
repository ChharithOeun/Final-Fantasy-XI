"""Bard performance — public concerts + fame meter.

Distinct from `bardsong` (BRD combat buffs). This is the social /
economic performance system: a bard takes the stage at a tavern,
plaza, or arena, plays a SET, and audience NPCs (or players)
gather, listen, tip, and rate. Higher fame → bigger crowds →
better tips → more booking offers.

Performance lifecycle
---------------------
    SCHEDULED   — booking made, venue + slot reserved
    LIVE        — set in progress; ticks accumulate audience
    FINISHED    — set ended; fame + tips computed
    CANCELLED   — bard or venue cancelled

Each set has a MOOD (lively / somber / heroic / mournful /
romantic / patriotic) drawn from a small palette. Audience
appreciation depends on mood-fit with the venue and time of day
(romantic at the tavern at dusk pays well; patriotic at midday
plaza pays well; mournful before noon is awkward).

Public surface
--------------
    PerformanceMood enum
    VenueKind enum
    Venue dataclass
    Performance dataclass
    PerformanceTickResult dataclass
    BardPerformanceRegistry
        .register_venue(venue)
        .schedule(bard_id, venue_id, mood, scheduled_at, hour)
        .start(performance_id, now)
        .audience_tick(performance_id, now) -> applause/tips
        .finish(performance_id, now) -> result
        .fame_for(bard_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Maximum fame value.
FAME_MAX = 1000
DEFAULT_TIP_PER_AUDIENCE = 25
SET_LENGTH_SECONDS = 60 * 30   # 30-minute set
APPLAUSE_TIER_OK = 60
APPLAUSE_TIER_GREAT = 80


class PerformanceMood(str, enum.Enum):
    LIVELY = "lively"
    SOMBER = "somber"
    HEROIC = "heroic"
    MOURNFUL = "mournful"
    ROMANTIC = "romantic"
    PATRIOTIC = "patriotic"


class VenueKind(str, enum.Enum):
    TAVERN = "tavern"
    PLAZA = "plaza"
    ARENA = "arena"
    TEMPLE = "temple"
    PALACE = "palace"
    DOCK = "dock"


class PerformanceStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    CANCELLED = "cancelled"


# Mood preferences per venue kind. Higher score = better fit.
_MOOD_VENUE_FIT: dict[
    tuple[VenueKind, PerformanceMood], int,
] = {
    (VenueKind.TAVERN, PerformanceMood.LIVELY): 5,
    (VenueKind.TAVERN, PerformanceMood.ROMANTIC): 5,
    (VenueKind.TAVERN, PerformanceMood.HEROIC): 3,
    (VenueKind.TAVERN, PerformanceMood.MOURNFUL): 1,
    (VenueKind.TAVERN, PerformanceMood.SOMBER): 1,
    (VenueKind.TAVERN, PerformanceMood.PATRIOTIC): 3,
    (VenueKind.PLAZA, PerformanceMood.PATRIOTIC): 5,
    (VenueKind.PLAZA, PerformanceMood.HEROIC): 5,
    (VenueKind.PLAZA, PerformanceMood.LIVELY): 4,
    (VenueKind.PLAZA, PerformanceMood.ROMANTIC): 2,
    (VenueKind.PLAZA, PerformanceMood.SOMBER): 1,
    (VenueKind.PLAZA, PerformanceMood.MOURNFUL): 1,
    (VenueKind.ARENA, PerformanceMood.HEROIC): 5,
    (VenueKind.ARENA, PerformanceMood.LIVELY): 4,
    (VenueKind.ARENA, PerformanceMood.PATRIOTIC): 3,
    (VenueKind.TEMPLE, PerformanceMood.SOMBER): 5,
    (VenueKind.TEMPLE, PerformanceMood.MOURNFUL): 5,
    (VenueKind.TEMPLE, PerformanceMood.ROMANTIC): 1,
    (VenueKind.TEMPLE, PerformanceMood.LIVELY): 1,
    (VenueKind.PALACE, PerformanceMood.PATRIOTIC): 5,
    (VenueKind.PALACE, PerformanceMood.HEROIC): 5,
    (VenueKind.PALACE, PerformanceMood.ROMANTIC): 3,
    (VenueKind.DOCK, PerformanceMood.LIVELY): 5,
    (VenueKind.DOCK, PerformanceMood.ROMANTIC): 3,
    (VenueKind.DOCK, PerformanceMood.MOURNFUL): 2,
}


def _venue_fit(
    venue_kind: VenueKind, mood: PerformanceMood,
) -> int:
    return _MOOD_VENUE_FIT.get((venue_kind, mood), 1)


def _hour_modifier(*, kind: VenueKind, hour: int) -> int:
    h = hour % 24
    # Night taverns peak; daytime plazas peak
    if kind == VenueKind.TAVERN:
        if 18 <= h <= 23 or 0 <= h <= 1:
            return 2
        if 8 <= h <= 11:
            return -1
        return 0
    if kind == VenueKind.PLAZA:
        if 10 <= h <= 16:
            return 2
        if 22 <= h or h <= 4:
            return -2
        return 0
    if kind == VenueKind.TEMPLE:
        if 5 <= h <= 9:
            return 2
        if 18 <= h <= 22:
            return 1
        return 0
    if kind == VenueKind.ARENA:
        if 14 <= h <= 19:
            return 2
        return 0
    if kind == VenueKind.DOCK:
        if 6 <= h <= 10 or 18 <= h <= 22:
            return 1
        return 0
    return 0


@dataclasses.dataclass(frozen=True)
class Venue:
    venue_id: str
    label: str
    kind: VenueKind
    base_audience_capacity: int = 20


@dataclasses.dataclass
class Performance:
    performance_id: str
    bard_id: str
    venue_id: str
    mood: PerformanceMood
    scheduled_at_seconds: float
    scheduled_hour: int
    status: PerformanceStatus = PerformanceStatus.SCHEDULED
    started_at_seconds: t.Optional[float] = None
    finished_at_seconds: t.Optional[float] = None
    audience_count: int = 0
    applause_score: int = 0     # 0..100 cumulative quality
    tips_collected: int = 0
    fame_gained: int = 0
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class PerformanceTickResult:
    accepted: bool
    audience_added: int = 0
    applause_added: int = 0
    tips_added: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class FinishResult:
    accepted: bool
    fame_gained: int = 0
    tips_collected: int = 0
    final_applause: int = 0
    audience_count: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ScheduleResult:
    accepted: bool
    performance: t.Optional[Performance] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BardPerformanceRegistry:
    _venues: dict[str, Venue] = dataclasses.field(
        default_factory=dict,
    )
    _performances: dict[
        str, Performance,
    ] = dataclasses.field(default_factory=dict)
    _fame: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    _next_perf_id: int = 0
    # Reservations: (venue_id, hour-of-day) -> performance_id
    _bookings: dict[
        tuple[str, int], str,
    ] = dataclasses.field(default_factory=dict)

    def register_venue(self, venue: Venue) -> Venue:
        if venue.base_audience_capacity <= 0:
            raise ValueError("capacity must be positive")
        self._venues[venue.venue_id] = venue
        return venue

    def venue(self, venue_id: str) -> t.Optional[Venue]:
        return self._venues.get(venue_id)

    def fame_for(self, bard_id: str) -> int:
        return self._fame.get(bard_id, 0)

    def schedule(
        self, *, bard_id: str, venue_id: str,
        mood: PerformanceMood,
        scheduled_at_seconds: float,
        scheduled_hour: int,
    ) -> ScheduleResult:
        venue = self._venues.get(venue_id)
        if venue is None:
            return ScheduleResult(False, reason="unknown venue")
        slot_key = (venue_id, scheduled_hour % 24)
        if slot_key in self._bookings:
            return ScheduleResult(
                False, reason="slot already booked",
            )
        pid = f"perf_{self._next_perf_id}"
        self._next_perf_id += 1
        perf = Performance(
            performance_id=pid, bard_id=bard_id,
            venue_id=venue_id, mood=mood,
            scheduled_at_seconds=scheduled_at_seconds,
            scheduled_hour=scheduled_hour,
        )
        self._performances[pid] = perf
        self._bookings[slot_key] = pid
        return ScheduleResult(True, performance=perf)

    def start(
        self, *, performance_id: str, now_seconds: float,
    ) -> bool:
        p = self._performances.get(performance_id)
        if p is None or p.status != PerformanceStatus.SCHEDULED:
            return False
        p.status = PerformanceStatus.LIVE
        p.started_at_seconds = now_seconds
        return True

    def cancel(self, *, performance_id: str) -> bool:
        p = self._performances.get(performance_id)
        if p is None or p.status not in (
            PerformanceStatus.SCHEDULED, PerformanceStatus.LIVE,
        ):
            return False
        p.status = PerformanceStatus.CANCELLED
        # Free the slot
        slot = (p.venue_id, p.scheduled_hour % 24)
        if self._bookings.get(slot) == performance_id:
            del self._bookings[slot]
        return True

    def audience_tick(
        self, *, performance_id: str,
        bard_fame_floor: int = 0,
    ) -> PerformanceTickResult:
        p = self._performances.get(performance_id)
        if p is None:
            return PerformanceTickResult(
                False, reason="no such performance",
            )
        if p.status != PerformanceStatus.LIVE:
            return PerformanceTickResult(
                False, reason="performance not live",
            )
        venue = self._venues[p.venue_id]
        fit = _venue_fit(venue.kind, p.mood)
        hour_mod = _hour_modifier(
            kind=venue.kind, hour=p.scheduled_hour,
        )
        # Audience pull = capacity * (fit/5) * (fame multiplier)
        fame = max(self.fame_for(p.bard_id), bard_fame_floor)
        fame_mult = 1.0 + (fame / FAME_MAX) * 1.5
        target = int(round(
            venue.base_audience_capacity
            * (fit / 5.0) * fame_mult,
        ))
        target = max(0, target + hour_mod * 2)
        added = max(0, target - p.audience_count)
        p.audience_count += added
        # Applause this tick = 5 * fit + hour_mod*2
        applause_add = max(0, 5 * fit + hour_mod * 2)
        p.applause_score = min(100, p.applause_score + applause_add)
        tips_add = (
            p.audience_count * DEFAULT_TIP_PER_AUDIENCE
            * applause_add // 100
        )
        p.tips_collected += tips_add
        return PerformanceTickResult(
            accepted=True,
            audience_added=added,
            applause_added=applause_add,
            tips_added=tips_add,
        )

    def finish(
        self, *, performance_id: str, now_seconds: float,
    ) -> FinishResult:
        p = self._performances.get(performance_id)
        if p is None:
            return FinishResult(
                False, reason="no such performance",
            )
        if p.status != PerformanceStatus.LIVE:
            return FinishResult(
                False, reason="performance not live",
            )
        p.status = PerformanceStatus.FINISHED
        p.finished_at_seconds = now_seconds
        # Fame gained scales with applause + audience
        fame_gain = (
            (p.applause_score * (1 + p.audience_count // 5))
            // 4
        )
        if p.applause_score >= APPLAUSE_TIER_GREAT:
            fame_gain *= 2
        elif p.applause_score < APPLAUSE_TIER_OK:
            fame_gain = max(0, fame_gain // 2)
        new_fame = min(
            FAME_MAX, self._fame.get(p.bard_id, 0) + fame_gain,
        )
        self._fame[p.bard_id] = new_fame
        p.fame_gained = fame_gain
        return FinishResult(
            accepted=True,
            fame_gained=fame_gain,
            tips_collected=p.tips_collected,
            final_applause=p.applause_score,
            audience_count=p.audience_count,
        )

    def performance(
        self, performance_id: str,
    ) -> t.Optional[Performance]:
        return self._performances.get(performance_id)

    def total_performances(self) -> int:
        return len(self._performances)


__all__ = [
    "FAME_MAX", "SET_LENGTH_SECONDS",
    "DEFAULT_TIP_PER_AUDIENCE",
    "APPLAUSE_TIER_OK", "APPLAUSE_TIER_GREAT",
    "PerformanceMood", "VenueKind",
    "PerformanceStatus",
    "Venue", "Performance",
    "PerformanceTickResult", "FinishResult", "ScheduleResult",
    "BardPerformanceRegistry",
]
