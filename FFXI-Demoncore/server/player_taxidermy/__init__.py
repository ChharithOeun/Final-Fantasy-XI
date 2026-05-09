"""Player taxidermy — mob trophies → mounted displays.

Slay something noteworthy and you can KEEP a part of
it. Taxidermy lets a player commission (or self-craft)
a mounted display from a trophy_part. The result is a
furniture item with optional fame_signature: famous
hunters' names appear on the brass plaque.

Lifecycle per mount:
    HARVESTED       trophy part claimed from kill
    PREPARING       skinning/cleaning
    MOUNTING        building the display
    DISPLAYED       finished, ready to place

Each mount has a quality_grade derived from how fresh
the part is (degrades by tick) plus the crafter's
skill at MOUNTING time.

Public surface
--------------
    MountStage enum
    Grade enum (5 grades)
    TrophyPart dataclass (frozen)
    Mount dataclass (frozen)
    PlayerTaxidermySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MountStage(str, enum.Enum):
    HARVESTED = "harvested"
    PREPARING = "preparing"
    MOUNTING = "mounting"
    DISPLAYED = "displayed"
    RUINED = "ruined"


class Grade(str, enum.Enum):
    POOR = "poor"
    STANDARD = "standard"
    FINE = "fine"
    EXCELLENT = "excellent"
    MUSEUM = "museum"


@dataclasses.dataclass(frozen=True)
class TrophyPart:
    part_id: str
    owner_id: str
    mob_kind: str
    mob_was_named: bool  # NM kill?
    harvested_day: int
    freshness: int  # 0..100
    decayed_after_days: int


@dataclasses.dataclass(frozen=True)
class Mount:
    mount_id: str
    owner_id: str
    part_id: str
    plaque_text: str
    fame_signature: str
    stage: MountStage
    grade: t.Optional[Grade]
    started_day: int
    completed_day: t.Optional[int]


@dataclasses.dataclass
class PlayerTaxidermySystem:
    _parts: dict[str, TrophyPart] = (
        dataclasses.field(default_factory=dict)
    )
    _mounts: dict[str, Mount] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def harvest_part(
        self, *, part_id: str, owner_id: str,
        mob_kind: str, mob_was_named: bool,
        harvested_day: int,
        decayed_after_days: int = 14,
    ) -> bool:
        if not part_id or not owner_id:
            return False
        if not mob_kind:
            return False
        if harvested_day < 0:
            return False
        if decayed_after_days <= 0:
            return False
        if part_id in self._parts:
            return False
        self._parts[part_id] = TrophyPart(
            part_id=part_id, owner_id=owner_id,
            mob_kind=mob_kind,
            mob_was_named=mob_was_named,
            harvested_day=harvested_day,
            freshness=100,
            decayed_after_days=decayed_after_days,
        )
        return True

    def tick_part(
        self, *, part_id: str, now_day: int,
    ) -> int:
        """Decay freshness linearly. Returns
        current freshness."""
        if part_id not in self._parts:
            return 0
        p = self._parts[part_id]
        if now_day <= p.harvested_day:
            return p.freshness
        days_elapsed = now_day - p.harvested_day
        if days_elapsed >= p.decayed_after_days:
            new_fresh = 0
        else:
            new_fresh = max(
                0,
                100 * (
                    p.decayed_after_days
                    - days_elapsed
                ) // p.decayed_after_days,
            )
        self._parts[part_id] = dataclasses.replace(
            p, freshness=new_fresh,
        )
        return new_fresh

    def begin_mount(
        self, *, part_id: str,
        plaque_text: str,
        fame_signature: str = "",
        started_day: int,
    ) -> t.Optional[str]:
        if part_id not in self._parts:
            return None
        if not plaque_text or started_day < 0:
            return None
        p = self._parts[part_id]
        if p.freshness <= 0:
            return None
        # Each part can only be mounted once
        for m in self._mounts.values():
            if (m.part_id == part_id
                    and m.stage != MountStage.RUINED):
                return None
        mid = f"mount_{self._next_id}"
        self._next_id += 1
        self._mounts[mid] = Mount(
            mount_id=mid, owner_id=p.owner_id,
            part_id=part_id,
            plaque_text=plaque_text,
            fame_signature=fame_signature,
            stage=MountStage.PREPARING,
            grade=None, started_day=started_day,
            completed_day=None,
        )
        return mid

    def advance_to_mounting(
        self, *, mount_id: str,
    ) -> bool:
        if mount_id not in self._mounts:
            return False
        m = self._mounts[mount_id]
        if m.stage != MountStage.PREPARING:
            return False
        self._mounts[mount_id] = (
            dataclasses.replace(
                m, stage=MountStage.MOUNTING,
            )
        )
        return True

    def complete_mount(
        self, *, mount_id: str,
        crafter_skill: int, now_day: int,
    ) -> t.Optional[Grade]:
        if mount_id not in self._mounts:
            return None
        if not 0 <= crafter_skill <= 100:
            return None
        m = self._mounts[mount_id]
        if m.stage != MountStage.MOUNTING:
            return None
        p = self._parts[m.part_id]
        # Composite score: freshness + skill +
        # named-mob bonus.
        score = p.freshness + crafter_skill
        if p.mob_was_named:
            score += 30
        # Score range ~0..230. Bucket into grades.
        if score < 60:
            grade = Grade.POOR
        elif score < 110:
            grade = Grade.STANDARD
        elif score < 160:
            grade = Grade.FINE
        elif score < 200:
            grade = Grade.EXCELLENT
        else:
            grade = Grade.MUSEUM
        self._mounts[mount_id] = (
            dataclasses.replace(
                m, stage=MountStage.DISPLAYED,
                grade=grade, completed_day=now_day,
            )
        )
        return grade

    def ruin_mount(
        self, *, mount_id: str,
    ) -> bool:
        if mount_id not in self._mounts:
            return False
        m = self._mounts[mount_id]
        if m.stage in (
            MountStage.DISPLAYED,
            MountStage.RUINED,
        ):
            return False
        self._mounts[mount_id] = (
            dataclasses.replace(
                m, stage=MountStage.RUINED,
            )
        )
        return True

    def part(
        self, *, part_id: str,
    ) -> t.Optional[TrophyPart]:
        return self._parts.get(part_id)

    def mount(
        self, *, mount_id: str,
    ) -> t.Optional[Mount]:
        return self._mounts.get(mount_id)

    def mounts_of(
        self, *, owner_id: str,
    ) -> list[Mount]:
        return [
            m for m in self._mounts.values()
            if m.owner_id == owner_id
        ]

    def parts_of(
        self, *, owner_id: str,
    ) -> list[TrophyPart]:
        return [
            p for p in self._parts.values()
            if p.owner_id == owner_id
        ]


__all__ = [
    "MountStage", "Grade", "TrophyPart", "Mount",
    "PlayerTaxidermySystem",
]
