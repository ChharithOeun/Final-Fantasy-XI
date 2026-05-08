"""Tests for guild_war_arena."""
from __future__ import annotations

from server.guild_war_arena import (
    GuildWarArenaSystem, MatchFormat, Ruleset,
    BookingState,
)


def _propose(s, **overrides):
    args = dict(
        arena_id="bastok_arena",
        challenger_ls="ls_alpha",
        defender_ls="ls_beta",
        match_format=MatchFormat.SKIRMISH_6V6,
        rules=Ruleset.OPEN, wager_gil=10_000,
        booked_day=10,
    )
    args.update(overrides)
    return s.propose(**args)


def test_propose_happy():
    s = GuildWarArenaSystem()
    assert _propose(s) is not None


def test_propose_blank_arena_blocked():
    s = GuildWarArenaSystem()
    assert _propose(s, arena_id="") is None


def test_propose_self_match_blocked():
    s = GuildWarArenaSystem()
    assert _propose(
        s, challenger_ls="x", defender_ls="x",
    ) is None


def test_propose_negative_wager():
    s = GuildWarArenaSystem()
    assert _propose(s, wager_gil=-1) is None


def test_accept_happy():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    assert s.accept(booking_id=bid) is True


def test_accept_unknown():
    s = GuildWarArenaSystem()
    assert s.accept(booking_id="ghost") is False


def test_double_accept_blocked():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    s.accept(booking_id=bid)
    assert s.accept(booking_id=bid) is False


def test_schedule_happy():
    s = GuildWarArenaSystem()
    bid = _propose(s, booked_day=10)
    s.accept(booking_id=bid)
    assert s.schedule(
        booking_id=bid, day=15,
    ) is True


def test_schedule_before_booked_blocked():
    s = GuildWarArenaSystem()
    bid = _propose(s, booked_day=10)
    s.accept(booking_id=bid)
    assert s.schedule(
        booking_id=bid, day=5,
    ) is False


def test_schedule_when_proposed_blocked():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    assert s.schedule(
        booking_id=bid, day=15,
    ) is False


def test_start_happy():
    s = GuildWarArenaSystem()
    bid = _propose(s, booked_day=10)
    s.accept(booking_id=bid)
    s.schedule(booking_id=bid, day=15)
    assert s.start(
        booking_id=bid, now_day=15,
    ) is True


def test_start_too_early():
    s = GuildWarArenaSystem()
    bid = _propose(s, booked_day=10)
    s.accept(booking_id=bid)
    s.schedule(booking_id=bid, day=15)
    assert s.start(
        booking_id=bid, now_day=14,
    ) is False


def test_finalize_happy():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    s.accept(booking_id=bid)
    s.schedule(booking_id=bid, day=15)
    s.start(booking_id=bid, now_day=15)
    assert s.finalize(
        booking_id=bid, winner_ls="ls_alpha",
        now_day=15,
    ) is True


def test_finalize_unknown_winner():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    s.accept(booking_id=bid)
    s.schedule(booking_id=bid, day=15)
    s.start(booking_id=bid, now_day=15)
    assert s.finalize(
        booking_id=bid, winner_ls="ls_omega",
        now_day=15,
    ) is False


def test_finalize_when_not_live_blocked():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    assert s.finalize(
        booking_id=bid, winner_ls="ls_alpha",
        now_day=15,
    ) is False


def test_forfeit_assigns_other_as_winner():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    s.accept(booking_id=bid)
    s.schedule(booking_id=bid, day=15)
    s.start(booking_id=bid, now_day=15)
    assert s.forfeit(
        booking_id=bid, forfeiting_ls="ls_alpha",
        now_day=15,
    ) is True
    b = s.booking(booking_id=bid)
    assert b.winner_ls == "ls_beta"
    assert b.state == BookingState.FORFEITED


def test_forfeit_outsider_blocked():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    s.accept(booking_id=bid)
    s.schedule(booking_id=bid, day=15)
    s.start(booking_id=bid, now_day=15)
    assert s.forfeit(
        booking_id=bid, forfeiting_ls="ls_omega",
        now_day=15,
    ) is False


def test_forfeit_when_proposed_blocked():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    assert s.forfeit(
        booking_id=bid, forfeiting_ls="ls_alpha",
        now_day=15,
    ) is False


def test_cancel_when_proposed_ok():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    assert s.cancel(booking_id=bid) is True


def test_cancel_when_accepted_blocked():
    s = GuildWarArenaSystem()
    bid = _propose(s)
    s.accept(booking_id=bid)
    assert s.cancel(booking_id=bid) is False


def test_bookings_for_ls():
    s = GuildWarArenaSystem()
    _propose(s, challenger_ls="ls_alpha",
             defender_ls="ls_beta")
    _propose(s, challenger_ls="ls_gamma",
             defender_ls="ls_alpha")
    _propose(s, challenger_ls="ls_beta",
             defender_ls="ls_gamma")
    out = s.bookings_for(ls_id="ls_alpha")
    assert len(out) == 2


def test_booking_unknown():
    s = GuildWarArenaSystem()
    assert s.booking(booking_id="ghost") is None


def test_enum_counts():
    assert len(list(MatchFormat)) == 3
    assert len(list(Ruleset)) == 5
    assert len(list(BookingState)) == 7
