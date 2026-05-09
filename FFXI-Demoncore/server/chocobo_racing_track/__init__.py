"""Chocobo racing track — race brackets and betting pools.

Players bring their bred chocobos (from chocobo_breeding)
to a TRACK and run scheduled races. Each race has 4-8
runners; payouts are pari-mutuel — bettors split the pool
proportional to their wager among bettors who picked the
winner. The chocobo's speed/stamina from breeding plus
race-day variance determine the result.

Lifecycle per race:
    REGISTRATION_OPEN   accepting runners
    BETS_OPEN           runners locked, accepting wagers
    RUNNING             race in progress
    SETTLED             results posted, payouts paid

Public surface
--------------
    RaceState enum
    Runner dataclass (frozen)
    Bet dataclass (frozen)
    Race dataclass (frozen)
    ChocoboRacingTrackSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_HOUSE_TAKE_BPS = 500  # 5% house cut


class RaceState(str, enum.Enum):
    REGISTRATION_OPEN = "registration_open"
    BETS_OPEN = "bets_open"
    RUNNING = "running"
    SETTLED = "settled"


@dataclasses.dataclass(frozen=True)
class Runner:
    runner_id: str
    chocobo_id: str
    owner_id: str
    speed: int       # 1..100
    stamina: int     # 1..100


@dataclasses.dataclass(frozen=True)
class Bet:
    bet_id: str
    bettor_id: str
    runner_id: str
    wager_gil: int
    placed_day: int


@dataclasses.dataclass(frozen=True)
class Race:
    race_id: str
    track_id: str
    distance_furlongs: int
    field_min: int
    field_max: int
    state: RaceState
    winner_runner_id: str
    pool_total_gil: int


@dataclasses.dataclass
class _RState:
    spec: Race
    runners: dict[str, Runner] = dataclasses.field(
        default_factory=dict,
    )
    bets: dict[str, Bet] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class ChocoboRacingTrackSystem:
    _races: dict[str, _RState] = dataclasses.field(
        default_factory=dict,
    )
    _next_race: int = 1
    _next_bet: int = 1

    def schedule_race(
        self, *, track_id: str,
        distance_furlongs: int,
        field_min: int = 4, field_max: int = 8,
    ) -> t.Optional[str]:
        if not track_id:
            return None
        if distance_furlongs <= 0:
            return None
        if field_min < 2 or field_max < field_min:
            return None
        rid = f"race_{self._next_race}"
        self._next_race += 1
        spec = Race(
            race_id=rid, track_id=track_id,
            distance_furlongs=distance_furlongs,
            field_min=field_min,
            field_max=field_max,
            state=RaceState.REGISTRATION_OPEN,
            winner_runner_id="", pool_total_gil=0,
        )
        self._races[rid] = _RState(spec=spec)
        return rid

    def register_runner(
        self, *, race_id: str, chocobo_id: str,
        owner_id: str, speed: int, stamina: int,
    ) -> t.Optional[str]:
        if race_id not in self._races:
            return None
        st = self._races[race_id]
        if st.spec.state != (
            RaceState.REGISTRATION_OPEN
        ):
            return None
        if not chocobo_id or not owner_id:
            return None
        if not 1 <= speed <= 100:
            return None
        if not 1 <= stamina <= 100:
            return None
        if len(st.runners) >= st.spec.field_max:
            return None
        # One chocobo per race
        for r in st.runners.values():
            if r.chocobo_id == chocobo_id:
                return None
        runner_id = f"{race_id}_runner_{len(st.runners) + 1}"
        st.runners[runner_id] = Runner(
            runner_id=runner_id,
            chocobo_id=chocobo_id,
            owner_id=owner_id, speed=speed,
            stamina=stamina,
        )
        return runner_id

    def open_bets(self, *, race_id: str) -> bool:
        if race_id not in self._races:
            return False
        st = self._races[race_id]
        if st.spec.state != (
            RaceState.REGISTRATION_OPEN
        ):
            return False
        if len(st.runners) < st.spec.field_min:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=RaceState.BETS_OPEN,
        )
        return True

    def place_bet(
        self, *, race_id: str, bettor_id: str,
        runner_id: str, wager_gil: int,
        placed_day: int,
    ) -> t.Optional[str]:
        if race_id not in self._races:
            return None
        st = self._races[race_id]
        if st.spec.state != RaceState.BETS_OPEN:
            return None
        if not bettor_id or wager_gil <= 0:
            return None
        if placed_day < 0:
            return None
        if runner_id not in st.runners:
            return None
        bid = f"bet_{self._next_bet}"
        self._next_bet += 1
        st.bets[bid] = Bet(
            bet_id=bid, bettor_id=bettor_id,
            runner_id=runner_id, wager_gil=wager_gil,
            placed_day=placed_day,
        )
        st.spec = dataclasses.replace(
            st.spec, pool_total_gil=(
                st.spec.pool_total_gil + wager_gil
            ),
        )
        return bid

    def start_race(
        self, *, race_id: str,
    ) -> bool:
        if race_id not in self._races:
            return False
        st = self._races[race_id]
        if st.spec.state != RaceState.BETS_OPEN:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=RaceState.RUNNING,
        )
        return True

    def resolve_race(
        self, *, race_id: str, seed: int,
    ) -> t.Optional[str]:
        """Determine winner deterministically.
        Score = speed*2 + stamina + variance(seed).
        Highest score wins.
        """
        if race_id not in self._races:
            return None
        st = self._races[race_id]
        if st.spec.state != RaceState.RUNNING:
            return None
        if not st.runners:
            return None
        scored: list[tuple[int, str]] = []
        for i, (rid, r) in enumerate(
            sorted(st.runners.items()),
        ):
            variance = ((seed >> (i * 3)) & 0xFF) % 30
            score = (
                r.speed * 2 + r.stamina + variance
            )
            # Tie break by stable runner_id ordering
            scored.append((-score, rid))
        scored.sort()
        winner_id = scored[0][1]
        st.spec = dataclasses.replace(
            st.spec, state=RaceState.SETTLED,
            winner_runner_id=winner_id,
        )
        return winner_id

    def payout(
        self, *, race_id: str, bettor_id: str,
    ) -> int:
        """Pari-mutuel payout: bettor's share of the
        prize pool (after house take) proportional to
        their wager among winning bets."""
        if race_id not in self._races:
            return 0
        st = self._races[race_id]
        if st.spec.state != RaceState.SETTLED:
            return 0
        winner = st.spec.winner_runner_id
        if not winner:
            return 0
        my_winning_total = sum(
            b.wager_gil
            for b in st.bets.values()
            if (b.bettor_id == bettor_id
                and b.runner_id == winner)
        )
        if my_winning_total == 0:
            return 0
        all_winning_total = sum(
            b.wager_gil
            for b in st.bets.values()
            if b.runner_id == winner
        )
        if all_winning_total == 0:
            return 0
        prize_pool = (
            st.spec.pool_total_gil
            * (10_000 - _HOUSE_TAKE_BPS) // 10_000
        )
        return (
            prize_pool * my_winning_total
            // all_winning_total
        )

    def race(
        self, *, race_id: str,
    ) -> t.Optional[Race]:
        if race_id not in self._races:
            return None
        return self._races[race_id].spec

    def runners(
        self, *, race_id: str,
    ) -> list[Runner]:
        if race_id not in self._races:
            return []
        return list(
            self._races[race_id].runners.values(),
        )


__all__ = [
    "RaceState", "Runner", "Bet", "Race",
    "ChocoboRacingTrackSystem",
]
