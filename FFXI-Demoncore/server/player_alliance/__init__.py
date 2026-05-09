"""Player alliance — mutual defense pact.

A formal alliance binds 2..12 players in mutual defense. When
one member is attacked or killed by an outsider, the others
have automatic provocation: they can post bounties against
the attacker without the usual hostile_event check (the
alliance's defense pact substitutes for individual provocation).
Alliance members share a defense_pool that funds counter-
bounties on behalf of the group.

Lifecycle
    FORMING       founder created, recruiting members
    ACTIVE        at minimum size, defense pact in effect
    DISSOLVED     wound down by founder vote

Public surface
--------------
    AllianceState enum
    Alliance dataclass (frozen)
    AttackEvent dataclass (frozen)
    PlayerAllianceSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_MEMBERS = 2
_MAX_MEMBERS = 12


class AllianceState(str, enum.Enum):
    FORMING = "forming"
    ACTIVE = "active"
    DISSOLVED = "dissolved"


@dataclasses.dataclass(frozen=True)
class AttackEvent:
    event_id: str
    alliance_id: str
    victim_id: str
    attacker_id: str
    occurred_day: int


@dataclasses.dataclass(frozen=True)
class Alliance:
    alliance_id: str
    name: str
    founder_id: str
    members: tuple[str, ...]
    state: AllianceState
    defense_pool_gil: int
    formed_day: int


@dataclasses.dataclass
class PlayerAllianceSystem:
    _alliances: dict[str, Alliance] = dataclasses.field(
        default_factory=dict,
    )
    _attacks: dict[str, AttackEvent] = (
        dataclasses.field(default_factory=dict)
    )
    _next_alliance: int = 1
    _next_attack: int = 1

    def found(
        self, *, name: str, founder_id: str,
        formed_day: int,
    ) -> t.Optional[str]:
        if not name or not founder_id:
            return None
        if formed_day < 0:
            return None
        for a in self._alliances.values():
            if a.name == name:
                return None
        aid = f"all_{self._next_alliance}"
        self._next_alliance += 1
        self._alliances[aid] = Alliance(
            alliance_id=aid, name=name,
            founder_id=founder_id,
            members=(founder_id,),
            state=AllianceState.FORMING,
            defense_pool_gil=0,
            formed_day=formed_day,
        )
        return aid

    def add_member(
        self, *, alliance_id: str, member_id: str,
    ) -> bool:
        if alliance_id not in self._alliances:
            return False
        a = self._alliances[alliance_id]
        if a.state == AllianceState.DISSOLVED:
            return False
        if not member_id:
            return False
        if member_id in a.members:
            return False
        if len(a.members) >= _MAX_MEMBERS:
            return False
        new_members = a.members + (member_id,)
        new_state = a.state
        if (
            a.state == AllianceState.FORMING
            and len(new_members) >= _MIN_MEMBERS
        ):
            new_state = AllianceState.ACTIVE
        self._alliances[alliance_id] = (
            dataclasses.replace(
                a, members=new_members,
                state=new_state,
            )
        )
        return True

    def remove_member(
        self, *, alliance_id: str, member_id: str,
    ) -> bool:
        if alliance_id not in self._alliances:
            return False
        a = self._alliances[alliance_id]
        if a.state == AllianceState.DISSOLVED:
            return False
        if member_id not in a.members:
            return False
        if member_id == a.founder_id:
            return False
        new_members = tuple(
            m for m in a.members if m != member_id
        )
        new_state = a.state
        if (
            a.state == AllianceState.ACTIVE
            and len(new_members) < _MIN_MEMBERS
        ):
            new_state = AllianceState.FORMING
        self._alliances[alliance_id] = (
            dataclasses.replace(
                a, members=new_members,
                state=new_state,
            )
        )
        return True

    def contribute_to_pool(
        self, *, alliance_id: str, contributor_id: str,
        amount_gil: int,
    ) -> bool:
        if alliance_id not in self._alliances:
            return False
        a = self._alliances[alliance_id]
        if a.state != AllianceState.ACTIVE:
            return False
        if contributor_id not in a.members:
            return False
        if amount_gil <= 0:
            return False
        self._alliances[alliance_id] = (
            dataclasses.replace(
                a, defense_pool_gil=(
                    a.defense_pool_gil + amount_gil
                ),
            )
        )
        return True

    def report_attack(
        self, *, alliance_id: str, victim_id: str,
        attacker_id: str, occurred_day: int,
    ) -> t.Optional[str]:
        """Member reports being attacked. Logs the
        event for downstream provocation by other
        members. Attacker must NOT be a member.
        """
        if alliance_id not in self._alliances:
            return None
        a = self._alliances[alliance_id]
        if a.state != AllianceState.ACTIVE:
            return None
        if victim_id not in a.members:
            return None
        if attacker_id in a.members:
            return None
        if not attacker_id:
            return None
        if occurred_day < 0:
            return None
        eid = f"event_{self._next_attack}"
        self._next_attack += 1
        self._attacks[eid] = AttackEvent(
            event_id=eid, alliance_id=alliance_id,
            victim_id=victim_id,
            attacker_id=attacker_id,
            occurred_day=occurred_day,
        )
        return eid

    def has_provocation_against(
        self, *, alliance_id: str, attacker_id: str,
    ) -> bool:
        """Any member of the alliance can post
        bounties against attacker if there's an
        attack event on file."""
        if alliance_id not in self._alliances:
            return False
        for e in self._attacks.values():
            if (
                e.alliance_id == alliance_id
                and e.attacker_id == attacker_id
            ):
                return True
        return False

    def dissolve(
        self, *, alliance_id: str, founder_id: str,
    ) -> t.Optional[int]:
        if alliance_id not in self._alliances:
            return None
        a = self._alliances[alliance_id]
        if a.state == AllianceState.DISSOLVED:
            return None
        if a.founder_id != founder_id:
            return None
        final_pool = a.defense_pool_gil
        self._alliances[alliance_id] = (
            dataclasses.replace(
                a, state=AllianceState.DISSOLVED,
                defense_pool_gil=0,
            )
        )
        return final_pool

    def alliance(
        self, *, alliance_id: str,
    ) -> t.Optional[Alliance]:
        return self._alliances.get(alliance_id)

    def attacks_against(
        self, *, alliance_id: str,
    ) -> list[AttackEvent]:
        return [
            e for e in self._attacks.values()
            if e.alliance_id == alliance_id
        ]


__all__ = [
    "AllianceState", "Alliance", "AttackEvent",
    "PlayerAllianceSystem",
]
