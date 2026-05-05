"""Boarding party PvP — crew fights deck-to-deck after grapple.

Once surface_ship_combat resolves a successful GRAPPLE, the
two ships are locked together and BOARDING begins. Crew fight
on each other's decks; whoever clears the opposing deck WINS
the encounter and gains control of the captured ship's CARGO
+ optionally the ship itself (see prize_court).

Boarding rules:
  * Each side fields up to 6 active fighters at a time
    (party_system cap)
  * KO timeout 60s (you can be revived/replaced)
  * Deck CLEARED when the opposing side has zero active
    fighters AND no replacements waiting
  * Outlaws-vs-outlaws is sanctioned (no honor cost); other
    boardings flag the boarder as outlaw_pvp via outlaw_system

Public surface
--------------
    BoardingState enum
    BoardingResult dataclass
    BoardingPartyPvp
        .start_boarding(boarding_id, attacker_party,
                        defender_party, sanctioned, now_seconds)
        .ko_fighter(boarding_id, fighter_id, side, now_seconds)
        .revive_fighter(boarding_id, fighter_id, side, now_seconds)
        .check_resolution(boarding_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BoardingState(str, enum.Enum):
    ACTIVE = "active"
    ATTACKER_WINS = "attacker_wins"
    DEFENDER_WINS = "defender_wins"


class Side(str, enum.Enum):
    ATTACKER = "attacker"
    DEFENDER = "defender"


KO_REVIVE_WINDOW_SECONDS = 60
MAX_PARTY_SIZE = 6


@dataclasses.dataclass
class _Fighter:
    fighter_id: str
    side: Side
    ko_at: t.Optional[int] = None
    revived: bool = False


@dataclasses.dataclass
class _Boarding:
    boarding_id: str
    sanctioned: bool
    fighters: dict[str, _Fighter] = dataclasses.field(default_factory=dict)
    state: BoardingState = BoardingState.ACTIVE
    started_at: int = 0
    resolved_at: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class BoardingResult:
    accepted: bool
    state: t.Optional[BoardingState] = None
    winner: t.Optional[Side] = None
    flagged_outlaw: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BoardingPartyPvp:
    _boardings: dict[str, _Boarding] = dataclasses.field(
        default_factory=dict,
    )

    def start_boarding(
        self, *, boarding_id: str,
        attacker_party: tuple[str, ...],
        defender_party: tuple[str, ...],
        sanctioned: bool,
        now_seconds: int,
    ) -> BoardingResult:
        if not boarding_id or boarding_id in self._boardings:
            return BoardingResult(False, reason="bad id")
        if (
            not attacker_party or not defender_party
            or len(attacker_party) > MAX_PARTY_SIZE
            or len(defender_party) > MAX_PARTY_SIZE
        ):
            return BoardingResult(False, reason="bad party size")
        # check for shared fighters
        if set(attacker_party) & set(defender_party):
            return BoardingResult(
                False, reason="overlapping rosters",
            )
        b = _Boarding(
            boarding_id=boarding_id,
            sanctioned=sanctioned,
            started_at=now_seconds,
        )
        for fid in attacker_party:
            b.fighters[fid] = _Fighter(
                fighter_id=fid, side=Side.ATTACKER,
            )
        for fid in defender_party:
            b.fighters[fid] = _Fighter(
                fighter_id=fid, side=Side.DEFENDER,
            )
        self._boardings[boarding_id] = b
        return BoardingResult(
            accepted=True,
            state=BoardingState.ACTIVE,
            flagged_outlaw=(not sanctioned),
        )

    def ko_fighter(
        self, *, boarding_id: str,
        fighter_id: str,
        now_seconds: int,
    ) -> BoardingResult:
        b = self._boardings.get(boarding_id)
        if b is None or b.state != BoardingState.ACTIVE:
            return BoardingResult(False, reason="no active boarding")
        f = b.fighters.get(fighter_id)
        if f is None:
            return BoardingResult(False, reason="unknown fighter")
        if f.ko_at is not None:
            return BoardingResult(False, reason="already ko")
        f.ko_at = now_seconds
        return BoardingResult(accepted=True, state=b.state)

    def revive_fighter(
        self, *, boarding_id: str,
        fighter_id: str,
        now_seconds: int,
    ) -> BoardingResult:
        b = self._boardings.get(boarding_id)
        if b is None or b.state != BoardingState.ACTIVE:
            return BoardingResult(False, reason="no active boarding")
        f = b.fighters.get(fighter_id)
        if f is None or f.ko_at is None:
            return BoardingResult(False, reason="cannot revive")
        if (now_seconds - f.ko_at) > KO_REVIVE_WINDOW_SECONDS:
            return BoardingResult(False, reason="revive window expired")
        f.ko_at = None
        f.revived = True
        return BoardingResult(accepted=True, state=b.state)

    def check_resolution(
        self, *, boarding_id: str, now_seconds: int,
    ) -> BoardingResult:
        b = self._boardings.get(boarding_id)
        if b is None:
            return BoardingResult(False, reason="unknown")
        if b.state != BoardingState.ACTIVE:
            return BoardingResult(
                accepted=True, state=b.state,
                winner=(
                    Side.ATTACKER
                    if b.state == BoardingState.ATTACKER_WINS
                    else Side.DEFENDER
                ),
            )
        # an "active" fighter is one not KO'd OR within the
        # revive window
        def is_active(f: _Fighter) -> bool:
            if f.ko_at is None:
                return True
            return (now_seconds - f.ko_at) <= KO_REVIVE_WINDOW_SECONDS
        attacker_active = any(
            is_active(f) for f in b.fighters.values()
            if f.side == Side.ATTACKER
        )
        defender_active = any(
            is_active(f) for f in b.fighters.values()
            if f.side == Side.DEFENDER
        )
        if not defender_active and attacker_active:
            b.state = BoardingState.ATTACKER_WINS
            b.resolved_at = now_seconds
            return BoardingResult(
                accepted=True,
                state=BoardingState.ATTACKER_WINS,
                winner=Side.ATTACKER,
                flagged_outlaw=(not b.sanctioned),
            )
        if not attacker_active and defender_active:
            b.state = BoardingState.DEFENDER_WINS
            b.resolved_at = now_seconds
            return BoardingResult(
                accepted=True,
                state=BoardingState.DEFENDER_WINS,
                winner=Side.DEFENDER,
            )
        # else still active or both wiped
        return BoardingResult(accepted=True, state=b.state)


__all__ = [
    "BoardingState", "Side", "BoardingResult",
    "BoardingPartyPvp",
    "KO_REVIVE_WINDOW_SECONDS", "MAX_PARTY_SIZE",
]
