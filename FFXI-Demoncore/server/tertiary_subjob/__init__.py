"""Tertiary subjob — third subjob unlocked via 'The Threefold Path'.

Demoncore extension to canonical FFXI's main + sub job model: a
third subjob slot. Unlocked through "The Threefold Path" quest at
main level 50.

Tertiary level = floor(min(main, CLASSIC_LEVEL_CAP) / 2). The
clamp at the classic 99 cap is deliberate: at master levels
(100-150) the SECONDARY subjob continues to scale (a lvl-150
main has a lvl-75 sub), but the TERTIARY stays bounded at 49.

Why: a triple-class build at lvl 150 with three full half-mains
would dominate everything. Holding tertiary at 49 keeps it as
a meaningful utility slot — self-Cure I-II, Sneak/Invis, basic
Utsusemi — without making it a third primary. The strategic
depth lives in *which* tertiary you pick, not in raw power.

Example loadout: RDM/NIN/DNC at lvl 150
    main      = RDM 150
    secondary = NIN 75   (main / 2)
    tertiary  = DNC 49   (min(main, 99) / 2)

Public surface
--------------
    TERTIARY_UNLOCK_QUEST_ID
    TERTIARY_MIN_MAIN_LEVEL
    CLASSIC_LEVEL_CAP, MAX_TERTIARY_LEVEL
    tertiary_level_for(main_level) -> int
    PlayerTertiarySubjob ...
"""
from __future__ import annotations

import dataclasses
import typing as t


# Quest the player must complete to unlock the third subjob slot.
TERTIARY_UNLOCK_QUEST_ID = "the_threefold_path"

# Main job level required to begin the unlock quest. Pinned to 50
# so tertiary opens up alongside the post-Genkai endgame curve.
TERTIARY_MIN_MAIN_LEVEL = 50

# The classic-cap we clamp tertiary at. Master Levels (100-150)
# don't grow the tertiary beyond floor(99 / 2) = 49.
CLASSIC_LEVEL_CAP = 99
MAX_TERTIARY_LEVEL = CLASSIC_LEVEL_CAP // 2   # 49


def tertiary_level_for(*, main_job_level: int) -> int:
    """Tertiary subjob level = floor(min(main, 99) / 2).

    Clamped at >= 1 once the slot is filled, and clamped at
    MAX_TERTIARY_LEVEL (49) regardless of master-level main."""
    clamped_main = min(main_job_level, CLASSIC_LEVEL_CAP)
    if clamped_main < 2:
        return 1
    return clamped_main // 2


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
    "CLASSIC_LEVEL_CAP", "MAX_TERTIARY_LEVEL",
    "tertiary_level_for",
    "SetResult", "PlayerTertiarySubjob",
]
