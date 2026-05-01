"""SynthesisResolver — the mood-aware proc table that runs an attempt.

A craft action is a mini-game-with-physics in UE5, but the engine
sees it as a (recipe, crafter_state, mood, skill_score, rng) tuple
that resolves to a SynthesisResult. The skill_score is the player's
mini-game performance, 0..1.

Per CRAFTING_SYSTEM.md mood gates:
    content        : standard rates
    mischievous    : +10% to creative procs (alternate output)
    weary          : -20% success, +30% mundane procs (extra material)
    furious        : refuse — no synth happens
    contemplative  : +15% to higher-tier procs (rare quality)

HQ table (standard mood, baseline skill):
    standard 81.7% | +1 15% | +2 3% | +3 0.3% | failure 0%
    (failure rate is computed separately; HQ table only applies when
     the synth doesn't fail outright)

Failure consequences:
    - All materials consumed
    - Tool durability -10% on one tool
    - Mood weary += 0.10
    - Audible disappointed grunt (orchestrator hook)
"""
from __future__ import annotations

import dataclasses
import random
import typing as t

from .crafter_state import (
    CraftLevels,
    grant_xp,
    stable_hands_active,
    xp_for_synth,
)
from .crafts import Craft, HqTier, SynthesisOutcome
from .recipes import Recipe


# Base HQ probability table (standard mood, baseline skill).
# Cumulative: standard ~ 0.817, +1 ~ 0.15, +2 ~ 0.03, +3 ~ 0.003.
HQ_BASE_TABLE: dict[HqTier, float] = {
    HqTier.STANDARD: 0.817,
    HqTier.PLUS_1: 0.150,
    HqTier.PLUS_2: 0.030,
    HqTier.PLUS_3: 0.003,
}


@dataclasses.dataclass
class MoodModifier:
    """Per-mood synthesis modifier."""
    success_delta: float = 0.0          # added to base success rate
    refuse: bool = False                 # furious refuses to craft
    creative_proc_bonus: float = 0.0    # +10% to alternate-output procs
    mundane_proc_bonus: float = 0.0     # +30% extra material output on success
    high_tier_bonus: float = 0.0        # +15% to +2/+3 rates


MOOD_MODIFIERS: dict[str, MoodModifier] = {
    "content":        MoodModifier(),
    "mischievous":    MoodModifier(creative_proc_bonus=0.10),
    "weary":          MoodModifier(success_delta=-0.20,
                                      mundane_proc_bonus=0.30),
    "furious":        MoodModifier(refuse=True),
    "contemplative":  MoodModifier(high_tier_bonus=0.15),
    # Other moods default to neutral
}


@dataclasses.dataclass
class SynthesisResult:
    """Outcome of one synthesis attempt."""
    outcome: SynthesisOutcome
    hq_tier: HqTier
    output_id: t.Optional[str]
    output_qty: int
    materials_consumed: dict[str, int]
    xp_gained: float
    tool_durability_lost_pct: float
    mood_deltas: list[tuple[str, float]]   # (mood, delta) for orchestrator
    callouts: list[str]                     # for AUDIBLE_CALLOUTS layer
    signed_by: t.Optional[str] = None       # set by Master Synthesis LB

    def is_hq(self) -> bool:
        return self.hq_tier > HqTier.STANDARD


def base_success_rate(*,
                       crafter_level: int,
                       recipe_level: int,
                       skill_score: float,
                       has_stable_hands: bool) -> float:
    """Probability the synth itself doesn't fail.

    diff = crafter_level - recipe_level
    < -10: 0% (impossible)
    -10..0: 50% at parity, scales linearly
    > 0: rises to 95% cap as the crafter exceeds the recipe

    skill_score is the mini-game performance 0..1. Stable hands
    (mastery >= 5) lifts a sloppy score by +0.15 floor.
    """
    diff = crafter_level - recipe_level
    if diff < -10:
        return 0.0

    if diff <= 0:
        # 50% at parity, drops to 0% at -10
        rate = 0.50 + 0.05 * diff
    else:
        rate = min(0.95, 0.50 + 0.03 * diff)

    # Skill score scales the rate: from 0.7x at score=0 to 1.0x at score=1
    score = max(0.0, min(1.0, skill_score))
    if has_stable_hands:
        score = max(score, 0.15)
    rate *= 0.70 + 0.30 * score

    return max(0.0, min(0.95, rate))


def _resolve_hq_tier(*,
                      mood_mod: MoodModifier,
                      skill_score: float,
                      rng: random.Random) -> HqTier:
    """Roll the HQ tier given the base table + mood adjustments.

    contemplative_high_tier_bonus shifts probability mass from
    standard -> +2 / +3.
    skill_score similarly biases toward HQ tiers.
    """
    table = dict(HQ_BASE_TABLE)
    if mood_mod.high_tier_bonus > 0:
        # Lift +2 and +3 by the bonus, take from STANDARD
        shift_total = (table[HqTier.PLUS_2] + table[HqTier.PLUS_3]) * mood_mod.high_tier_bonus
        table[HqTier.PLUS_2] += table[HqTier.PLUS_2] * mood_mod.high_tier_bonus
        table[HqTier.PLUS_3] += table[HqTier.PLUS_3] * mood_mod.high_tier_bonus
        table[HqTier.STANDARD] = max(0.0, table[HqTier.STANDARD] - shift_total)

    # Skill score lifts +1/+2/+3 chances, biases away from STANDARD
    score = max(0.0, min(1.0, skill_score))
    if score > 0.5:
        boost = (score - 0.5) * 0.30   # up to +15% relative for perfect score
        for tier in (HqTier.PLUS_1, HqTier.PLUS_2, HqTier.PLUS_3):
            old = table[tier]
            table[tier] = old * (1.0 + boost)
        # Re-normalize STANDARD as the residual
        consumed = sum(v for k, v in table.items() if k != HqTier.STANDARD)
        table[HqTier.STANDARD] = max(0.0, 1.0 - consumed)

    # Roll
    roll = rng.random()
    cumulative = 0.0
    # Iterate from highest tier down so apex rare wins ties
    for tier in (HqTier.PLUS_3, HqTier.PLUS_2, HqTier.PLUS_1):
        cumulative += table[tier]
        if roll < cumulative:
            return tier
    return HqTier.STANDARD


class SynthesisResolver:
    """Pure-function resolver for a single synthesis attempt."""

    def __init__(self,
                  *,
                  rng: t.Optional[random.Random] = None) -> None:
        self.rng = rng or random.Random()

    def attempt(self,
                  *,
                  recipe: Recipe,
                  crafter: CraftLevels,
                  mood: str,
                  skill_score: float = 0.5,
                  ) -> SynthesisResult:
        """Resolve a single synth.

        recipe       - what we're crafting
        crafter      - levels + state (mutated: XP gain on success)
        mood         - mood key matching MOOD_MODIFIERS
        skill_score  - 0..1 mini-game performance
        """
        mood_mod = MOOD_MODIFIERS.get(mood, MoodModifier())

        # Furious refuses outright
        if mood_mod.refuse:
            return SynthesisResult(
                outcome=SynthesisOutcome.REFUSED,
                hq_tier=HqTier.STANDARD,
                output_id=None, output_qty=0,
                materials_consumed={},
                xp_gained=0.0,
                tool_durability_lost_pct=0.0,
                mood_deltas=[],
                callouts=["Cannot focus."],
            )

        # Wrong-craft refusal: a smithing recipe attempted at a cooking
        # station etc. would be caught upstream; here we just trust the
        # caller passed a valid recipe.

        crafter_level = crafter.level(recipe.craft)
        success_rate = base_success_rate(
            crafter_level=crafter_level,
            recipe_level=recipe.required_level,
            skill_score=skill_score,
            has_stable_hands=stable_hands_active(crafter, recipe.craft),
        )
        success_rate = max(0.0, min(0.95, success_rate + mood_mod.success_delta))

        if self.rng.random() >= success_rate:
            return self._failure(recipe, mood_mod)

        # Success: roll HQ tier
        hq = _resolve_hq_tier(mood_mod=mood_mod,
                                skill_score=skill_score, rng=self.rng)

        # Mundane proc bonus (weary): chance to double output qty
        out_qty = recipe.output_qty
        if mood_mod.mundane_proc_bonus > 0:
            if self.rng.random() < mood_mod.mundane_proc_bonus:
                out_qty *= 2

        # Award XP on the crafter
        xp = xp_for_synth(recipe_level=recipe.required_level,
                            crafter_level=crafter_level)
        grant_xp(crafter, recipe.craft, xp=xp)

        callouts = ["Crafting now."]
        mood_deltas: list[tuple[str, float]] = []
        if hq == HqTier.PLUS_1:
            callouts.append("Plus one!")
        elif hq == HqTier.PLUS_2:
            callouts.append("Plus two!")
            mood_deltas.append(("content", 0.30))
        elif hq == HqTier.PLUS_3:
            callouts.append("Plus three!")
            mood_deltas.append(("content", 0.30))

        return SynthesisResult(
            outcome=SynthesisOutcome.SUCCESS,
            hq_tier=hq,
            output_id=recipe.output_id,
            output_qty=out_qty,
            materials_consumed=dict(recipe.materials),
            xp_gained=xp,
            tool_durability_lost_pct=0.0,
            mood_deltas=mood_deltas,
            callouts=callouts,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _failure(recipe: Recipe, mood_mod: MoodModifier) -> SynthesisResult:
        return SynthesisResult(
            outcome=SynthesisOutcome.FAILED,
            hq_tier=HqTier.STANDARD,
            output_id=None,
            output_qty=0,
            materials_consumed=dict(recipe.materials),
            xp_gained=0.0,
            tool_durability_lost_pct=0.10,
            mood_deltas=[("weary", 0.10)],
            callouts=["[disappointed grunt]"],
        )
