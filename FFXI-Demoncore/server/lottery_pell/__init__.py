"""Lottery Pell — Mog Pell scratch ticket mini-game.

Buy a 5000-gil ticket. Three slots are revealed; if all three match
the same prize tier, you win that tier's reward. Two-of-a-kind
returns a small consolation. Otherwise, nothing.

Public surface
--------------
    PrizeTier enum (JACKPOT, MID, LOW, BLANK)
    PrizeSpec catalog
    PellResult
    purchase_and_scratch(rng_pool, world_seed) -> PellResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_LOOT_DROPS


TICKET_COST_GIL = 5000


class PrizeTier(str, enum.Enum):
    BLANK = "blank"
    LOW = "low"
    MID = "mid"
    JACKPOT = "jackpot"


@dataclasses.dataclass(frozen=True)
class PrizeSpec:
    tier: PrizeTier
    item_id: str
    weight: int            # roll weight per scratch slot


# Each slot rolls one of these. JACKPOT is rare, BLANK is common.
SCRATCH_POOL: tuple[PrizeSpec, ...] = (
    PrizeSpec(PrizeTier.BLANK, "scratch_blank", weight=60),
    PrizeSpec(PrizeTier.LOW, "scratch_potion", weight=20),
    PrizeSpec(PrizeTier.MID, "scratch_ether", weight=15),
    PrizeSpec(PrizeTier.JACKPOT, "scratch_kupo", weight=5),
)


# Match-3 jackpot rewards
TIER_REWARDS: dict[PrizeTier, str] = {
    PrizeTier.BLANK: "",
    PrizeTier.LOW: "potion_x99",
    PrizeTier.MID: "vile_elixir_+1",
    PrizeTier.JACKPOT: "moogle_charm",
}


# Match-2 consolation
CONSOLATION_REWARDS: dict[PrizeTier, str] = {
    PrizeTier.LOW: "potion_x10",
    PrizeTier.MID: "ether_x10",
    PrizeTier.JACKPOT: "rare_token",
}


@dataclasses.dataclass(frozen=True)
class PellResult:
    accepted: bool
    gil_charged: int
    revealed: tuple[PrizeTier, ...]
    win_kind: t.Literal["match_3", "match_2", "blank"] = "blank"
    reward_item_id: t.Optional[str] = None
    reason: t.Optional[str] = None


def _roll_one(rng) -> PrizeTier:
    total = sum(s.weight for s in SCRATCH_POOL)
    pick = rng.uniform(0, total)
    cum = 0.0
    for s in SCRATCH_POOL:
        cum += s.weight
        if pick <= cum:
            return s.tier
    return SCRATCH_POOL[-1].tier


def purchase_and_scratch(
    *,
    player_gil: int,
    rng_pool: RngPool,
    stream_name: str = STREAM_LOOT_DROPS,
) -> PellResult:
    if player_gil < TICKET_COST_GIL:
        return PellResult(
            accepted=False,
            gil_charged=0,
            revealed=(),
            reason=f"need {TICKET_COST_GIL} gil",
        )
    rng = rng_pool.stream(stream_name)
    revealed = tuple(_roll_one(rng) for _ in range(3))

    # Match-3 jackpot
    if revealed[0] == revealed[1] == revealed[2]:
        tier = revealed[0]
        reward = TIER_REWARDS.get(tier, "")
        if tier == PrizeTier.BLANK:
            return PellResult(
                accepted=True, gil_charged=TICKET_COST_GIL,
                revealed=revealed, win_kind="blank",
            )
        return PellResult(
            accepted=True, gil_charged=TICKET_COST_GIL,
            revealed=revealed, win_kind="match_3",
            reward_item_id=reward,
        )

    # Match-2 consolation
    counts: dict[PrizeTier, int] = {}
    for r in revealed:
        counts[r] = counts.get(r, 0) + 1
    for tier, n in counts.items():
        if n == 2 and tier != PrizeTier.BLANK:
            return PellResult(
                accepted=True, gil_charged=TICKET_COST_GIL,
                revealed=revealed, win_kind="match_2",
                reward_item_id=CONSOLATION_REWARDS[tier],
            )

    return PellResult(
        accepted=True, gil_charged=TICKET_COST_GIL,
        revealed=revealed, win_kind="blank",
    )


__all__ = [
    "TICKET_COST_GIL",
    "PrizeTier", "PrizeSpec", "SCRATCH_POOL",
    "TIER_REWARDS", "CONSOLATION_REWARDS",
    "PellResult", "purchase_and_scratch",
]
