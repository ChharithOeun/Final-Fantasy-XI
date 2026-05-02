"""Linkshell — guild membership with rank hierarchy.

Three rank tiers, mirroring retail FFXI's pearl/sack/leader items:

  PEARL_HOLDER - basic member; can chat in the linkshell
  SACK_HOLDER  - officer; can promote pearls + remove pearls
  LEADER       - owner; can promote sacks, demote, kick anyone,
                  disband the linkshell

Public surface
--------------
    LinkshellRank enum
    Linkshell dataclass
    LinkshellRoster facade
        .add_member(by_actor, target, rank)
        .promote(by, target, to)
        .demote(by, target, to)
        .kick(by, target)
        .disband(by)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LinkshellRank(int, enum.Enum):
    PEARL_HOLDER = 1
    SACK_HOLDER = 2
    LEADER = 3


@dataclasses.dataclass(frozen=True)
class ActionResult:
    accepted: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass
class LinkshellRoster:
    linkshell_id: str
    name: str
    leader_id: str
    _members: dict[str, LinkshellRank] = dataclasses.field(
        default_factory=dict, repr=False,
    )
    disbanded: bool = False

    def __post_init__(self) -> None:
        # Initialize the leader as a leader-rank member.
        if self.leader_id and self.leader_id not in self._members:
            self._members[self.leader_id] = LinkshellRank.LEADER

    @property
    def member_count(self) -> int:
        return len(self._members)

    def rank_of(self, player_id: str) -> t.Optional[LinkshellRank]:
        return self._members.get(player_id)

    def is_member(self, player_id: str) -> bool:
        return player_id in self._members

    def members_with_rank(
        self, rank: LinkshellRank,
    ) -> tuple[str, ...]:
        return tuple(
            pid for pid, r in self._members.items() if r == rank
        )

    def add_member(
        self, *, by_actor: str, target_id: str,
    ) -> ActionResult:
        if self.disbanded:
            return ActionResult(False, "linkshell disbanded")
        if target_id in self._members:
            return ActionResult(False, "already a member")
        actor_rank = self._members.get(by_actor)
        if actor_rank is None:
            return ActionResult(False, "actor not a member")
        if actor_rank.value < LinkshellRank.SACK_HOLDER.value:
            return ActionResult(False, "must be sack or leader to invite")
        self._members[target_id] = LinkshellRank.PEARL_HOLDER
        return ActionResult(True)

    def promote(
        self, *, by_actor: str, target_id: str,
        to_rank: LinkshellRank,
    ) -> ActionResult:
        if self.disbanded:
            return ActionResult(False, "linkshell disbanded")
        actor_rank = self._members.get(by_actor)
        target_rank = self._members.get(target_id)
        if actor_rank is None:
            return ActionResult(False, "actor not a member")
        if target_rank is None:
            return ActionResult(False, "target not a member")
        if to_rank.value <= target_rank.value:
            return ActionResult(False, "must be a promotion")
        # Sack can only promote to sack (i.e. promote pearl to sack
        # is forbidden — that's a leader-only action).
        # Wait — in retail, sack-holders can hand out pearls but not
        # promote pearls to sacks. Only leaders can promote to sack.
        if to_rank == LinkshellRank.LEADER:
            return ActionResult(False, "use leader-transfer flow")
        if to_rank == LinkshellRank.SACK_HOLDER:
            if actor_rank != LinkshellRank.LEADER:
                return ActionResult(False,
                                    "only leader can grant sack")
        self._members[target_id] = to_rank
        return ActionResult(True)

    def demote(
        self, *, by_actor: str, target_id: str,
        to_rank: LinkshellRank,
    ) -> ActionResult:
        if self.disbanded:
            return ActionResult(False, "linkshell disbanded")
        actor_rank = self._members.get(by_actor)
        target_rank = self._members.get(target_id)
        if actor_rank is None or target_rank is None:
            return ActionResult(False, "membership invalid")
        if to_rank.value >= target_rank.value:
            return ActionResult(False, "must be a demotion")
        if actor_rank.value <= target_rank.value:
            return ActionResult(False, "cannot demote equal or higher")
        if target_id == self.leader_id:
            return ActionResult(False, "cannot demote leader")
        self._members[target_id] = to_rank
        return ActionResult(True)

    def kick(
        self, *, by_actor: str, target_id: str,
    ) -> ActionResult:
        if self.disbanded:
            return ActionResult(False, "linkshell disbanded")
        actor_rank = self._members.get(by_actor)
        target_rank = self._members.get(target_id)
        if actor_rank is None or target_rank is None:
            return ActionResult(False, "membership invalid")
        if actor_rank.value <= target_rank.value:
            return ActionResult(False, "cannot kick equal or higher")
        if target_id == self.leader_id:
            return ActionResult(False, "cannot kick leader")
        del self._members[target_id]
        return ActionResult(True)

    def leave(self, *, target_id: str) -> ActionResult:
        if target_id == self.leader_id:
            return ActionResult(False,
                                "leader must transfer or disband")
        if target_id not in self._members:
            return ActionResult(False, "not a member")
        del self._members[target_id]
        return ActionResult(True)

    def disband(self, *, by_actor: str) -> ActionResult:
        if self.disbanded:
            return ActionResult(False, "already disbanded")
        if by_actor != self.leader_id:
            return ActionResult(False, "only leader can disband")
        self.disbanded = True
        self._members.clear()
        return ActionResult(True)


__all__ = [
    "LinkshellRank", "ActionResult",
    "LinkshellRoster",
]
