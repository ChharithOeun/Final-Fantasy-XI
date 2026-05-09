"""Tavern dice — multi-dice gambling minigame.

Inn-side gambling. A house dealer rolls a target
score; players match the bid and try to beat it with
their own roll. The simplest variant is 5d6 sum-vs-
sum: highest total wins, push on tie.

Rounds:
    OPEN          house has set the target, taking bids
    LOCKED        no more bids; players roll
    SETTLED       payouts processed

Each player_bid is a wager_gil amount paired with a
player_roll. When the round LOCKS, every wager is
compared to the dealer roll. Win = wager * win_payout
multiplier; loss = wager forfeited; push = wager
returned.

Public surface
--------------
    RoundState enum
    Bid dataclass (frozen)
    Round dataclass (frozen)
    TavernDiceSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RoundState(str, enum.Enum):
    OPEN = "open"
    LOCKED = "locked"
    SETTLED = "settled"


class BidOutcome(str, enum.Enum):
    PENDING = "pending"
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"


@dataclasses.dataclass(frozen=True)
class Bid:
    bid_id: str
    round_id: str
    player_id: str
    wager_gil: int
    player_roll: int
    placed_day: int
    outcome: BidOutcome
    payout_gil: int


@dataclasses.dataclass(frozen=True)
class Round:
    round_id: str
    table_id: str
    dealer_id: str
    dice_count: int
    dice_sides: int
    dealer_roll: int
    win_payout_x100: int   # 200 = 2.00x
    state: RoundState
    pool_total_gil: int


@dataclasses.dataclass
class _RState:
    spec: Round
    bids: dict[str, Bid] = dataclasses.field(
        default_factory=dict,
    )


def _roll_seeded(
    *, dice_count: int, dice_sides: int, seed: int,
) -> int:
    total = 0
    for i in range(dice_count):
        total += (
            (seed >> (i * 4)) & 0xFF
        ) % dice_sides + 1
    return total


@dataclasses.dataclass
class TavernDiceSystem:
    _rounds: dict[str, _RState] = dataclasses.field(
        default_factory=dict,
    )
    _next_round: int = 1
    _next_bid: int = 1

    def open_round(
        self, *, table_id: str, dealer_id: str,
        dice_count: int, dice_sides: int,
        win_payout_x100: int = 200,
    ) -> t.Optional[str]:
        if not table_id or not dealer_id:
            return None
        if dice_count <= 0 or dice_count > 10:
            return None
        if dice_sides not in (4, 6, 8, 10, 12, 20):
            return None
        if win_payout_x100 <= 100:
            # Need > 1.00x or losing house edge
            return None
        rid = f"round_{self._next_round}"
        self._next_round += 1
        spec = Round(
            round_id=rid, table_id=table_id,
            dealer_id=dealer_id,
            dice_count=dice_count,
            dice_sides=dice_sides,
            dealer_roll=0,
            win_payout_x100=win_payout_x100,
            state=RoundState.OPEN,
            pool_total_gil=0,
        )
        self._rounds[rid] = _RState(spec=spec)
        return rid

    def place_bid(
        self, *, round_id: str, player_id: str,
        wager_gil: int, placed_day: int,
    ) -> t.Optional[str]:
        if round_id not in self._rounds:
            return None
        st = self._rounds[round_id]
        if st.spec.state != RoundState.OPEN:
            return None
        if not player_id:
            return None
        if wager_gil <= 0 or placed_day < 0:
            return None
        if player_id == st.spec.dealer_id:
            return None
        # One bid per player per round
        for b in st.bids.values():
            if b.player_id == player_id:
                return None
        bid_id = f"bid_{self._next_bid}"
        self._next_bid += 1
        st.bids[bid_id] = Bid(
            bid_id=bid_id, round_id=round_id,
            player_id=player_id,
            wager_gil=wager_gil,
            player_roll=0, placed_day=placed_day,
            outcome=BidOutcome.PENDING,
            payout_gil=0,
        )
        st.spec = dataclasses.replace(
            st.spec, pool_total_gil=(
                st.spec.pool_total_gil + wager_gil
            ),
        )
        return bid_id

    def lock(
        self, *, round_id: str,
    ) -> bool:
        if round_id not in self._rounds:
            return False
        st = self._rounds[round_id]
        if st.spec.state != RoundState.OPEN:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=RoundState.LOCKED,
        )
        return True

    def resolve(
        self, *, round_id: str, dealer_seed: int,
        bid_seeds: t.Mapping[str, int],
    ) -> t.Optional[int]:
        """Roll dealer + each player; settle bids.
        Returns dealer's roll, or None on invalid."""
        if round_id not in self._rounds:
            return None
        st = self._rounds[round_id]
        if st.spec.state != RoundState.LOCKED:
            return None
        dealer_roll = _roll_seeded(
            dice_count=st.spec.dice_count,
            dice_sides=st.spec.dice_sides,
            seed=dealer_seed,
        )
        st.spec = dataclasses.replace(
            st.spec, dealer_roll=dealer_roll,
            state=RoundState.SETTLED,
        )
        for bid_id, bid in list(st.bids.items()):
            seed = bid_seeds.get(bid_id, 0)
            roll = _roll_seeded(
                dice_count=st.spec.dice_count,
                dice_sides=st.spec.dice_sides,
                seed=seed,
            )
            if roll > dealer_roll:
                outcome = BidOutcome.WIN
                payout = (
                    bid.wager_gil
                    * st.spec.win_payout_x100
                    // 100
                )
            elif roll == dealer_roll:
                outcome = BidOutcome.PUSH
                payout = bid.wager_gil
            else:
                outcome = BidOutcome.LOSS
                payout = 0
            st.bids[bid_id] = dataclasses.replace(
                bid, player_roll=roll,
                outcome=outcome,
                payout_gil=payout,
            )
        return dealer_roll

    def round(
        self, *, round_id: str,
    ) -> t.Optional[Round]:
        if round_id not in self._rounds:
            return None
        return self._rounds[round_id].spec

    def bids(
        self, *, round_id: str,
    ) -> list[Bid]:
        if round_id not in self._rounds:
            return []
        return list(
            self._rounds[round_id].bids.values(),
        )

    def player_bid(
        self, *, round_id: str, player_id: str,
    ) -> t.Optional[Bid]:
        if round_id not in self._rounds:
            return None
        for b in self._rounds[round_id].bids.values():
            if b.player_id == player_id:
                return b
        return None


__all__ = [
    "RoundState", "BidOutcome", "Bid", "Round",
    "TavernDiceSystem",
]
