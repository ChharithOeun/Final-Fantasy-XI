"""Weaponskill VFX — physical WS visual chain.

Physical weapon skills in FFXI are nothing without their
flash. The wind-up animation tells you damage is coming;
the blade trail follows the arc; the impact flash + dust
+ shockwave land the hit; the camera-anchored hitstop
holds the crunch for 40-250 ms; the skillchain glyph
blooms over the corpse if a chain closed. This module is
the table that wires every named WS to that chain. It is
the "make me feel it" budget.

Skillchain glyphs follow canonical FFXI lore:
Liquefaction is red/orange (fire), Scission is neutral
(earth), Impaction is yellow (lightning), Detonation is
green (wind), Induration is light blue (ice),
Reverberation is purple (water), Transfixion is neon-blue
(piercing), Compression is violet (smothering). Level-2
chains (Fusion, Fragmentation, Distortion, Gravitation)
get bright derived hues. Level-3 chains (Light,
Darkness) are spectrum/void. Level-4 (Crystal/Umbra) is
the rainbow-prism / void-black shimmer reserved for
big-fight setpieces.

Hitstop tuning is a single weight axis: light WS = 40 ms
(quick & flashy), medium = 80 ms, heavy = 150 ms (the
two-handed slammers), ultra = 250 ms (relic / mythic
finishers — the camera literally holds for a quarter
second on the killing blow).

Blade trails read the weapon class. Swords and katana
get an anamorphic-style ribbon: thin, taut, slightly
elongated horizontally, the kind of trail Akira Kurosawa
shot through. Axes and great-axes get broader trails —
heavier metal moves heavier light. Hand-to-Hand gets
nothing per-strike but a wrist-pulse glow when the chain
finisher fires.

Public surface
--------------
    WeaponClass enum
    HitstopWeight enum
    SkillchainAttribute enum
    WsVisualChain dataclass (frozen)
    SkillchainGlyph dataclass (frozen)
    BladeTrailProfile dataclass (frozen)
    WeaponskillVfxSystem
"""
from __future__ import annotations

import dataclasses
import enum


class WeaponClass(enum.Enum):
    SWORD = "sword"
    GREAT_SWORD = "great_sword"
    AXE = "axe"
    GREAT_AXE = "great_axe"
    SCYTHE = "scythe"
    POLEARM = "polearm"
    KATANA = "katana"
    GREAT_KATANA = "great_katana"
    CLUB = "club"
    STAFF = "staff"
    H2H = "h2h"
    DAGGER = "dagger"
    BOW = "bow"
    CROSSBOW = "crossbow"
    GUN = "gun"
    MARKSMAN = "marksman"


class HitstopWeight(enum.Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    ULTRA = "ultra"


class SkillchainAttribute(enum.Enum):
    # Level 2
    LIQUEFACTION = "liquefaction"
    SCISSION = "scission"
    IMPACTION = "impaction"
    DETONATION = "detonation"
    INDURATION = "induration"
    REVERBERATION = "reverberation"
    TRANSFIXION = "transfixion"
    COMPRESSION = "compression"
    # Level 2 derived
    FUSION = "fusion"
    FRAGMENTATION = "fragmentation"
    DISTORTION = "distortion"
    GRAVITATION = "gravitation"
    # Level 3
    LIGHT = "light"
    DARKNESS = "darkness"
    # Level 4
    CRYSTAL = "crystal"
    UMBRA = "umbra"


_HITSTOP_MS: dict[HitstopWeight, int] = {
    HitstopWeight.LIGHT:  40,
    HitstopWeight.MEDIUM: 80,
    HitstopWeight.HEAVY: 150,
    HitstopWeight.ULTRA: 250,
}


_GLYPH_COLORS: dict[SkillchainAttribute, str] = {
    SkillchainAttribute.LIQUEFACTION: "red_orange",
    SkillchainAttribute.SCISSION: "neutral_flicker",
    SkillchainAttribute.IMPACTION: "yellow",
    SkillchainAttribute.DETONATION: "green",
    SkillchainAttribute.INDURATION: "light_blue",
    SkillchainAttribute.REVERBERATION: "purple",
    SkillchainAttribute.TRANSFIXION: "neon_blue",
    SkillchainAttribute.COMPRESSION: "violet",
    SkillchainAttribute.FUSION: "bright_yellow",
    SkillchainAttribute.FRAGMENTATION: "cyan",
    SkillchainAttribute.DISTORTION: "ice_blue",
    SkillchainAttribute.GRAVITATION: "dark_purple",
    SkillchainAttribute.LIGHT: "white_spectrum",
    SkillchainAttribute.DARKNESS: "black_with_edge",
    SkillchainAttribute.CRYSTAL: "rainbow_prism",
    SkillchainAttribute.UMBRA: "void_black",
}


# Anamorphic-style: thin & elongated. Broader: chunkier
# ribbons for heavy-class weapons.
_ANAMORPHIC = frozenset({
    WeaponClass.SWORD,
    WeaponClass.KATANA,
    WeaponClass.GREAT_KATANA,
    WeaponClass.DAGGER,
})

_BROAD = frozenset({
    WeaponClass.AXE,
    WeaponClass.GREAT_AXE,
    WeaponClass.GREAT_SWORD,
    WeaponClass.CLUB,
    WeaponClass.SCYTHE,
})


@dataclasses.dataclass(frozen=True)
class WsVisualChain:
    ws_id: str
    weapon_class: WeaponClass
    wind_up_anim_id: str
    blade_trail_color: str
    blade_trail_thickness: float
    impact_flash_vfx_id: str
    blood_arc_count: int
    dust_burst_id: str
    shockwave_id: str
    screen_shake_intensity: float
    hitstop_ms: int
    camera_shake_axis: str  # e.g. "xy", "yz", "z"


@dataclasses.dataclass(frozen=True)
class SkillchainGlyph:
    attribute: SkillchainAttribute
    color: str
    runic_pattern_id: str
    sustain_duration_s: float
    magic_burst_extends_duration_s: float


@dataclasses.dataclass(frozen=True)
class BladeTrailProfile:
    style: str         # "anamorphic" | "broad" | "minimal"
    thickness: float
    elongation: float


def hitstop_for(weight: HitstopWeight) -> int:
    return _HITSTOP_MS[weight]


def glyph_color(attribute: SkillchainAttribute) -> str:
    return _GLYPH_COLORS[attribute]


def blade_trail_for_weapon(
    weapon_class: WeaponClass,
) -> BladeTrailProfile:
    if weapon_class in _ANAMORPHIC:
        return BladeTrailProfile(
            style="anamorphic",
            thickness=0.05,
            elongation=2.5,
        )
    if weapon_class in _BROAD:
        return BladeTrailProfile(
            style="broad",
            thickness=0.18,
            elongation=1.1,
        )
    return BladeTrailProfile(
        style="minimal",
        thickness=0.02,
        elongation=1.0,
    )


@dataclasses.dataclass
class WeaponskillVfxSystem:
    _chains: dict[str, WsVisualChain] = dataclasses.field(
        default_factory=dict,
    )
    _glyphs: dict[
        SkillchainAttribute, SkillchainGlyph,
    ] = dataclasses.field(default_factory=dict)

    def register_ws(
        self, ws_id: str, chain: WsVisualChain,
    ) -> None:
        if not ws_id:
            raise ValueError("ws_id required")
        if chain.ws_id != ws_id:
            raise ValueError(
                "chain.ws_id must match ws_id",
            )
        if ws_id in self._chains:
            raise ValueError(f"duplicate ws_id: {ws_id}")
        self._chains[ws_id] = chain

    def register_glyph(self, glyph: SkillchainGlyph) -> None:
        self._glyphs[glyph.attribute] = glyph

    def resolve_ws_vfx(self, ws_id: str) -> WsVisualChain:
        if ws_id not in self._chains:
            raise KeyError(f"unknown ws: {ws_id}")
        return self._chains[ws_id]

    def glyph_for(
        self, attribute: SkillchainAttribute,
    ) -> SkillchainGlyph:
        if attribute not in self._glyphs:
            raise KeyError(
                f"no glyph registered for {attribute}",
            )
        return self._glyphs[attribute]

    def all_ws_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._chains.keys()))

    def chains_for_weapon(
        self, weapon_class: WeaponClass,
    ) -> tuple[WsVisualChain, ...]:
        return tuple(
            sorted(
                (c for c in self._chains.values()
                 if c.weapon_class == weapon_class),
                key=lambda c: c.ws_id,
            )
        )

    def ws_count(self) -> int:
        return len(self._chains)

    def glyph_count(self) -> int:
        return len(self._glyphs)


def populate_default_glyphs(
    sys: WeaponskillVfxSystem,
) -> int:
    """Register the canonical 16 skillchain glyphs."""
    n = 0
    for attr in SkillchainAttribute:
        # Level 3+4 sustain longer.
        if attr in (
            SkillchainAttribute.LIGHT,
            SkillchainAttribute.DARKNESS,
        ):
            sustain = 4.0
            mb_extend = 2.0
        elif attr in (
            SkillchainAttribute.CRYSTAL,
            SkillchainAttribute.UMBRA,
        ):
            sustain = 5.5
            mb_extend = 3.0
        else:
            sustain = 2.5
            mb_extend = 1.5
        sys.register_glyph(SkillchainGlyph(
            attribute=attr,
            color=_GLYPH_COLORS[attr],
            runic_pattern_id=f"runic_{attr.value}",
            sustain_duration_s=sustain,
            magic_burst_extends_duration_s=mb_extend,
        ))
        n += 1
    return n


# A starter catalog of canonical FFXI weaponskills mapped
# to representative weapon classes. Not exhaustive — these
# are the iconic ones the demo's combat beats use.
_DEFAULT_WS: tuple[
    tuple[str, WeaponClass, HitstopWeight], ...
] = (
    # Sword
    ("vorpal_blade", WeaponClass.SWORD, HitstopWeight.MEDIUM),
    ("savage_blade", WeaponClass.SWORD, HitstopWeight.HEAVY),
    ("knights_of_round", WeaponClass.SWORD, HitstopWeight.ULTRA),
    # Great Sword
    ("ground_strike", WeaponClass.GREAT_SWORD, HitstopWeight.HEAVY),
    ("scourge", WeaponClass.GREAT_SWORD, HitstopWeight.ULTRA),
    # Axe / Great Axe
    ("rampage", WeaponClass.AXE, HitstopWeight.MEDIUM),
    ("ruinator", WeaponClass.AXE, HitstopWeight.HEAVY),
    ("steel_cyclone", WeaponClass.GREAT_AXE, HitstopWeight.HEAVY),
    ("ukko_fury", WeaponClass.GREAT_AXE, HitstopWeight.ULTRA),
    # Scythe
    ("spiral_hell", WeaponClass.SCYTHE, HitstopWeight.HEAVY),
    ("entropy", WeaponClass.SCYTHE, HitstopWeight.ULTRA),
    # Polearm
    ("penta_thrust", WeaponClass.POLEARM, HitstopWeight.MEDIUM),
    ("camlanns_torment", WeaponClass.POLEARM, HitstopWeight.ULTRA),
    # Katana / Great Katana
    ("blade_of_jin", WeaponClass.KATANA, HitstopWeight.LIGHT),
    ("blade_of_ku", WeaponClass.KATANA, HitstopWeight.MEDIUM),
    ("tachi_kasha", WeaponClass.GREAT_KATANA, HitstopWeight.MEDIUM),
    ("tachi_shoha", WeaponClass.GREAT_KATANA, HitstopWeight.ULTRA),
    # Club / Staff
    ("hexa_strike", WeaponClass.CLUB, HitstopWeight.MEDIUM),
    ("realmrazer", WeaponClass.CLUB, HitstopWeight.HEAVY),
    ("retribution", WeaponClass.STAFF, HitstopWeight.HEAVY),
    # H2H
    ("ascetics_fury", WeaponClass.H2H, HitstopWeight.MEDIUM),
    ("victory_smite", WeaponClass.H2H, HitstopWeight.HEAVY),
    # Dagger
    ("evisceration", WeaponClass.DAGGER, HitstopWeight.LIGHT),
    ("rudras_storm", WeaponClass.DAGGER, HitstopWeight.HEAVY),
    # Bow / Crossbow / Gun
    ("namas_arrow", WeaponClass.BOW, HitstopWeight.HEAVY),
    ("jishnus_radiance", WeaponClass.BOW, HitstopWeight.MEDIUM),
    ("hot_shot", WeaponClass.GUN, HitstopWeight.MEDIUM),
    ("leaden_salute", WeaponClass.GUN, HitstopWeight.HEAVY),
    ("wildfire", WeaponClass.GUN, HitstopWeight.ULTRA),
)


def _trail_color_for(weapon: WeaponClass) -> str:
    if weapon in _BROAD:
        return "amber_metal"
    if weapon in _ANAMORPHIC:
        return "silver_blue"
    return "neutral_white"


def populate_default_ws_library(
    sys: WeaponskillVfxSystem,
) -> int:
    n = 0
    for ws_id, weapon, weight in _DEFAULT_WS:
        profile = blade_trail_for_weapon(weapon)
        # Iron Eater intro and the bandit raid use a heavy
        # impact + dust burst by default; lighter dagger /
        # katana hits get a lighter impact flash.
        if weight in (HitstopWeight.HEAVY, HitstopWeight.ULTRA):
            impact = "impact_flash_heavy"
            blood = 6
            dust = "dust_explosion"
            shockwave = "spark_metal_heavy"
            shake = 0.45 if weight == HitstopWeight.ULTRA else 0.3
        elif weight == HitstopWeight.MEDIUM:
            impact = "impact_flash_med"
            blood = 4
            dust = "dust_kickup"
            shockwave = "spark_metal"
            shake = 0.2
        else:  # LIGHT
            impact = "impact_flash_med"
            blood = 2
            dust = "dust_kickup"
            shockwave = "spark_metal"
            shake = 0.12
        sys.register_ws(ws_id, WsVisualChain(
            ws_id=ws_id,
            weapon_class=weapon,
            wind_up_anim_id=f"anim_ws_windup_{ws_id}",
            blade_trail_color=_trail_color_for(weapon),
            blade_trail_thickness=profile.thickness,
            impact_flash_vfx_id=impact,
            blood_arc_count=blood,
            dust_burst_id=dust,
            shockwave_id=shockwave,
            screen_shake_intensity=shake,
            hitstop_ms=hitstop_for(weight),
            camera_shake_axis=(
                "xyz" if weight == HitstopWeight.ULTRA else "xy"
            ),
        ))
        n += 1
    return n


__all__ = [
    "WeaponClass",
    "HitstopWeight",
    "SkillchainAttribute",
    "WsVisualChain",
    "SkillchainGlyph",
    "BladeTrailProfile",
    "WeaponskillVfxSystem",
    "hitstop_for",
    "glyph_color",
    "blade_trail_for_weapon",
    "populate_default_glyphs",
    "populate_default_ws_library",
]
