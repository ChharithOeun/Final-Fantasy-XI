"""Guild war arena — formal LS-vs-LS PvP arena bookings.

Casual ganking happens in the open world. But when two
linkshells have a grudge or wager to settle, they book
the GUILD WAR ARENA — a moderated, neutral-ground PvP
match with rules, timer, witness slots, and a recorded
outcome.

A booking has:
    booking_id
    arena_id          which physical arena
    challenger_ls
    defender_ls
    match_format      DUEL_3v3 / SKIRMISH_6v6 / FULL_18
    rules             enum: NO_ITEMS / NO_HP / NO_2H /
                      LIMITED_JOBS / OPEN
    wager_gil         optional pot held in escrow
    booked_day
    scheduled_day     when the match runs
    state             PROPOSED / ACCEPTED / SCHEDULED /
                      LIVE / COMPLETED / FORFEITED /
                      CANCELLED

Lifecycle:
    propose()   challenger creates booking PROPOSED
    accept()    defender accepts -> ACCEPTED, then
                schedule()
    schedule(day)   ACCEPTED -> SCHEDULED, scheduled_day
                set
    start()     SCHEDULED -> LIVE on the scheduled_day
    finalize(winner) LIVE -> COMPLETED, winner recorded,
                wager paid out
    forfeit()   either side bails -> FORFEITED, wager
                paid to the other side
    cancel()    PROPOSED only -> CANCELLED

Public surface
--------------
    MatchFormat enum
    Ruleset enum
    BookingState enum
    Booking dataclass (frozen)
    GuildWarArenaSystem
        .propose(...) -> Optional[str]
        .accept(booking_id) -> bool
        .schedule(booking_id, day) -> bool
        .start(booking_id, now_day) -> bool
        .finalize(booking_id, winner_ls,
                  now_day) -> bool
        .forfeit(booking_id, forfeiting_ls,
                 now_day) -> bool
        .cancel(booking_id) -> bool
        .booking(booking_id) -> Optional[Booking]
        .bookings_for(ls_id) -> list[Booking]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MatchFormat(str, enum.Enum):
    DUEL_3V3 = "duel_3v3"
    SKIRMISH_6V6 = "skirmish_6v6"
    FULL_18 = "full_18"


class Ruleset(str, enum.Enum):
    OPEN = "open"
    NO_ITEMS = "no_items"
    NO_HP = "no_hp"
    NO_2H = "no_2h"
    LIMITED_JOBS = "limited_jobs"


class BookingState(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    FORFEITED = "forfeited"
    CANCELLED = "cancelled"


@dataclasses.dataclass(frozen=True)
class Booking:
    booking_id: str
    arena_id: str
    challenger_ls: str
    defender_ls: str
    match_format: MatchFormat
    rules: Ruleset
    wager_gil: int
    booked_day: int
    scheduled_day: t.Optional[int]
    winner_ls: t.Optional[str]
    state: BookingState


@dataclasses.dataclass
class GuildWarArenaSystem:
    _bookings: dict[str, Booking] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def propose(
        self, *, arena_id: str, challenger_ls: str,
        defender_ls: str, match_format: MatchFormat,
        rules: Ruleset, wager_gil: int,
        booked_day: int,
    ) -> t.Optional[str]:
        if not arena_id:
            return None
        if not challenger_ls or not defender_ls:
            return None
        if challenger_ls == defender_ls:
            return None
        if wager_gil < 0 or booked_day < 0:
            return None
        bid = f"book_{self._next_id}"
        self._next_id += 1
        self._bookings[bid] = Booking(
            booking_id=bid, arena_id=arena_id,
            challenger_ls=challenger_ls,
            defender_ls=defender_ls,
            match_format=match_format, rules=rules,
            wager_gil=wager_gil, booked_day=booked_day,
            scheduled_day=None, winner_ls=None,
            state=BookingState.PROPOSED,
        )
        return bid

    def accept(self, *, booking_id: str) -> bool:
        if booking_id not in self._bookings:
            return False
        b = self._bookings[booking_id]
        if b.state != BookingState.PROPOSED:
            return False
        self._bookings[booking_id] = dataclasses.replace(
            b, state=BookingState.ACCEPTED,
        )
        return True

    def schedule(
        self, *, booking_id: str, day: int,
    ) -> bool:
        if booking_id not in self._bookings:
            return False
        b = self._bookings[booking_id]
        if b.state != BookingState.ACCEPTED:
            return False
        if day < b.booked_day:
            return False
        self._bookings[booking_id] = dataclasses.replace(
            b, scheduled_day=day,
            state=BookingState.SCHEDULED,
        )
        return True

    def start(
        self, *, booking_id: str, now_day: int,
    ) -> bool:
        if booking_id not in self._bookings:
            return False
        b = self._bookings[booking_id]
        if b.state != BookingState.SCHEDULED:
            return False
        if b.scheduled_day is None:
            return False
        if now_day < b.scheduled_day:
            return False
        self._bookings[booking_id] = dataclasses.replace(
            b, state=BookingState.LIVE,
        )
        return True

    def finalize(
        self, *, booking_id: str, winner_ls: str,
        now_day: int,
    ) -> bool:
        if booking_id not in self._bookings:
            return False
        b = self._bookings[booking_id]
        if b.state != BookingState.LIVE:
            return False
        if winner_ls not in (
            b.challenger_ls, b.defender_ls,
        ):
            return False
        self._bookings[booking_id] = dataclasses.replace(
            b, state=BookingState.COMPLETED,
            winner_ls=winner_ls,
        )
        return True

    def forfeit(
        self, *, booking_id: str,
        forfeiting_ls: str, now_day: int,
    ) -> bool:
        if booking_id not in self._bookings:
            return False
        b = self._bookings[booking_id]
        if b.state not in (
            BookingState.SCHEDULED, BookingState.LIVE,
            BookingState.ACCEPTED,
        ):
            return False
        if forfeiting_ls not in (
            b.challenger_ls, b.defender_ls,
        ):
            return False
        winner = (
            b.defender_ls
            if forfeiting_ls == b.challenger_ls
            else b.challenger_ls
        )
        self._bookings[booking_id] = dataclasses.replace(
            b, state=BookingState.FORFEITED,
            winner_ls=winner,
        )
        return True

    def cancel(self, *, booking_id: str) -> bool:
        if booking_id not in self._bookings:
            return False
        b = self._bookings[booking_id]
        if b.state != BookingState.PROPOSED:
            return False
        self._bookings[booking_id] = dataclasses.replace(
            b, state=BookingState.CANCELLED,
        )
        return True

    def booking(
        self, *, booking_id: str,
    ) -> t.Optional[Booking]:
        return self._bookings.get(booking_id)

    def bookings_for(
        self, *, ls_id: str,
    ) -> list[Booking]:
        return [
            b for b in self._bookings.values()
            if (b.challenger_ls == ls_id
                or b.defender_ls == ls_id)
        ]


__all__ = [
    "MatchFormat", "Ruleset", "BookingState",
    "Booking", "GuildWarArenaSystem",
]
