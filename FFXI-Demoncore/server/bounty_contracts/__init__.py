"""Bounty contracts — placing prices on heads, with safeguards.

A bounty is a commission to eliminate a specific target player.
Bounties carry abuse potential that generic guild jobs don't:
whales funding grief campaigns, perpetual targeting, retaliation
spirals. This module enforces the specific safeguards.

Hard rules
----------
1.  PROVOCATION REQUIRED. The poster must register a verified
    hostile_event against the target (kill, loot, betrayal)
    within HOSTILE_WINDOW_DAYS (default 14). Posting without
    a registered provocation is rejected.
2.  PER-PAIR COOLDOWN. The same poster cannot bounty the same
    target more than once per BOUNTY_COOLDOWN_DAYS (default 7).
3.  TARGET NOTIFICATION. When a bounty is opened, the target
    is notified — they can lay low, surrender, or buy
    protection.
4.  MUTUAL-BOUNTY → FEUD. If the target also has the poster
    on their bounty list (currently OPEN), the system locks
    both into FEUD. Both bounty escrows go to a public arena
    prize pool — neither side can claim.
5.  BOUNTY EXPIRY. Open bounties expire after EXPIRY_DAYS
    (default 21). Refund 50% to poster.
6.  WITHDRAW. Poster can withdraw an OPEN bounty for a 50%
    refund (the other 50% stays with the guild).

Lifecycle
    OPEN          bounty active, hunters can claim
    PAID          target eliminated, claimant paid
    EXPIRED       deadline passed, partial refund
    REFUNDED      poster withdrew, partial refund
    FEUD_LOCKED   mutual bounty detected; arena pool

Public surface
--------------
    BountyState enum
    HostileKind enum
    HostileEvent dataclass (frozen)
    Bounty dataclass (frozen)
    BountyContractsSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


HOSTILE_WINDOW_DAYS = 14
BOUNTY_COOLDOWN_DAYS = 7
EXPIRY_DAYS = 21


class HostileKind(str, enum.Enum):
    KILL = "kill"
    LOOT = "loot"
    BETRAYAL = "betrayal"


class BountyState(str, enum.Enum):
    OPEN = "open"
    PAID = "paid"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    FEUD_LOCKED = "feud_locked"


@dataclasses.dataclass(frozen=True)
class HostileEvent:
    event_id: str
    aggressor_id: str
    victim_id: str
    kind: HostileKind
    occurred_day: int


@dataclasses.dataclass(frozen=True)
class Bounty:
    bounty_id: str
    poster_id: str
    target_id: str
    reward_gil: int
    state: BountyState
    posted_day: int
    expires_day: int
    claimed_by: str
    claimed_day: int
    notification_sent: bool


@dataclasses.dataclass
class BountyContractsSystem:
    _events: dict[str, HostileEvent] = dataclasses.field(
        default_factory=dict,
    )
    _bounties: dict[str, Bounty] = dataclasses.field(
        default_factory=dict,
    )
    _next_event: int = 1
    _next_bounty: int = 1

    def register_hostile_event(
        self, *, aggressor_id: str, victim_id: str,
        kind: HostileKind, occurred_day: int,
    ) -> t.Optional[str]:
        if not aggressor_id or not victim_id:
            return None
        if aggressor_id == victim_id:
            return None
        if occurred_day < 0:
            return None
        eid = f"event_{self._next_event}"
        self._next_event += 1
        self._events[eid] = HostileEvent(
            event_id=eid, aggressor_id=aggressor_id,
            victim_id=victim_id, kind=kind,
            occurred_day=occurred_day,
        )
        return eid

    def _has_provocation(
        self, *, poster_id: str, target_id: str,
        current_day: int,
    ) -> bool:
        for e in self._events.values():
            if (
                e.aggressor_id == target_id
                and e.victim_id == poster_id
                and current_day - e.occurred_day
                <= HOSTILE_WINDOW_DAYS
                and current_day >= e.occurred_day
            ):
                return True
        return False

    def _recent_open_against(
        self, *, target_id: str,
    ) -> list[Bounty]:
        return [
            b for b in self._bounties.values()
            if b.target_id == target_id
            and b.state == BountyState.OPEN
        ]

    def _per_pair_cooldown_ok(
        self, *, poster_id: str, target_id: str,
        current_day: int,
    ) -> bool:
        for b in self._bounties.values():
            if (
                b.poster_id == poster_id
                and b.target_id == target_id
                and current_day - b.posted_day
                < BOUNTY_COOLDOWN_DAYS
            ):
                return False
        return True

    def open_bounty(
        self, *, poster_id: str, target_id: str,
        reward_gil: int, posted_day: int,
    ) -> t.Optional[str]:
        if not poster_id or not target_id:
            return None
        if poster_id == target_id:
            return None
        if reward_gil <= 0:
            return None
        if posted_day < 0:
            return None
        if not self._has_provocation(
            poster_id=poster_id, target_id=target_id,
            current_day=posted_day,
        ):
            return None
        if not self._per_pair_cooldown_ok(
            poster_id=poster_id, target_id=target_id,
            current_day=posted_day,
        ):
            return None
        bid = f"bounty_{self._next_bounty}"
        self._next_bounty += 1
        # Check for mutual bounty (target → poster)
        mutual = None
        for b in self._bounties.values():
            if (
                b.poster_id == target_id
                and b.target_id == poster_id
                and b.state == BountyState.OPEN
            ):
                mutual = b
                break
        new_state = BountyState.OPEN
        if mutual is not None:
            new_state = BountyState.FEUD_LOCKED
        self._bounties[bid] = Bounty(
            bounty_id=bid, poster_id=poster_id,
            target_id=target_id,
            reward_gil=reward_gil,
            state=new_state,
            posted_day=posted_day,
            expires_day=posted_day + EXPIRY_DAYS,
            claimed_by="", claimed_day=0,
            notification_sent=True,
        )
        if mutual is not None:
            # Lock the other side too
            self._bounties[mutual.bounty_id] = (
                dataclasses.replace(
                    mutual,
                    state=BountyState.FEUD_LOCKED,
                )
            )
        return bid

    def claim_bounty(
        self, *, bounty_id: str, claimant_id: str,
        eliminated_day: int,
    ) -> t.Optional[int]:
        """Hunter claims after eliminating target.
        Returns reward gil. Cannot self-claim.
        """
        if bounty_id not in self._bounties:
            return None
        b = self._bounties[bounty_id]
        if b.state != BountyState.OPEN:
            return None
        if not claimant_id:
            return None
        if claimant_id == b.poster_id:
            return None
        if claimant_id == b.target_id:
            return None
        if eliminated_day < b.posted_day:
            return None
        if eliminated_day > b.expires_day:
            return None
        self._bounties[bounty_id] = dataclasses.replace(
            b, state=BountyState.PAID,
            claimed_by=claimant_id,
            claimed_day=eliminated_day,
        )
        return b.reward_gil

    def withdraw_bounty(
        self, *, bounty_id: str, poster_id: str,
    ) -> t.Optional[int]:
        """Poster withdraws an OPEN bounty for 50%
        refund. Returns gil refunded.
        """
        if bounty_id not in self._bounties:
            return None
        b = self._bounties[bounty_id]
        if b.state != BountyState.OPEN:
            return None
        if b.poster_id != poster_id:
            return None
        refund = b.reward_gil // 2
        self._bounties[bounty_id] = dataclasses.replace(
            b, state=BountyState.REFUNDED,
        )
        return refund

    def expire_bounty(
        self, *, bounty_id: str, current_day: int,
    ) -> t.Optional[int]:
        if bounty_id not in self._bounties:
            return None
        b = self._bounties[bounty_id]
        if b.state != BountyState.OPEN:
            return None
        if current_day <= b.expires_day:
            return None
        refund = b.reward_gil // 2
        self._bounties[bounty_id] = dataclasses.replace(
            b, state=BountyState.EXPIRED,
        )
        return refund

    def feud_pool_total(self) -> int:
        """Sum of reward_gil across all FEUD_LOCKED
        bounties — these flow to the arena prize
        pool."""
        return sum(
            b.reward_gil for b in self._bounties.values()
            if b.state == BountyState.FEUD_LOCKED
        )

    def open_bounties_against(
        self, *, target_id: str,
    ) -> list[Bounty]:
        return self._recent_open_against(
            target_id=target_id,
        )

    def bounty(
        self, *, bounty_id: str,
    ) -> t.Optional[Bounty]:
        return self._bounties.get(bounty_id)


__all__ = [
    "HostileKind", "BountyState", "HostileEvent",
    "Bounty", "BountyContractsSystem",
    "HOSTILE_WINDOW_DAYS", "BOUNTY_COOLDOWN_DAYS",
    "EXPIRY_DAYS",
]
