"""DeployableBoss — one boss authored from the catalog spine.

Per BOSS_GRAMMAR.md: 'Boss authors pick a sub-variant, override
specifics, and ship a new boss in 4-6 hours.'

This module is the composition site. It pulls:
    - a SubVariant from mob_class_library (the body archetype)
    - a BossRecipe from boss_grammar (Body/Repertoire/Phases/Mind)
    - cinematic clones from cinematic_grammar (entrance + defeat)

and produces a DeployableBoss object the orchestrator can spawn.
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.boss_grammar import (
    BossRecipe,
    validate_recipe,
)
from server.cinematic_grammar import ClonedCinematic
from server.mob_class_library import (
    FamilyId,
    SubVariant,
    get_sub_variant,
)


@dataclasses.dataclass(frozen=True)
class DeployableBoss:
    """One boss ready for the orchestrator to spawn.

    The recipe is the canonical truth (5 layers); the sub-variant
    + cinematics enrich it with catalog-grade defaults the author
    picked from the menu.
    """
    boss_id: str
    label: str
    sub_variant_id: str            # which mob_class_library entry
    nation: str                     # 'Bastok' / 'Sandy' / 'Windy' / etc.
    recipe: BossRecipe
    entrance_cinematic: ClonedCinematic
    defeat_cinematic: ClonedCinematic
    optional_aftermath: t.Optional[ClonedCinematic] = None

    @property
    def family(self) -> FamilyId:
        sv = get_sub_variant(self.sub_variant_id)
        return sv.family

    @property
    def level_band(self) -> tuple[int, int]:
        sv = get_sub_variant(self.sub_variant_id)
        return (sv.level_min, sv.level_max)


def validate_deployable(boss: DeployableBoss) -> list[str]:
    """Cross-system validation. Returns complaint list."""
    complaints: list[str] = []
    # Recipe-side validation (delegates to boss_grammar)
    complaints.extend(validate_recipe(boss.recipe))
    # Sub-variant must exist in the catalog
    try:
        sv: t.Optional[SubVariant] = get_sub_variant(boss.sub_variant_id)
    except KeyError:
        complaints.append(
            f"sub_variant_id {boss.sub_variant_id!r} not in catalog")
        sv = None
    # Cinematics must point at the same boss_id as the recipe
    if boss.entrance_cinematic.target_actor_id != boss.recipe.boss_id:
        complaints.append(
            f"entrance cinematic targets "
            f"{boss.entrance_cinematic.target_actor_id!r} but recipe is "
            f"for {boss.recipe.boss_id!r}")
    if boss.defeat_cinematic.target_actor_id != boss.recipe.boss_id:
        complaints.append(
            f"defeat cinematic targets "
            f"{boss.defeat_cinematic.target_actor_id!r} but recipe is "
            f"for {boss.recipe.boss_id!r}")
    # If sub-variant is known, verify the recipe boss_id matches
    if sv is not None and boss.recipe.boss_id != boss.boss_id:
        complaints.append(
            f"recipe boss_id {boss.recipe.boss_id!r} differs from "
            f"deployable boss_id {boss.boss_id!r}")
    return complaints
