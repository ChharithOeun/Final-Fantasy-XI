"""/check command — vague descriptors per the doc.

Per VISUAL_HEALTH_SYSTEM.md the /check returns three reads:
    - level descriptor (Easy Prey / Decent / Tough / etc.)
    - mood read           (seems content / agitated / furious)
    - damage read         (unharmed / slightly hurt / badly wounded)

No numbers, ever.

The level-difference math is canonical FFXI bracket-based:
    +5 levels ahead    -> 'Incredibly Tough'
    +3 to +5           -> 'Very Tough'
    +1 to +2           -> 'Tough'
    -2 to 0            -> 'Decent Challenge'
    -5 to -3           -> 'Easy Prey'
    < -5               -> 'Too Weak To Be Worthwhile'
    flag override      -> 'Impossible to Gauge' (NMs/HNMs)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .damage_stages import DamageStage, stage_for_check_descriptor


class LevelDescriptor(str, enum.Enum):
    TOO_WEAK = "Too Weak To Be Worthwhile"
    EASY_PREY = "Easy Prey"
    DECENT_CHALLENGE = "Decent Challenge"
    TOUGH = "Tough"
    VERY_TOUGH = "Very Tough"
    INCREDIBLY_TOUGH = "Incredibly Tough"
    IMPOSSIBLE_TO_GAUGE = "Impossible to Gauge"


def level_descriptor_for(player_level: int,
                            target_level: int,
                            *,
                            impossible_to_gauge: bool = False
                            ) -> LevelDescriptor:
    """Resolve the FFXI-canonical level-bracket label.

    `impossible_to_gauge=True` is the NM / HNM override the doc
    explicitly carves out.
    """
    if impossible_to_gauge:
        return LevelDescriptor.IMPOSSIBLE_TO_GAUGE
    diff = target_level - player_level
    if diff >= 5:
        return LevelDescriptor.INCREDIBLY_TOUGH
    if diff >= 3:
        return LevelDescriptor.VERY_TOUGH
    if diff >= 1:
        return LevelDescriptor.TOUGH
    if diff >= -2:
        return LevelDescriptor.DECENT_CHALLENGE
    if diff >= -5:
        return LevelDescriptor.EASY_PREY
    return LevelDescriptor.TOO_WEAK


# Mood -> /check descriptor mapping. Mood module owns the source of
# truth for what a mood vector looks like; we just expose the labels
# the /check returns for the three most legible mood states.
MOOD_DESCRIPTOR: dict[str, str] = {
    "content": "(seems content)",
    "agitated": "(seems agitated)",
    "furious": "(looks furious)",
    "fearful": "(looks frightened)",
    "alert": "(looks alert)",
    "weary": "(seems weary)",
    "mischievous": "(seems amused)",
    "contemplative": "(seems thoughtful)",
}


def mood_descriptor_for(mood_label: str) -> str:
    """Doc /check mood read. Falls back to (seems content) for any
    unknown label so the response always renders."""
    return MOOD_DESCRIPTOR.get(mood_label, "(seems content)")


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """The full /check return per the doc."""
    level_descriptor: LevelDescriptor
    mood_descriptor: str
    damage_descriptor: str

    def render(self) -> str:
        """Produce the player-visible sentence."""
        return (f"{self.level_descriptor.value} "
                  f"{self.mood_descriptor} "
                  f"({self.damage_descriptor})")


def perform_check(*,
                     player_level: int,
                     target_level: int,
                     mood_label: str,
                     damage_stage: DamageStage,
                     impossible_to_gauge: bool = False
                     ) -> CheckResult:
    """Compose all three /check reads into one CheckResult."""
    return CheckResult(
        level_descriptor=level_descriptor_for(
            player_level, target_level,
            impossible_to_gauge=impossible_to_gauge),
        mood_descriptor=mood_descriptor_for(mood_label),
        damage_descriptor=stage_for_check_descriptor(damage_stage),
    )
