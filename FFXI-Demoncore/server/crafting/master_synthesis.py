"""Master Synthesis Limit Break — the apex crafter content.

Per CRAFTING_SYSTEM.md: at grandmaster (90+) per craft a player
unlocks Master Synthesis. Once-per-game-day per craft. Properties:
    - Guarantees an HQ tier 2+ on the next synth
    - 5% chance to yield HQ tier 4 (signed item with crafter's name)
    - Audible: 'Master Synthesis!' shout + golden particles

The signed item carries `signed_by=crafter_name` in the result;
the persistence layer engraves the lore.
"""
from __future__ import annotations

import random
import typing as t

from .crafter_state import CraftLevels, can_use_master_synthesis
from .crafts import Craft, HqTier, SynthesisOutcome
from .recipes import Recipe
from .synthesis import (
    SynthesisResolver,
    SynthesisResult,
)


MASTER_SYNTHESIS_MIN_HQ = HqTier.PLUS_2          # guaranteed floor
MASTER_SYNTHESIS_SIGNED_CHANCE = 0.05            # 5% to PLUS_4 / signed
MASTER_SYNTHESIS_PLUS_3_BIAS = 0.30              # 30% of guaranteed pool
                                                   # bumps to +3 instead of +2


class MasterSynthesisLB:
    """The once-per-day Limit Break. Wraps the standard
    SynthesisResolver, guarantees ≥ HQ tier 2, and rolls 5% for the
    signed apex.
    """

    def __init__(self,
                  *,
                  rng: t.Optional[random.Random] = None,
                  resolver: t.Optional[SynthesisResolver] = None) -> None:
        self.rng = rng or random.Random()
        self.resolver = resolver or SynthesisResolver(rng=self.rng)

    def can_use(self,
                  crafter: CraftLevels,
                  craft: Craft,
                  *,
                  now: float) -> bool:
        """Available iff grandmaster + cooldown elapsed."""
        return can_use_master_synthesis(crafter, craft, now=now)

    def attempt(self,
                  *,
                  recipe: Recipe,
                  crafter: CraftLevels,
                  crafter_name: str,
                  mood: str,
                  skill_score: float = 0.7,
                  now: float = 0.0,
                  ) -> SynthesisResult:
        """Roll the Master Synthesis. Caller is responsible for
        gating on can_use(); we'll re-check defensively and refuse
        if the LB isn't available.

        Returns the SynthesisResult; signed_by is set on PLUS_4.
        """
        if not self.can_use(crafter, recipe.craft, now=now):
            # Fall through to standard synthesis (no LB consumed)
            return self.resolver.attempt(
                recipe=recipe, crafter=crafter,
                mood=mood, skill_score=skill_score,
            )

        # Run the standard synthesis as the underlying roll. We then
        # apply the LB floor + signed roll on top.
        result = self.resolver.attempt(
            recipe=recipe, crafter=crafter,
            mood=mood, skill_score=skill_score,
        )

        # Furious mood: the LB doesn't override refusal — the crafter
        # still won't focus. But we DON'T burn the cooldown.
        if result.outcome == SynthesisOutcome.REFUSED:
            return result

        # Mark cooldown — LB consumed even on a failure (the act of
        # invoking it is what costs the day).
        crafter.last_master_synthesis[recipe.craft] = now

        # If the synth failed, the LB still 'fires' but produces only
        # the failure. The cooldown is consumed. Game-design rationale:
        # Master Synthesis isn't a "guaranteed success" button; it's a
        # "guaranteed peak quality if you can complete the synth"
        # button. A failure is rare (the crafter is grandmaster) but
        # not impossible.
        if result.outcome == SynthesisOutcome.FAILED:
            result.callouts.append("Master Synthesis fizzled!")
            return result

        # Apply HQ floor: bump anything below +2 up to at least +2.
        if result.hq_tier < MASTER_SYNTHESIS_MIN_HQ:
            result.hq_tier = MASTER_SYNTHESIS_MIN_HQ
            # 30% of the guaranteed floor jumps to +3
            if self.rng.random() < MASTER_SYNTHESIS_PLUS_3_BIAS:
                result.hq_tier = HqTier.PLUS_3

        # Roll the 5% signed chance — only if we're at the floor or
        # higher (guaranteed HQ2+). Signed items are PLUS_4.
        if self.rng.random() < MASTER_SYNTHESIS_SIGNED_CHANCE:
            result.hq_tier = HqTier.PLUS_4
            result.signed_by = crafter_name

        # Add the signature callouts
        result.callouts.append("Master Synthesis!")
        if result.hq_tier == HqTier.PLUS_4:
            result.callouts.append(f"Crafted by {crafter_name}.")
            result.mood_deltas.append(("content", 0.50))

        return result
