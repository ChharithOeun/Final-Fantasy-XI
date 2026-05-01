"""BossBuilder — convenience composer that wraps the doc workflow.

Per BOSS_GRAMMAR.md the doc workflow is:
    1. Pick sub-variant from mob_class_library catalog
    2. Author/clone a BossRecipe in boss_grammar
    3. Clone entrance + defeat cinematics from cinematic_grammar
    4. Register the DeployableBoss

This builder bundles those steps into one fluent call so authors
don't have to re-derive the wiring each time.
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.boss_grammar import (
    BossCinematic,
    BossRecipe,
)
from server.cinematic_grammar import (
    TemplateId,
    clone_for_boss,
)
from server.mob_class_library import (
    FamilyId,
    SubVariant,
    get_sub_variant,
)

from .instance import DeployableBoss


@dataclasses.dataclass
class BossBuildPlan:
    """The author's intent — a sub-variant + recipe + cinematics
    pointers. The builder resolves this into a DeployableBoss."""
    boss_id: str
    label: str
    sub_variant_id: str
    nation: str
    recipe: BossRecipe
    entrance_template: TemplateId
    defeat_template: TemplateId
    voice_clip_intro: str
    voice_clip_defeat: str
    music_cue_intro: str
    music_cue_defeat: str
    aftermath_template: t.Optional[TemplateId] = None
    voice_clip_aftermath: t.Optional[str] = None
    music_cue_aftermath: t.Optional[str] = None


def build(plan: BossBuildPlan) -> DeployableBoss:
    """Resolve a BossBuildPlan into a DeployableBoss.

    Verifies the sub_variant exists, clones the cinematic templates
    with the boss's id baked in, and stitches everything together.
    """
    # Sub-variant must exist
    sv: SubVariant = get_sub_variant(plan.sub_variant_id)

    entrance = clone_for_boss(
        template_id=plan.entrance_template,
        boss_id=plan.boss_id,
        voice_clip_id=plan.voice_clip_intro,
        music_cue_id=plan.music_cue_intro,
        nation=plan.nation,
    )
    defeat = clone_for_boss(
        template_id=plan.defeat_template,
        boss_id=plan.boss_id,
        voice_clip_id=plan.voice_clip_defeat,
        music_cue_id=plan.music_cue_defeat,
        nation=plan.nation,
    )
    aftermath = None
    if (plan.aftermath_template is not None
            and plan.voice_clip_aftermath is not None
            and plan.music_cue_aftermath is not None):
        aftermath = clone_for_boss(
            template_id=plan.aftermath_template,
            boss_id=plan.boss_id,
            voice_clip_id=plan.voice_clip_aftermath,
            music_cue_id=plan.music_cue_aftermath,
            nation=plan.nation,
        )

    return DeployableBoss(
        boss_id=plan.boss_id,
        label=plan.label,
        sub_variant_id=plan.sub_variant_id,
        nation=plan.nation,
        recipe=plan.recipe,
        entrance_cinematic=entrance,
        defeat_cinematic=defeat,
        optional_aftermath=aftermath,
    )


def family_for_plan(plan: BossBuildPlan) -> FamilyId:
    """Convenience: surface the family the plan ultimately uses."""
    sv = get_sub_variant(plan.sub_variant_id)
    return sv.family
