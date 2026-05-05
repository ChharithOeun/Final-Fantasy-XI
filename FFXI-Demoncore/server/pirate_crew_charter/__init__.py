"""Pirate crew charter — formal multi-player ship crew registry.

A CREW is the ship-bound equivalent of a linkshell. Up to 24
members under a single CHARTER. The charter has a CAPTAIN
(founder), up to 4 OFFICERS (promoted by the captain), and
the rest are CREW. The captain can transfer captaincy or
disband the charter (see cult_disbandment for the latter).

Charter flag determines policy:
  PIRATE       - outlaw-aligned crew; boarding by default
                 unsanctioned
  PRIVATEER    - holds a letter_of_marque under a nation;
                 boarding sanctioned per the letter scope
  MERCHANT     - non-combat trade crew; can't initiate
                 boarding (only defend)

Public surface
--------------
    CharterFlag enum
    CrewRole enum
    CrewRecord dataclass
    PirateCrewCharter
        .found(charter_id, founder_id, charter_name, flag,
               now_seconds)
        .invite(charter_id, captain_id, recruit_id)
        .accept_invite(charter_id, recruit_id)
        .promote(charter_id, captain_id, member_id, role)
        .demote(charter_id, captain_id, member_id)
        .leave(charter_id, member_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CharterFlag(str, enum.Enum):
    PIRATE = "pirate"
    PRIVATEER = "privateer"
    MERCHANT = "merchant"


class CrewRole(str, enum.Enum):
    CAPTAIN = "captain"
    OFFICER = "officer"
    CREW = "crew"


MAX_CREW_SIZE = 24
MAX_OFFICERS = 4


@dataclasses.dataclass
class CrewRecord:
    charter_id: str
    charter_name: str
    flag: CharterFlag
    captain_id: str
    members: dict[str, CrewRole] = dataclasses.field(default_factory=dict)
    pending_invites: set[str] = dataclasses.field(default_factory=set)
    founded_at: int = 0


@dataclasses.dataclass(frozen=True)
class CharterResult:
    accepted: bool
    charter_id: t.Optional[str] = None
    new_role: t.Optional[CrewRole] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PirateCrewCharter:
    _charters: dict[str, CrewRecord] = dataclasses.field(default_factory=dict)
    # player -> charter_id (a player may belong to only one)
    _membership: dict[str, str] = dataclasses.field(default_factory=dict)

    def found(
        self, *, charter_id: str,
        founder_id: str,
        charter_name: str,
        flag: CharterFlag,
        now_seconds: int,
    ) -> CharterResult:
        if not charter_id or charter_id in self._charters:
            return CharterResult(False, reason="bad charter id")
        if not founder_id or not charter_name:
            return CharterResult(False, reason="bad founder/name")
        if flag not in CharterFlag:
            return CharterResult(False, reason="unknown flag")
        if founder_id in self._membership:
            return CharterResult(
                False, reason="founder already in a crew",
            )
        rec = CrewRecord(
            charter_id=charter_id,
            charter_name=charter_name,
            flag=flag,
            captain_id=founder_id,
            founded_at=now_seconds,
        )
        rec.members[founder_id] = CrewRole.CAPTAIN
        self._charters[charter_id] = rec
        self._membership[founder_id] = charter_id
        return CharterResult(
            accepted=True, charter_id=charter_id,
            new_role=CrewRole.CAPTAIN,
        )

    def invite(
        self, *, charter_id: str,
        captain_id: str,
        recruit_id: str,
    ) -> CharterResult:
        rec = self._charters.get(charter_id)
        if rec is None:
            return CharterResult(False, reason="unknown charter")
        if rec.captain_id != captain_id:
            return CharterResult(False, reason="not captain")
        if not recruit_id:
            return CharterResult(False, reason="bad recruit")
        if recruit_id in self._membership:
            return CharterResult(
                False, reason="recruit already in a crew",
            )
        if recruit_id in rec.pending_invites:
            return CharterResult(False, reason="already invited")
        if len(rec.members) >= MAX_CREW_SIZE:
            return CharterResult(False, reason="crew full")
        rec.pending_invites.add(recruit_id)
        return CharterResult(accepted=True, charter_id=charter_id)

    def accept_invite(
        self, *, charter_id: str, recruit_id: str,
    ) -> CharterResult:
        rec = self._charters.get(charter_id)
        if rec is None:
            return CharterResult(False, reason="unknown charter")
        if recruit_id not in rec.pending_invites:
            return CharterResult(False, reason="no invite")
        if recruit_id in self._membership:
            return CharterResult(False, reason="already in a crew")
        if len(rec.members) >= MAX_CREW_SIZE:
            return CharterResult(False, reason="crew full")
        rec.pending_invites.discard(recruit_id)
        rec.members[recruit_id] = CrewRole.CREW
        self._membership[recruit_id] = charter_id
        return CharterResult(
            accepted=True, charter_id=charter_id,
            new_role=CrewRole.CREW,
        )

    def promote(
        self, *, charter_id: str,
        captain_id: str,
        member_id: str,
        role: CrewRole,
    ) -> CharterResult:
        rec = self._charters.get(charter_id)
        if rec is None:
            return CharterResult(False, reason="unknown charter")
        if rec.captain_id != captain_id:
            return CharterResult(False, reason="not captain")
        if member_id not in rec.members:
            return CharterResult(False, reason="not a member")
        if role == CrewRole.CAPTAIN:
            # transfer captaincy
            rec.members[rec.captain_id] = CrewRole.OFFICER
            rec.members[member_id] = CrewRole.CAPTAIN
            rec.captain_id = member_id
            return CharterResult(
                accepted=True, charter_id=charter_id,
                new_role=CrewRole.CAPTAIN,
            )
        if role == CrewRole.OFFICER:
            officer_count = sum(
                1 for r in rec.members.values()
                if r == CrewRole.OFFICER
            )
            if rec.members[member_id] == CrewRole.OFFICER:
                return CharterResult(
                    False, reason="already officer",
                )
            if officer_count >= MAX_OFFICERS:
                return CharterResult(
                    False, reason="officer slots full",
                )
            rec.members[member_id] = CrewRole.OFFICER
            return CharterResult(
                accepted=True, charter_id=charter_id,
                new_role=CrewRole.OFFICER,
            )
        return CharterResult(False, reason="bad role")

    def demote(
        self, *, charter_id: str,
        captain_id: str,
        member_id: str,
    ) -> CharterResult:
        rec = self._charters.get(charter_id)
        if rec is None or rec.captain_id != captain_id:
            return CharterResult(
                False, reason="bad charter or not captain",
            )
        if member_id == captain_id:
            return CharterResult(False, reason="cannot demote captain")
        if rec.members.get(member_id) != CrewRole.OFFICER:
            return CharterResult(False, reason="not an officer")
        rec.members[member_id] = CrewRole.CREW
        return CharterResult(
            accepted=True, charter_id=charter_id,
            new_role=CrewRole.CREW,
        )

    def leave(
        self, *, charter_id: str, member_id: str,
    ) -> CharterResult:
        rec = self._charters.get(charter_id)
        if rec is None or member_id not in rec.members:
            return CharterResult(False, reason="not a member")
        if rec.captain_id == member_id:
            return CharterResult(
                False, reason="captain must transfer or disband",
            )
        del rec.members[member_id]
        del self._membership[member_id]
        return CharterResult(accepted=True, charter_id=charter_id)

    def charter_for(
        self, *, charter_id: str,
    ) -> t.Optional[CrewRecord]:
        return self._charters.get(charter_id)

    def membership_of(self, *, player_id: str) -> t.Optional[str]:
        return self._membership.get(player_id)


__all__ = [
    "CharterFlag", "CrewRole", "CrewRecord", "CharterResult",
    "PirateCrewCharter",
    "MAX_CREW_SIZE", "MAX_OFFICERS",
]
