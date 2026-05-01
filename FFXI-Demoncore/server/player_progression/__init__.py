"""Player progression — 3-axis growth, skill mastery, unlock cadence, Genkai.

Per PLAYER_PROGRESSION.md the player-side mirror of NPC_PROGRESSION:
    Axis 1: Job Level 1-99 (vanilla FFXI; permadeath at 99 per HARDCORE_DEATH)
    Axis 2: Skill Mastery 0-5 per skill (NEW — tied to character, not gear)
    Axis 3: Reputation + Honor (per honor_reputation module)

Plus the unlock cadence: 21 system-introduction checkpoints from lvl
1 (visual health + weight) through lvl 99 (permadeath active). Each
unlock is preceded by a tutorial NPC encounter so players don't drown.

Plus Genkai (limit-break) tests: 5 forced-solo rite-of-passage fights
at lvl 50/55/60/65/70 — Maat at 50 + 70, NMs in between. No party
allowed; pure test of mastery.

Public surface:
    SkillFamily, SkillMastery, SkillMasteryTracker
    MASTERY_XP_THRESHOLDS, MASTERY_XP_AWARDS, MASTERY_5_PERKS
    UNLOCK_CADENCE, system_unlocked, newly_unlocked_at, all_unlocked_up_to
    GenkaiTest, GENKAI_TESTS, GenkaiTestManager
    PlayerProgressionState
"""
from .genkai import (
    GENKAI_TESTS,
    GenkaiTest,
    GenkaiTestManager,
)
from .skill_mastery import (
    MASTERY_5_PERKS,
    MASTERY_XP_AWARDS,
    MASTERY_XP_THRESHOLDS,
    SkillFamily,
    SkillMastery,
    SkillMasteryTracker,
)
from .state import (
    PlayerProgressionState,
)
from .unlock_cadence import (
    UNLOCK_CADENCE,
    all_unlocked_up_to,
    newly_unlocked_at,
    system_unlocked,
)

__all__ = [
    # Skill mastery
    "SkillFamily",
    "SkillMastery",
    "SkillMasteryTracker",
    "MASTERY_XP_THRESHOLDS",
    "MASTERY_XP_AWARDS",
    "MASTERY_5_PERKS",
    # Unlock cadence
    "UNLOCK_CADENCE",
    "system_unlocked",
    "newly_unlocked_at",
    "all_unlocked_up_to",
    # Genkai
    "GenkaiTest",
    "GENKAI_TESTS",
    "GenkaiTestManager",
    # State
    "PlayerProgressionState",
]
