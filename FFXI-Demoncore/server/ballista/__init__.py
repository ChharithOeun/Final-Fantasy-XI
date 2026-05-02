"""Ballista — formal consensual PvP arena.

Different from outlaw_system (open-world bounty PvP). Ballista is a
scheduled match: teams sign up at the recruiter, get teleported into
a closed arena, score points by killing opponents and throwing petras
at the rook (the team objective). Highest score at timer wins.

Public surface
--------------
    BallistaTeam enum (TEAM_A / TEAM_B)
    BallistaMatch lifecycle
        .add_player(team, player_id)
        .record_kill(killer, victim)
        .record_petra_throw(player, target_team)
        .conclude() -> MatchResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BallistaTeam(str, enum.Enum):
    TEAM_A = "team_a"
    TEAM_B = "team_b"


# Scoring values
SCORE_KILL = 100
SCORE_PETRA_HIT = 50


DEFAULT_MATCH_SECONDS = 30 * 60      # 30-minute match


@dataclasses.dataclass(frozen=True)
class MatchResult:
    accepted: bool
    winner: t.Optional[BallistaTeam]
    score_a: int
    score_b: int
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BallistaMatch:
    match_id: str
    started_at_tick: int
    expires_at_tick: int
    team_a: set[str] = dataclasses.field(default_factory=set)
    team_b: set[str] = dataclasses.field(default_factory=set)
    score_a: int = 0
    score_b: int = 0
    concluded: bool = False
    per_player_kills: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def add_player(
        self, *, team: BallistaTeam, player_id: str,
    ) -> bool:
        if self.concluded:
            return False
        if player_id in self.team_a or player_id in self.team_b:
            return False
        if team == BallistaTeam.TEAM_A:
            self.team_a.add(player_id)
        else:
            self.team_b.add(player_id)
        return True

    def team_of(self, player_id: str) -> t.Optional[BallistaTeam]:
        if player_id in self.team_a:
            return BallistaTeam.TEAM_A
        if player_id in self.team_b:
            return BallistaTeam.TEAM_B
        return None

    def record_kill(
        self, *, killer_id: str, victim_id: str,
    ) -> bool:
        if self.concluded:
            return False
        k_team = self.team_of(killer_id)
        v_team = self.team_of(victim_id)
        if k_team is None or v_team is None:
            return False
        if k_team == v_team:
            return False    # team kill no score
        if k_team == BallistaTeam.TEAM_A:
            self.score_a += SCORE_KILL
        else:
            self.score_b += SCORE_KILL
        self.per_player_kills[killer_id] = (
            self.per_player_kills.get(killer_id, 0) + 1
        )
        return True

    def record_petra_throw(
        self, *, thrower_id: str, target_team: BallistaTeam,
    ) -> bool:
        if self.concluded:
            return False
        t_team = self.team_of(thrower_id)
        if t_team is None:
            return False
        if t_team == target_team:
            return False    # can't petra own rook
        if t_team == BallistaTeam.TEAM_A:
            self.score_a += SCORE_PETRA_HIT
        else:
            self.score_b += SCORE_PETRA_HIT
        return True

    def conclude(self) -> MatchResult:
        self.concluded = True
        if self.score_a > self.score_b:
            winner = BallistaTeam.TEAM_A
        elif self.score_b > self.score_a:
            winner = BallistaTeam.TEAM_B
        else:
            winner = None       # tie
        return MatchResult(
            accepted=True, winner=winner,
            score_a=self.score_a, score_b=self.score_b,
        )


def open_match(
    *, match_id: str, now_tick: int,
    duration_seconds: int = DEFAULT_MATCH_SECONDS,
) -> BallistaMatch:
    return BallistaMatch(
        match_id=match_id,
        started_at_tick=now_tick,
        expires_at_tick=now_tick + duration_seconds,
    )


__all__ = [
    "BallistaTeam", "SCORE_KILL", "SCORE_PETRA_HIT",
    "DEFAULT_MATCH_SECONDS",
    "MatchResult", "BallistaMatch",
    "open_match",
]
