"""Player stargazing — constellation observation, lunar phases, eclipses.

Stargazers run observation sessions at night. Constellations
are visible only in certain seasons; lunar phase cycles every
8 game days; eclipses happen on specific scheduled days and
hand out exceptional fame to anyone observing that night.

Lifecycle (per session)
    OPEN          observer at telescope, gathering data
    CLOSED        session ended, observations recorded

Public surface
--------------
    Season enum
    LunarPhase enum
    SessionState enum
    Constellation dataclass (frozen)
    Observation dataclass (frozen)
    Session dataclass (frozen)
    PlayerStargazingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_LUNAR_CYCLE = 8


class Season(str, enum.Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class LunarPhase(str, enum.Enum):
    NEW = "new"
    WAXING = "waxing"
    FULL = "full"
    WANING = "waning"


class SessionState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclasses.dataclass(frozen=True)
class Constellation:
    name: str
    visible_seasons: tuple[Season, ...]
    fame_value: int


@dataclasses.dataclass(frozen=True)
class Observation:
    constellation_name: str
    observed_day: int


@dataclasses.dataclass(frozen=True)
class Session:
    session_id: str
    observer_id: str
    started_day: int
    season: Season
    state: SessionState
    observations: tuple[Observation, ...]
    eclipse_witnessed: bool


def _lunar_phase_for_day(day: int) -> LunarPhase:
    """Cycle: 0=NEW, 1-2=WAXING, 3-4=FULL, 5-7=WANING."""
    pos = day % _LUNAR_CYCLE
    if pos == 0:
        return LunarPhase.NEW
    if pos in (1, 2):
        return LunarPhase.WAXING
    if pos in (3, 4):
        return LunarPhase.FULL
    return LunarPhase.WANING


@dataclasses.dataclass
class PlayerStargazingSystem:
    _constellations: dict[str, Constellation] = (
        dataclasses.field(default_factory=dict)
    )
    _eclipse_days: set[int] = dataclasses.field(
        default_factory=set,
    )
    _sessions: dict[str, Session] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def register_constellation(
        self, *, name: str,
        visible_seasons: tuple[Season, ...],
        fame_value: int,
    ) -> bool:
        if not name or name in self._constellations:
            return False
        if not visible_seasons:
            return False
        if fame_value < 0:
            return False
        self._constellations[name] = Constellation(
            name=name,
            visible_seasons=visible_seasons,
            fame_value=fame_value,
        )
        return True

    def schedule_eclipse(self, *, day: int) -> bool:
        if day < 0:
            return False
        self._eclipse_days.add(day)
        return True

    def open_session(
        self, *, observer_id: str, started_day: int,
        season: Season,
    ) -> t.Optional[str]:
        if not observer_id or started_day < 0:
            return None
        sid = f"sess_{self._next}"
        self._next += 1
        self._sessions[sid] = Session(
            session_id=sid, observer_id=observer_id,
            started_day=started_day, season=season,
            state=SessionState.OPEN,
            observations=(),
            eclipse_witnessed=(
                started_day in self._eclipse_days
            ),
        )
        return sid

    def observe(
        self, *, session_id: str,
        constellation_name: str,
    ) -> bool:
        """Record an observation. Constellation must
        be visible in the session's season.
        """
        if session_id not in self._sessions:
            return False
        s = self._sessions[session_id]
        if s.state != SessionState.OPEN:
            return False
        if constellation_name not in self._constellations:
            return False
        c = self._constellations[constellation_name]
        if s.season not in c.visible_seasons:
            return False
        # No duplicates within a session
        for o in s.observations:
            if o.constellation_name == constellation_name:
                return False
        new_obs = s.observations + (
            Observation(
                constellation_name=constellation_name,
                observed_day=s.started_day,
            ),
        )
        self._sessions[session_id] = (
            dataclasses.replace(s, observations=new_obs)
        )
        return True

    def close_session(
        self, *, session_id: str,
    ) -> t.Optional[int]:
        """Close session. Returns total fame earned:
        sum of constellation fame_values + 50 if
        eclipse_witnessed.
        """
        if session_id not in self._sessions:
            return None
        s = self._sessions[session_id]
        if s.state != SessionState.OPEN:
            return None
        fame = sum(
            self._constellations[
                o.constellation_name
            ].fame_value
            for o in s.observations
        )
        if s.eclipse_witnessed:
            fame += 50
        self._sessions[session_id] = dataclasses.replace(
            s, state=SessionState.CLOSED,
        )
        return fame

    def lunar_phase(self, *, day: int) -> LunarPhase:
        return _lunar_phase_for_day(day)

    def session(
        self, *, session_id: str,
    ) -> t.Optional[Session]:
        return self._sessions.get(session_id)

    def constellation(
        self, *, name: str,
    ) -> t.Optional[Constellation]:
        return self._constellations.get(name)


__all__ = [
    "Season", "LunarPhase", "SessionState",
    "Constellation", "Observation", "Session",
    "PlayerStargazingSystem",
]
