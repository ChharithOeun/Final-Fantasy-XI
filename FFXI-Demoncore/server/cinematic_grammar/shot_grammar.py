"""5-shot grammar from CINEMATIC_GRAMMAR.md.

Every Demoncore cutscene uses one of five shot types:
    ESTABLISHING (4-6s) - wide; slow dolly-in; music swells
    HERO_ENTRY   (3-5s) - low-angle; tracks boss silhouette
    EXCHANGE     (5-8s) - chest-level two-shot; held; voice line
    CHAOS        (var)  - handheld; tracks combat; off-balance
    AFTERMATH    (8-12s)- slow tracking glide across the field

Camera operators learn the language and execute it the same way
every time. Editor stitches takes together in Sequencer.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ShotType(str, enum.Enum):
    ESTABLISHING = "establishing"
    HERO_ENTRY = "hero_entry"
    EXCHANGE = "exchange"
    CHAOS = "chaos"
    AFTERMATH = "aftermath"


@dataclasses.dataclass(frozen=True)
class ShotProfile:
    """One row of the 5-shot table."""
    shot_type: ShotType
    min_duration_s: float
    max_duration_s: float
    camera_motion: str
    camera_height: str            # 'low_angle' | 'chest_level' | 'wide' | etc.
    music_behavior: str
    is_handheld: bool
    use_cases: tuple[str, ...]


SHOT_PROFILES: dict[ShotType, ShotProfile] = {
    ShotType.ESTABLISHING: ShotProfile(
        shot_type=ShotType.ESTABLISHING,
        min_duration_s=4.0, max_duration_s=6.0,
        camera_motion="slow_dolly_in",
        camera_height="wide",
        music_behavior="swell",
        is_handheld=True,
        use_cases=(
            "zone_entry_cutscene",
            "boss_arena_reveal",
        ),
    ),
    ShotType.HERO_ENTRY: ShotProfile(
        shot_type=ShotType.HERO_ENTRY,
        min_duration_s=3.0, max_duration_s=5.0,
        camera_motion="dolly_track_low_to_pose",
        camera_height="low_angle",
        music_behavior="hit_on_pose",
        is_handheld=True,
        use_cases=(
            "tier3_boss_entrance",
            "boss_recipe_layer_5_entrance",
        ),
    ),
    ShotType.EXCHANGE: ShotProfile(
        shot_type=ShotType.EXCHANGE,
        min_duration_s=5.0, max_duration_s=8.0,
        camera_motion="held_two_shot",
        camera_height="chest_level",
        music_behavior="under_dialogue",
        is_handheld=False,
        use_cases=(
            "pre_fight_banter",
            "mid_fight_phase_transition_line",
            "defeat_dialogue",
        ),
    ),
    ShotType.CHAOS: ShotProfile(
        shot_type=ShotType.CHAOS,
        min_duration_s=0.05,        # whip 50ms or longer
        max_duration_s=999.0,        # variable; follows action
        camera_motion="handheld_tracking",
        camera_height="action_follow",
        music_behavior="combat_loop",
        is_handheld=True,
        use_cases=(
            "skillchain_detonation_whip",
            "ultimate_attack_pullback",
            "party_wipe_tilt_to_sky",
        ),
    ),
    ShotType.AFTERMATH: ShotProfile(
        shot_type=ShotType.AFTERMATH,
        min_duration_s=8.0, max_duration_s=12.0,
        camera_motion="slow_tracking_glide",
        camera_height="mid_to_wide",
        music_behavior="fade",
        is_handheld=True,
        use_cases=(
            "tier3_boss_defeat",
            "end_of_genkai",
            "story_mission_ending",
        ),
    ),
}


def get_profile(shot_type: ShotType) -> ShotProfile:
    return SHOT_PROFILES[shot_type]


def is_within_band(shot_type: ShotType, duration_s: float) -> bool:
    """Sanity check: does the configured duration land inside the
    doc's band?"""
    p = SHOT_PROFILES[shot_type]
    return p.min_duration_s <= duration_s <= p.max_duration_s


def shots_with_use_case(use_case: str) -> tuple[ShotType, ...]:
    """Reverse lookup — which shots support a given use case."""
    return tuple(p.shot_type for p in SHOT_PROFILES.values()
                  if use_case in p.use_cases)


def midpoint_duration(shot_type: ShotType) -> float:
    p = SHOT_PROFILES[shot_type]
    return (p.min_duration_s + p.max_duration_s) / 2.0
