"""Tests for player_stargazing."""
from __future__ import annotations

from server.player_stargazing import (
    PlayerStargazingSystem, Season, LunarPhase,
    SessionState,
)


def _populate(s: PlayerStargazingSystem) -> None:
    s.register_constellation(
        name="The Phoenix",
        visible_seasons=(Season.SUMMER, Season.AUTUMN),
        fame_value=20,
    )
    s.register_constellation(
        name="The Crab",
        visible_seasons=(Season.WINTER,),
        fame_value=10,
    )
    s.register_constellation(
        name="The Dragon",
        visible_seasons=(
            Season.SPRING, Season.SUMMER,
            Season.AUTUMN, Season.WINTER,
        ),
        fame_value=5,
    )


def test_register_constellation_happy():
    s = PlayerStargazingSystem()
    assert s.register_constellation(
        name="X", visible_seasons=(Season.SPRING,),
        fame_value=10,
    ) is True


def test_register_duplicate_blocked():
    s = PlayerStargazingSystem()
    s.register_constellation(
        name="X", visible_seasons=(Season.SPRING,),
        fame_value=10,
    )
    assert s.register_constellation(
        name="X", visible_seasons=(Season.SUMMER,),
        fame_value=20,
    ) is False


def test_register_no_seasons_blocked():
    s = PlayerStargazingSystem()
    assert s.register_constellation(
        name="X", visible_seasons=(),
        fame_value=10,
    ) is False


def test_register_negative_fame_blocked():
    s = PlayerStargazingSystem()
    assert s.register_constellation(
        name="X", visible_seasons=(Season.SPRING,),
        fame_value=-1,
    ) is False


def test_schedule_eclipse_happy():
    s = PlayerStargazingSystem()
    assert s.schedule_eclipse(day=42) is True


def test_schedule_eclipse_negative_blocked():
    s = PlayerStargazingSystem()
    assert s.schedule_eclipse(day=-1) is False


def test_open_session_happy():
    s = PlayerStargazingSystem()
    sid = s.open_session(
        observer_id="naji", started_day=10,
        season=Season.SUMMER,
    )
    assert sid is not None


def test_open_session_empty_observer():
    s = PlayerStargazingSystem()
    assert s.open_session(
        observer_id="", started_day=10,
        season=Season.SUMMER,
    ) is None


def test_observe_happy():
    s = PlayerStargazingSystem()
    _populate(s)
    sid = s.open_session(
        observer_id="naji", started_day=10,
        season=Season.SUMMER,
    )
    assert s.observe(
        session_id=sid,
        constellation_name="The Phoenix",
    ) is True


def test_observe_wrong_season_blocked():
    s = PlayerStargazingSystem()
    _populate(s)
    sid = s.open_session(
        observer_id="naji", started_day=10,
        season=Season.SPRING,
    )
    # Phoenix only visible summer/autumn
    assert s.observe(
        session_id=sid,
        constellation_name="The Phoenix",
    ) is False


def test_observe_unknown_constellation():
    s = PlayerStargazingSystem()
    sid = s.open_session(
        observer_id="naji", started_day=10,
        season=Season.SUMMER,
    )
    assert s.observe(
        session_id=sid, constellation_name="Ghost",
    ) is False


def test_observe_duplicate_blocked():
    s = PlayerStargazingSystem()
    _populate(s)
    sid = s.open_session(
        observer_id="naji", started_day=10,
        season=Season.SUMMER,
    )
    s.observe(
        session_id=sid,
        constellation_name="The Phoenix",
    )
    assert s.observe(
        session_id=sid,
        constellation_name="The Phoenix",
    ) is False


def test_close_session_returns_fame():
    s = PlayerStargazingSystem()
    _populate(s)
    sid = s.open_session(
        observer_id="naji", started_day=10,
        season=Season.SUMMER,
    )
    s.observe(
        session_id=sid,
        constellation_name="The Phoenix",
    )
    s.observe(
        session_id=sid,
        constellation_name="The Dragon",
    )
    fame = s.close_session(session_id=sid)
    # 20 + 5 = 25
    assert fame == 25


def test_close_session_state_transition():
    s = PlayerStargazingSystem()
    sid = s.open_session(
        observer_id="naji", started_day=10,
        season=Season.SUMMER,
    )
    s.close_session(session_id=sid)
    assert s.session(
        session_id=sid,
    ).state == SessionState.CLOSED


def test_close_session_double_blocked():
    s = PlayerStargazingSystem()
    sid = s.open_session(
        observer_id="naji", started_day=10,
        season=Season.SUMMER,
    )
    s.close_session(session_id=sid)
    assert s.close_session(session_id=sid) is None


def test_observe_after_close_blocked():
    s = PlayerStargazingSystem()
    _populate(s)
    sid = s.open_session(
        observer_id="naji", started_day=10,
        season=Season.SUMMER,
    )
    s.close_session(session_id=sid)
    assert s.observe(
        session_id=sid,
        constellation_name="The Phoenix",
    ) is False


def test_eclipse_bonus_fame():
    s = PlayerStargazingSystem()
    _populate(s)
    s.schedule_eclipse(day=42)
    sid = s.open_session(
        observer_id="naji", started_day=42,
        season=Season.SUMMER,
    )
    s.observe(
        session_id=sid,
        constellation_name="The Phoenix",
    )
    fame = s.close_session(session_id=sid)
    # 20 + 50 (eclipse) = 70
    assert fame == 70


def test_eclipse_only_on_scheduled_day():
    s = PlayerStargazingSystem()
    _populate(s)
    s.schedule_eclipse(day=42)
    sid = s.open_session(
        observer_id="naji", started_day=43,
        season=Season.SUMMER,
    )
    s.observe(
        session_id=sid,
        constellation_name="The Phoenix",
    )
    fame = s.close_session(session_id=sid)
    assert fame == 20  # no bonus


def test_lunar_phase_cycle():
    s = PlayerStargazingSystem()
    assert s.lunar_phase(day=0) == LunarPhase.NEW
    assert s.lunar_phase(day=1) == LunarPhase.WAXING
    assert s.lunar_phase(day=3) == LunarPhase.FULL
    assert s.lunar_phase(day=6) == LunarPhase.WANING
    assert s.lunar_phase(day=8) == LunarPhase.NEW
    assert s.lunar_phase(day=11) == LunarPhase.FULL


def test_unknown_session():
    s = PlayerStargazingSystem()
    assert s.session(session_id="ghost") is None


def test_unknown_constellation_lookup():
    s = PlayerStargazingSystem()
    assert s.constellation(name="ghost") is None


def test_enum_counts():
    assert len(list(Season)) == 4
    assert len(list(LunarPhase)) == 4
    assert len(list(SessionState)) == 2
