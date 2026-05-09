"""Player treaty — formal peace agreement between two players.

After a feud cools off, or before one starts, two players can
sign a treaty — a formal agreement registered with the
Adventurers' Guild that prevents bounties between them and
declares no-combat status. Treaties are public records, expire
after 90 days unless renewed, and breaking one costs the
breaker a substantial honor hit.

Lifecycle
    PROPOSED     one party offered, other hasn't signed
    SIGNED       both signed, terms in effect
    EXPIRED      term ended without renewal
    BROKEN       one party violated, honor penalty applied

Public surface
--------------
    TreatyState enum
    TreatyTerm enum
    Treaty dataclass (frozen)
    PlayerTreatySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_DEFAULT_TERM_DAYS = 90
_BREAK_HONOR_PENALTY = 50


class TreatyState(str, enum.Enum):
    PROPOSED = "proposed"
    SIGNED = "signed"
    EXPIRED = "expired"
    BROKEN = "broken"


class TreatyTerm(str, enum.Enum):
    NO_COMBAT = "no_combat"
    NO_BOUNTIES = "no_bounties"
    SHARED_ZONE_ACCESS = "shared_zone_access"
    LOOT_RIGHTS = "loot_rights"


@dataclasses.dataclass(frozen=True)
class Treaty:
    treaty_id: str
    proposer_id: str
    accepter_id: str
    terms: tuple[TreatyTerm, ...]
    state: TreatyState
    proposed_day: int
    signed_day: int
    expires_day: int
    breaker_id: str
    honor_penalty: int


@dataclasses.dataclass
class PlayerTreatySystem:
    _treaties: dict[str, Treaty] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def propose(
        self, *, proposer_id: str, accepter_id: str,
        terms: tuple[TreatyTerm, ...],
        proposed_day: int,
        term_days: int = _DEFAULT_TERM_DAYS,
    ) -> t.Optional[str]:
        if not proposer_id or not accepter_id:
            return None
        if proposer_id == accepter_id:
            return None
        if not terms or len(set(terms)) != len(terms):
            return None
        if proposed_day < 0:
            return None
        if term_days <= 0:
            return None
        # Block duplicate active treaty between same pair
        for t_ in self._treaties.values():
            if t_.state in (
                TreatyState.PROPOSED, TreatyState.SIGNED,
            ) and {
                t_.proposer_id, t_.accepter_id,
            } == {proposer_id, accepter_id}:
                return None
        tid = f"treaty_{self._next}"
        self._next += 1
        self._treaties[tid] = Treaty(
            treaty_id=tid, proposer_id=proposer_id,
            accepter_id=accepter_id, terms=terms,
            state=TreatyState.PROPOSED,
            proposed_day=proposed_day, signed_day=0,
            expires_day=proposed_day + term_days,
            breaker_id="", honor_penalty=0,
        )
        return tid

    def sign(
        self, *, treaty_id: str, signer_id: str,
        signed_day: int,
    ) -> bool:
        if treaty_id not in self._treaties:
            return False
        t_ = self._treaties[treaty_id]
        if t_.state != TreatyState.PROPOSED:
            return False
        if signer_id != t_.accepter_id:
            return False
        if signed_day < t_.proposed_day:
            return False
        self._treaties[treaty_id] = dataclasses.replace(
            t_, state=TreatyState.SIGNED,
            signed_day=signed_day,
            expires_day=(
                signed_day
                + (t_.expires_day - t_.proposed_day)
            ),
        )
        return True

    def break_treaty(
        self, *, treaty_id: str, breaker_id: str,
    ) -> t.Optional[int]:
        if treaty_id not in self._treaties:
            return None
        t_ = self._treaties[treaty_id]
        if t_.state != TreatyState.SIGNED:
            return None
        if breaker_id not in (
            t_.proposer_id, t_.accepter_id,
        ):
            return None
        self._treaties[treaty_id] = dataclasses.replace(
            t_, state=TreatyState.BROKEN,
            breaker_id=breaker_id,
            honor_penalty=_BREAK_HONOR_PENALTY,
        )
        return _BREAK_HONOR_PENALTY

    def expire(
        self, *, treaty_id: str, current_day: int,
    ) -> bool:
        if treaty_id not in self._treaties:
            return False
        t_ = self._treaties[treaty_id]
        if t_.state != TreatyState.SIGNED:
            return False
        if current_day <= t_.expires_day:
            return False
        self._treaties[treaty_id] = dataclasses.replace(
            t_, state=TreatyState.EXPIRED,
        )
        return True

    def is_active_between(
        self, *, player_a: str, player_b: str,
    ) -> bool:
        for t_ in self._treaties.values():
            if (
                t_.state == TreatyState.SIGNED
                and {
                    t_.proposer_id, t_.accepter_id,
                } == {player_a, player_b}
            ):
                return True
        return False

    def treaty(
        self, *, treaty_id: str,
    ) -> t.Optional[Treaty]:
        return self._treaties.get(treaty_id)

    def treaties_of(
        self, *, player_id: str,
    ) -> list[Treaty]:
        return [
            t_ for t_ in self._treaties.values()
            if player_id in (
                t_.proposer_id, t_.accepter_id,
            )
        ]


__all__ = [
    "TreatyState", "TreatyTerm", "Treaty",
    "PlayerTreatySystem",
]
