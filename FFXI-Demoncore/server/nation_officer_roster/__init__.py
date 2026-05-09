"""Nation officer roster — named officers with stats.

Inspired by Romance of the Three Kingdoms II: every
nation maintains a roster of NAMED OFFICERS — heroic
NPCs with five stats and a current ASSIGNMENT. They
command nation_army units, captain nation_navy ships,
run nation_intelligence operations, and sit on the
advisory council. An officer who's KIA, captured, or
has defected is removed from the active roster.

Five canonical stats (each 1..100):
    martial         physical combat ability
    intellect       strategy / spell power
    leadership      morale / unit cohesion
    charisma        recruit + persuade
    loyalty         resistance to defection

Each stat is treated separately by callers; the roster
just stores them. The system also tracks ASSIGNMENT
(what the officer is currently doing) and STATUS (alive,
captured, retired, deceased). An officer is uniquely
identified across nations — defections move them, they
don't get re-created.

Public surface
--------------
    OfficerStatus enum
    Assignment enum
    OfficerStats dataclass (frozen)
    Officer dataclass (frozen)
    NationOfficerRosterSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class OfficerStatus(str, enum.Enum):
    ACTIVE = "active"
    CAPTURED = "captured"
    RETIRED = "retired"
    DECEASED = "deceased"


class Assignment(str, enum.Enum):
    UNASSIGNED = "unassigned"
    ARMY_COMMAND = "army_command"
    NAVY_COMMAND = "navy_command"
    INTEL = "intel"
    GOVERNOR = "governor"
    COUNCIL = "council"
    GUARD = "guard"
    AT_LIBERTY = "at_liberty"


@dataclasses.dataclass(frozen=True)
class OfficerStats:
    martial: int
    intellect: int
    leadership: int
    charisma: int
    loyalty: int


@dataclasses.dataclass(frozen=True)
class Officer:
    officer_id: str
    name: str
    nation_id: str
    stats: OfficerStats
    assignment: Assignment
    age: int
    enlisted_day: int
    status: OfficerStatus
    last_status_day: t.Optional[int]


def _validate_stat(v: int) -> bool:
    return 1 <= v <= 100


@dataclasses.dataclass
class NationOfficerRosterSystem:
    _officers: dict[str, Officer] = dataclasses.field(
        default_factory=dict,
    )

    def enlist(
        self, *, officer_id: str, name: str,
        nation_id: str, stats: OfficerStats,
        age: int, enlisted_day: int,
    ) -> bool:
        if not officer_id or not name:
            return False
        if not nation_id:
            return False
        if age < 1 or enlisted_day < 0:
            return False
        for v in (
            stats.martial, stats.intellect,
            stats.leadership, stats.charisma,
            stats.loyalty,
        ):
            if not _validate_stat(v):
                return False
        if officer_id in self._officers:
            return False
        self._officers[officer_id] = Officer(
            officer_id=officer_id, name=name,
            nation_id=nation_id, stats=stats,
            assignment=Assignment.UNASSIGNED,
            age=age, enlisted_day=enlisted_day,
            status=OfficerStatus.ACTIVE,
            last_status_day=None,
        )
        return True

    def assign(
        self, *, officer_id: str,
        assignment: Assignment,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status != OfficerStatus.ACTIVE:
            return False
        self._officers[officer_id] = (
            dataclasses.replace(o, assignment=assignment)
        )
        return True

    def adjust_loyalty(
        self, *, officer_id: str, delta: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status != OfficerStatus.ACTIVE:
            return False
        new_loy = max(1, min(100, o.stats.loyalty + delta))
        new_stats = dataclasses.replace(
            o.stats, loyalty=new_loy,
        )
        self._officers[officer_id] = (
            dataclasses.replace(o, stats=new_stats)
        )
        return True

    def transfer_nation(
        self, *, officer_id: str,
        new_nation: str,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        if not new_nation:
            return False
        o = self._officers[officer_id]
        if o.status != OfficerStatus.ACTIVE:
            return False
        if o.nation_id == new_nation:
            return False
        self._officers[officer_id] = (
            dataclasses.replace(
                o, nation_id=new_nation,
                assignment=Assignment.UNASSIGNED,
            )
        )
        return True

    def capture(
        self, *, officer_id: str, now_day: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status != OfficerStatus.ACTIVE:
            return False
        self._officers[officer_id] = (
            dataclasses.replace(
                o, status=OfficerStatus.CAPTURED,
                assignment=Assignment.UNASSIGNED,
                last_status_day=now_day,
            )
        )
        return True

    def release(
        self, *, officer_id: str, now_day: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status != OfficerStatus.CAPTURED:
            return False
        self._officers[officer_id] = (
            dataclasses.replace(
                o, status=OfficerStatus.ACTIVE,
                last_status_day=now_day,
            )
        )
        return True

    def retire(
        self, *, officer_id: str, now_day: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status not in (
            OfficerStatus.ACTIVE,
            OfficerStatus.CAPTURED,
        ):
            return False
        self._officers[officer_id] = (
            dataclasses.replace(
                o, status=OfficerStatus.RETIRED,
                assignment=Assignment.UNASSIGNED,
                last_status_day=now_day,
            )
        )
        return True

    def kill(
        self, *, officer_id: str, now_day: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status == OfficerStatus.DECEASED:
            return False
        self._officers[officer_id] = (
            dataclasses.replace(
                o, status=OfficerStatus.DECEASED,
                assignment=Assignment.UNASSIGNED,
                last_status_day=now_day,
            )
        )
        return True

    def officer(
        self, *, officer_id: str,
    ) -> t.Optional[Officer]:
        return self._officers.get(officer_id)

    def roster_for(
        self, *, nation_id: str,
    ) -> list[Officer]:
        return [
            o for o in self._officers.values()
            if (o.nation_id == nation_id
                and o.status == OfficerStatus.ACTIVE)
        ]

    def by_assignment(
        self, *, nation_id: str,
        assignment: Assignment,
    ) -> list[Officer]:
        return [
            o for o in self._officers.values()
            if (o.nation_id == nation_id
                and o.status == OfficerStatus.ACTIVE
                and o.assignment == assignment)
        ]

    def top_by(
        self, *, nation_id: str, stat: str,
        limit: int,
    ) -> list[Officer]:
        if limit <= 0:
            return []
        if stat not in (
            "martial", "intellect", "leadership",
            "charisma", "loyalty",
        ):
            return []
        ros = self.roster_for(nation_id=nation_id)
        return sorted(
            ros, key=lambda o: -getattr(o.stats, stat),
        )[:limit]


__all__ = [
    "OfficerStatus", "Assignment", "OfficerStats",
    "Officer", "NationOfficerRosterSystem",
]
