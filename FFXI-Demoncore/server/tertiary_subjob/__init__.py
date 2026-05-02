"""Tertiary subjob — third subjob unlocked via 'The Threefold Path'.

Demoncore extension to canonical FFXI's main + sub job model: a
third subjob slot. Unlocked through "The Threefold Path" quest at
main level 50. The tertiary subjob is always capped at floor(main /
2) — half the main job's level — which keeps it tactical instead
of overpowered. Strategic builds get more flexibility (e.g. WAR/
NIN/WHM for self-Cure on a tank) without trivializing content.

Public surface
--------------
    TERTIARY_UNLOCK_QUEST_ID
    TERTIARY_MIN_MAIN_LEVEL
    tertiary_level_for(main_level) -> int
    PlayerTertiarySubjob
        .complete_unlock_quest(main_level)
        .set_tertiary(job, current_zone_is_town,
                      main_job, secondary_subjob, available_jobs)
        .clear()
"""
from __future__ import annotations

import dataclasses
import typing as t


# Quest the player must complete to unlock the third subjob slot.
TERTIARY_UNLOCK_QUEST_ID = "the_threefold_path"

# Main job level required to begin the unlock quest. Pinned to 50
# so tertiary opens up alongside the post-Genkai endgame curve.
TERTIARY_MIN_MAIN_LEVEL = 50


def tertiary_level_for(*, main_job_level: int) -> int:
    """Tertiary subjob level = floor(main_job_level / 2).

    Always clamped at >= 1 once the slot is filled."""
    if main_job_level < 2:
        return 1
    return main_job_level // 2


@dataclasses.dataclass(frozen=True)
class SetResult:
    accepted: bool
    new_tertiary: t.Optional[str] = None
    tertiary_level: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerTertiarySubjob:
    """Per-character tertiary subjob slot state."""
    player_id: str
    unlocked: bool = False
    tertiary_job: t.Optional[str] = None

    def complete_unlock_quest(
        self, *, main_job_level: int,
    ) -> bool:
        """Mark the slot as unlocked. Returns True iff state changed."""
        if self.unlocked:
            return False
        if main_job_level < TERTIARY_MIN_MAIN_LEVEL:
            return False
        self.unlocked = True
        return True

    def set_tertiary(
        self, *,
        target_job: t.Optional[str],
        current_zone_is_town: bool,
        main_job: str,
        secondary_subjob: t.Optional[str],
        available_jobs: t.Iterable[str],
        main_job_level: int,
    ) -> SetResult:
        """Set or clear the tertiary slot.

        Rules:
          - Slot must be unlocked.
          - Must be in town to swap.
          - target_job=None clears the slot.
          - target_job must be in `available_jobs` (the player's
            unlocked job list — same list job_change uses).
          - Cannot equal main_job or secondary_subjob.
        """
        if not self.unlocked:
            return SetResult(False, reason="tertiary slot locked")
        if not current_zone_is_town:
            return SetResult(False, reason="must be in town")
        if target_job is None:
            self.tertiary_job = None
            return SetResult(True, new_tertiary=None,
                             tertiary_level=0)
        if target_job not in set(available_jobs):
            return SetResult(False, reason="job not unlocked")
        if target_job == main_job:
            return SetResult(False,
                             reason="cannot tertiary = main job")
        if secondary_subjob is not None and \
                target_job == secondary_subjob:
            return SetResult(False,
                             reason="cannot tertiary = secondary sub")
        self.tertiary_job = target_job
        return SetResult(
            True, new_tertiary=target_job,
            tertiary_level=tertiary_level_for(
                main_job_level=main_job_level,
            ),
        )

    def clear(self) -> bool:
        if self.tertiary_job is None:
            return False
        self.tertiary_job = None
        return True

    def effective_level(
        self, *, main_job_level: int,
    ) -> int:
        """Current tertiary level given the main job level. 0 if
        slot is empty."""
        if self.tertiary_job is None:
            return 0
        return tertiary_level_for(main_job_level=main_job_level)


__all__ = [
    "TERTIARY_UNLOCK_QUEST_ID", "TERTIARY_MIN_MAIN_LEVEL",
    "tertiary_level_for",
    "SetResult", "PlayerTertiarySubjob",
]
