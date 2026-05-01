"""PlayerProgressionState — combined per-character progression bundle.

Composes the three axes into one dataclass so the orchestrator + UI
have a single object to query. Persistence is the caller's job.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .skill_mastery import SkillMasteryTracker


@dataclasses.dataclass
class PlayerProgressionState:
    """Per-character progression snapshot."""
    actor_id: str
    job: str = "WAR"
    sub_job: t.Optional[str] = None
    job_level: int = 1
    sub_job_level: int = 0
    masteries: SkillMasteryTracker = dataclasses.field(
        default_factory=SkillMasteryTracker)
    genkais_passed: set[int] = dataclasses.field(default_factory=set)
    # Tutorials the player has completed. The orchestrator pops new
    # tutorials off `unlock_cadence.newly_unlocked_at(level)` on
    # level-up and adds them here as the player completes them.
    tutorials_completed: set[str] = dataclasses.field(default_factory=set)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def has_completed(self, tutorial_id: str) -> bool:
        return tutorial_id in self.tutorials_completed

    def mark_tutorial_complete(self, tutorial_id: str) -> None:
        self.tutorials_completed.add(tutorial_id)

    def has_passed_genkai(self, genkai_level: int) -> bool:
        return genkai_level in self.genkais_passed

    def effective_level_cap(self, *, base_cap: int = 50) -> int:
        """Resolve the current level cap from the Genkais the player
        has passed."""
        from .genkai import GENKAI_TESTS
        cap = base_cap
        for level in sorted(GENKAI_TESTS.keys()):
            if level in self.genkais_passed:
                cap = GENKAI_TESTS[level].next_level_cap
        return cap

    def is_endgame(self) -> bool:
        """Endgame defined as lvl 75+ per the cadence (BCNM/Limbus
        unlock at 75)."""
        return self.job_level >= 75

    def is_apex(self) -> bool:
        """Apex = lvl 99 with permadeath active."""
        return self.job_level >= 99
