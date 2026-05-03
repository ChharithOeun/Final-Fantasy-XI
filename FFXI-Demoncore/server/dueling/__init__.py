"""Dueling — consensual one-on-one PvP.

Distinct from the global outlaw / sanctioned PvP frameworks.
A duel is a CONSENT-BASED one-on-one fight that:

* Both parties accept (challenge -> accept).
* Plays out in an auto-formed arena (or current zone, with
  bystander exclusion).
* Has NO XP loss, NO bounty, NO permadeath.
* Ends on first KO or forfeit.
* Can be a CONTRACT (gil/item wager) or HONOR (bragging rights).

State machine
-------------
    PROPOSED   — challenge sent, waiting on response
    ACCEPTED   — both consented, arena forming
    LIVE       — fight in progress
    FINISHED   — winner decided
    DECLINED   — opposing party rejected
    EXPIRED    — challenge timed out

Public surface
--------------
    DuelStakes enum (HONOR / GIL / ITEM)
    DuelOutcome enum (WIN / FORFEIT / DOUBLE_KO / TIMEOUT)
    Duel dataclass
    DuelRegistry
        .challenge(challenger_id, defender_id, stakes_kind,
                    stakes_amount)
        .accept(duel_id) / .decline(duel_id)
        .start_fight(duel_id, now)
        .resolve(duel_id, winner_id, outcome, now)
        .forfeit(duel_id, forfeiting_id)
        .expire_old(now)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


CHALLENGE_TIMEOUT_SECONDS = 60.0       # 1 minute to accept
DUEL_MAX_DURATION_SECONDS = 600.0      # 10 minutes max fight


class DuelState(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    LIVE = "live"
    FINISHED = "finished"
    DECLINED = "declined"
    EXPIRED = "expired"


class DuelStakesKind(str, enum.Enum):
    HONOR = "honor"        # bragging rights only
    GIL = "gil"            # gil wager
    ITEM = "item"          # item stake


class DuelOutcome(str, enum.Enum):
    WIN = "win"
    FORFEIT = "forfeit"
    DOUBLE_KO = "double_ko"
    TIMEOUT = "timeout"


@dataclasses.dataclass
class Duel:
    duel_id: str
    challenger_id: str
    defender_id: str
    stakes_kind: DuelStakesKind = DuelStakesKind.HONOR
    stakes_amount: int = 0           # gil amount or item count
    stakes_payload: str = ""          # item id if ITEM
    state: DuelState = DuelState.PROPOSED
    proposed_at_seconds: float = 0.0
    accepted_at_seconds: t.Optional[float] = None
    started_at_seconds: t.Optional[float] = None
    finished_at_seconds: t.Optional[float] = None
    winner_id: t.Optional[str] = None
    outcome: t.Optional[DuelOutcome] = None
    notes: str = ""

    @property
    def participants(self) -> tuple[str, str]:
        return (self.challenger_id, self.defender_id)


@dataclasses.dataclass(frozen=True)
class ChallengeResult:
    accepted: bool
    duel_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class DuelRegistry:
    challenge_timeout_seconds: float = CHALLENGE_TIMEOUT_SECONDS
    duel_max_duration_seconds: float = DUEL_MAX_DURATION_SECONDS
    _duels: dict[str, Duel] = dataclasses.field(
        default_factory=dict,
    )
    _next_duel_id: int = 0

    def challenge(
        self, *, challenger_id: str, defender_id: str,
        stakes_kind: DuelStakesKind = DuelStakesKind.HONOR,
        stakes_amount: int = 0,
        stakes_payload: str = "",
        now_seconds: float = 0.0,
    ) -> ChallengeResult:
        if challenger_id == defender_id:
            return ChallengeResult(
                False, reason="cannot duel self",
            )
        # Reject if either party has an open duel
        for d in self._duels.values():
            if d.state in (DuelState.PROPOSED, DuelState.ACCEPTED, DuelState.LIVE):
                if (
                    challenger_id in d.participants
                    or defender_id in d.participants
                ):
                    return ChallengeResult(
                        False, reason="party already in a duel",
                    )
        if stakes_kind != DuelStakesKind.HONOR and stakes_amount <= 0:
            return ChallengeResult(
                False, reason="stake amount must be positive",
            )
        did = f"duel_{self._next_duel_id}"
        self._next_duel_id += 1
        duel = Duel(
            duel_id=did,
            challenger_id=challenger_id,
            defender_id=defender_id,
            stakes_kind=stakes_kind,
            stakes_amount=stakes_amount,
            stakes_payload=stakes_payload,
            proposed_at_seconds=now_seconds,
        )
        self._duels[did] = duel
        return ChallengeResult(True, duel_id=did)

    def get(self, duel_id: str) -> t.Optional[Duel]:
        return self._duels.get(duel_id)

    def accept(
        self, *, duel_id: str, defender_id: str,
        now_seconds: float,
    ) -> bool:
        d = self._duels.get(duel_id)
        if d is None or d.state != DuelState.PROPOSED:
            return False
        if d.defender_id != defender_id:
            return False
        # Timeout check
        if (
            now_seconds - d.proposed_at_seconds
            > self.challenge_timeout_seconds
        ):
            d.state = DuelState.EXPIRED
            return False
        d.state = DuelState.ACCEPTED
        d.accepted_at_seconds = now_seconds
        return True

    def decline(
        self, *, duel_id: str, defender_id: str,
    ) -> bool:
        d = self._duels.get(duel_id)
        if d is None or d.state != DuelState.PROPOSED:
            return False
        if d.defender_id != defender_id:
            return False
        d.state = DuelState.DECLINED
        return True

    def start_fight(
        self, *, duel_id: str, now_seconds: float,
    ) -> bool:
        d = self._duels.get(duel_id)
        if d is None or d.state != DuelState.ACCEPTED:
            return False
        d.state = DuelState.LIVE
        d.started_at_seconds = now_seconds
        return True

    def resolve(
        self, *, duel_id: str, winner_id: t.Optional[str],
        outcome: DuelOutcome, now_seconds: float,
    ) -> bool:
        d = self._duels.get(duel_id)
        if d is None or d.state != DuelState.LIVE:
            return False
        if winner_id is not None and winner_id not in d.participants:
            return False
        d.state = DuelState.FINISHED
        d.winner_id = winner_id
        d.outcome = outcome
        d.finished_at_seconds = now_seconds
        return True

    def forfeit(
        self, *, duel_id: str, forfeiting_id: str,
        now_seconds: float,
    ) -> bool:
        d = self._duels.get(duel_id)
        if d is None or d.state != DuelState.LIVE:
            return False
        if forfeiting_id not in d.participants:
            return False
        winner = (
            d.defender_id
            if forfeiting_id == d.challenger_id
            else d.challenger_id
        )
        d.state = DuelState.FINISHED
        d.winner_id = winner
        d.outcome = DuelOutcome.FORFEIT
        d.finished_at_seconds = now_seconds
        return True

    def expire_old(self, *, now_seconds: float) -> int:
        expired = 0
        for d in self._duels.values():
            if (
                d.state == DuelState.PROPOSED
                and now_seconds - d.proposed_at_seconds
                > self.challenge_timeout_seconds
            ):
                d.state = DuelState.EXPIRED
                expired += 1
            elif (
                d.state == DuelState.LIVE
                and d.started_at_seconds is not None
                and now_seconds - d.started_at_seconds
                > self.duel_max_duration_seconds
            ):
                d.state = DuelState.FINISHED
                d.outcome = DuelOutcome.TIMEOUT
                d.finished_at_seconds = now_seconds
                expired += 1
        return expired

    def open_duels_for(
        self, player_id: str,
    ) -> tuple[Duel, ...]:
        return tuple(
            d for d in self._duels.values()
            if player_id in d.participants
            and d.state in (
                DuelState.PROPOSED,
                DuelState.ACCEPTED,
                DuelState.LIVE,
            )
        )

    def total(self) -> int:
        return len(self._duels)


__all__ = [
    "CHALLENGE_TIMEOUT_SECONDS", "DUEL_MAX_DURATION_SECONDS",
    "DuelState", "DuelStakesKind", "DuelOutcome",
    "Duel", "ChallengeResult", "DuelRegistry",
]
