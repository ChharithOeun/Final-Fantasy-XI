"""Cultural calendar — faction-specific cultural events.

Vana'diel doesn't have a single shared calendar of festivals
(seasonal_events handles game-wide ones like Mog Bonanza). Each
faction has its OWN cultural events: Yagudo Equinox, Bastokian
Republic Day, Sanddorian Mourning Week, the Goblin Market
Festival. During these windows:

* NPC daily routines shift (a shopkeeper may close shop early
  to attend the parade)
* Vendors stock event-specific goods (commemorative trinkets,
  ceremonial food)
* Participation grants faction reputation
* Some events are HOSTILE to outsiders (Yagudo Equinox is a
  faith ritual; outsiders provoke retaliation)
* Other events welcome the world (Bastokian Republic Day is a
  parade tourists are invited to)

Period model
------------
A `CulturalEvent` has a `period_kind`:
    ANNUAL_FIXED       — same days every year (e.g. doy 60-65)
    SEASONAL_TIE       — tied to a season (3-day Solstice block)
    LUNAR              — tied to moon phase
    ONE_OFF            — bespoke schedule
We use day-of-year (1..365) for ANNUAL_FIXED, the most common.

Public surface
--------------
    PeriodKind enum
    EventStance enum (WELCOMING / HOSTILE / RESTRICTED)
    CulturalEvent dataclass
    CulturalCalendar
        .register(event)
        .active_events_at(faction_id, day_of_year)
        .event_stance_for_outsider(event_id)
        .vendor_specials_for(event_id)
        .npc_routine_overrides_for(event_id)
        .participate(player_id, event_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


YEAR_DAYS = 365


class PeriodKind(str, enum.Enum):
    ANNUAL_FIXED = "annual_fixed"
    SEASONAL_TIE = "seasonal_tie"
    LUNAR = "lunar"
    ONE_OFF = "one_off"


class EventStance(str, enum.Enum):
    WELCOMING = "welcoming"        # outsiders invited
    RESTRICTED = "restricted"      # locals only, no aggression
    HOSTILE = "hostile"            # outsiders provoke retaliation


@dataclasses.dataclass(frozen=True)
class VendorSpecial:
    item_id: str
    discount_pct: int = 0
    is_event_exclusive: bool = False
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class RoutineOverride:
    """During an event, an NPC's normal schedule may shift.
    Caller maps this to npc_daily_routines temporarily."""
    npc_id: str
    waypoint_id: str
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class CulturalEvent:
    event_id: str
    label: str
    faction_id: str
    period_kind: PeriodKind
    # For ANNUAL_FIXED: inclusive [start_doy, end_doy].
    # If end_doy < start_doy, the event wraps year-end.
    start_day_of_year: int = 1
    end_day_of_year: int = 1
    stance: EventStance = EventStance.WELCOMING
    participation_rep_reward: int = 10
    vendor_specials: tuple[VendorSpecial, ...] = ()
    routine_overrides: tuple[RoutineOverride, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        for d in (self.start_day_of_year, self.end_day_of_year):
            if not (1 <= d <= YEAR_DAYS):
                raise ValueError(
                    f"day_of_year {d} out of 1..{YEAR_DAYS}",
                )

    def is_active_on(self, day_of_year: int) -> bool:
        if self.period_kind != PeriodKind.ANNUAL_FIXED:
            return False
        s, e = self.start_day_of_year, self.end_day_of_year
        if s <= e:
            return s <= day_of_year <= e
        # Wrap (e.g. start=360, end=10) covers Dec-Jan
        return day_of_year >= s or day_of_year <= e


@dataclasses.dataclass(frozen=True)
class ParticipationResult:
    accepted: bool
    rep_gained: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class CulturalCalendar:
    _events: dict[str, CulturalEvent] = dataclasses.field(
        default_factory=dict,
    )
    # player -> set of event_ids participated in
    _participation: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)

    def register(self, event: CulturalEvent) -> CulturalEvent:
        self._events[event.event_id] = event
        return event

    def event(self, event_id: str) -> t.Optional[CulturalEvent]:
        return self._events.get(event_id)

    def active_events_at(
        self, *, day_of_year: int,
        faction_id: t.Optional[str] = None,
    ) -> tuple[CulturalEvent, ...]:
        out: list[CulturalEvent] = []
        for e in self._events.values():
            if faction_id and e.faction_id != faction_id:
                continue
            if e.is_active_on(day_of_year):
                out.append(e)
        return tuple(out)

    def event_stance_for_outsider(
        self, event_id: str,
    ) -> t.Optional[EventStance]:
        e = self._events.get(event_id)
        return e.stance if e else None

    def vendor_specials_for(
        self, event_id: str,
    ) -> tuple[VendorSpecial, ...]:
        e = self._events.get(event_id)
        return e.vendor_specials if e else ()

    def npc_routine_overrides_for(
        self, event_id: str,
    ) -> tuple[RoutineOverride, ...]:
        e = self._events.get(event_id)
        return e.routine_overrides if e else ()

    def participate(
        self, *, player_id: str, event_id: str,
        day_of_year: int,
    ) -> ParticipationResult:
        e = self._events.get(event_id)
        if e is None:
            return ParticipationResult(False, reason="no such event")
        if not e.is_active_on(day_of_year):
            return ParticipationResult(
                False, reason="event not currently active",
            )
        if e.stance == EventStance.HOSTILE:
            return ParticipationResult(
                False,
                reason="outsiders aren't welcome to participate",
            )
        bucket = self._participation.setdefault(player_id, set())
        if event_id in bucket:
            return ParticipationResult(
                False,
                reason="already participated this cycle",
            )
        bucket.add(event_id)
        return ParticipationResult(
            accepted=True,
            rep_gained=e.participation_rep_reward,
        )

    def participations_of(
        self, player_id: str,
    ) -> frozenset[str]:
        return frozenset(self._participation.get(player_id, set()))

    def reset_year(self) -> None:
        """Wipe per-year participation. Called at year rollover."""
        self._participation.clear()

    def total_events(self) -> int:
        return len(self._events)


# --------------------------------------------------------------------
# Default seed — canonical Vana'diel cultural events
# --------------------------------------------------------------------
def _default_events() -> tuple[CulturalEvent, ...]:
    return (
        CulturalEvent(
            event_id="bastok_republic_day",
            label="Bastokian Republic Day",
            faction_id="bastok",
            period_kind=PeriodKind.ANNUAL_FIXED,
            start_day_of_year=120,
            end_day_of_year=122,
            stance=EventStance.WELCOMING,
            participation_rep_reward=15,
            vendor_specials=(
                VendorSpecial(
                    item_id="republic_brew",
                    is_event_exclusive=True,
                ),
                VendorSpecial(
                    item_id="commemorative_pin",
                    is_event_exclusive=True,
                ),
            ),
            notes="Three-day parade and feast.",
        ),
        CulturalEvent(
            event_id="san_doria_mourning_week",
            label="Sanddorian Mourning Week",
            faction_id="san_doria",
            period_kind=PeriodKind.ANNUAL_FIXED,
            start_day_of_year=270,
            end_day_of_year=276,
            stance=EventStance.RESTRICTED,
            participation_rep_reward=20,
            vendor_specials=(
                VendorSpecial(
                    item_id="black_lily",
                    is_event_exclusive=True,
                ),
            ),
            notes=(
                "Solemn week of remembrance for fallen knights."
            ),
        ),
        CulturalEvent(
            event_id="windurst_starlit_festival",
            label="Windurstian Starlit Festival",
            faction_id="windurst",
            period_kind=PeriodKind.ANNUAL_FIXED,
            start_day_of_year=200,
            end_day_of_year=202,
            stance=EventStance.WELCOMING,
            participation_rep_reward=12,
            vendor_specials=(
                VendorSpecial(
                    item_id="star_lantern",
                    discount_pct=10,
                ),
            ),
        ),
        CulturalEvent(
            event_id="yagudo_equinox",
            label="Yagudo Equinox",
            faction_id="yagudo",
            period_kind=PeriodKind.ANNUAL_FIXED,
            start_day_of_year=80,
            end_day_of_year=82,
            stance=EventStance.HOSTILE,
            participation_rep_reward=0,
            notes=(
                "Sacred ritual — Yagudo zealots attack any "
                "outsider who approaches."
            ),
        ),
        CulturalEvent(
            event_id="goblin_market_festival",
            label="Goblin Market Festival",
            faction_id="goblin",
            period_kind=PeriodKind.ANNUAL_FIXED,
            start_day_of_year=300,
            end_day_of_year=303,
            stance=EventStance.WELCOMING,
            participation_rep_reward=8,
            vendor_specials=(
                VendorSpecial(
                    item_id="bizarre_goblin_stew",
                    discount_pct=25,
                ),
                VendorSpecial(
                    item_id="goblin_lucky_charm",
                    is_event_exclusive=True,
                ),
            ),
            notes=(
                "Open marketplace; goblins are uncommonly polite."
            ),
        ),
        CulturalEvent(
            event_id="orc_war_song_night",
            label="Orcish War-Song Night",
            faction_id="orc",
            period_kind=PeriodKind.ANNUAL_FIXED,
            start_day_of_year=360,
            end_day_of_year=5,           # year-wrap
            stance=EventStance.HOSTILE,
            participation_rep_reward=0,
            notes="The Orcish Empire whips itself into war frenzy.",
        ),
    )


def seed_default_calendar(
    calendar: CulturalCalendar,
) -> CulturalCalendar:
    for e in _default_events():
        calendar.register(e)
    return calendar


__all__ = [
    "YEAR_DAYS",
    "PeriodKind", "EventStance",
    "VendorSpecial", "RoutineOverride", "CulturalEvent",
    "ParticipationResult", "CulturalCalendar",
    "seed_default_calendar",
]
