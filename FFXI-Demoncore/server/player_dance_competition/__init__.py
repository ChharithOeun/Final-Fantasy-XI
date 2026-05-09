"""Player dance competition — judged dance tournaments.

Tournaments register dancers, each performs once, judges score
performances on tempo / precision / style. Weighted total
ranks the field, top 3 split a prize purse 50/30/20.

Lifecycle
    OPEN_REGISTRATION  dancers signing up
    JUDGING            performances delivered, scoring
    COMPLETED          rankings final, payouts done

Public surface
--------------
    TournamentState enum
    Performance dataclass (frozen)
    Tournament dataclass (frozen)
    PlayerDanceCompetitionSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_TEMPO_WEIGHT = 30      # of 100
_PRECISION_WEIGHT = 40
_STYLE_WEIGHT = 30


class TournamentState(str, enum.Enum):
    OPEN_REGISTRATION = "open_registration"
    JUDGING = "judging"
    COMPLETED = "completed"


@dataclasses.dataclass(frozen=True)
class Performance:
    performance_id: str
    dancer_id: str
    tempo_score: int       # 1..100
    precision_score: int   # 1..100
    style_score: int       # 1..100
    weighted_total: int


@dataclasses.dataclass(frozen=True)
class Tournament:
    tournament_id: str
    venue_id: str
    field_min: int
    field_max: int
    prize_purse_gil: int
    state: TournamentState
    rankings: tuple[str, ...]    # dancer_ids in rank order


@dataclasses.dataclass
class _TState:
    spec: Tournament
    performances: dict[str, Performance] = (
        dataclasses.field(default_factory=dict)
    )


@dataclasses.dataclass
class PlayerDanceCompetitionSystem:
    _tournaments: dict[str, _TState] = dataclasses.field(
        default_factory=dict,
    )
    _next_tournament: int = 1
    _next_performance: int = 1

    def open_tournament(
        self, *, venue_id: str, field_min: int = 3,
        field_max: int = 12, prize_purse_gil: int = 0,
    ) -> t.Optional[str]:
        if not venue_id:
            return None
        if field_min < 2 or field_max < field_min:
            return None
        if prize_purse_gil < 0:
            return None
        tid = f"tour_{self._next_tournament}"
        self._next_tournament += 1
        spec = Tournament(
            tournament_id=tid, venue_id=venue_id,
            field_min=field_min, field_max=field_max,
            prize_purse_gil=prize_purse_gil,
            state=TournamentState.OPEN_REGISTRATION,
            rankings=(),
        )
        self._tournaments[tid] = _TState(spec=spec)
        return tid

    def register_dancer(
        self, *, tournament_id: str, dancer_id: str,
    ) -> bool:
        if tournament_id not in self._tournaments:
            return False
        st = self._tournaments[tournament_id]
        if st.spec.state != (
            TournamentState.OPEN_REGISTRATION
        ):
            return False
        if not dancer_id:
            return False
        # No double registration; field cap.
        for p in st.performances.values():
            if p.dancer_id == dancer_id:
                return False
        if len(st.performances) >= st.spec.field_max:
            return False
        # Pre-register a placeholder performance so the
        # cap and uniqueness checks compose. Real
        # scoring happens in submit_performance.
        pid = f"perf_{self._next_performance}"
        self._next_performance += 1
        st.performances[pid] = Performance(
            performance_id=pid, dancer_id=dancer_id,
            tempo_score=0, precision_score=0,
            style_score=0, weighted_total=0,
        )
        return True

    def lock_field(
        self, *, tournament_id: str,
    ) -> bool:
        if tournament_id not in self._tournaments:
            return False
        st = self._tournaments[tournament_id]
        if st.spec.state != (
            TournamentState.OPEN_REGISTRATION
        ):
            return False
        if len(st.performances) < st.spec.field_min:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=TournamentState.JUDGING,
        )
        return True

    def submit_performance(
        self, *, tournament_id: str, dancer_id: str,
        tempo_score: int, precision_score: int,
        style_score: int,
    ) -> t.Optional[int]:
        if tournament_id not in self._tournaments:
            return None
        st = self._tournaments[tournament_id]
        if st.spec.state != TournamentState.JUDGING:
            return None
        for s in (
            tempo_score, precision_score, style_score,
        ):
            if not 1 <= s <= 100:
                return None
        target_pid = None
        for pid, p in st.performances.items():
            if p.dancer_id == dancer_id:
                target_pid = pid
                break
        if target_pid is None:
            return None
        weighted = (
            tempo_score * _TEMPO_WEIGHT
            + precision_score * _PRECISION_WEIGHT
            + style_score * _STYLE_WEIGHT
        ) // 100
        st.performances[target_pid] = Performance(
            performance_id=target_pid,
            dancer_id=dancer_id,
            tempo_score=tempo_score,
            precision_score=precision_score,
            style_score=style_score,
            weighted_total=weighted,
        )
        return weighted

    def finalize(
        self, *, tournament_id: str,
    ) -> t.Optional[tuple[str, ...]]:
        if tournament_id not in self._tournaments:
            return None
        st = self._tournaments[tournament_id]
        if st.spec.state != TournamentState.JUDGING:
            return None
        ranked = sorted(
            st.performances.values(),
            key=lambda p: -p.weighted_total,
        )
        rankings = tuple(p.dancer_id for p in ranked)
        st.spec = dataclasses.replace(
            st.spec, state=TournamentState.COMPLETED,
            rankings=rankings,
        )
        return rankings

    def payout(
        self, *, tournament_id: str, dancer_id: str,
    ) -> int:
        if tournament_id not in self._tournaments:
            return 0
        st = self._tournaments[tournament_id]
        if st.spec.state != TournamentState.COMPLETED:
            return 0
        if dancer_id not in st.spec.rankings:
            return 0
        rank = st.spec.rankings.index(dancer_id)
        purse = st.spec.prize_purse_gil
        if rank == 0:
            return purse * 50 // 100
        if rank == 1:
            return purse * 30 // 100
        if rank == 2:
            return purse * 20 // 100
        return 0

    def tournament(
        self, *, tournament_id: str,
    ) -> t.Optional[Tournament]:
        st = self._tournaments.get(tournament_id)
        return st.spec if st else None

    def performances(
        self, *, tournament_id: str,
    ) -> list[Performance]:
        st = self._tournaments.get(tournament_id)
        if st is None:
            return []
        return list(st.performances.values())


__all__ = [
    "TournamentState", "Performance", "Tournament",
    "PlayerDanceCompetitionSystem",
]
