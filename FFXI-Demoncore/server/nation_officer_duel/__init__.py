"""Nation officer duel — single-combat resolution.

Two officers face off. One challenges, one accepts (or
declines). If accepted, a stat-driven roll resolves the
duel: martial is the primary, with leadership giving a
small modifier (a leader's poise). The duel can end in
victory, draw, or — rarely — death of the loser.

Stake options:
    HONOR_ONLY      no material consequence; just
                    fame/loyalty deltas
    GIL_PURSE       loser pays a gil sum
    HOSTAGE         loser is captured (caller routes
                    to officer_roster.capture)
    HEAD            to the death (loser killed)

Lifecycle:
    PROPOSED        challenge issued, awaiting reply
    ACCEPTED        accepted, awaiting resolve()
    RESOLVED        complete, outcome stored
    DECLINED        target said no
    EXPIRED         target took too long (caller-driven)

This module is deterministic (caller passes a seed for
the resolution roll). It does NOT mutate officer
records — the caller does that based on the duel
outcome (e.g. capture or kill).

Public surface
--------------
    Stake enum
    DuelState enum
    DuelOutcome enum
    Duel dataclass (frozen)
    DuelResult dataclass (frozen)
    NationOfficerDuelSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Stake(str, enum.Enum):
    HONOR_ONLY = "honor_only"
    GIL_PURSE = "gil_purse"
    HOSTAGE = "hostage"
    HEAD = "head"


class DuelState(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    RESOLVED = "resolved"
    DECLINED = "declined"
    EXPIRED = "expired"


class DuelOutcome(str, enum.Enum):
    NONE = "none"
    CHALLENGER_WINS = "challenger_wins"
    TARGET_WINS = "target_wins"
    DRAW = "draw"


@dataclasses.dataclass(frozen=True)
class Duel:
    duel_id: str
    challenger: str
    target: str
    stake: Stake
    purse_gil: int
    proposed_day: int
    state: DuelState
    outcome: DuelOutcome
    winner: str
    loser: str
    death: bool
    resolved_day: t.Optional[int]


@dataclasses.dataclass(frozen=True)
class DuelResult:
    outcome: DuelOutcome
    winner: str
    loser: str
    death: bool
    challenger_score: int
    target_score: int


@dataclasses.dataclass
class NationOfficerDuelSystem:
    _duels: dict[str, Duel] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def propose(
        self, *, challenger: str, target: str,
        stake: Stake, purse_gil: int,
        proposed_day: int,
    ) -> t.Optional[str]:
        if not challenger or not target:
            return None
        if challenger == target:
            return None
        if purse_gil < 0 or proposed_day < 0:
            return None
        if (stake == Stake.GIL_PURSE
                and purse_gil <= 0):
            return None
        did = f"duel_{self._next_id}"
        self._next_id += 1
        self._duels[did] = Duel(
            duel_id=did, challenger=challenger,
            target=target, stake=stake,
            purse_gil=purse_gil,
            proposed_day=proposed_day,
            state=DuelState.PROPOSED,
            outcome=DuelOutcome.NONE,
            winner="", loser="", death=False,
            resolved_day=None,
        )
        return did

    def accept(self, *, duel_id: str) -> bool:
        if duel_id not in self._duels:
            return False
        d = self._duels[duel_id]
        if d.state != DuelState.PROPOSED:
            return False
        self._duels[duel_id] = dataclasses.replace(
            d, state=DuelState.ACCEPTED,
        )
        return True

    def decline(self, *, duel_id: str) -> bool:
        if duel_id not in self._duels:
            return False
        d = self._duels[duel_id]
        if d.state != DuelState.PROPOSED:
            return False
        self._duels[duel_id] = dataclasses.replace(
            d, state=DuelState.DECLINED,
        )
        return True

    def expire(self, *, duel_id: str) -> bool:
        if duel_id not in self._duels:
            return False
        d = self._duels[duel_id]
        if d.state != DuelState.PROPOSED:
            return False
        self._duels[duel_id] = dataclasses.replace(
            d, state=DuelState.EXPIRED,
        )
        return True

    def resolve(
        self, *, duel_id: str,
        challenger_martial: int,
        challenger_leadership: int,
        target_martial: int,
        target_leadership: int,
        seed: int, now_day: int,
    ) -> t.Optional[DuelResult]:
        if duel_id not in self._duels:
            return None
        d = self._duels[duel_id]
        if d.state != DuelState.ACCEPTED:
            return None
        if any(
            s < 1 or s > 100
            for s in (
                challenger_martial,
                challenger_leadership,
                target_martial,
                target_leadership,
            )
        ):
            return None
        # Score = martial + leadership/4 + (seed-derived
        # variance per side).
        c_score = (
            challenger_martial
            + challenger_leadership // 4
            + (seed % 11)
        )
        t_score = (
            target_martial
            + target_leadership // 4
            + ((seed >> 4) % 11)
        )
        if c_score > t_score + 3:
            outcome = DuelOutcome.CHALLENGER_WINS
            winner, loser = d.challenger, d.target
        elif t_score > c_score + 3:
            outcome = DuelOutcome.TARGET_WINS
            winner, loser = d.target, d.challenger
        else:
            outcome = DuelOutcome.DRAW
            winner, loser = "", ""
        # Death is possible only on HEAD stake AND a
        # decisive (>10 point) margin.
        death = (
            d.stake == Stake.HEAD
            and outcome != DuelOutcome.DRAW
            and abs(c_score - t_score) > 10
        )
        self._duels[duel_id] = dataclasses.replace(
            d, state=DuelState.RESOLVED,
            outcome=outcome, winner=winner,
            loser=loser, death=death,
            resolved_day=now_day,
        )
        return DuelResult(
            outcome=outcome, winner=winner,
            loser=loser, death=death,
            challenger_score=c_score,
            target_score=t_score,
        )

    def duel(
        self, *, duel_id: str,
    ) -> t.Optional[Duel]:
        return self._duels.get(duel_id)

    def duels_for(
        self, *, officer_id: str,
    ) -> list[Duel]:
        return [
            d for d in self._duels.values()
            if (d.challenger == officer_id
                or d.target == officer_id)
        ]


__all__ = [
    "Stake", "DuelState", "DuelOutcome", "Duel",
    "DuelResult", "NationOfficerDuelSystem",
]
