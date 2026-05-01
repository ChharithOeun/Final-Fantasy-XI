"""BossRecipe — the full 5-layer composition + validator."""
from __future__ import annotations

import dataclasses
import typing as t

from .cinematic import BossCinematic
from .phases import BossPhase, PhaseRule, PHASE_RULES
from .repertoire import Repertoire, validate_repertoire


@dataclasses.dataclass(frozen=True)
class BodyLayer:
    """Layer 1: SkeletalMesh + race-style + visible-health archetype."""
    skeletal_mesh_id: str
    animation_set: str
    visible_health_archetype: str
    mood_axes: tuple[str, ...]            # which moods this body honors
    is_hero_tier: bool = False             # 1-2 day hero authoring vs reskin


@dataclasses.dataclass(frozen=True)
class MindLayer:
    """Layer 4: Tier-3 generative agent + critic LLM."""
    agent_profile_id: str
    has_critic_llm: bool
    critic_review_interval_seconds: float = 30.0
    daily_schedule_id: t.Optional[str] = None
    backstory_id: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class BossRecipe:
    """The full 5-layer boss spec."""
    boss_id: str
    label: str
    body: BodyLayer
    repertoire: Repertoire
    phase_rules: dict[BossPhase, PhaseRule]
    mind: MindLayer
    cinematic: BossCinematic


def validate_recipe(recipe: BossRecipe) -> list[str]:
    """Doc-conformance check."""
    complaints: list[str] = []
    complaints.extend(validate_repertoire(recipe.repertoire))
    # All 6 phases must be represented
    for phase in PHASE_RULES.keys():
        if phase not in recipe.phase_rules:
            complaints.append(
                f"{recipe.boss_id} missing phase rule for {phase.value}")
    if recipe.body.is_hero_tier and not recipe.mind.has_critic_llm:
        complaints.append(
            f"{recipe.boss_id} is hero-tier but lacks the critic LLM "
            "the doc requires for hero bosses")
    if recipe.cinematic.entrance.duration_seconds <= 0:
        complaints.append(f"{recipe.boss_id} entrance must be > 0s")
    return complaints
