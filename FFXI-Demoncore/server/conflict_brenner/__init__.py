"""Conflict — Brenner 4-team capture-the-flame PvP.

Canonical FFXI Brenner: four teams (Sandy/Bastok/Windy/Jeuno
+ neutral mercs) compete in a fenced arena. Each team starts
with a Brenner Flame guarded in their base. Players carry
opposing teams' flames to their own brazier to score; whoever
hits the score cap or has the most points at timer expiry wins.

Scoring rules:
* Stealing an opposing flame: +1 point (committed when carried
  to base brazier and ignited)
* Defending: +1 point per opposing flame-carrier defeated
  inside your base
* No score for ground kills outside flag carry / defense

Public surface
--------------
    BrennerTeam enum
    BrennerMatchState enum
    BrennerMatch dataclass
        .add_player(team, player_id) -> bool
        .ignite_stolen_flame(team, attacker_id) -> int
        .defender_kill(team, defender_id) -> int
        .resolve(now) -> BrennerResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


SCORE_CAP = 7
DEFAULT_MATCH_SECONDS = 30 * 60       # 30-minute match
MAX_PER_TEAM = 6
MIN_PER_TEAM = 1


class BrennerTeam(str, enum.Enum):
    SANDY = "san_doria"
    BASTOK = "bastok"
    WINDY = "windurst"
    MERCS = "jeunoan_mercs"


class BrennerMatchState(str, enum.Enum):
    OPEN = "open"
    ACTIVE = "active"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


@dataclasses.dataclass
class _TeamState:
    score: int = 0
    members: list[str] = dataclasses.field(default_factory=list)
    ignite_credits: dict[str, int] = dataclasses.field(default_factory=dict)
    defense_credits: dict[str, int] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class PlayerContribution:
    player_id: str
    team: BrennerTeam
    ignites: int
    defenses: int
    points_earned: int


@dataclasses.dataclass(frozen=True)
class BrennerResult:
    accepted: bool
    winner: t.Optional[BrennerTeam] = None
    reason: t.Optional[str] = None
    scores: dict[BrennerTeam, int] = dataclasses.field(
        default_factory=dict,
    )
    contributions: tuple[PlayerContribution, ...] = ()


@dataclasses.dataclass
class BrennerMatch:
    match_id: str
    started_at: float = 0.0
    ends_at: float = 0.0
    state: BrennerMatchState = BrennerMatchState.OPEN
    teams: dict[BrennerTeam, _TeamState] = dataclasses.field(
        default_factory=lambda: {t: _TeamState() for t in BrennerTeam},
    )

    @classmethod
    def open(cls, *, match_id: str,
             timer_seconds: int = DEFAULT_MATCH_SECONDS,
             now_seconds: float = 0.0) -> "BrennerMatch":
        m = cls(match_id=match_id)
        m.started_at = now_seconds
        m.ends_at = now_seconds + timer_seconds
        return m

    @property
    def all_teams_filled(self) -> bool:
        return all(
            len(self.teams[t].members) >= MIN_PER_TEAM
            for t in BrennerTeam
        )

    def add_player(
        self, *, team: BrennerTeam, player_id: str,
    ) -> bool:
        if self.state != BrennerMatchState.OPEN:
            return False
        if any(player_id in self.teams[t].members for t in BrennerTeam):
            return False
        if len(self.teams[team].members) >= MAX_PER_TEAM:
            return False
        self.teams[team].members.append(player_id)
        return True

    def begin(self, *, now_seconds: float = 0.0) -> bool:
        if self.state != BrennerMatchState.OPEN:
            return False
        if not self.all_teams_filled:
            return False
        self.state = BrennerMatchState.ACTIVE
        self.started_at = now_seconds
        return True

    def ignite_stolen_flame(
        self, *, team: BrennerTeam, attacker_id: str,
    ) -> int:
        if self.state != BrennerMatchState.ACTIVE:
            return 0
        if attacker_id not in self.teams[team].members:
            return 0
        self.teams[team].score += 1
        self.teams[team].ignite_credits[attacker_id] = (
            self.teams[team].ignite_credits.get(attacker_id, 0) + 1
        )
        return self.teams[team].score

    def defender_kill(
        self, *, team: BrennerTeam, defender_id: str,
    ) -> int:
        if self.state != BrennerMatchState.ACTIVE:
            return 0
        if defender_id not in self.teams[team].members:
            return 0
        self.teams[team].score += 1
        self.teams[team].defense_credits[defender_id] = (
            self.teams[team].defense_credits.get(defender_id, 0) + 1
        )
        return self.teams[team].score

    def cancel(self) -> bool:
        if self.state in (BrennerMatchState.RESOLVED,
                          BrennerMatchState.CANCELLED):
            return False
        self.state = BrennerMatchState.CANCELLED
        return True

    def resolve(self, *, now_seconds: float) -> BrennerResult:
        if self.state == BrennerMatchState.RESOLVED:
            return BrennerResult(False, reason="already resolved")
        if self.state != BrennerMatchState.ACTIVE:
            return BrennerResult(False, reason="match not active")
        # Either someone hit cap, or timer expired
        scores = {t: self.teams[t].score for t in BrennerTeam}
        capped = [t for t, s in scores.items() if s >= SCORE_CAP]
        timed = now_seconds >= self.ends_at
        if not capped and not timed:
            return BrennerResult(
                False, reason="match still in progress", scores=scores,
            )
        winner: t.Optional[BrennerTeam] = None
        if capped:
            winner = capped[0]
        else:
            # Highest score wins, ties resolved by alphabetical
            top_score = max(scores.values())
            top = [t for t, s in scores.items() if s == top_score]
            if len(top) == 1:
                winner = top[0]
            # ties — winner = None (cooperative draw)
        self.state = BrennerMatchState.RESOLVED
        contributions: list[PlayerContribution] = []
        for team in BrennerTeam:
            ts = self.teams[team]
            for pid in ts.members:
                ig = ts.ignite_credits.get(pid, 0)
                df = ts.defense_credits.get(pid, 0)
                contributions.append(PlayerContribution(
                    player_id=pid, team=team,
                    ignites=ig, defenses=df,
                    points_earned=ig + df,
                ))
        return BrennerResult(
            accepted=True, winner=winner, scores=scores,
            contributions=tuple(contributions),
        )


__all__ = [
    "SCORE_CAP", "DEFAULT_MATCH_SECONDS",
    "MAX_PER_TEAM", "MIN_PER_TEAM",
    "BrennerTeam", "BrennerMatchState",
    "PlayerContribution", "BrennerResult",
    "BrennerMatch",
]
