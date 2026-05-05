"""Underwater jobs — 2 new water-themed jobs.

The underwater expansion adds two new jobs unlocked via job
quests gated behind the underwater MSQ:

  TIDEMAGE  - Water arcanist. INT/MND scaling, full water
              spell access, signature ABILITY = SUMMON_TIDE
              (AOE water damage + Slow), gear weight LIGHT.
              Subjob unlock: complete BLM 30 + Tidemage trial.
  SPEAR_DIVER - Harpoon-wielding deep-water bruiser. STR/DEX
              scaling, polearm + harpoon weapon skills,
              signature ABILITY = DEEP_PLUNGE (long-range
              charge + bleed). Subjob unlock: complete DRG 30
              + Spear-Diver trial.

Both jobs grant SWIM_MASTERY: -50% breath drain underwater
and ignore one tier of pressure damage. Max levels 99 + 50 ML
(same as canonical jobs).

Public surface
--------------
    UnderwaterJob enum
    JobProfile dataclass
    UnderwaterJobsRegistry
        .profile_for(job)
        .unlock_for(player_id, job, prereq_job_level,
                    completed_trial)
        .is_unlocked(player_id, job)
        .swim_mastery_bonus(job)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class UnderwaterJob(str, enum.Enum):
    TIDEMAGE = "tidemage"
    SPEAR_DIVER = "spear_diver"


@dataclasses.dataclass(frozen=True)
class JobProfile:
    job: UnderwaterJob
    primary_stat: str
    secondary_stat: str
    weapon_kinds: tuple[str, ...]
    signature_ability: str
    prereq_job: str
    prereq_level: int
    trial_id: str
    grants_swim_mastery: bool = True


_PROFILES: dict[UnderwaterJob, JobProfile] = {
    UnderwaterJob.TIDEMAGE: JobProfile(
        job=UnderwaterJob.TIDEMAGE,
        primary_stat="INT",
        secondary_stat="MND",
        weapon_kinds=("staff", "club"),
        signature_ability="summon_tide",
        prereq_job="BLM",
        prereq_level=30,
        trial_id="tidemage_initiation",
    ),
    UnderwaterJob.SPEAR_DIVER: JobProfile(
        job=UnderwaterJob.SPEAR_DIVER,
        primary_stat="STR",
        secondary_stat="DEX",
        weapon_kinds=("polearm", "harpoon"),
        signature_ability="deep_plunge",
        prereq_job="DRG",
        prereq_level=30,
        trial_id="spear_diver_initiation",
    ),
}


@dataclasses.dataclass(frozen=True)
class UnlockResult:
    accepted: bool
    job: UnderwaterJob
    reason: t.Optional[str] = None


@dataclasses.dataclass
class UnderwaterJobsRegistry:
    _unlocked: dict[
        str, set[UnderwaterJob],
    ] = dataclasses.field(default_factory=dict)

    def profile_for(
        self, *, job: UnderwaterJob,
    ) -> t.Optional[JobProfile]:
        return _PROFILES.get(job)

    def unlock_for(
        self, *, player_id: str,
        job: UnderwaterJob,
        prereq_job: str,
        prereq_level: int,
        completed_trial_id: str,
    ) -> UnlockResult:
        prof = _PROFILES.get(job)
        if prof is None:
            return UnlockResult(
                False, job, reason="unknown job",
            )
        if prereq_job != prof.prereq_job:
            return UnlockResult(
                False, job, reason="wrong prerequisite job",
            )
        if prereq_level < prof.prereq_level:
            return UnlockResult(
                False, job, reason="prereq level too low",
            )
        if completed_trial_id != prof.trial_id:
            return UnlockResult(
                False, job, reason="trial not completed",
            )
        roster = self._unlocked.setdefault(player_id, set())
        if job in roster:
            return UnlockResult(
                False, job, reason="already unlocked",
            )
        roster.add(job)
        return UnlockResult(accepted=True, job=job)

    def is_unlocked(
        self, *, player_id: str, job: UnderwaterJob,
    ) -> bool:
        return job in self._unlocked.get(player_id, set())

    def swim_mastery_bonus(
        self, *, job: UnderwaterJob,
    ) -> dict[str, t.Any]:
        prof = _PROFILES.get(job)
        if prof is None or not prof.grants_swim_mastery:
            return {
                "breath_drain_pct": 0,
                "pressure_tier_skip": 0,
            }
        return {
            "breath_drain_pct": -50,
            "pressure_tier_skip": 1,
        }

    def total_jobs(self) -> int:
        return len(_PROFILES)


__all__ = [
    "UnderwaterJob", "JobProfile",
    "UnlockResult",
    "UnderwaterJobsRegistry",
]
