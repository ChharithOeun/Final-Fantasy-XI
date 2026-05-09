"""Bounty hunter ranks — promotion ladder for bounty claimants.

Hunters progress through 5 ranks based on claim count:
    BRONZE     0..4 claims         can claim up to 5,000 gil
    SILVER     5..14                up to 20,000
    GOLD       15..39               up to 100,000
    PLATINUM   40..99               up to 500,000
    LEGENDARY  100+                 unlimited

Higher-rank bounties are gated to higher-rank hunters — newbie
hunters can't gunsling 500k contracts. Ranks decay if a hunter
goes inactive: every 30 days without a claim, score drops by 1
(min 0). This keeps the ladder fresh — legends who quit lose
their ceiling.

Public surface
--------------
    HunterRank enum
    HunterRecord dataclass (frozen)
    BountyHunterRanksSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_RANK_THRESHOLDS = (
    (0, "bronze", 5_000),
    (5, "silver", 20_000),
    (15, "gold", 100_000),
    (40, "platinum", 500_000),
    (100, "legendary", 1_000_000_000),
)
_INACTIVITY_DECAY_DAYS = 30


class HunterRank(str, enum.Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    LEGENDARY = "legendary"


@dataclasses.dataclass(frozen=True)
class HunterRecord:
    hunter_id: str
    successful_claims: int
    last_claim_day: int


def _rank_for_claims(claims: int) -> HunterRank:
    name = "bronze"
    for thresh, label, _cap in _RANK_THRESHOLDS:
        if claims >= thresh:
            name = label
    return HunterRank(name)


def _max_bounty_for_rank(rank: HunterRank) -> int:
    for _t, label, cap in _RANK_THRESHOLDS:
        if label == rank.value:
            return cap
    return 0


@dataclasses.dataclass
class BountyHunterRanksSystem:
    _hunters: dict[str, HunterRecord] = (
        dataclasses.field(default_factory=dict)
    )

    def register_hunter(
        self, *, hunter_id: str, registered_day: int,
    ) -> bool:
        if not hunter_id or hunter_id in self._hunters:
            return False
        if registered_day < 0:
            return False
        self._hunters[hunter_id] = HunterRecord(
            hunter_id=hunter_id,
            successful_claims=0,
            last_claim_day=registered_day,
        )
        return True

    def can_claim_bounty(
        self, *, hunter_id: str, reward_gil: int,
    ) -> bool:
        rec = self._hunters.get(hunter_id)
        if rec is None:
            return False
        rank = _rank_for_claims(rec.successful_claims)
        cap = _max_bounty_for_rank(rank)
        return reward_gil <= cap

    def record_claim(
        self, *, hunter_id: str, claimed_day: int,
    ) -> bool:
        rec = self._hunters.get(hunter_id)
        if rec is None:
            return False
        if claimed_day < rec.last_claim_day:
            return False
        self._hunters[hunter_id] = dataclasses.replace(
            rec,
            successful_claims=rec.successful_claims + 1,
            last_claim_day=claimed_day,
        )
        return True

    def apply_inactivity_decay(
        self, *, hunter_id: str, current_day: int,
    ) -> int:
        """Apply decay if the hunter has been
        inactive. Returns number of points lost.
        """
        rec = self._hunters.get(hunter_id)
        if rec is None:
            return 0
        elapsed = current_day - rec.last_claim_day
        if elapsed <= _INACTIVITY_DECAY_DAYS:
            return 0
        # 1 point per full 30-day inactivity period
        # past the first
        decay = elapsed // _INACTIVITY_DECAY_DAYS - 1
        if decay <= 0:
            return 0
        new_claims = max(
            0, rec.successful_claims - decay,
        )
        actual_decay = rec.successful_claims - new_claims
        # Reset last_claim_day so we don't keep
        # decaying without a fresh inactivity window
        self._hunters[hunter_id] = dataclasses.replace(
            rec, successful_claims=new_claims,
            last_claim_day=current_day,
        )
        return actual_decay

    def rank(
        self, *, hunter_id: str,
    ) -> t.Optional[HunterRank]:
        rec = self._hunters.get(hunter_id)
        if rec is None:
            return None
        return _rank_for_claims(rec.successful_claims)

    def max_bounty(
        self, *, hunter_id: str,
    ) -> int:
        r = self.rank(hunter_id=hunter_id)
        if r is None:
            return 0
        return _max_bounty_for_rank(r)

    def hunter(
        self, *, hunter_id: str,
    ) -> t.Optional[HunterRecord]:
        return self._hunters.get(hunter_id)

    def claim_count(
        self, *, hunter_id: str,
    ) -> int:
        rec = self._hunters.get(hunter_id)
        return 0 if rec is None else rec.successful_claims


__all__ = [
    "HunterRank", "HunterRecord",
    "BountyHunterRanksSystem",
]
