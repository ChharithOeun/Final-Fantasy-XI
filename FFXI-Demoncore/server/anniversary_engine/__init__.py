"""Anniversary engine — recurring commemorations of history events.

A year ago today, Iron Wing brought down Vorrak. The
anniversary engine remembers, and surfaces the right
commemoration: NPCs gather at the obelisk, the bard
plays the ballad, the chronicle resurfaces the article.
The tenth anniversary lights a beacon visible from
every nation.

A Commemoration is bound to one server_history_log entry.
The engine ticks each time the world clock advances. When
the elapsed time crosses an anniversary boundary
(1y, 5y, 10y, 25y...), it fires a CommemorationEvent
that the rest of the game consumes (NPC dialogues,
hall_of_heroes lighting, world_chronicle re-publication).

Tier ladder (years since the event):
    NEW        < 1y      no commemoration yet
    YEARLY     1-4y      simple — bards play the song
    LUSTRUM    5-9y      five-year mark, NPCs gather
    DECENNIAL  10-24y    ten-year, server-wide reminder
    QUARTER    25-49y    silver remembrance
    CENTENNIAL >=100y    civilization-scale event

Public surface
--------------
    AnniversaryTier enum
    Commemoration dataclass (frozen)
    CommemorationEvent dataclass (frozen) — tier, year_count
    AnniversaryEngine
        .schedule(commemoration_id, source_entry_id, summary,
                  origin_seconds, seconds_per_year) -> bool
        .check_now(now_seconds) -> tuple[CommemorationEvent, ...]
        .last_fired_tier(commemoration_id) -> Optional[AnniversaryTier]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AnniversaryTier(str, enum.Enum):
    NEW = "new"
    YEARLY = "yearly"
    LUSTRUM = "lustrum"
    DECENNIAL = "decennial"
    QUARTER = "quarter"
    CENTENNIAL = "centennial"


def _tier_for_years(years: int) -> AnniversaryTier:
    if years < 1:
        return AnniversaryTier.NEW
    if years < 5:
        return AnniversaryTier.YEARLY
    if years < 10:
        return AnniversaryTier.LUSTRUM
    if years < 25:
        return AnniversaryTier.DECENNIAL
    if years < 100:
        return AnniversaryTier.QUARTER
    return AnniversaryTier.CENTENNIAL


@dataclasses.dataclass(frozen=True)
class Commemoration:
    commemoration_id: str
    source_entry_id: str
    summary: str
    origin_seconds: int
    seconds_per_year: int


@dataclasses.dataclass(frozen=True)
class CommemorationEvent:
    commemoration_id: str
    source_entry_id: str
    summary: str
    tier: AnniversaryTier
    year_count: int
    fired_at: int


@dataclasses.dataclass
class AnniversaryEngine:
    _commemorations: dict[str, Commemoration] = dataclasses.field(
        default_factory=dict,
    )
    _last_fired: dict[str, AnniversaryTier] = dataclasses.field(
        default_factory=dict,
    )
    _last_year_count: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def schedule(
        self, *, commemoration_id: str,
        source_entry_id: str, summary: str,
        origin_seconds: int,
        seconds_per_year: int,
    ) -> bool:
        if not commemoration_id or not source_entry_id:
            return False
        if not summary:
            return False
        if seconds_per_year <= 0:
            return False
        if commemoration_id in self._commemorations:
            return False
        self._commemorations[commemoration_id] = Commemoration(
            commemoration_id=commemoration_id,
            source_entry_id=source_entry_id,
            summary=summary, origin_seconds=origin_seconds,
            seconds_per_year=seconds_per_year,
        )
        return True

    def check_now(
        self, *, now_seconds: int,
    ) -> tuple[CommemorationEvent, ...]:
        events: list[CommemorationEvent] = []
        for cid, c in self._commemorations.items():
            elapsed = now_seconds - c.origin_seconds
            if elapsed < 0:
                continue
            year = elapsed // c.seconds_per_year
            if year < 1:
                continue
            last_year = self._last_year_count.get(cid, 0)
            if year <= last_year:
                continue
            tier = _tier_for_years(year)
            events.append(CommemorationEvent(
                commemoration_id=cid,
                source_entry_id=c.source_entry_id,
                summary=c.summary, tier=tier,
                year_count=year, fired_at=now_seconds,
            ))
            self._last_fired[cid] = tier
            self._last_year_count[cid] = year
        return tuple(events)

    def last_fired_tier(
        self, *, commemoration_id: str,
    ) -> t.Optional[AnniversaryTier]:
        return self._last_fired.get(commemoration_id)

    def total_scheduled(self) -> int:
        return len(self._commemorations)


__all__ = [
    "AnniversaryTier", "Commemoration", "CommemorationEvent",
    "AnniversaryEngine",
]
