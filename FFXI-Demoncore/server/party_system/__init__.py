"""Party system — invite, join, leader role, kick, leave.

Canonical FFXI party rules
--------------------------
* Max 6 members per party
* One leader; leader can /pcmd add invite, /pcmd kick, /pcmd
  leader to promote.
* Member receiving an invite must accept; pending invites can be
  declined or expire after 60s.
* Leader leaving auto-promotes the longest-tenured remaining
  member.
* Empty party (no members) auto-disbands.

Public surface
--------------
    PartyRole enum (LEADER / MEMBER)
    PartyMember dataclass
    Party
        .invite(target_id, now) -> bool
        .accept_invite(target_id, now) -> bool
        .decline_invite(target_id) -> bool
        .leave(player_id) -> bool
        .kick(by_leader_id, target_id) -> bool
        .promote(by_leader_id, target_id) -> bool
        .members property
        .leader_id property
        .is_disbanded property
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_PARTY_SIZE = 6
INVITE_TTL_SECONDS = 60


class PartyRole(str, enum.Enum):
    LEADER = "leader"
    MEMBER = "member"


@dataclasses.dataclass
class PartyMember:
    player_id: str
    role: PartyRole = PartyRole.MEMBER
    joined_at: float = 0.0


@dataclasses.dataclass
class _PendingInvite:
    target_id: str
    expires_at: float


@dataclasses.dataclass
class Party:
    party_id: str
    _members: list[PartyMember] = dataclasses.field(default_factory=list)
    _pending: list[_PendingInvite] = dataclasses.field(default_factory=list)
    _disbanded: bool = False

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def create(cls, *, party_id: str, leader_id: str, now: float = 0.0) -> "Party":
        p = cls(party_id=party_id)
        p._members.append(PartyMember(
            player_id=leader_id, role=PartyRole.LEADER, joined_at=now,
        ))
        return p

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def members(self) -> tuple[PartyMember, ...]:
        return tuple(self._members)

    @property
    def member_ids(self) -> tuple[str, ...]:
        return tuple(m.player_id for m in self._members)

    @property
    def leader_id(self) -> t.Optional[str]:
        for m in self._members:
            if m.role == PartyRole.LEADER:
                return m.player_id
        return None

    @property
    def size(self) -> int:
        return len(self._members)

    @property
    def is_full(self) -> bool:
        return self.size >= MAX_PARTY_SIZE

    @property
    def is_disbanded(self) -> bool:
        return self._disbanded

    @property
    def pending_invite_targets(self) -> tuple[str, ...]:
        return tuple(p.target_id for p in self._pending)

    # ------------------------------------------------------------------
    # Lifecycle ops
    # ------------------------------------------------------------------
    def invite(self, *, by_leader_id: str, target_id: str,
               now: float = 0.0) -> bool:
        if self._disbanded:
            return False
        if self.leader_id != by_leader_id:
            return False
        if target_id in self.member_ids:
            return False
        if self.is_full:
            return False
        # purge expired pendings, then check duplicate
        self._purge_expired(now)
        if target_id in self.pending_invite_targets:
            return False
        self._pending.append(_PendingInvite(
            target_id=target_id,
            expires_at=now + INVITE_TTL_SECONDS,
        ))
        return True

    def accept_invite(self, *, target_id: str, now: float = 0.0) -> bool:
        if self._disbanded or self.is_full:
            return False
        self._purge_expired(now)
        for p in list(self._pending):
            if p.target_id == target_id:
                self._pending.remove(p)
                self._members.append(PartyMember(
                    player_id=target_id,
                    role=PartyRole.MEMBER,
                    joined_at=now,
                ))
                return True
        return False

    def decline_invite(self, *, target_id: str) -> bool:
        for p in list(self._pending):
            if p.target_id == target_id:
                self._pending.remove(p)
                return True
        return False

    def leave(self, *, player_id: str) -> bool:
        if self._disbanded:
            return False
        for m in list(self._members):
            if m.player_id == player_id:
                was_leader = m.role == PartyRole.LEADER
                self._members.remove(m)
                if not self._members:
                    self._disbanded = True
                    return True
                if was_leader:
                    # auto-promote longest-tenured remaining member
                    self._members.sort(key=lambda x: x.joined_at)
                    self._members[0].role = PartyRole.LEADER
                return True
        return False

    def kick(self, *, by_leader_id: str, target_id: str) -> bool:
        if self.leader_id != by_leader_id:
            return False
        if target_id == by_leader_id:
            # leaders use leave(), not kick on self
            return False
        return self.leave(player_id=target_id)

    def promote(self, *, by_leader_id: str, target_id: str) -> bool:
        if self.leader_id != by_leader_id:
            return False
        if target_id not in self.member_ids:
            return False
        if target_id == by_leader_id:
            return False
        for m in self._members:
            if m.role == PartyRole.LEADER:
                m.role = PartyRole.MEMBER
            elif m.player_id == target_id:
                m.role = PartyRole.LEADER
        return True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _purge_expired(self, now: float) -> None:
        self._pending = [p for p in self._pending if p.expires_at > now]


__all__ = [
    "MAX_PARTY_SIZE",
    "INVITE_TTL_SECONDS",
    "PartyRole",
    "PartyMember",
    "Party",
]
