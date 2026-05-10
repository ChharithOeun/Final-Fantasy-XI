"""Spell VFX resolver — FFXI spell name -> Niagara vfx chain.

Each spell in FFXI has a recognizable visual signature: the
ground circle that lights up under the caster, the glow at
the casting hand, the projectile or AOE that lands, the
flash on impact, and (for some) a lingering puddle of
burning ground or chilling mist. This module owns the
mapping. Tier I through tier IV escalates particle density,
light pulse, and screen shake; tier V (Ancient Magic — Fire
V, Flare, Comet, Tornado II, Quake II...) flips the
cinematic tier override on so the engine pumps particle
counts to HIGH regardless of cinematic LOD.

Magic Burst overlay rides on top: when a spell lands inside
the magic-burst window opened by a closed skillchain,
resolve() adds the MB_HALO vfx and multiplies screen shake
+ light pulse by 1.5x, plus a chromatic-aberration spike
the lens_optics module reads. That overlay is the visual
"YES, THE BURST CONNECTED" feedback that retail FFXI never
quite delivered.

The resolver is element-agnostic at the surface: register a
spell once with its base chain, the resolver picks the
right particle pack from the niagara_vfx_library by name
convention (fire_tier_iii, ice_tier_iv, etc.) and serves
the right impact + casting circle for the element.

Public surface
--------------
    Element enum
    SpellTier enum
    SpellVfxChain dataclass (frozen)
    ResolvedSpellVfx dataclass (frozen)
    MbOverlay dataclass (frozen)
    SpellVfxResolver
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Element(enum.Enum):
    FIRE = "fire"
    EARTH = "earth"
    WATER = "water"
    WIND = "wind"
    ICE = "ice"
    LIGHTNING = "lightning"
    LIGHT = "light"
    DARK = "dark"
    NONE = "none"


class SpellTier(enum.Enum):
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"
    AM = "AM"          # Ancient Magic (Flare, Comet, etc.)
    UTIL = "UTIL"      # Utility (Cure, Haste, Sleep...)


@dataclasses.dataclass(frozen=True)
class SpellVfxChain:
    spell_id: str
    casting_circle_vfx: str
    hand_glow_left_vfx: str
    hand_glow_right_vfx: str
    projectile_or_aoe_vfx: str | None
    impact_vfx: str
    lingering_vfx: str | None
    screen_shake_intensity: float
    light_pulse_lux: float
    sound_event_id: str
    element: Element = Element.NONE
    tier: SpellTier = SpellTier.UTIL


@dataclasses.dataclass(frozen=True)
class MbOverlay:
    halo_vfx: str
    shake_multiplier: float
    light_multiplier: float
    chromatic_aberration_spike: float


@dataclasses.dataclass(frozen=True)
class ResolvedSpellVfx:
    spell_id: str
    casting_circle_vfx: str
    hand_glow_left_vfx: str
    hand_glow_right_vfx: str
    projectile_or_aoe_vfx: str | None
    impact_vfx: str
    lingering_vfx: str | None
    screen_shake_intensity: float
    light_pulse_lux: float
    sound_event_id: str
    element: Element
    tier: SpellTier
    mb_active: bool
    mb_halo_vfx: str | None
    chromatic_aberration_spike: float
    cinematic_tier_override: bool


# Tier scaling — particles, shake, light all step up. The
# ratios apply to the registered base values; tier V doubles
# the tier-IV escalation again.
_TIER_SCALE: dict[SpellTier, tuple[float, float]] = {
    # (shake_mult, light_mult)
    SpellTier.I:    (1.0, 1.0),
    SpellTier.II:   (1.4, 1.5),
    SpellTier.III:  (1.8, 2.2),
    SpellTier.IV:   (2.4, 3.2),
    SpellTier.V:    (3.0, 4.0),
    SpellTier.AM:   (4.0, 6.0),
    SpellTier.UTIL: (1.0, 1.0),
}


_DEFAULT_MB_OVERLAY = MbOverlay(
    halo_vfx="mb_halo_default",
    shake_multiplier=1.5,
    light_multiplier=1.5,
    chromatic_aberration_spike=0.35,
)


@dataclasses.dataclass
class SpellVfxResolver:
    _chains: dict[str, SpellVfxChain] = dataclasses.field(
        default_factory=dict,
    )
    _mb_overlay: MbOverlay = dataclasses.field(
        default_factory=lambda: _DEFAULT_MB_OVERLAY,
    )

    def register_spell(
        self, spell_id: str, chain: SpellVfxChain,
    ) -> None:
        if not spell_id:
            raise ValueError("spell_id required")
        if chain.spell_id != spell_id:
            raise ValueError(
                "chain.spell_id must match spell_id",
            )
        if spell_id in self._chains:
            raise ValueError(f"duplicate spell_id: {spell_id}")
        self._chains[spell_id] = chain

    def get_chain(self, spell_id: str) -> SpellVfxChain:
        if spell_id not in self._chains:
            raise KeyError(f"unknown spell: {spell_id}")
        return self._chains[spell_id]

    def resolve(
        self,
        spell_id: str,
        element_tier: SpellTier | None = None,
        is_mb_active: bool = False,
    ) -> ResolvedSpellVfx:
        ch = self.get_chain(spell_id)
        tier = element_tier or ch.tier
        shake_mult, light_mult = _TIER_SCALE[tier]
        shake = ch.screen_shake_intensity * shake_mult
        light = ch.light_pulse_lux * light_mult
        chrom_spike = 0.0
        mb_halo: str | None = None
        if is_mb_active:
            shake *= self._mb_overlay.shake_multiplier
            light *= self._mb_overlay.light_multiplier
            chrom_spike = self._mb_overlay.chromatic_aberration_spike
            mb_halo = self._mb_overlay.halo_vfx
        cinematic_override = tier in (SpellTier.V, SpellTier.AM)
        return ResolvedSpellVfx(
            spell_id=ch.spell_id,
            casting_circle_vfx=ch.casting_circle_vfx,
            hand_glow_left_vfx=ch.hand_glow_left_vfx,
            hand_glow_right_vfx=ch.hand_glow_right_vfx,
            projectile_or_aoe_vfx=ch.projectile_or_aoe_vfx,
            impact_vfx=ch.impact_vfx,
            lingering_vfx=ch.lingering_vfx,
            screen_shake_intensity=shake,
            light_pulse_lux=light,
            sound_event_id=ch.sound_event_id,
            element=ch.element,
            tier=tier,
            mb_active=is_mb_active,
            mb_halo_vfx=mb_halo,
            chromatic_aberration_spike=chrom_spike,
            cinematic_tier_override=cinematic_override,
        )

    def chains_for_element(
        self, element: Element,
    ) -> tuple[SpellVfxChain, ...]:
        return tuple(
            sorted(
                (c for c in self._chains.values()
                 if c.element == element),
                key=lambda c: c.spell_id,
            )
        )

    def chains_for_tier(
        self, tier: SpellTier,
    ) -> tuple[SpellVfxChain, ...]:
        return tuple(
            sorted(
                (c for c in self._chains.values() if c.tier == tier),
                key=lambda c: c.spell_id,
            )
        )

    def mb_overlay(self) -> MbOverlay:
        return self._mb_overlay

    def set_mb_overlay(self, overlay: MbOverlay) -> None:
        self._mb_overlay = overlay

    def ancient_magic_chain(
        self, spell_id: str,
    ) -> ResolvedSpellVfx:
        """Special handler for AM spells — always treats the
        cast as a TRAILER-tier event, even when the global
        cinematic LOD is lower."""
        ch = self.get_chain(spell_id)
        if ch.tier != SpellTier.AM:
            raise ValueError(
                f"{spell_id} is not Ancient Magic",
            )
        return self.resolve(
            spell_id, element_tier=SpellTier.AM,
            is_mb_active=False,
        )

    def chain_count(self) -> int:
        return len(self._chains)


# ---------------------------------------------------------
# Default catalog.
# ---------------------------------------------------------

_ELEMENT_BASE_NAME: dict[Element, str] = {
    Element.FIRE: "fire",
    Element.EARTH: "stone",
    Element.WATER: "water",
    Element.WIND: "aero",
    Element.ICE: "blizzard",
    Element.LIGHTNING: "thunder",
    Element.LIGHT: "banish",
    Element.DARK: "drain",
}


_TIER_NAMES: dict[SpellTier, str] = {
    SpellTier.I: "i",
    SpellTier.II: "ii",
    SpellTier.III: "iii",
    SpellTier.IV: "iv",
    SpellTier.V: "v",
}


_HAND_GLOW_BY_ELEMENT: dict[Element, str] = {
    Element.FIRE: "hand_glow_warm",
    Element.EARTH: "hand_glow_warm",
    Element.WATER: "hand_glow_cool",
    Element.WIND: "hand_glow_cool",
    Element.ICE: "hand_glow_cool",
    Element.LIGHTNING: "hand_glow_warm",
    Element.LIGHT: "hand_glow_warm",
    Element.DARK: "hand_glow_cool",
}


_CASTING_CIRCLE_BY_ELEMENT: dict[Element, str] = {
    Element.LIGHT: "casting_circle_white",
    Element.DARK: "casting_circle_dark",
    Element.FIRE: "casting_circle_white",
    Element.EARTH: "casting_circle_white",
    Element.WATER: "casting_circle_white",
    Element.WIND: "casting_circle_white",
    Element.ICE: "casting_circle_white",
    Element.LIGHTNING: "casting_circle_white",
    Element.NONE: "casting_circle_white",
}


def _tier_base_shake(tier: SpellTier) -> float:
    if tier == SpellTier.I: return 0.10
    if tier == SpellTier.II: return 0.15
    if tier == SpellTier.III: return 0.22
    if tier == SpellTier.IV: return 0.32
    if tier == SpellTier.V: return 0.45
    if tier == SpellTier.AM: return 0.65
    return 0.0


def _tier_base_light(tier: SpellTier) -> float:
    if tier == SpellTier.I: return 800.0
    if tier == SpellTier.II: return 1600.0
    if tier == SpellTier.III: return 3200.0
    if tier == SpellTier.IV: return 6400.0
    if tier == SpellTier.V: return 12000.0
    if tier == SpellTier.AM: return 24000.0
    return 0.0


def populate_default_library(res: SpellVfxResolver) -> int:
    """Pre-populate canonical FFXI spell mappings: 8 elements
    x 5 tiers (40 elemental) + Cure I-V + Banish I-III +
    Raise I-III + Drain + Aspir + Sleep + Silence + Slow +
    Haste + Protect + Shell. Returns the number registered."""
    n = 0
    for elem in (
        Element.FIRE, Element.EARTH, Element.WATER, Element.WIND,
        Element.ICE, Element.LIGHTNING, Element.LIGHT, Element.DARK,
    ):
        base = _ELEMENT_BASE_NAME[elem]
        for tier, tname in _TIER_NAMES.items():
            spell_id = f"{base}_{tname}"
            element_vfx = f"{elem.value}_tier_{tname}"
            res.register_spell(spell_id, SpellVfxChain(
                spell_id=spell_id,
                casting_circle_vfx=_CASTING_CIRCLE_BY_ELEMENT[elem],
                hand_glow_left_vfx=_HAND_GLOW_BY_ELEMENT[elem],
                hand_glow_right_vfx=_HAND_GLOW_BY_ELEMENT[elem],
                projectile_or_aoe_vfx=element_vfx,
                impact_vfx="impact_flash_med",
                lingering_vfx=(
                    "ember_drift" if elem == Element.FIRE
                    and tier in (SpellTier.III, SpellTier.IV,
                                 SpellTier.V)
                    else None
                ),
                screen_shake_intensity=_tier_base_shake(tier),
                light_pulse_lux=_tier_base_light(tier),
                sound_event_id=f"sfx_{spell_id}",
                element=elem,
                tier=tier,
            ))
            n += 1

    # Ancient Magic: Flare, Freeze, Burst, Flood, Quake,
    # Tornado, Holy II, Comet — 8 spells.
    am_spells = (
        ("flare",   Element.FIRE),
        ("freeze",  Element.ICE),
        ("burst",   Element.LIGHTNING),
        ("flood",   Element.WATER),
        ("quake",   Element.EARTH),
        ("tornado", Element.WIND),
        ("holy_ii", Element.LIGHT),
        ("comet",   Element.DARK),
    )
    for spell_id, elem in am_spells:
        res.register_spell(spell_id, SpellVfxChain(
            spell_id=spell_id,
            casting_circle_vfx=_CASTING_CIRCLE_BY_ELEMENT[elem],
            hand_glow_left_vfx=_HAND_GLOW_BY_ELEMENT[elem],
            hand_glow_right_vfx=_HAND_GLOW_BY_ELEMENT[elem],
            projectile_or_aoe_vfx=f"{elem.value}_tier_v",
            impact_vfx="impact_flash_heavy",
            lingering_vfx=(
                "ember_storm" if elem == Element.FIRE else None
            ),
            screen_shake_intensity=_tier_base_shake(SpellTier.AM),
            light_pulse_lux=_tier_base_light(SpellTier.AM),
            sound_event_id=f"sfx_{spell_id}",
            element=elem,
            tier=SpellTier.AM,
        ))
        n += 1

    # Utility / status / heal spells.
    util_spells = (
        ("cure_i",   Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
        ("cure_ii",  Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
        ("cure_iii", Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
        ("cure_iv",  Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
        ("cure_v",   Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
        ("raise_i",   Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
        ("raise_ii",  Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
        ("raise_iii", Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
        ("drain",  Element.DARK, "casting_circle_dark",
            "impact_flash_med"),
        ("aspir",  Element.DARK, "casting_circle_dark",
            "impact_flash_med"),
        ("sleep",  Element.DARK, "casting_circle_dark",
            "impact_flash_med"),
        ("silence", Element.NONE, "casting_circle_white",
            "impact_flash_med"),
        ("slow",   Element.NONE, "casting_circle_white",
            "impact_flash_med"),
        ("haste",  Element.NONE, "casting_circle_white",
            "impact_flash_med"),
        ("protect",  Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
        ("shell",  Element.LIGHT, "casting_circle_white",
            "raise_glow_white"),
    )
    for spell_id, elem, circle, impact in util_spells:
        hand = (
            "hand_glow_warm"
            if elem in (Element.FIRE, Element.LIGHT,
                        Element.LIGHTNING, Element.EARTH)
            else "hand_glow_cool"
        )
        res.register_spell(spell_id, SpellVfxChain(
            spell_id=spell_id,
            casting_circle_vfx=circle,
            hand_glow_left_vfx=hand,
            hand_glow_right_vfx=hand,
            projectile_or_aoe_vfx=None,
            impact_vfx=impact,
            lingering_vfx=None,
            screen_shake_intensity=0.0,
            light_pulse_lux=400.0,
            sound_event_id=f"sfx_{spell_id}",
            element=elem,
            tier=SpellTier.UTIL,
        ))
        n += 1

    return n


__all__ = [
    "Element",
    "SpellTier",
    "SpellVfxChain",
    "ResolvedSpellVfx",
    "MbOverlay",
    "SpellVfxResolver",
    "populate_default_library",
]
