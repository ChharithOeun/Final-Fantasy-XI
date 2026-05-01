"""Fomor snapshot — captured at 1-hour timer expiry.

Per HARDCORE_DEATH.md the snapshot freezes:
    - appearance (race / face / hair / gear / dye)
    - all jobs + levels
    - all sub-skills
    - merits + JP totals
    - name (preserved)

This dataclass is server-authoritative truth. The fomor instance
the orchestrator drives reads from this snapshot to decide combat
behavior, gear drops, voice, etc.
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class Appearance:
    race: str
    face_id: str
    hair_id: str
    eye_id: str
    skin_id: str
    dye_id: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class JobLevel:
    """One job + level entry. main_job tag indicates which is current."""
    job: str
    level: int
    is_main: bool = False
    is_sub: bool = False


@dataclasses.dataclass(frozen=True)
class GearPiece:
    slot: str                       # 'head' / 'body' / 'main_hand' etc.
    item_id: str
    rarity: str = "common"          # 'common' / 'rare' / 'ex' / 'relic'
                                       # / 'empyrean' / 'mythic'
    quality_tier: int = 0           # 0..4 per fomor_gear lineage


@dataclasses.dataclass(frozen=True)
class FomorSnapshot:
    """The frozen state of a fallen player at fomor conversion time."""
    char_id: str
    name: str                       # preserved per doc
    appearance: Appearance
    jobs: tuple[JobLevel, ...]
    sub_skills: tuple[str, ...]     # named non-job skills
    merit_points: int
    job_points: int
    gear: tuple[GearPiece, ...]
    snapshotted_at: float
    death_zone_id: str

    @property
    def main_job(self) -> t.Optional[JobLevel]:
        for j in self.jobs:
            if j.is_main:
                return j
        return None

    @property
    def sub_job(self) -> t.Optional[JobLevel]:
        for j in self.jobs:
            if j.is_sub:
                return j
        return None

    @property
    def main_level(self) -> int:
        m = self.main_job
        return m.level if m is not None else 0


def take_snapshot(*,
                      char_id: str,
                      name: str,
                      appearance: Appearance,
                      jobs: t.Iterable[JobLevel],
                      sub_skills: t.Iterable[str],
                      merit_points: int,
                      job_points: int,
                      gear: t.Iterable[GearPiece],
                      death_zone_id: str,
                      now: float
                      ) -> FomorSnapshot:
    """Construct a snapshot. Light validation — main_job must exist."""
    jobs_tuple = tuple(jobs)
    if not any(j.is_main for j in jobs_tuple):
        raise ValueError(
            f"snapshot for {char_id} has no main_job marked")
    if merit_points < 0 or job_points < 0:
        raise ValueError("merit/job points must be non-negative")
    return FomorSnapshot(
        char_id=char_id, name=name,
        appearance=appearance,
        jobs=jobs_tuple,
        sub_skills=tuple(sub_skills),
        merit_points=merit_points,
        job_points=job_points,
        gear=tuple(gear),
        snapshotted_at=now,
        death_zone_id=death_zone_id,
    )
