"""Shot list — production-side shooting schedule.

The Production Strip Board in code. Each row is one shot
the crew has to capture: slate, lens, location, time-of-
day, talent, props, vfx flags, audio flags, mocap flags,
expected setup minutes, and current status. The system
groups shots by location and time-of-day to minimise crew
moves, builds per-day call sheets, aggregates equipment
pull lists, and walks dependency graphs to surface the
critical path through the shoot.

Public surface
--------------
    ShotStatus enum
    TimeOfDay enum
    ShotRow dataclass (frozen)
    CallSheet dataclass (frozen)
    EquipmentPull dataclass (frozen)
    ShotListSystem
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import typing as t


class ShotStatus(enum.Enum):
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    SHOT = "shot"
    HOLDS = "holds"          # captured but quality-flagged
    OMITTED = "omitted"


class TimeOfDay(enum.Enum):
    DAWN = "dawn"
    DAY = "day"
    GOLDEN_HOUR = "golden_hour"
    DUSK = "dusk"
    NIGHT = "night"
    MAGIC_HOUR = "magic_hour"


@dataclasses.dataclass(frozen=True)
class ShotRow:
    shot_id: str
    scene_id: str
    slate: str                       # e.g. "37A", "12B-2"
    description: str
    lens_mm: float
    location: str
    time_of_day: TimeOfDay
    talent_ids: tuple[str, ...]
    props_required: tuple[str, ...] = ()
    vfx_required: bool = False
    audio_required: bool = True
    mocap_required: bool = False
    expected_setup_minutes: int = 30
    status: ShotStatus = ShotStatus.PLANNED
    shoot_date: t.Optional[dt.date] = None
    depends_on: tuple[str, ...] = ()  # shot_ids this one needs


@dataclasses.dataclass(frozen=True)
class CallSheet:
    shoot_date: dt.date
    location_groups: tuple[tuple[str, tuple[str, ...]], ...]
    talent_required: tuple[str, ...]
    total_setup_minutes: int


@dataclasses.dataclass(frozen=True)
class EquipmentPull:
    lenses_mm: tuple[float, ...]
    needs_audio: bool
    needs_vfx: bool
    needs_mocap: bool
    location_count: int


@dataclasses.dataclass
class ShotListSystem:
    _shots: dict[str, ShotRow] = dataclasses.field(
        default_factory=dict,
    )

    def register_shot(self, row: ShotRow) -> ShotRow:
        if row.shot_id in self._shots:
            raise ValueError(
                f"shot_id already registered: {row.shot_id}",
            )
        if row.lens_mm <= 0:
            raise ValueError(
                f"lens_mm must be > 0: {row.lens_mm}",
            )
        if row.expected_setup_minutes < 0:
            raise ValueError(
                f"expected_setup_minutes must be >= 0: "
                f"{row.expected_setup_minutes}",
            )
        if not row.slate:
            raise ValueError("slate required")
        for dep in row.depends_on:
            if dep == row.shot_id:
                raise ValueError(
                    f"shot {row.shot_id} cannot depend on itself",
                )
        self._shots[row.shot_id] = row
        return row

    def lookup(self, shot_id: str) -> ShotRow:
        if shot_id not in self._shots:
            raise KeyError(f"unknown shot_id: {shot_id}")
        return self._shots[shot_id]

    def all_shots(self) -> tuple[ShotRow, ...]:
        return tuple(self._shots.values())

    def shots_for_scene(self, scene_id: str) -> tuple[ShotRow, ...]:
        return tuple(
            r for r in self._shots.values() if r.scene_id == scene_id
        )

    def group_by_location(self) -> dict[str, tuple[ShotRow, ...]]:
        out: dict[str, list[ShotRow]] = {}
        for row in self._shots.values():
            out.setdefault(row.location, []).append(row)
        return {k: tuple(v) for k, v in out.items()}

    def group_by_time_of_day(
        self,
    ) -> dict[TimeOfDay, tuple[ShotRow, ...]]:
        out: dict[TimeOfDay, list[ShotRow]] = {}
        for row in self._shots.values():
            out.setdefault(row.time_of_day, []).append(row)
        return {k: tuple(v) for k, v in out.items()}

    def shots_for_talent(self, talent_id: str) -> tuple[ShotRow, ...]:
        return tuple(
            r for r in self._shots.values()
            if talent_id in r.talent_ids
        )

    def shots_for_date(self, date: dt.date) -> tuple[ShotRow, ...]:
        return tuple(
            r for r in self._shots.values() if r.shoot_date == date
        )

    def call_sheet_for(self, date: dt.date) -> CallSheet:
        shots = self.shots_for_date(date)
        loc_map: dict[str, list[str]] = {}
        talent: set[str] = set()
        total_setup = 0
        for r in shots:
            loc_map.setdefault(r.location, []).append(r.shot_id)
            for t_id in r.talent_ids:
                talent.add(t_id)
            total_setup += r.expected_setup_minutes
        loc_groups = tuple(
            (loc, tuple(ids)) for loc, ids in sorted(loc_map.items())
        )
        return CallSheet(
            shoot_date=date,
            location_groups=loc_groups,
            talent_required=tuple(sorted(talent)),
            total_setup_minutes=total_setup,
        )

    def equipment_pull_list(
        self, scene_ids: t.Optional[t.Sequence[str]] = None,
    ) -> EquipmentPull:
        if scene_ids is None:
            rows = tuple(self._shots.values())
        else:
            rows = tuple(
                r for r in self._shots.values()
                if r.scene_id in set(scene_ids)
            )
        lenses: set[float] = set()
        needs_audio = False
        needs_vfx = False
        needs_mocap = False
        locations: set[str] = set()
        for r in rows:
            lenses.add(r.lens_mm)
            if r.audio_required:
                needs_audio = True
            if r.vfx_required:
                needs_vfx = True
            if r.mocap_required:
                needs_mocap = True
            locations.add(r.location)
        return EquipmentPull(
            lenses_mm=tuple(sorted(lenses)),
            needs_audio=needs_audio,
            needs_vfx=needs_vfx,
            needs_mocap=needs_mocap,
            location_count=len(locations),
        )

    def mark_status(
        self, shot_id: str, status: ShotStatus,
    ) -> ShotRow:
        row = self.lookup(shot_id)
        new_row = dataclasses.replace(row, status=status)
        self._shots[shot_id] = new_row
        return new_row

    def assign_date(
        self, shot_id: str, date: dt.date,
    ) -> ShotRow:
        row = self.lookup(shot_id)
        new_row = dataclasses.replace(
            row, shoot_date=date, status=ShotStatus.SCHEDULED,
        )
        self._shots[shot_id] = new_row
        return new_row

    def critical_path(self) -> tuple[str, ...]:
        """Walk depends_on edges; return shots that block the
        most downstream shots, ordered by descending block-count.
        """
        # Build reverse graph: shot -> shots that depend on it.
        downstream: dict[str, set[str]] = {
            s: set() for s in self._shots
        }
        for s_id, row in self._shots.items():
            for dep in row.depends_on:
                if dep in downstream:
                    downstream[dep].add(s_id)
        # Transitive closure — count everything reachable.
        def _reach(start: str) -> set[str]:
            seen: set[str] = set()
            stack = [start]
            while stack:
                cur = stack.pop()
                for nxt in downstream.get(cur, set()):
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
            return seen

        scored = [
            (s_id, len(_reach(s_id))) for s_id in self._shots
        ]
        scored.sort(key=lambda it: (-it[1], it[0]))
        # Drop terminal shots (block 0 things) — they are
        # not on the critical path by definition.
        return tuple(s for s, n in scored if n > 0)

    def shots_by_status(
        self, status: ShotStatus,
    ) -> tuple[ShotRow, ...]:
        return tuple(
            r for r in self._shots.values() if r.status == status
        )

    def completion_percent(self) -> float:
        if not self._shots:
            return 0.0
        done = sum(
            1 for r in self._shots.values()
            if r.status in (ShotStatus.SHOT, ShotStatus.OMITTED)
        )
        return round(100.0 * done / len(self._shots), 2)


__all__ = [
    "ShotStatus", "TimeOfDay",
    "ShotRow", "CallSheet", "EquipmentPull",
    "ShotListSystem",
]
