"""Beastman seasonal events — beastman-specific holidays.

Each beastman race has its own annual cycle of CULTURAL events,
plus shared cross-race festivals from the Shathar pantheon. These
are time-windowed gates: they OPEN on a registered start day and
CLOSE after duration_days. While OPEN, players can claim event
prizes (each event has a per-player prize daily limit).

Sample events:
  YAGUDO    - EGG_FEAST (spring), TENGU_DUEL (autumn)
  QUADAV    - STONE_VIGIL (winter), MINERAL_RITES (summer)
  LAMIA     - TIDE_FESTIVAL (summer), SCALE_NIGHT (autumn)
  ORC       - REAVING (winter), BANNER_BURNING (spring)
  PAN-RACE  - DAY_OF_THE_OUTCAST (Shathar feast)

Public surface
--------------
    EventRace enum    YAGUDO / QUADAV / LAMIA / ORC / PAN_RACE
    EventState enum   PENDING / OPEN / CLOSED
    SeasonalEvent dataclass
    BeastmanSeasonalEvents
        .register_event(event_id, race, start_day, duration_days,
                        prize_per_day_limit, prize_item_id)
        .open_event(event_id, now_day)
        .close_event(event_id, now_day)
        .claim(player_id, event_id, now_day)
        .state_for(event_id, now_day)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EventRace(str, enum.Enum):
    YAGUDO = "yagudo"
    QUADAV = "quadav"
    LAMIA = "lamia"
    ORC = "orc"
    PAN_RACE = "pan_race"


class EventState(str, enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"


@dataclasses.dataclass
class SeasonalEvent:
    event_id: str
    race: EventRace
    start_day: int
    duration_days: int
    prize_per_day_limit: int
    prize_item_id: str
    state: EventState = EventState.PENDING


@dataclasses.dataclass(frozen=True)
class ClaimResult:
    accepted: bool
    event_id: str
    item_id: str = ""
    claims_today: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanSeasonalEvents:
    _events: dict[str, SeasonalEvent] = dataclasses.field(
        default_factory=dict,
    )
    # claims keyed by (player_id, event_id, day)
    _claims: dict[
        tuple[str, str, int], int,
    ] = dataclasses.field(default_factory=dict)

    def register_event(
        self, *, event_id: str,
        race: EventRace,
        start_day: int,
        duration_days: int,
        prize_per_day_limit: int,
        prize_item_id: str,
    ) -> t.Optional[SeasonalEvent]:
        if event_id in self._events:
            return None
        if duration_days <= 0 or prize_per_day_limit <= 0:
            return None
        if not prize_item_id:
            return None
        if start_day < 0:
            return None
        e = SeasonalEvent(
            event_id=event_id,
            race=race,
            start_day=start_day,
            duration_days=duration_days,
            prize_per_day_limit=prize_per_day_limit,
            prize_item_id=prize_item_id,
        )
        self._events[event_id] = e
        return e

    def open_event(
        self, *, event_id: str, now_day: int,
    ) -> bool:
        e = self._events.get(event_id)
        if e is None:
            return False
        if now_day < e.start_day:
            return False
        if e.state != EventState.PENDING:
            return False
        e.state = EventState.OPEN
        return True

    def close_event(
        self, *, event_id: str, now_day: int,
    ) -> bool:
        e = self._events.get(event_id)
        if e is None or e.state != EventState.OPEN:
            return False
        e.state = EventState.CLOSED
        return True

    def state_for(
        self, *, event_id: str, now_day: int,
    ) -> EventState:
        e = self._events.get(event_id)
        if e is None:
            return EventState.PENDING
        # Lazy auto-close once duration elapsed
        if (
            e.state == EventState.OPEN
            and now_day >= e.start_day + e.duration_days
        ):
            e.state = EventState.CLOSED
        return e.state

    def claim(
        self, *, player_id: str,
        event_id: str,
        now_day: int,
    ) -> ClaimResult:
        e = self._events.get(event_id)
        if e is None:
            return ClaimResult(
                False, event_id, reason="unknown event",
            )
        # Run the lazy auto-close check
        state = self.state_for(
            event_id=event_id, now_day=now_day,
        )
        if state != EventState.OPEN:
            return ClaimResult(
                False, event_id, reason="event not open",
            )
        key = (player_id, event_id, now_day)
        cur = self._claims.get(key, 0)
        if cur >= e.prize_per_day_limit:
            return ClaimResult(
                False, event_id,
                claims_today=cur,
                reason="daily limit reached",
            )
        self._claims[key] = cur + 1
        return ClaimResult(
            accepted=True,
            event_id=event_id,
            item_id=e.prize_item_id,
            claims_today=cur + 1,
        )

    def claims_today(
        self, *, player_id: str,
        event_id: str,
        now_day: int,
    ) -> int:
        return self._claims.get(
            (player_id, event_id, now_day), 0,
        )

    def total_events(self) -> int:
        return len(self._events)


__all__ = [
    "EventRace", "EventState",
    "SeasonalEvent", "ClaimResult",
    "BeastmanSeasonalEvents",
]
