"""Nation ranks — per-rank reward catalog and gates.

Each nation has 10 ranks. Advancing a rank unlocks: a fixed gear
piece (signet bracelet etc), Mog House tab access, certain teleport
options, increased gil-loan cap. Defines the catalog and the helper
to enumerate what a player just unlocked at rank-up.

Public surface
--------------
    Nation enum (already in conquest_tally; re-imported)
    RankReward dataclass
    rewards_at_rank(nation, rank)
    cumulative_rewards_through(nation, rank)
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.conquest_tally import Nation


@dataclasses.dataclass(frozen=True)
class RankReward:
    rank: int
    gear_unlock: t.Optional[str] = None
    mog_house_tier_unlock: t.Optional[str] = None
    teleport_unlock: t.Optional[str] = None
    gil_loan_cap: int = 0
    description: str = ""


# Per-nation reward catalog (samples)
def _build_table() -> dict[Nation, tuple[RankReward, ...]]:
    out: dict[Nation, tuple[RankReward, ...]] = {}
    for nation, prefix in (
        (Nation.BASTOK, "bastok"),
        (Nation.SANDY, "sandy"),
        (Nation.WINDY, "windy"),
    ):
        out[nation] = (
            RankReward(rank=1,
                        gear_unlock=f"{prefix}_signet_bracelet",
                        gil_loan_cap=2000),
            RankReward(rank=2,
                        teleport_unlock=f"{prefix}_op_north",
                        gil_loan_cap=5000),
            RankReward(rank=3,
                        gear_unlock=f"{prefix}_signet_ring_1",
                        gil_loan_cap=10000),
            RankReward(rank=4,
                        teleport_unlock=f"{prefix}_op_south",
                        mog_house_tier_unlock="storage_tier_2",
                        gil_loan_cap=20000),
            RankReward(rank=5,
                        gear_unlock=f"{prefix}_signet_armor",
                        gil_loan_cap=40000),
            RankReward(rank=6,
                        teleport_unlock=f"{prefix}_op_east",
                        gil_loan_cap=80000),
            RankReward(rank=7,
                        mog_house_tier_unlock="storage_tier_3",
                        gil_loan_cap=160000),
            RankReward(rank=8,
                        gear_unlock=f"{prefix}_signet_ring_2",
                        gil_loan_cap=320000),
            RankReward(rank=9,
                        teleport_unlock=f"{prefix}_op_west",
                        gil_loan_cap=500000),
            RankReward(rank=10,
                        gear_unlock=f"{prefix}_marshal_armor",
                        mog_house_tier_unlock="storage_tier_max",
                        gil_loan_cap=1000000,
                        description="Marshal/General/etc title."),
        )
    return out


_TABLE: dict[Nation, tuple[RankReward, ...]] = _build_table()


MAX_RANK = 10


def rewards_at_rank(
    *, nation: Nation, rank: int,
) -> t.Optional[RankReward]:
    if not 1 <= rank <= MAX_RANK:
        return None
    rewards = _TABLE[nation]
    for r in rewards:
        if r.rank == rank:
            return r
    return None


def cumulative_rewards_through(
    *, nation: Nation, rank: int,
) -> tuple[RankReward, ...]:
    if rank < 1:
        return ()
    rank = min(rank, MAX_RANK)
    rewards = _TABLE[nation]
    return tuple(r for r in rewards if r.rank <= rank)


def gil_loan_cap_at_rank(
    *, nation: Nation, rank: int,
) -> int:
    """Highest gil-loan cap unlocked through this rank."""
    rewards = cumulative_rewards_through(nation=nation, rank=rank)
    if not rewards:
        return 0
    return max(r.gil_loan_cap for r in rewards)


def all_teleports_unlocked(
    *, nation: Nation, rank: int,
) -> tuple[str, ...]:
    rewards = cumulative_rewards_through(nation=nation, rank=rank)
    return tuple(
        r.teleport_unlock for r in rewards
        if r.teleport_unlock is not None
    )


__all__ = [
    "RankReward", "MAX_RANK",
    "rewards_at_rank", "cumulative_rewards_through",
    "gil_loan_cap_at_rank", "all_teleports_unlocked",
]
