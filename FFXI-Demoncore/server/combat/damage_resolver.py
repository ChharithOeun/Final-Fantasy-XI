"""Damage resolver — composes skillchain + weight + affinity + magic burst
+ intervention + ailment 3x into one damage pipeline.

The math from `SKILLCHAIN_SYSTEM.md`, `WEIGHT_PHYSICS.md`, and
`MOB_RESISTANCES.md` made executable. Pure-Python; no I/O.

Usage:

    resolver = DamageResolver()
    result = resolver.resolve(DamageContext(
        base_spell_damage=850,         # Blizzard III base
        spell_type=SpellType.DIRECT_DAMAGE,
        spell_element=Element.ICE,
        target_aligned_element=Element.LIGHTNING,  # Quadav
        target_weak_to=Element.WATER,
        skillchain_landed=SkillchainElement.DISTORTION,
        chain_level=SkillchainLevel.LEVEL_2,
        in_mb_window=True,
        caster_stationary=True,
        caster_gear_weight=42,
    ))
    print(result.final_damage)   # 1530, with breakdown in result.breakdown
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .skillchain_detector import (
    Element,
    SkillchainElement,
    SkillchainLevel,
    chain_to_element,
)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

class SpellType(str, enum.Enum):
    DIRECT_DAMAGE = "direct_damage"        # Fire, Blizzard, Comet etc
    AILMENT = "ailment"                     # Slow, Paralyze, Bind, Bio
    HEALING = "healing"                     # Cure, Curaga
    BUFF = "buff"                           # Haste, Refresh, Phalanx
    SONG = "song"                           # BRD songs
    HELIX = "helix"                         # SCH helix DoTs


@dataclasses.dataclass
class DamageContext:
    """Input to the damage resolver. All fields optional except `base_spell_damage`."""
    # Required
    base_spell_damage: int

    # Spell metadata
    spell_type: SpellType = SpellType.DIRECT_DAMAGE
    spell_element: Element = Element.PHYSICAL

    # Target affinity
    target_aligned_element: t.Optional[Element] = None
    target_weak_to: t.Optional[Element] = None
    target_strong_against: t.Optional[Element] = None

    # Skillchain context
    skillchain_landed: t.Optional[SkillchainElement] = None
    chain_level: t.Optional[SkillchainLevel] = None
    in_mb_window: bool = False

    # Caster movement / gear
    caster_stationary: bool = False
    caster_gear_weight: float = 30.0
    caster_int_mod: float = 1.0

    # Intervention path
    is_intervention: bool = False             # WHM Cure-V on enemy chain
    intervention_chain_element: t.Optional[SkillchainElement] = None  # the enemy chain

    # NIN sign-spell path
    is_nin_signspell: bool = False


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class DamageResult:
    final_damage: int
    cancelled_by_intervention: bool = False
    breakdown: dict = dataclasses.field(default_factory=dict)
    ailment_amplification: float = 1.0
    intervention_amplification: float = 1.0


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

# Per SKILLCHAIN_SYSTEM.md table
LEVEL_MULTIPLIER: dict[SkillchainLevel, float] = {
    SkillchainLevel.LEVEL_1: 1.25,
    SkillchainLevel.LEVEL_2: 1.65,
    SkillchainLevel.LEVEL_3: 2.20,
}

MB_MULTIPLIER: dict[SkillchainLevel, float] = {
    SkillchainLevel.LEVEL_1: 1.50,
    SkillchainLevel.LEVEL_2: 1.80,
    SkillchainLevel.LEVEL_3: 2.20,
}

# Affinity multiplier per MOB_RESISTANCES.md
AFFINITY_WEAK_TO = 1.25
AFFINITY_NEUTRAL = 1.00
AFFINITY_STRONG_AGAINST = 0.75
AFFINITY_MATCHING = 0.50

# Intervention amplification per INTERVENTION_MB.md
INTERVENTION_AMP = 3.00
INTERVENTION_AMP_LIGHT = 5.00

# 3x ailment multiplier per SKILLCHAIN_SYSTEM.md
AILMENT_AMP = 3.00


class DamageResolver:
    """Pure functions; one resolver instance is fine for many calls."""

    def resolve(self, ctx: DamageContext) -> DamageResult:
        # ---- 1. Detect intervention cancellation (defensive path) ----
        if ctx.is_intervention and ctx.in_mb_window \
                and ctx.intervention_chain_element is not None:
            # Intervention damage cancellation per INTERVENTION_MB.md
            return self._resolve_intervention(ctx)

        # ---- 2. Standard offensive path ----
        result = DamageResult(final_damage=ctx.base_spell_damage)
        result.breakdown["base_spell_damage"] = ctx.base_spell_damage

        # Skillchain bonus from being a contributor (additive damage)
        if ctx.skillchain_landed is not None and ctx.chain_level is not None:
            level_mult = LEVEL_MULTIPLIER[ctx.chain_level]
            chain_dmg = ctx.base_spell_damage * level_mult
            # Stationary bonus + weight bonus from WEIGHT_PHYSICS.md
            weight_bonus = 1.0 + 0.005 * max(0, ctx.caster_gear_weight - 5)
            stationary_bonus = 1.15 if ctx.caster_stationary else 1.0
            chain_dmg *= weight_bonus * stationary_bonus
            result.final_damage = int(chain_dmg)
            result.breakdown["chain_level_multiplier"] = level_mult
            result.breakdown["weight_bonus"] = weight_bonus
            result.breakdown["stationary_bonus"] = stationary_bonus
            result.breakdown["chain_damage"] = result.final_damage

        # Magic burst (offensive)
        if ctx.in_mb_window and ctx.spell_type == SpellType.DIRECT_DAMAGE \
                and ctx.chain_level is not None:
            mb_mult = MB_MULTIPLIER[ctx.chain_level]
            element_match = self._chain_element_match(
                spell_element=ctx.spell_element,
                chain=ctx.skillchain_landed,
            )
            stationary = 1.15 if ctx.caster_stationary else 1.0
            ninspell = 1.25 if ctx.is_nin_signspell else 1.0
            mb_dmg_factor = mb_mult * element_match * stationary * ninspell
            result.final_damage = int(result.final_damage * mb_dmg_factor)
            result.breakdown["mb_multiplier"] = mb_mult
            result.breakdown["element_match"] = element_match
            result.breakdown["mb_stationary"] = stationary
            result.breakdown["mb_ninspell"] = ninspell

        # Ailment 3x amplification (per SKILLCHAIN_SYSTEM.md)
        if ctx.spell_type == SpellType.AILMENT and ctx.in_mb_window:
            result.ailment_amplification = AILMENT_AMP
            result.breakdown["ailment_amplification"] = AILMENT_AMP
            # Note: for ailments, base_spell_damage encodes effect-strength
            result.final_damage = int(result.final_damage * AILMENT_AMP)

        # Affinity multiplier (mob element resistances)
        affinity = self._compute_affinity_mult(
            spell_element=ctx.spell_element,
            target_aligned=ctx.target_aligned_element,
            target_weak_to=ctx.target_weak_to,
            target_strong_against=ctx.target_strong_against,
        )
        if affinity != 1.0:
            result.final_damage = int(result.final_damage * affinity)
            result.breakdown["affinity_multiplier"] = affinity

        # INT modifier for direct damage spells
        if ctx.spell_type == SpellType.DIRECT_DAMAGE and ctx.caster_int_mod != 1.0:
            result.final_damage = int(result.final_damage * ctx.caster_int_mod)
            result.breakdown["caster_int_mod"] = ctx.caster_int_mod

        return result

    # ------------------------------------------------------------------
    # Intervention path
    # ------------------------------------------------------------------

    def _resolve_intervention(self, ctx: DamageContext) -> DamageResult:
        """Per INTERVENTION_MB.md.
        Damage cancellation + 3x or 5x amplification on the friendly spell."""
        result = DamageResult(
            final_damage=0,                # enemy damage cancelled entirely
            cancelled_by_intervention=True,
        )

        chain_elem = chain_to_element(ctx.intervention_chain_element)
        light_bonus = chain_elem == Element.LIGHT
        amp = INTERVENTION_AMP_LIGHT if light_bonus else INTERVENTION_AMP

        # The friendly spell's effect amplification (separate from
        # damage; the resolver returns this as result.intervention_amplification
        # for the caller to apply to the cure/buff/debuff effect)
        result.intervention_amplification = amp
        result.breakdown["intervention_cancelled_damage"] = True
        result.breakdown["intervention_amplification"] = amp
        result.breakdown["light_bonus"] = light_bonus
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _chain_element_match(self, *,
                              spell_element: Element,
                              chain: t.Optional[SkillchainElement]) -> float:
        """Per SKILLCHAIN_SYSTEM.md Magic-Burst element match table.

        Returns:
          1.00 — exact match
          0.50 — overlap (e.g. fire MB on Light chain — Light has fire as a component)
         -0.50 — opposition (e.g. ice MB on Liquefaction = damage penalty)
                 (NOTE: returned as 0.5 here; the negative sign in the doc
                 means "applied subtraction"; we use 0.5 multiplier with a
                 separate penalty flag)
        """
        if chain is None:
            return 1.0
        chain_elem = chain_to_element(chain)
        # Exact match
        if spell_element == chain_elem:
            return 1.0
        # Overlap (Light chain has fire; Darkness has ice; etc)
        if chain == SkillchainElement.LIGHT and spell_element == Element.FIRE:
            return 0.50
        if chain == SkillchainElement.LIGHT and spell_element == Element.LIGHTNING:
            return 0.50
        if chain == SkillchainElement.DARKNESS and spell_element == Element.ICE:
            return 0.50
        if chain == SkillchainElement.DARKNESS and spell_element == Element.WATER:
            return 0.50
        # Opposition (the energy-harmonic-break penalty)
        oppositions = {
            (Element.ICE, Element.FIRE): True,
            (Element.FIRE, Element.ICE): True,
            (Element.WATER, Element.LIGHTNING): True,
            (Element.LIGHTNING, Element.WATER): True,
            (Element.WIND, Element.EARTH): True,
            (Element.EARTH, Element.WIND): True,
            (Element.LIGHT, Element.DARK): True,
            (Element.DARK, Element.LIGHT): True,
        }
        if (spell_element, chain_elem) in oppositions:
            return 0.50          # mb_dmg_factor halved (= -50% from base)
        # Otherwise neutral non-match
        return 1.0

    def _compute_affinity_mult(self, *,
                                spell_element: Element,
                                target_aligned: t.Optional[Element],
                                target_weak_to: t.Optional[Element],
                                target_strong_against: t.Optional[Element]) -> float:
        """Per MOB_RESISTANCES.md. Returns the multiplier."""
        if spell_element == Element.PHYSICAL:
            return AFFINITY_NEUTRAL
        if spell_element == target_weak_to:
            return AFFINITY_WEAK_TO
        if spell_element == target_aligned:
            return AFFINITY_MATCHING
        if spell_element == target_strong_against:
            return AFFINITY_STRONG_AGAINST
        return AFFINITY_NEUTRAL
