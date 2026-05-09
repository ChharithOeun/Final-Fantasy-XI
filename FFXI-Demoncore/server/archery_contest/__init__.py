"""Archery contest — solo precision skill challenge.

A standalone solo minigame: 10 arrows at a target,
each scored 0..10 based on a deterministic
archer_skill + bow_quality + variance roll. Total
score determines a leaderboard entry. Tournaments
group multiple archers and rank their score totals.

Lifecycle:
    REGISTERED       archer signed up; not yet shooting
    SHOOTING         arrows being loosed
    COMPLETED        all arrows shot; score final

Public surface
--------------
    SessionState enum
    ArrowResult dataclass (frozen)
    Session dataclass (frozen)
    ArcheryContestSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_ARROWS_PER_SESSION = 10
_PERFECT_SCORE = 100


class SessionState(str, enum.Enum):
    REGISTERED = "registered"
    SHOOTING = "shooting"
    COMPLETED = "completed"


@dataclasses.dataclass(frozen=True)
class ArrowResult:
    arrow_index: int
    points: int  # 0..10


@dataclasses.dataclass(frozen=True)
class Session:
    session_id: str
    archer_id: str
    contest_id: str
    archer_skill: int
    bow_quality: int
    started_day: int
    arrows: tuple[ArrowResult, ...]
    state: SessionState
    total_score: int


@dataclasses.dataclass
class ArcheryContestSystem:
    _sessions: dict[str, Session] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def register(
        self, *, archer_id: str, contest_id: str,
        archer_skill: int, bow_quality: int,
        started_day: int,
    ) -> t.Optional[str]:
        if not archer_id or not contest_id:
            return None
        if not 1 <= archer_skill <= 100:
            return None
        if not 1 <= bow_quality <= 100:
            return None
        if started_day < 0:
            return None
        # One active session per archer per contest
        for s in self._sessions.values():
            if (s.archer_id == archer_id
                    and s.contest_id == contest_id
                    and s.state != (
                        SessionState.COMPLETED)):
                return None
        sid = f"sess_{self._next_id}"
        self._next_id += 1
        self._sessions[sid] = Session(
            session_id=sid, archer_id=archer_id,
            contest_id=contest_id,
            archer_skill=archer_skill,
            bow_quality=bow_quality,
            started_day=started_day,
            arrows=(),
            state=SessionState.REGISTERED,
            total_score=0,
        )
        return sid

    def begin_shooting(
        self, *, session_id: str,
    ) -> bool:
        if session_id not in self._sessions:
            return False
        s = self._sessions[session_id]
        if s.state != SessionState.REGISTERED:
            return False
        self._sessions[session_id] = (
            dataclasses.replace(
                s, state=SessionState.SHOOTING,
            )
        )
        return True

    def loose_arrow(
        self, *, session_id: str, seed: int,
    ) -> t.Optional[int]:
        """Score one arrow deterministically.
        Composite: skill/10 + bow/10 + variance(0..3)
        clamped 0..10. Returns the points awarded.
        """
        if session_id not in self._sessions:
            return None
        s = self._sessions[session_id]
        if s.state != SessionState.SHOOTING:
            return None
        if len(s.arrows) >= _ARROWS_PER_SESSION:
            return None
        idx = len(s.arrows)
        variance = (seed >> (idx * 2)) % 4
        raw = (
            s.archer_skill // 20
            + s.bow_quality // 20
            + variance
        )
        # Each side caps at 10; total cap 10 per
        # arrow.
        points = max(0, min(10, raw))
        new_arrows = s.arrows + (ArrowResult(
            arrow_index=idx, points=points,
        ),)
        new_total = s.total_score + points
        new_state = (
            SessionState.COMPLETED
            if len(new_arrows)
            == _ARROWS_PER_SESSION
            else SessionState.SHOOTING
        )
        self._sessions[session_id] = (
            dataclasses.replace(
                s, arrows=new_arrows,
                total_score=new_total,
                state=new_state,
            )
        )
        return points

    def session(
        self, *, session_id: str,
    ) -> t.Optional[Session]:
        return self._sessions.get(session_id)

    def leaderboard(
        self, *, contest_id: str, limit: int,
    ) -> list[Session]:
        if limit <= 0:
            return []
        completed = [
            s for s in self._sessions.values()
            if (s.contest_id == contest_id
                and s.state
                == SessionState.COMPLETED)
        ]
        return sorted(
            completed,
            key=lambda s: -s.total_score,
        )[:limit]

    def archer_best(
        self, *, archer_id: str, contest_id: str,
    ) -> t.Optional[Session]:
        completed = [
            s for s in self._sessions.values()
            if (s.archer_id == archer_id
                and s.contest_id == contest_id
                and s.state
                == SessionState.COMPLETED)
        ]
        if not completed:
            return None
        return max(
            completed, key=lambda s: s.total_score,
        )

    def is_perfect(
        self, *, session_id: str,
    ) -> bool:
        s = self._sessions.get(session_id)
        if s is None:
            return False
        return (
            s.state == SessionState.COMPLETED
            and s.total_score == _PERFECT_SCORE
        )


__all__ = [
    "SessionState", "ArrowResult", "Session",
    "ArcheryContestSystem",
]
