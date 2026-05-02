"""Mog Bonanza marbles — prediction lottery + weekly drawing.

Players buy a marble for 1000 gil and pick a 5-digit number. At the
weekly drawing, the server rolls the winning number deterministically
via rng_pool. Prize tier is set by how many digits match (last N
digits, like real lotteries).

Public surface
--------------
    BonanzaCampaign with start/draw lifecycle
        .open(now_tick)
        .buy_marble(player_id, picked_number, gil)
        .draw(rng_pool) - sets winning_number
        .check_prize(player_picks, winning_number) -> PrizeTier
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_LOOT_DROPS


MARBLE_PRICE_GIL = 1000
DIGITS = 5                     # 5-digit pick e.g. 12345
MARBLE_NUMBER_MIN = 0
MARBLE_NUMBER_MAX = 99999      # inclusive


class CampaignState(str, enum.Enum):
    OPEN = "open"
    DRAWN = "drawn"


class PrizeTier(str, enum.Enum):
    NONE = "none"
    LAST_DIGIT = "last_digit"        # match last 1 digit
    LAST_TWO = "last_two"            # match last 2
    LAST_THREE = "last_three"        # match last 3
    LAST_FOUR = "last_four"          # match last 4
    JACKPOT = "jackpot"              # all 5 match


@dataclasses.dataclass(frozen=True)
class Marble:
    player_id: str
    picked_number: int
    purchased_at_tick: int


@dataclasses.dataclass(frozen=True)
class PrizeAward:
    tier: PrizeTier
    reward_item_id: t.Optional[str]


# Prize rewards (representative)
TIER_REWARDS: dict[PrizeTier, t.Optional[str]] = {
    PrizeTier.JACKPOT: "kupopurr",            # rare moogle gear
    PrizeTier.LAST_FOUR: "mog_bonanza_pearl",
    PrizeTier.LAST_THREE: "rare_food_voucher",
    PrizeTier.LAST_TWO: "small_gil_pile_5k",
    PrizeTier.LAST_DIGIT: "moogle_charm",
    PrizeTier.NONE: None,
}


@dataclasses.dataclass(frozen=True)
class BuyResult:
    accepted: bool
    marble: t.Optional[Marble] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BonanzaCampaign:
    campaign_id: str
    state: CampaignState = CampaignState.OPEN
    opened_at_tick: int = 0
    drawn_at_tick: int = 0
    winning_number: t.Optional[int] = None
    marbles: list[Marble] = dataclasses.field(default_factory=list)

    def buy_marble(
        self, *,
        player_id: str, picked_number: int,
        player_gil: int, now_tick: int,
    ) -> BuyResult:
        if self.state != CampaignState.OPEN:
            return BuyResult(False, reason="campaign closed")
        if not (MARBLE_NUMBER_MIN <= picked_number <= MARBLE_NUMBER_MAX):
            return BuyResult(
                False, reason=(
                    f"number out of range "
                    f"[{MARBLE_NUMBER_MIN}, {MARBLE_NUMBER_MAX}]"
                ),
            )
        if player_gil < MARBLE_PRICE_GIL:
            return BuyResult(
                False, reason=f"need {MARBLE_PRICE_GIL} gil",
            )
        marble = Marble(
            player_id=player_id,
            picked_number=picked_number,
            purchased_at_tick=now_tick,
        )
        self.marbles.append(marble)
        return BuyResult(True, marble=marble)

    def draw(
        self, *, rng_pool: RngPool, now_tick: int,
        stream_name: str = STREAM_LOOT_DROPS,
    ) -> int:
        if self.state == CampaignState.DRAWN:
            assert self.winning_number is not None
            return self.winning_number
        rng = rng_pool.stream(stream_name)
        winner = rng.randint(MARBLE_NUMBER_MIN, MARBLE_NUMBER_MAX)
        self.winning_number = winner
        self.state = CampaignState.DRAWN
        self.drawn_at_tick = now_tick
        return winner


def check_prize(
    *, picked_number: int, winning_number: int,
) -> PrizeAward:
    """Compare last N digits between pick and winner."""
    if picked_number == winning_number:
        return PrizeAward(
            tier=PrizeTier.JACKPOT,
            reward_item_id=TIER_REWARDS[PrizeTier.JACKPOT],
        )
    pick_str = str(picked_number).zfill(DIGITS)
    win_str = str(winning_number).zfill(DIGITS)
    # Count matching trailing digits
    matched = 0
    for i in range(1, DIGITS + 1):
        if pick_str[-i] == win_str[-i]:
            matched += 1
        else:
            break
    if matched >= 4:
        tier = PrizeTier.LAST_FOUR
    elif matched == 3:
        tier = PrizeTier.LAST_THREE
    elif matched == 2:
        tier = PrizeTier.LAST_TWO
    elif matched == 1:
        tier = PrizeTier.LAST_DIGIT
    else:
        tier = PrizeTier.NONE
    return PrizeAward(tier=tier, reward_item_id=TIER_REWARDS[tier])


__all__ = [
    "MARBLE_PRICE_GIL", "DIGITS",
    "MARBLE_NUMBER_MIN", "MARBLE_NUMBER_MAX",
    "CampaignState", "PrizeTier",
    "Marble", "PrizeAward", "TIER_REWARDS",
    "BuyResult", "BonanzaCampaign",
    "check_prize",
]
