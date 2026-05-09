"""Player sworn brotherhood — informal but tracked bond.

Sworn brotherhoods are 2..7 player groups bonded by mutual
ceremony — less formal than a marriage but stronger than a
linkshell. Members can find each other's coordinates from any
zone (\"brother sense\"), gain a shared brotherhood_fame
tally that grows when any member earns fame, and have
recognition by NPCs in dialog. Disbanding requires unanimous
consent from all current members.

Lifecycle
    PROPOSED      founder created, others haven't sworn in
    ACTIVE        at least 2 members sworn in
    DISBANDED     unanimous dissolution

Public surface
--------------
    BrotherhoodState enum
    Brotherhood dataclass (frozen)
    PlayerSwornBrotherhoodSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_MEMBERS = 2
_MAX_MEMBERS = 7


class BrotherhoodState(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    DISBANDED = "disbanded"


@dataclasses.dataclass(frozen=True)
class Brotherhood:
    brotherhood_id: str
    name: str
    founder_id: str
    members: tuple[str, ...]
    state: BrotherhoodState
    formed_day: int
    shared_fame: int
    disband_votes: tuple[str, ...]


@dataclasses.dataclass
class PlayerSwornBrotherhoodSystem:
    _bonds: dict[str, Brotherhood] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def found(
        self, *, name: str, founder_id: str,
        formed_day: int,
    ) -> t.Optional[str]:
        if not name or not founder_id:
            return None
        if formed_day < 0:
            return None
        for b in self._bonds.values():
            if b.name == name:
                return None
        bid = f"bro_{self._next}"
        self._next += 1
        self._bonds[bid] = Brotherhood(
            brotherhood_id=bid, name=name,
            founder_id=founder_id,
            members=(founder_id,),
            state=BrotherhoodState.PROPOSED,
            formed_day=formed_day,
            shared_fame=0, disband_votes=(),
        )
        return bid

    def swear_in(
        self, *, brotherhood_id: str, member_id: str,
    ) -> bool:
        """A new member joins. Triggers ACTIVE
        promotion when >=2 members.
        """
        if brotherhood_id not in self._bonds:
            return False
        b = self._bonds[brotherhood_id]
        if b.state == BrotherhoodState.DISBANDED:
            return False
        if not member_id or member_id in b.members:
            return False
        if len(b.members) >= _MAX_MEMBERS:
            return False
        new_members = b.members + (member_id,)
        new_state = b.state
        if (
            b.state == BrotherhoodState.PROPOSED
            and len(new_members) >= _MIN_MEMBERS
        ):
            new_state = BrotherhoodState.ACTIVE
        self._bonds[brotherhood_id] = (
            dataclasses.replace(
                b, members=new_members,
                state=new_state,
            )
        )
        return True

    def can_sense(
        self, *, brotherhood_id: str,
        seeker_id: str, target_id: str,
    ) -> bool:
        """\"Brother sense\" — both must be in the
        same active brotherhood.
        """
        if brotherhood_id not in self._bonds:
            return False
        b = self._bonds[brotherhood_id]
        if b.state != BrotherhoodState.ACTIVE:
            return False
        return (
            seeker_id in b.members
            and target_id in b.members
            and seeker_id != target_id
        )

    def add_fame(
        self, *, brotherhood_id: str, fame_amount: int,
    ) -> bool:
        if brotherhood_id not in self._bonds:
            return False
        b = self._bonds[brotherhood_id]
        if b.state != BrotherhoodState.ACTIVE:
            return False
        if fame_amount <= 0:
            return False
        self._bonds[brotherhood_id] = (
            dataclasses.replace(
                b, shared_fame=b.shared_fame + fame_amount,
            )
        )
        return True

    def vote_disband(
        self, *, brotherhood_id: str, voter_id: str,
    ) -> bool:
        if brotherhood_id not in self._bonds:
            return False
        b = self._bonds[brotherhood_id]
        if b.state != BrotherhoodState.ACTIVE:
            return False
        if voter_id not in b.members:
            return False
        if voter_id in b.disband_votes:
            return False
        new_votes = b.disband_votes + (voter_id,)
        new_state = b.state
        if set(new_votes) == set(b.members):
            new_state = BrotherhoodState.DISBANDED
        self._bonds[brotherhood_id] = (
            dataclasses.replace(
                b, disband_votes=new_votes,
                state=new_state,
            )
        )
        return True

    def withdraw_disband_vote(
        self, *, brotherhood_id: str, voter_id: str,
    ) -> bool:
        if brotherhood_id not in self._bonds:
            return False
        b = self._bonds[brotherhood_id]
        if b.state != BrotherhoodState.ACTIVE:
            return False
        if voter_id not in b.disband_votes:
            return False
        new_votes = tuple(
            v for v in b.disband_votes if v != voter_id
        )
        self._bonds[brotherhood_id] = (
            dataclasses.replace(
                b, disband_votes=new_votes,
            )
        )
        return True

    def brotherhood(
        self, *, brotherhood_id: str,
    ) -> t.Optional[Brotherhood]:
        return self._bonds.get(brotherhood_id)

    def brotherhoods_of(
        self, *, member_id: str,
    ) -> list[Brotherhood]:
        return [
            b for b in self._bonds.values()
            if member_id in b.members
        ]


__all__ = [
    "BrotherhoodState", "Brotherhood",
    "PlayerSwornBrotherhoodSystem",
]
