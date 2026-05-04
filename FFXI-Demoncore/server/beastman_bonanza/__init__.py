"""Beastman bonanza — beastman-side Mog Bonanza lottery.

Periodic SHADOW BONANZA event. Each round:
  - Players buy MARBLES (each marble = a 5-digit number, gil cost)
  - Each marble has a per-player cap (default 8)
  - When the round CLOSES, the winning number is set; players
    whose marble matches in n of 5 digits win a prize tier:
      5/5 (perfect)  - jackpot
      4/5 (4 right)  - tier_2 prize
      3/5 (3 right)  - tier_3 prize
      <3            - no prize

Public surface
--------------
    BonanzaState enum   OPEN / DRAWN / CLOSED
    Marble dataclass
    DrawResult dataclass
    BeastmanBonanza
        .open_round(round_id, marble_cost, max_per_player)
        .buy(player_id, round_id, number)
        .draw(round_id, winning_number)
        .check(player_id, round_id)
        .close_round(round_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BonanzaState(str, enum.Enum):
    OPEN = "open"
    DRAWN = "drawn"
    CLOSED = "closed"


_DEFAULT_MAX_PER_PLAYER = 8


@dataclasses.dataclass(frozen=True)
class Marble:
    marble_id: int
    round_id: str
    player_id: str
    number: str   # 5-digit string


@dataclasses.dataclass
class _Round:
    round_id: str
    marble_cost: int
    max_per_player: int
    state: BonanzaState = BonanzaState.OPEN
    winning_number: t.Optional[str] = None
    marbles: list[Marble] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class BuyResult:
    accepted: bool
    marble_id: int = 0
    cost: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CheckResult:
    accepted: bool
    matches_5: int = 0
    matches_4: int = 0
    matches_3: int = 0
    reason: t.Optional[str] = None


def _matches(a: str, b: str) -> int:
    if len(a) != 5 or len(b) != 5:
        return 0
    # FFXI-style digit-match counts matching positions left-to-right
    # consecutively from the left
    count = 0
    for i in range(5):
        if a[i] != b[i]:
            break
        count += 1
    return count


def _is_5_digit(n: str) -> bool:
    return len(n) == 5 and n.isdigit()


@dataclasses.dataclass
class BeastmanBonanza:
    _rounds: dict[str, _Round] = dataclasses.field(default_factory=dict)
    _next_marble_id: int = 1

    def open_round(
        self, *, round_id: str,
        marble_cost: int,
        max_per_player: int = _DEFAULT_MAX_PER_PLAYER,
    ) -> bool:
        if round_id in self._rounds:
            return False
        if marble_cost <= 0 or max_per_player <= 0:
            return False
        self._rounds[round_id] = _Round(
            round_id=round_id,
            marble_cost=marble_cost,
            max_per_player=max_per_player,
        )
        return True

    def _player_count(
        self, round_id: str, player_id: str,
    ) -> int:
        r = self._rounds[round_id]
        return sum(1 for m in r.marbles if m.player_id == player_id)

    def buy(
        self, *, player_id: str,
        round_id: str,
        number: str,
    ) -> BuyResult:
        r = self._rounds.get(round_id)
        if r is None:
            return BuyResult(False, reason="unknown round")
        if r.state != BonanzaState.OPEN:
            return BuyResult(False, reason="round not open")
        if not _is_5_digit(number):
            return BuyResult(False, reason="number must be 5 digits")
        if (
            self._player_count(round_id, player_id)
            >= r.max_per_player
        ):
            return BuyResult(
                False, reason="per-player cap reached",
            )
        mid = self._next_marble_id
        self._next_marble_id += 1
        r.marbles.append(
            Marble(
                marble_id=mid,
                round_id=round_id,
                player_id=player_id,
                number=number,
            ),
        )
        return BuyResult(
            accepted=True, marble_id=mid, cost=r.marble_cost,
        )

    def draw(
        self, *, round_id: str, winning_number: str,
    ) -> bool:
        r = self._rounds.get(round_id)
        if r is None or r.state != BonanzaState.OPEN:
            return False
        if not _is_5_digit(winning_number):
            return False
        r.winning_number = winning_number
        r.state = BonanzaState.DRAWN
        return True

    def check(
        self, *, player_id: str, round_id: str,
    ) -> CheckResult:
        r = self._rounds.get(round_id)
        if r is None:
            return CheckResult(False, reason="unknown round")
        if r.state != BonanzaState.DRAWN:
            return CheckResult(False, reason="not drawn yet")
        wn = r.winning_number or ""
        m5 = m4 = m3 = 0
        for m in r.marbles:
            if m.player_id != player_id:
                continue
            mc = _matches(m.number, wn)
            if mc == 5:
                m5 += 1
            elif mc == 4:
                m4 += 1
            elif mc == 3:
                m3 += 1
        return CheckResult(
            accepted=True,
            matches_5=m5, matches_4=m4, matches_3=m3,
        )

    def close_round(
        self, *, round_id: str,
    ) -> bool:
        r = self._rounds.get(round_id)
        if r is None or r.state == BonanzaState.CLOSED:
            return False
        r.state = BonanzaState.CLOSED
        return True

    def state_for(
        self, *, round_id: str,
    ) -> t.Optional[BonanzaState]:
        r = self._rounds.get(round_id)
        if r is None:
            return None
        return r.state

    def total_rounds(self) -> int:
        return len(self._rounds)


__all__ = [
    "BonanzaState", "Marble",
    "BuyResult", "CheckResult",
    "BeastmanBonanza",
]
