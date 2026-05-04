"""Beastman arena circuit — gladiator pits + ranked ladder.

The civic gladiator culture of the beastman cities. Each city
runs its own ARENA with seasonal CHALLENGER LADDERS divided
into WEIGHT CLASSES (light/medium/heavy/champion). Players
register for a class, fight 1v1 sanctioned bouts, and accrue
ARENA POINTS that translate into rank.

A SEASON is a fixed window (default 30 days) that resets at
season-end. The top three of each weight class earn TITLE
ROSTERS and trophy gear.

Public surface
--------------
    ArenaCity enum
    WeightClass enum   LIGHT / MEDIUM / HEAVY / CHAMPION
    BoutOutcome enum   WIN / LOSS / DRAW / FORFEIT
    Bout dataclass
    SeasonStanding dataclass
    BeastmanArenaCircuit
        .open_season(city, weight_class, season_id, length_days,
                     now_seconds)
        .register(player_id, city, weight_class, season_id)
        .record_bout(season_id, attacker, defender, outcome)
        .standing_for(player_id, season_id)
        .top_three(season_id)
        .close_season(season_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ArenaCity(str, enum.Enum):
    OZTROJA = "oztroja"
    PALBOROUGH = "palborough"
    HALVUNG = "halvung"
    ARRAPAGO = "arrapago"


class WeightClass(str, enum.Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    CHAMPION = "champion"


class BoutOutcome(str, enum.Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    FORFEIT = "forfeit"


class SeasonState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


_OUTCOME_POINTS: dict[BoutOutcome, tuple[int, int]] = {
    # (attacker_delta, defender_delta)
    BoutOutcome.WIN: (3, 0),
    BoutOutcome.LOSS: (0, 3),
    BoutOutcome.DRAW: (1, 1),
    BoutOutcome.FORFEIT: (3, -1),
}


@dataclasses.dataclass
class Season:
    season_id: str
    city: ArenaCity
    weight_class: WeightClass
    opened_at: int
    length_seconds: int
    state: SeasonState = SeasonState.OPEN
    closed_at: t.Optional[int] = None
    points: dict[str, int] = dataclasses.field(default_factory=dict)
    bouts: list["Bout"] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Bout:
    bout_id: int
    season_id: str
    attacker_id: str
    defender_id: str
    outcome: BoutOutcome


@dataclasses.dataclass(frozen=True)
class SeasonStanding:
    player_id: str
    season_id: str
    points: int
    bouts_played: int


@dataclasses.dataclass(frozen=True)
class BoutResult:
    accepted: bool
    bout_id: int
    attacker_points: int
    defender_points: int
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanArenaCircuit:
    _seasons: dict[str, Season] = dataclasses.field(default_factory=dict)
    _registered: dict[
        str, set[str]
    ] = dataclasses.field(default_factory=dict)
    _next_bout_id: int = 1

    def open_season(
        self, *, season_id: str,
        city: ArenaCity,
        weight_class: WeightClass,
        length_days: int,
        now_seconds: int,
    ) -> t.Optional[Season]:
        if season_id in self._seasons:
            return None
        if length_days <= 0:
            return None
        s = Season(
            season_id=season_id,
            city=city,
            weight_class=weight_class,
            opened_at=now_seconds,
            length_seconds=length_days * 86_400,
        )
        self._seasons[season_id] = s
        self._registered[season_id] = set()
        return s

    def register(
        self, *, player_id: str, season_id: str,
    ) -> bool:
        s = self._seasons.get(season_id)
        if s is None or s.state != SeasonState.OPEN:
            return False
        roster = self._registered[season_id]
        if player_id in roster:
            return False
        roster.add(player_id)
        s.points[player_id] = 0
        return True

    def record_bout(
        self, *, season_id: str,
        attacker_id: str, defender_id: str,
        outcome: BoutOutcome,
    ) -> BoutResult:
        s = self._seasons.get(season_id)
        if s is None:
            return BoutResult(
                False, 0, 0, 0, reason="unknown season",
            )
        if s.state != SeasonState.OPEN:
            return BoutResult(
                False, 0, 0, 0, reason="season closed",
            )
        if attacker_id == defender_id:
            return BoutResult(
                False, 0, 0, 0, reason="same combatant",
            )
        roster = self._registered[season_id]
        if (
            attacker_id not in roster
            or defender_id not in roster
        ):
            return BoutResult(
                False, 0, 0, 0, reason="combatant not registered",
            )
        a_d, d_d = _OUTCOME_POINTS[outcome]
        s.points[attacker_id] = max(
            0, s.points.get(attacker_id, 0) + a_d,
        )
        s.points[defender_id] = max(
            0, s.points.get(defender_id, 0) + d_d,
        )
        bout_id = self._next_bout_id
        self._next_bout_id += 1
        s.bouts.append(
            Bout(
                bout_id=bout_id,
                season_id=season_id,
                attacker_id=attacker_id,
                defender_id=defender_id,
                outcome=outcome,
            ),
        )
        return BoutResult(
            accepted=True,
            bout_id=bout_id,
            attacker_points=s.points[attacker_id],
            defender_points=s.points[defender_id],
        )

    def standing_for(
        self, *, player_id: str, season_id: str,
    ) -> t.Optional[SeasonStanding]:
        s = self._seasons.get(season_id)
        if s is None:
            return None
        if player_id not in s.points:
            return None
        bouts = sum(
            1 for b in s.bouts
            if b.attacker_id == player_id or b.defender_id == player_id
        )
        return SeasonStanding(
            player_id=player_id,
            season_id=season_id,
            points=s.points[player_id],
            bouts_played=bouts,
        )

    def top_three(
        self, *, season_id: str,
    ) -> list[tuple[str, int]]:
        s = self._seasons.get(season_id)
        if s is None:
            return []
        ordered = sorted(
            s.points.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
        return ordered[:3]

    def close_season(
        self, *, season_id: str, now_seconds: int,
    ) -> bool:
        s = self._seasons.get(season_id)
        if s is None or s.state == SeasonState.CLOSED:
            return False
        s.state = SeasonState.CLOSED
        s.closed_at = now_seconds
        return True

    def total_seasons(self) -> int:
        return len(self._seasons)


__all__ = [
    "ArenaCity", "WeightClass", "BoutOutcome", "SeasonState",
    "Season", "Bout", "SeasonStanding", "BoutResult",
    "BeastmanArenaCircuit",
]
