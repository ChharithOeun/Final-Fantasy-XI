"""Voice session studio — booking, take logging, ADR.

Models the studio side of a real recording session. Six
named studios cover the realistic vendor space — one home
booth (Source-Connect from anywhere), four city studios
(LA / NYC / London / Tokyo), and one open-source remote
option (Jamulus). The director can book any of them by name
and log per-line takes against the booking.

Take marks follow the standard set:
    PICK — the take we'll print
    ALT  — usable alternate
    WILD — off-script improv worth keeping for the cutting room
    HOLD — keeper but not preferred

ADR (automated dialogue replacement) is a session kind, not a
separate workflow — it just means the actor is recording
pickups against picture lock instead of cold reads.

Public surface
--------------
    StudioKind enum
    SessionState enum
    SessionKind enum
    DirectorMark enum
    Studio dataclass (frozen)
    Take dataclass (frozen)
    Session dataclass
    SessionStudio
    STUDIOS dict
"""
from __future__ import annotations

import dataclasses
import enum
import itertools
import typing as t


class StudioKind(enum.Enum):
    IN_PERSON = "in_person"
    REMOTE = "remote"
    HYBRID = "hybrid"


class SessionState(enum.Enum):
    BOOKED = "booked"
    SETUP = "setup"
    RECORDING = "recording"
    WRAPPED = "wrapped"
    DELIVERED = "delivered"


class SessionKind(enum.Enum):
    NORMAL = "normal"
    ADR = "adr"


class DirectorMark(enum.Enum):
    PICK = "pick"
    ALT = "alt"
    WILD = "wild"
    HOLD = "hold"


@dataclasses.dataclass(frozen=True)
class Studio:
    name: str
    kind: StudioKind
    latency_ms_to_director: int
    max_actors_simultaneous: int
    hourly_rate_usd: float
    isolation_db: float
    supports_adr: bool


STUDIOS: dict[str, Studio] = {
    s.name: s for s in (
        Studio(
            name="home_booth",
            kind=StudioKind.REMOTE,
            latency_ms_to_director=120,
            max_actors_simultaneous=1,
            hourly_rate_usd=0.0,
            isolation_db=35.0,
            supports_adr=True,
        ),
        Studio(
            name="burbank_voiceworks",
            kind=StudioKind.IN_PERSON,
            latency_ms_to_director=2,
            max_actors_simultaneous=4,
            hourly_rate_usd=300.0,
            isolation_db=65.0,
            supports_adr=True,
        ),
        Studio(
            name="city_nyc",
            kind=StudioKind.IN_PERSON,
            latency_ms_to_director=2,
            max_actors_simultaneous=3,
            hourly_rate_usd=325.0,
            isolation_db=62.0,
            supports_adr=True,
        ),
        Studio(
            name="air_studios",
            kind=StudioKind.IN_PERSON,
            latency_ms_to_director=2,
            max_actors_simultaneous=8,
            hourly_rate_usd=600.0,
            isolation_db=70.0,
            supports_adr=True,
        ),
        Studio(
            name="aoi_tokyo",
            kind=StudioKind.IN_PERSON,
            latency_ms_to_director=2,
            max_actors_simultaneous=3,
            hourly_rate_usd=280.0,
            isolation_db=60.0,
            supports_adr=True,
        ),
        Studio(
            name="jamulus_remote",
            kind=StudioKind.REMOTE,
            latency_ms_to_director=40,
            max_actors_simultaneous=6,
            hourly_rate_usd=0.0,
            isolation_db=20.0,
            supports_adr=False,
        ),
    )
}


@dataclasses.dataclass(frozen=True)
class Take:
    line_id: str
    take_number: int
    duration_s: float
    director_mark: DirectorMark


@dataclasses.dataclass
class Session:
    session_id: str
    studio_name: str
    role_id: str
    va_name: str
    hours: float
    kind: SessionKind
    state: SessionState
    takes: list[Take] = dataclasses.field(default_factory=list)
    delivered_uri: str = ""

    @property
    def projected_cost_usd(self) -> float:
        return STUDIOS[self.studio_name].hourly_rate_usd * (
            self.hours
        )


@dataclasses.dataclass
class SessionStudio:
    _sessions: dict[str, Session] = dataclasses.field(
        default_factory=dict,
    )
    _id_seq: t.Iterator[int] = dataclasses.field(
        default_factory=lambda: itertools.count(1),
    )

    def list_studios(self) -> tuple[Studio, ...]:
        return tuple(STUDIOS.values())

    def book_session(
        self, studio: str, role_id: str, va_name: str,
        hours: float,
        kind: SessionKind = SessionKind.NORMAL,
    ) -> Session:
        if studio not in STUDIOS:
            raise ValueError(f"unknown studio: {studio}")
        if hours <= 0:
            raise ValueError(
                f"hours must be > 0: {hours}",
            )
        if not role_id:
            raise ValueError("role_id required")
        if not va_name:
            raise ValueError("va_name required")
        s = STUDIOS[studio]
        if kind == SessionKind.ADR and not s.supports_adr:
            raise ValueError(
                f"studio {studio} does not support ADR",
            )
        sess_id = f"sess_{next(self._id_seq):05d}"
        sess = Session(
            session_id=sess_id, studio_name=studio,
            role_id=role_id, va_name=va_name,
            hours=float(hours), kind=kind,
            state=SessionState.BOOKED,
        )
        self._sessions[sess_id] = sess
        return sess

    def _get(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            raise KeyError(
                f"unknown session_id: {session_id}",
            )
        return self._sessions[session_id]

    def begin_setup(self, session_id: str) -> Session:
        sess = self._get(session_id)
        if sess.state != SessionState.BOOKED:
            raise RuntimeError(
                "can only enter SETUP from BOOKED, not "
                f"{sess.state.value}",
            )
        sess.state = SessionState.SETUP
        return sess

    def begin_recording(self, session_id: str) -> Session:
        sess = self._get(session_id)
        if sess.state not in (
            SessionState.BOOKED, SessionState.SETUP,
        ):
            raise RuntimeError(
                "can only enter RECORDING from BOOKED/SETUP; "
                f"got {sess.state.value}",
            )
        sess.state = SessionState.RECORDING
        return sess

    def log_take(
        self, session_id: str, line_id: str,
        take_number: int, duration_s: float,
        director_mark: DirectorMark,
    ) -> Take:
        sess = self._get(session_id)
        if sess.state == SessionState.BOOKED:
            sess.state = SessionState.RECORDING
        if sess.state != SessionState.RECORDING:
            raise RuntimeError(
                "can only log takes during RECORDING; "
                f"got {sess.state.value}",
            )
        if take_number < 1:
            raise ValueError(
                f"take_number must be >= 1: {take_number}",
            )
        if duration_s <= 0:
            raise ValueError(
                f"duration_s must be > 0: {duration_s}",
            )
        take = Take(
            line_id=line_id, take_number=take_number,
            duration_s=float(duration_s),
            director_mark=director_mark,
        )
        sess.takes.append(take)
        return take

    def wrap(self, session_id: str) -> Session:
        sess = self._get(session_id)
        if sess.state not in (
            SessionState.RECORDING, SessionState.SETUP,
        ):
            raise RuntimeError(
                "wrap requires RECORDING or SETUP; got "
                f"{sess.state.value}",
            )
        sess.state = SessionState.WRAPPED
        return sess

    def deliver(
        self, session_id: str, asset_uri: str,
    ) -> Session:
        sess = self._get(session_id)
        if sess.state != SessionState.WRAPPED:
            raise RuntimeError(
                f"deliver requires WRAPPED; got "
                f"{sess.state.value}",
            )
        if not asset_uri:
            raise ValueError("asset_uri required")
        sess.state = SessionState.DELIVERED
        sess.delivered_uri = asset_uri
        return sess

    def session_summary(self, session_id: str) -> dict:
        sess = self._get(session_id)
        picks = [
            t for t in sess.takes
            if t.director_mark == DirectorMark.PICK
        ]
        return {
            "session_id": sess.session_id,
            "studio": sess.studio_name,
            "role_id": sess.role_id,
            "va_name": sess.va_name,
            "kind": sess.kind.value,
            "state": sess.state.value,
            "takes_total": len(sess.takes),
            "takes_pick": len(picks),
            "lines_recorded": len(
                {t.line_id for t in sess.takes},
            ),
            "projected_cost_usd": sess.projected_cost_usd,
            "delivered_uri": sess.delivered_uri,
        }

    def best_studio_for(
        self, va_location: str,
        budget_usd_max: float,
    ) -> Studio:
        """Pick the best-fit studio for a VA's location and a
        per-hour budget. Tokyo / London / NYC / LA prefer
        their local studio; otherwise default to home_booth
        if budget == 0, jamulus_remote if remote-comfortable,
        and the cheapest in-person if budget allows.
        """
        if budget_usd_max < 0:
            raise ValueError(
                f"budget_usd_max >= 0: {budget_usd_max}",
            )
        loc = va_location.lower()
        local_pref = {
            "la": "burbank_voiceworks",
            "los_angeles": "burbank_voiceworks",
            "burbank": "burbank_voiceworks",
            "nyc": "city_nyc",
            "new_york": "city_nyc",
            "ny": "city_nyc",
            "london": "air_studios",
            "tokyo": "aoi_tokyo",
        }
        candidate = local_pref.get(loc)
        if candidate is not None:
            s = STUDIOS[candidate]
            if s.hourly_rate_usd <= budget_usd_max:
                return s
        # No local match or it's too expensive — pick the
        # cheapest studio that fits the budget. Tie-break by
        # max_actors_simultaneous (more = better headroom).
        affordable = [
            s for s in STUDIOS.values()
            if s.hourly_rate_usd <= budget_usd_max
        ]
        if not affordable:
            raise ValueError(
                f"no studio within budget {budget_usd_max}",
            )
        affordable.sort(
            key=lambda s: (
                s.hourly_rate_usd,
                -s.max_actors_simultaneous,
            ),
        )
        return affordable[0]


__all__ = [
    "StudioKind", "SessionState", "SessionKind",
    "DirectorMark", "Studio", "Take", "Session",
    "SessionStudio", "STUDIOS",
]
