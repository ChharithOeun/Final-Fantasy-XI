"""Alliance system — combine up to 3 parties (max 18 players).

Used for HNM camps, sky/sea organization, dynamis. Alliance
leader is the leader of party 1 (the alliance founder). Other
parties keep their own leaders for /pcmd purposes; alliance
leader uses /acmd.

Public surface
--------------
    Alliance
        .add_party(party_id) -> bool
        .remove_party(party_id) -> bool
        .disband() -> bool
        .alliance_leader_id property (read from party 1)
        .total_members property
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.party_system import MAX_PARTY_SIZE, Party


MAX_PARTIES_PER_ALLIANCE = 3
MAX_ALLIANCE_MEMBERS = MAX_PARTIES_PER_ALLIANCE * MAX_PARTY_SIZE  # 18


@dataclasses.dataclass
class Alliance:
    alliance_id: str
    _parties: list[Party] = dataclasses.field(default_factory=list)
    _disbanded: bool = False

    @classmethod
    def create(cls, *, alliance_id: str, founder_party: Party) -> "Alliance":
        a = cls(alliance_id=alliance_id)
        a._parties.append(founder_party)
        return a

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def parties(self) -> tuple[Party, ...]:
        return tuple(self._parties)

    @property
    def party_ids(self) -> tuple[str, ...]:
        return tuple(p.party_id for p in self._parties)

    @property
    def party_count(self) -> int:
        return len(self._parties)

    @property
    def is_full(self) -> bool:
        return self.party_count >= MAX_PARTIES_PER_ALLIANCE

    @property
    def alliance_leader_id(self) -> t.Optional[str]:
        if not self._parties:
            return None
        return self._parties[0].leader_id

    @property
    def total_members(self) -> int:
        return sum(p.size for p in self._parties)

    @property
    def all_member_ids(self) -> tuple[str, ...]:
        out: list[str] = []
        for p in self._parties:
            out.extend(p.member_ids)
        return tuple(out)

    @property
    def is_disbanded(self) -> bool:
        return self._disbanded

    # ------------------------------------------------------------------
    # Lifecycle ops
    # ------------------------------------------------------------------
    def add_party(self, *, by_alliance_leader_id: str, party: Party) -> bool:
        if self._disbanded:
            return False
        if by_alliance_leader_id != self.alliance_leader_id:
            return False
        if self.is_full:
            return False
        if party.party_id in self.party_ids:
            return False
        if party.is_disbanded:
            return False
        # No member overlap allowed (a player is in at most one party)
        existing = set(self.all_member_ids)
        if existing & set(party.member_ids):
            return False
        self._parties.append(party)
        return True

    def remove_party(self, *, by_alliance_leader_id: str,
                     party_id: str) -> bool:
        if self._disbanded:
            return False
        if by_alliance_leader_id != self.alliance_leader_id:
            return False
        if party_id == self._parties[0].party_id:
            # Removing the founder = disband
            return False
        for p in list(self._parties):
            if p.party_id == party_id:
                self._parties.remove(p)
                return True
        return False

    def disband(self, *, by_alliance_leader_id: str) -> bool:
        if self._disbanded:
            return False
        if by_alliance_leader_id != self.alliance_leader_id:
            return False
        self._disbanded = True
        self._parties.clear()
        return True


__all__ = [
    "MAX_PARTIES_PER_ALLIANCE",
    "MAX_ALLIANCE_MEMBERS",
    "Alliance",
]
