"""Job change — subjob unlock + main/sub job switching.

Player jobs split into BASIC (unlocked from creation) and EXTRA
(must complete a quest). Subjobs unlock at level 18 via "The Old
Wounds" quest. Job changes only happen in town safe zones to
prevent mid-fight cheese.

Public surface
--------------
    Job enum (~20 jobs)
    JobUnlockSpec catalog
    PlayerJobs per-character
        .complete_unlock_quest(job)
        .change_main(target_job, current_zone_is_town) -> ChangeResult
        .change_sub(target_job, current_zone_is_town)
        .can_set_subjob(level)
        .available_jobs() -> tuple
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Job(str, enum.Enum):
    # Basic jobs (available from creation)
    WARRIOR = "warrior"
    MONK = "monk"
    WHITE_MAGE = "white_mage"
    BLACK_MAGE = "black_mage"
    RED_MAGE = "red_mage"
    THIEF = "thief"
    # Extra jobs (require quest)
    PALADIN = "paladin"
    DARK_KNIGHT = "dark_knight"
    BEASTMASTER = "beastmaster"
    BARD = "bard"
    RANGER = "ranger"
    SAMURAI = "samurai"
    NINJA = "ninja"
    DRAGOON = "dragoon"
    SUMMONER = "summoner"
    BLUE_MAGE = "blue_mage"
    CORSAIR = "corsair"
    PUPPETMASTER = "puppetmaster"
    DANCER = "dancer"
    SCHOLAR = "scholar"


BASIC_JOBS: frozenset[Job] = frozenset({
    Job.WARRIOR, Job.MONK, Job.WHITE_MAGE, Job.BLACK_MAGE,
    Job.RED_MAGE, Job.THIEF,
})


@dataclasses.dataclass(frozen=True)
class JobUnlockSpec:
    job: Job
    quest_id: str
    description: str = ""


# Sample unlock quests
UNLOCK_QUESTS: dict[Job, JobUnlockSpec] = {
    Job.PALADIN: JobUnlockSpec(Job.PALADIN, "knights_test"),
    Job.DARK_KNIGHT: JobUnlockSpec(Job.DARK_KNIGHT,
                                    "blade_of_darkness"),
    Job.BEASTMASTER: JobUnlockSpec(Job.BEASTMASTER,
                                    "save_my_son"),
    Job.BARD: JobUnlockSpec(Job.BARD, "calling_card"),
    Job.RANGER: JobUnlockSpec(Job.RANGER, "bow_of_destiny"),
    Job.SAMURAI: JobUnlockSpec(Job.SAMURAI, "mirror_mirror"),
    Job.NINJA: JobUnlockSpec(Job.NINJA, "ayame_and_kaede"),
    Job.DRAGOON: JobUnlockSpec(Job.DRAGOON, "dragon_scales"),
    Job.SUMMONER: JobUnlockSpec(Job.SUMMONER, "calling_summoner"),
    Job.BLUE_MAGE: JobUnlockSpec(Job.BLUE_MAGE, "immortal_sentries"),
    Job.CORSAIR: JobUnlockSpec(Job.CORSAIR, "luck_of_the_draw"),
    Job.PUPPETMASTER: JobUnlockSpec(Job.PUPPETMASTER,
                                     "trial_size_trial"),
    Job.DANCER: JobUnlockSpec(Job.DANCER, "shall_we_dance"),
    Job.SCHOLAR: JobUnlockSpec(Job.SCHOLAR, "scholarly_pursuits"),
}


SUBJOB_UNLOCK_LEVEL = 18
SUBJOB_UNLOCK_QUEST = "the_old_wounds"


@dataclasses.dataclass(frozen=True)
class ChangeResult:
    accepted: bool
    new_main: t.Optional[Job] = None
    new_sub: t.Optional[Job] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerJobs:
    player_id: str
    main_job: Job = Job.WARRIOR
    sub_job: t.Optional[Job] = None
    subjob_unlocked: bool = False
    unlocked: set[Job] = dataclasses.field(
        default_factory=lambda: set(BASIC_JOBS),
    )

    def complete_unlock_quest(self, *, job: Job) -> bool:
        """Mark a job as unlocked. Returns True if newly unlocked."""
        if job in self.unlocked:
            return False
        if job in BASIC_JOBS:
            return False    # already unlocked from creation
        self.unlocked.add(job)
        return True

    def unlock_subjob(self, *, main_job_level: int) -> bool:
        """Complete the subjob unlock quest at level >= 18."""
        if main_job_level < SUBJOB_UNLOCK_LEVEL:
            return False
        if self.subjob_unlocked:
            return False
        self.subjob_unlocked = True
        return True

    def is_unlocked(self, job: Job) -> bool:
        return job in self.unlocked

    def available_jobs(self) -> tuple[Job, ...]:
        return tuple(sorted(self.unlocked, key=lambda j: j.value))

    def change_main(
        self, *, target_job: Job, current_zone_is_town: bool,
    ) -> ChangeResult:
        if not current_zone_is_town:
            return ChangeResult(False, reason="must be in town")
        if target_job not in self.unlocked:
            return ChangeResult(False, reason="job not unlocked")
        if target_job == self.main_job:
            return ChangeResult(False, reason="already this job")
        # Cannot have main == sub
        if target_job == self.sub_job:
            return ChangeResult(False,
                                reason="cannot main = sub")
        self.main_job = target_job
        return ChangeResult(True, new_main=target_job,
                            new_sub=self.sub_job)

    def change_sub(
        self, *, target_job: t.Optional[Job],
        current_zone_is_town: bool,
    ) -> ChangeResult:
        if not current_zone_is_town:
            return ChangeResult(False, reason="must be in town")
        if not self.subjob_unlocked:
            return ChangeResult(
                False, reason="subjob not unlocked",
            )
        if target_job is None:
            self.sub_job = None
            return ChangeResult(True, new_main=self.main_job,
                                new_sub=None)
        if target_job not in self.unlocked:
            return ChangeResult(False, reason="job not unlocked")
        if target_job == self.main_job:
            return ChangeResult(False,
                                reason="cannot sub = main")
        self.sub_job = target_job
        return ChangeResult(True, new_main=self.main_job,
                            new_sub=target_job)


__all__ = [
    "Job", "BASIC_JOBS", "JobUnlockSpec", "UNLOCK_QUESTS",
    "SUBJOB_UNLOCK_LEVEL", "SUBJOB_UNLOCK_QUEST",
    "ChangeResult", "PlayerJobs",
]
