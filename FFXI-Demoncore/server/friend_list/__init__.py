"""Friend list — friends + blacklist + status visibility.

Each player has two sets: friends and blocklist. Visibility rules:
  - Friends see your online/offline status, current zone, current job
  - Blocked players cannot send tells, invites, or trade requests

Friend additions are mutual by default (both sides must accept).

Public surface
--------------
    FriendList per player
        .request_friend(target_id)
        .accept_friend(requester_id)
        .reject_friend(requester_id)
        .remove_friend(target_id)
        .block(target_id)
        .unblock(target_id)
        .can_message_from(sender_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class FriendStatus(str, enum.Enum):
    NONE = "none"
    PENDING_OUT = "pending_out"     # I sent a request
    PENDING_IN = "pending_in"        # They sent a request
    FRIENDS = "friends"


@dataclasses.dataclass
class FriendList:
    player_id: str
    _state: dict[str, FriendStatus] = dataclasses.field(
        default_factory=dict, repr=False,
    )
    blocked: set[str] = dataclasses.field(default_factory=set)

    def status_with(self, other_id: str) -> FriendStatus:
        return self._state.get(other_id, FriendStatus.NONE)

    def is_friend(self, other_id: str) -> bool:
        return self.status_with(other_id) == FriendStatus.FRIENDS

    def is_blocked(self, other_id: str) -> bool:
        return other_id in self.blocked

    # -- Friend lifecycle (caller wires both sides) --

    def request_outgoing(self, *, target_id: str) -> bool:
        if target_id == self.player_id:
            return False
        if self.is_blocked(target_id):
            return False
        if self.status_with(target_id) != FriendStatus.NONE:
            return False
        self._state[target_id] = FriendStatus.PENDING_OUT
        return True

    def receive_request(self, *, requester_id: str) -> bool:
        if requester_id == self.player_id:
            return False
        if self.is_blocked(requester_id):
            return False
        if self.status_with(requester_id) != FriendStatus.NONE:
            return False
        self._state[requester_id] = FriendStatus.PENDING_IN
        return True

    def accept_request(self, *, requester_id: str) -> bool:
        if self.status_with(requester_id) != FriendStatus.PENDING_IN:
            return False
        self._state[requester_id] = FriendStatus.FRIENDS
        return True

    def reject_request(self, *, requester_id: str) -> bool:
        if self.status_with(requester_id) != FriendStatus.PENDING_IN:
            return False
        del self._state[requester_id]
        return True

    def confirm_outgoing_accepted(self, *, target_id: str) -> bool:
        """Other side accepted; promote our pending_out to friends."""
        if self.status_with(target_id) != FriendStatus.PENDING_OUT:
            return False
        self._state[target_id] = FriendStatus.FRIENDS
        return True

    def remove_friend(self, *, target_id: str) -> bool:
        if self.status_with(target_id) != FriendStatus.FRIENDS:
            return False
        del self._state[target_id]
        return True

    # -- Blocklist --

    def block(self, *, target_id: str) -> bool:
        if target_id == self.player_id:
            return False
        # Blocking auto-removes friendship
        if target_id in self._state:
            del self._state[target_id]
        self.blocked.add(target_id)
        return True

    def unblock(self, *, target_id: str) -> bool:
        if target_id not in self.blocked:
            return False
        self.blocked.remove(target_id)
        return True

    # -- Visibility --

    def can_message_from(self, *, sender_id: str) -> bool:
        """Can sender_id send me a tell/invite right now?"""
        if self.is_blocked(sender_id):
            return False
        return True

    def friends(self) -> tuple[str, ...]:
        return tuple(
            pid for pid, s in self._state.items()
            if s == FriendStatus.FRIENDS
        )

    def pending_in(self) -> tuple[str, ...]:
        return tuple(
            pid for pid, s in self._state.items()
            if s == FriendStatus.PENDING_IN
        )


__all__ = ["FriendStatus", "FriendList"]
