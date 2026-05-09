"""Mercenary linkshell — formal LSes that fulfill guild contracts.

Solo mercenaries can take small jobs alone, but big contracts
(carry through Sortie, escort across multiple zones) need a
group. Mercenary linkshells are formal LSes registered with
the guild, with a declared specialization (the JobKind they
focus on) and 2..12 members. The LS founder collects job
acceptances on behalf of the LS; rewards are split among the
members who participated.

LSes can declare a specialization that boosts their match-
making priority for that JobKind on the guild board. They can
disband (refunds escrowed pool, removes registration) or
declare bankruptcy (forces dispute resolution on all open
contracts).

Public surface
--------------
    LinkshellState enum
    Specialization enum
    Linkshell dataclass (frozen)
    MercenaryLinkshellSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_MEMBERS = 2
_MAX_MEMBERS = 12


class Specialization(str, enum.Enum):
    CRAFT_ORDER = "craft_order"
    POWER_LEVEL = "power_level"
    CONTENT_CARRY = "content_carry"
    DELIVERY = "delivery"
    ESCORT = "escort"
    BOUNTY = "bounty"
    GENERALIST = "generalist"


class LinkshellState(str, enum.Enum):
    ACTIVE = "active"
    DISBANDED = "disbanded"
    BANKRUPT = "bankrupt"


@dataclasses.dataclass(frozen=True)
class Linkshell:
    ls_id: str
    name: str
    founder_id: str
    specialization: Specialization
    members: tuple[str, ...]
    state: LinkshellState
    contracts_completed: int
    pool_gil: int


@dataclasses.dataclass
class MercenaryLinkshellSystem:
    _lses: dict[str, Linkshell] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def register_ls(
        self, *, name: str, founder_id: str,
        specialization: Specialization,
    ) -> t.Optional[str]:
        if not name or not founder_id:
            return None
        # Names must be unique
        for ls in self._lses.values():
            if ls.name == name:
                return None
        lid = f"ls_{self._next}"
        self._next += 1
        self._lses[lid] = Linkshell(
            ls_id=lid, name=name,
            founder_id=founder_id,
            specialization=specialization,
            members=(founder_id,),
            state=LinkshellState.ACTIVE,
            contracts_completed=0, pool_gil=0,
        )
        return lid

    def add_member(
        self, *, ls_id: str, member_id: str,
    ) -> bool:
        if ls_id not in self._lses:
            return False
        ls = self._lses[ls_id]
        if ls.state != LinkshellState.ACTIVE:
            return False
        if member_id in ls.members:
            return False
        if len(ls.members) >= _MAX_MEMBERS:
            return False
        if not member_id:
            return False
        self._lses[ls_id] = dataclasses.replace(
            ls, members=ls.members + (member_id,),
        )
        return True

    def remove_member(
        self, *, ls_id: str, member_id: str,
    ) -> bool:
        if ls_id not in self._lses:
            return False
        ls = self._lses[ls_id]
        if ls.state != LinkshellState.ACTIVE:
            return False
        if member_id not in ls.members:
            return False
        if member_id == ls.founder_id:
            return False  # founder must transfer first
        new_members = tuple(
            m for m in ls.members if m != member_id
        )
        self._lses[ls_id] = dataclasses.replace(
            ls, members=new_members,
        )
        return True

    def transfer_founder(
        self, *, ls_id: str, current_founder: str,
        new_founder: str,
    ) -> bool:
        if ls_id not in self._lses:
            return False
        ls = self._lses[ls_id]
        if ls.state != LinkshellState.ACTIVE:
            return False
        if ls.founder_id != current_founder:
            return False
        if new_founder not in ls.members:
            return False
        self._lses[ls_id] = dataclasses.replace(
            ls, founder_id=new_founder,
        )
        return True

    def can_accept_kind(
        self, *, ls_id: str, kind: str,
    ) -> bool:
        """LS can accept any JobKind, but
        specialization-matching gigs get matchmaking
        priority. Returns True only if active and
        meets minimum members.
        """
        if ls_id not in self._lses:
            return False
        ls = self._lses[ls_id]
        if ls.state != LinkshellState.ACTIVE:
            return False
        if len(ls.members) < _MIN_MEMBERS:
            return False
        return True

    def credit_completion(
        self, *, ls_id: str, payout_gil: int,
    ) -> bool:
        """Job completed by the LS. Pool grows;
        completion count increments. Founder
        decides distribution policy.
        """
        if ls_id not in self._lses:
            return False
        ls = self._lses[ls_id]
        if ls.state != LinkshellState.ACTIVE:
            return False
        if payout_gil <= 0:
            return False
        if len(ls.members) < _MIN_MEMBERS:
            return False
        self._lses[ls_id] = dataclasses.replace(
            ls,
            contracts_completed=(
                ls.contracts_completed + 1
            ),
            pool_gil=ls.pool_gil + payout_gil,
        )
        return True

    def distribute_pool_evenly(
        self, *, ls_id: str, founder_id: str,
    ) -> t.Optional[int]:
        """Founder triggers distribution. Returns
        per-member share; remainder stays in pool.
        """
        if ls_id not in self._lses:
            return None
        ls = self._lses[ls_id]
        if ls.state != LinkshellState.ACTIVE:
            return None
        if ls.founder_id != founder_id:
            return None
        if not ls.members:
            return None
        per_member = ls.pool_gil // len(ls.members)
        remainder = ls.pool_gil % len(ls.members)
        self._lses[ls_id] = dataclasses.replace(
            ls, pool_gil=remainder,
        )
        return per_member

    def disband(
        self, *, ls_id: str, founder_id: str,
    ) -> t.Optional[int]:
        """Founder disbands. Returns final pool
        which would be split (here: returned to
        founder for distribution off-ledger).
        """
        if ls_id not in self._lses:
            return None
        ls = self._lses[ls_id]
        if ls.state != LinkshellState.ACTIVE:
            return None
        if ls.founder_id != founder_id:
            return None
        final = ls.pool_gil
        self._lses[ls_id] = dataclasses.replace(
            ls, state=LinkshellState.DISBANDED,
            pool_gil=0,
        )
        return final

    def linkshell(
        self, *, ls_id: str,
    ) -> t.Optional[Linkshell]:
        return self._lses.get(ls_id)

    def lses_by_specialization(
        self, *, specialization: Specialization,
    ) -> list[Linkshell]:
        return [
            ls for ls in self._lses.values()
            if ls.specialization == specialization
            and ls.state == LinkshellState.ACTIVE
        ]


__all__ = [
    "Specialization", "LinkshellState", "Linkshell",
    "MercenaryLinkshellSystem",
]
