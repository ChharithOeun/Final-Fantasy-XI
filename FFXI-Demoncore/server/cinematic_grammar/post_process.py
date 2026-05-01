"""PostProcessVolumes — per-shot lighting/color grading.

Per CINEMATIC_GRAMMAR.md: 'A "Maat tea-set entrance" PPV pushes
warmth +20%, contrast +10%, slight orange tint. A defeat cinematic
PPV pulls saturation -30%, slight desaturated cool shift.'

PPVs are UE5-side; we expose the parameter contracts here so
designers + tooling agree on what the dials mean.
"""
from __future__ import annotations

import dataclasses
import enum


class PpvPreset(str, enum.Enum):
    """Doc-named PPV presets."""
    MAAT_TEA_SET = "maat_tea_set"
    DEFEAT_COOL = "defeat_cool"
    AFTERMATH_LORE = "aftermath_lore"
    ENTRANCE_WARM = "entrance_warm"
    PHASE_TRANSITION_PUNCH = "phase_transition_punch"


@dataclasses.dataclass(frozen=True)
class PostProcessVolume:
    """One PPV's parameter set."""
    preset: PpvPreset
    warmth_delta: float              # +0.20 == 'warmth +20%'
    contrast_delta: float            # +0.10 == 'contrast +10%'
    saturation_delta: float          # -0.30 == 'saturation -30%'
    color_tint: str                  # 'orange' / 'cool' / 'neutral'
    description: str = ""


PPV_PRESETS: dict[PpvPreset, PostProcessVolume] = {
    PpvPreset.MAAT_TEA_SET: PostProcessVolume(
        preset=PpvPreset.MAAT_TEA_SET,
        warmth_delta=0.20,
        contrast_delta=0.10,
        saturation_delta=0.0,
        color_tint="orange",
        description=("Maat tea-set entrance — warm, slightly more "
                       "contrasty, faint orange overlay"),
    ),
    PpvPreset.DEFEAT_COOL: PostProcessVolume(
        preset=PpvPreset.DEFEAT_COOL,
        warmth_delta=-0.10,
        contrast_delta=0.0,
        saturation_delta=-0.30,
        color_tint="cool",
        description=("Defeat cinematic — desaturated cool shift; "
                       "the world is bleak"),
    ),
    PpvPreset.AFTERMATH_LORE: PostProcessVolume(
        preset=PpvPreset.AFTERMATH_LORE,
        warmth_delta=0.05,
        contrast_delta=0.05,
        saturation_delta=-0.10,
        color_tint="neutral",
        description=("Lore aftermath — slight golden hour, "
                       "subtle desaturation for reflective tone"),
    ),
    PpvPreset.ENTRANCE_WARM: PostProcessVolume(
        preset=PpvPreset.ENTRANCE_WARM,
        warmth_delta=0.15,
        contrast_delta=0.05,
        saturation_delta=0.05,
        color_tint="warm",
        description="Generic warm entrance for non-Maat bosses",
    ),
    PpvPreset.PHASE_TRANSITION_PUNCH: PostProcessVolume(
        preset=PpvPreset.PHASE_TRANSITION_PUNCH,
        warmth_delta=0.0,
        contrast_delta=0.20,           # punchy contrast for impact
        saturation_delta=0.10,
        color_tint="neutral",
        description=("Phase transition punch — high contrast + "
                       "saturation to sell the shift"),
    ),
}


def get_preset(preset: PpvPreset) -> PostProcessVolume:
    return PPV_PRESETS[preset]


def stack_presets(presets: tuple[PpvPreset, ...]) -> PostProcessVolume:
    """Stack multiple presets into one effective PPV.

    Deltas are additive. Color tint of the last preset wins (UE5
    can only render one tint at a time).
    """
    if not presets:
        return PostProcessVolume(
            preset=PpvPreset.MAAT_TEA_SET,    # placeholder
            warmth_delta=0.0, contrast_delta=0.0,
            saturation_delta=0.0, color_tint="neutral",
            description="empty stack",
        )
    w = sum(PPV_PRESETS[p].warmth_delta for p in presets)
    c = sum(PPV_PRESETS[p].contrast_delta for p in presets)
    s = sum(PPV_PRESETS[p].saturation_delta for p in presets)
    last_tint = PPV_PRESETS[presets[-1]].color_tint
    return PostProcessVolume(
        preset=presets[-1],            # report last as primary
        warmth_delta=w, contrast_delta=c, saturation_delta=s,
        color_tint=last_tint,
        description=f"stack of {len(presets)} presets",
    )
