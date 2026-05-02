"""Seasonal events — Vana'fete, Mog Bonanza, Sunbreeze, etc.

Recurring server-wide festivals scheduled by the Vana'diel
calendar. Each event has:
* an active window (start_day .. end_day, both inclusive)
* festival-specific NPC vendor inventory swaps
* festival-specific quests / mini-games
* server-wide announcement hooks

We model events as immutable definitions plus a pure-function
`active_events_on_day()` that takes a Vana'diel day index and
returns the events live on that day.

Public surface
--------------
    SeasonalEvent dataclass / EVENT_CATALOG
    EventStatus enum (UPCOMING / ACTIVE / RECENT / OFFSEASON)
    active_events_on_day(day_of_year) -> tuple[SeasonalEvent, ...]
    status_of(event, day_of_year) -> EventStatus
    days_until_next_window(event, day_of_year) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Vana'diel year is 360 days (canonical). Easier to model than 365.
VANA_YEAR_DAYS = 360


class EventStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    RECENT = "recent"        # within 7 days of ending
    OFFSEASON = "offseason"


@dataclasses.dataclass(frozen=True)
class SeasonalEvent:
    event_id: str
    label: str
    start_day: int           # 0-based day in Vana'diel year
    end_day: int             # inclusive
    npc_vendor_overrides: tuple[str, ...]
    quests: tuple[str, ...]
    server_announcement: str = ""


EVENT_CATALOG: tuple[SeasonalEvent, ...] = (
    SeasonalEvent(
        event_id="starlight_celebration",
        label="Starlight Celebration",
        start_day=345, end_day=359,    # late winter
        npc_vendor_overrides=(
            "carolers_treats", "snowman_stamper",
        ),
        quests=("starlight_carol_circuit",
                 "smiles_to_go_long_haul"),
        server_announcement="The Starlight Celebration warms Vana'diel!",
    ),
    SeasonalEvent(
        event_id="vanafete",
        label="Vana'fete (anniversary)",
        start_day=120, end_day=140,    # mid year
        npc_vendor_overrides=(
            "vanafete_pin", "anniversary_brioche",
        ),
        quests=("vanafete_dial_in", "moogle_anniversary_quiz"),
        server_announcement="Vana'fete celebrations have begun!",
    ),
    SeasonalEvent(
        event_id="mog_bonanza",
        label="Mog Bonanza",
        start_day=10, end_day=40,      # early year
        npc_vendor_overrides=(
            "mog_bonanza_marble", "bonanza_pearl",
        ),
        quests=("mog_bonanza_winners_circle",),
        server_announcement="Mog Bonanza lottery is open!",
    ),
    SeasonalEvent(
        event_id="sunbreeze_festival",
        label="Sunbreeze Festival",
        start_day=200, end_day=215,    # mid summer
        npc_vendor_overrides=(
            "sunbreeze_yukata", "sunbreeze_uchiwa",
        ),
        quests=("sunbreeze_fishing_derby",
                 "sunbreeze_fireworks_show"),
        server_announcement="The Sunbreeze Festival lights the sky!",
    ),
    SeasonalEvent(
        event_id="harvest_festival",
        label="Harvest Festival",
        start_day=290, end_day=305,    # late autumn
        npc_vendor_overrides=(
            "pumpkin_treats", "ghost_pop",
        ),
        quests=("harvest_doctor_yoran_oran",
                 "tricks_n_treats"),
        server_announcement="The Harvest Festival has begun!",
    ),
    SeasonalEvent(
        event_id="adventurer_appreciation",
        label="Adventurer Appreciation Campaign",
        start_day=80, end_day=95,
        npc_vendor_overrides=(
            "campaign_op_credits_bonus",
        ),
        quests=("appreciation_field_assignment",),
        server_announcement="The Empire thanks all adventurers!",
    ),
)


def _day_in_window(day: int, start: int, end: int) -> bool:
    """Inclusive window check, accounting for wrap-around (e.g. an
    event spanning day 350..010 would split year-end)."""
    if start <= end:
        return start <= day <= end
    return day >= start or day <= end


def active_events_on_day(*, day_of_year: int
                          ) -> tuple[SeasonalEvent, ...]:
    out = [
        e for e in EVENT_CATALOG
        if _day_in_window(day_of_year % VANA_YEAR_DAYS,
                            e.start_day, e.end_day)
    ]
    return tuple(out)


def status_of(*, event: SeasonalEvent, day_of_year: int) -> EventStatus:
    day = day_of_year % VANA_YEAR_DAYS
    if _day_in_window(day, event.start_day, event.end_day):
        return EventStatus.ACTIVE
    # 7-day look-back / look-ahead
    for offset in range(1, 8):
        prev = (day - offset) % VANA_YEAR_DAYS
        if _day_in_window(prev, event.start_day, event.end_day):
            return EventStatus.RECENT
        nxt = (day + offset) % VANA_YEAR_DAYS
        if _day_in_window(nxt, event.start_day, event.end_day):
            return EventStatus.UPCOMING
    return EventStatus.OFFSEASON


def days_until_next_window(*, event: SeasonalEvent,
                            day_of_year: int) -> int:
    """How many days until this event's next start. 0 if currently
    active."""
    day = day_of_year % VANA_YEAR_DAYS
    if _day_in_window(day, event.start_day, event.end_day):
        return 0
    delta = (event.start_day - day) % VANA_YEAR_DAYS
    return delta if delta != 0 else VANA_YEAR_DAYS


def event_by_id(event_id: str) -> t.Optional[SeasonalEvent]:
    for e in EVENT_CATALOG:
        if e.event_id == event_id:
            return e
    return None


__all__ = [
    "VANA_YEAR_DAYS",
    "EventStatus", "SeasonalEvent", "EVENT_CATALOG",
    "active_events_on_day", "status_of",
    "days_until_next_window", "event_by_id",
]
