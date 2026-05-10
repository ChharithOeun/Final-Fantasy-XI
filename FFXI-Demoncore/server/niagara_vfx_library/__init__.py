"""Niagara VFX library — particle effect catalog.

The catalog of every particle effect the game can play.
Sixty-plus canonical effects covering all eight FFXI
elemental families at every spell tier (I/II/III/IV/V), the
physical impact effects (blood, sparks, smoke, dust, ember,
debris), the environment dressers (heat haze, rain splash),
the gameplay overlays (AOE telegraph rings + lines, impact
flashes, casting circles, hand glows, magic-burst halos, KO
auras, raise glows). Every effect carries a cinematic_tier
that scales the particle count up to 4x for the trailer
shot, a follows_emitter flag (the spark trail of a moving
weapon strike sticks to the blade; an explosion ring stays
where it was spawned), and a sound cue id that the audio
listener picks up.

The library does not own simulation; it owns *vocabulary*.
Real Niagara systems (built in UE5) live in the assets
folder and are referenced by vfx_id. This module is the
table of contents the engine consults at runtime to know
how big a fire_v cast should be (HIGH-tier, 800 particles
at LOW count, scaled to 3200 in the trailer shot) and
whether to pre-warm it before the cast (yes — anything over
500 particles gets a warmup recommendation so the first
frame doesn't hitch).

Public surface
--------------
    VfxKind enum
    VfxElement enum
    CinematicTier enum
    ComputeMode enum
    VfxEffect dataclass (frozen)
    VfxLibrary
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class VfxKind(enum.Enum):
    ELEMENT_FIRE = "element_fire"
    ELEMENT_ICE = "element_ice"
    ELEMENT_LIGHTNING = "element_lightning"
    ELEMENT_WATER = "element_water"
    ELEMENT_EARTH = "element_earth"
    ELEMENT_WIND = "element_wind"
    ELEMENT_LIGHT = "element_light"
    ELEMENT_DARK = "element_dark"
    PHYS_BLOOD = "phys_blood"
    PHYS_SPARK = "phys_spark"
    PHYS_SMOKE = "phys_smoke"
    PHYS_DUST = "phys_dust"
    PHYS_EMBER = "phys_ember"
    PHYS_DEBRIS = "phys_debris"
    ENV_HEAT_HAZE = "env_heat_haze"
    ENV_RAIN_SPLASH = "env_rain_splash"
    AOE_TELEGRAPH_RING = "aoe_telegraph_ring"
    AOE_TELEGRAPH_LINE = "aoe_telegraph_line"
    IMPACT_FLASH = "impact_flash"
    CASTING_CIRCLE = "casting_circle"
    HAND_GLOW = "hand_glow"
    MB_HALO = "mb_halo"
    KO_AURA = "ko_aura"
    RAISE_GLOW = "raise_glow"


class VfxElement(enum.Enum):
    FIRE = "fire"
    EARTH = "earth"
    WATER = "water"
    WIND = "wind"
    ICE = "ice"
    LIGHTNING = "lightning"
    LIGHT = "light"
    DARK = "dark"
    NONE = "none"


class CinematicTier(enum.Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"
    TRAILER = "trailer"


class ComputeMode(enum.Enum):
    GPU = "gpu"
    CPU = "cpu"


_KIND_TO_ELEMENT: dict[VfxKind, VfxElement] = {
    VfxKind.ELEMENT_FIRE: VfxElement.FIRE,
    VfxKind.ELEMENT_ICE: VfxElement.ICE,
    VfxKind.ELEMENT_LIGHTNING: VfxElement.LIGHTNING,
    VfxKind.ELEMENT_WATER: VfxElement.WATER,
    VfxKind.ELEMENT_EARTH: VfxElement.EARTH,
    VfxKind.ELEMENT_WIND: VfxElement.WIND,
    VfxKind.ELEMENT_LIGHT: VfxElement.LIGHT,
    VfxKind.ELEMENT_DARK: VfxElement.DARK,
}


_TIER_MULTIPLIER: dict[CinematicTier, float] = {
    CinematicTier.LOW: 1.0,
    CinematicTier.MED: 2.0,
    CinematicTier.HIGH: 3.0,
    CinematicTier.TRAILER: 4.0,
}


# Effects with more than this many base particles will be
# flagged as "warmup recommended" so the engine can fire a
# zero-emit pre-pass on the GPU before the player sees the
# first cast frame.
WARMUP_THRESHOLD = 500


@dataclasses.dataclass(frozen=True)
class VfxEffect:
    vfx_id: str
    name: str
    kind: VfxKind
    base_particle_count: int
    duration_s: float
    compute: ComputeMode
    follows_emitter: bool
    cinematic_tier: CinematicTier
    base_color_hex: str
    secondary_color_hex: str
    sound_cue_id: str
    light_emit_lux: float


@dataclasses.dataclass
class VfxLibrary:
    _effects: dict[str, VfxEffect] = dataclasses.field(
        default_factory=dict,
    )

    def register_effect(self, effect: VfxEffect) -> None:
        if not effect.vfx_id:
            raise ValueError("vfx_id required")
        if effect.duration_s <= 0:
            raise ValueError("duration_s must be > 0")
        if effect.base_particle_count < 0:
            raise ValueError("base_particle_count must be >= 0")
        if effect.vfx_id in self._effects:
            raise ValueError(
                f"duplicate vfx_id: {effect.vfx_id}",
            )
        self._effects[effect.vfx_id] = effect

    def lookup(self, vfx_id: str) -> VfxEffect:
        if vfx_id not in self._effects:
            raise KeyError(f"unknown vfx_id: {vfx_id}")
        return self._effects[vfx_id]

    def effects_with_kind(
        self, kind: VfxKind,
    ) -> tuple[VfxEffect, ...]:
        return tuple(
            sorted(
                (e for e in self._effects.values() if e.kind == kind),
                key=lambda e: e.vfx_id,
            )
        )

    def effects_for_element(
        self, element: VfxElement,
    ) -> tuple[VfxEffect, ...]:
        return tuple(
            sorted(
                (
                    e for e in self._effects.values()
                    if _KIND_TO_ELEMENT.get(e.kind) == element
                ),
                key=lambda e: e.vfx_id,
            )
        )

    def tier_scaled_particle_count(
        self, vfx_id: str, tier: CinematicTier,
    ) -> int:
        eff = self.lookup(vfx_id)
        mult = _TIER_MULTIPLIER[tier]
        return int(round(eff.base_particle_count * mult))

    def warmup_recommended(self, vfx_id: str) -> bool:
        eff = self.lookup(vfx_id)
        return eff.base_particle_count >= WARMUP_THRESHOLD

    def all_effect_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._effects.keys()))

    def effect_count(self) -> int:
        return len(self._effects)


# ---------------------------------------------------------
# Default catalog — 60+ canonical effects pre-populated.
# ---------------------------------------------------------

_ELEMENT_PALETTE: dict[VfxKind, tuple[str, str]] = {
    VfxKind.ELEMENT_FIRE: ("#ff5520", "#ffd060"),
    VfxKind.ELEMENT_ICE: ("#a8e0ff", "#ffffff"),
    VfxKind.ELEMENT_LIGHTNING: ("#fff060", "#a060ff"),
    VfxKind.ELEMENT_WATER: ("#3080ff", "#a0d0ff"),
    VfxKind.ELEMENT_EARTH: ("#a07840", "#603020"),
    VfxKind.ELEMENT_WIND: ("#a0ff90", "#e0ffe0"),
    VfxKind.ELEMENT_LIGHT: ("#ffffff", "#fff8a0"),
    VfxKind.ELEMENT_DARK: ("#200030", "#5010a0"),
}


# Tier rows: (tier_label, base_count, duration_s, light_lux,
#             cinematic_tier).
# The tier-V row gets HIGH cinematic with bigger numbers
# even at LOW tier — Ancient Magic is meant to feel huge.
_TIER_ROWS: tuple[
    tuple[str, int, float, float, CinematicTier], ...
] = (
    ("tier_I",  120,  1.6,  600.0,  CinematicTier.LOW),
    ("tier_II", 220,  2.0, 1200.0,  CinematicTier.MED),
    ("tier_III", 380, 2.4, 2400.0,  CinematicTier.MED),
    ("tier_IV", 600,  3.0, 4800.0,  CinematicTier.HIGH),
    ("tier_V",  900,  4.0, 9600.0,  CinematicTier.HIGH),
)


def _element_kind(elem: VfxElement) -> VfxKind:
    for k, e in _KIND_TO_ELEMENT.items():
        if e == elem:
            return k
    raise ValueError(f"no kind for element: {elem}")


def populate_default_library(lib: VfxLibrary) -> int:
    """Pre-populate canonical FFXI elemental tiers + the
    physical / overlay / environmental effects. Returns
    the number of effects registered (>= 60)."""
    n = 0
    # 8 elements x 5 tiers = 40 elemental effects.
    for elem in (
        VfxElement.FIRE, VfxElement.ICE, VfxElement.LIGHTNING,
        VfxElement.WATER, VfxElement.EARTH, VfxElement.WIND,
        VfxElement.LIGHT, VfxElement.DARK,
    ):
        kind = _element_kind(elem)
        base, second = _ELEMENT_PALETTE[kind]
        for tier_label, pcount, dur, lux, ctier in _TIER_ROWS:
            vfx_id = f"{elem.value}_{tier_label.lower()}"
            lib.register_effect(VfxEffect(
                vfx_id=vfx_id,
                name=f"{elem.value.title()} {tier_label}",
                kind=kind,
                base_particle_count=pcount,
                duration_s=dur,
                compute=ComputeMode.GPU,
                follows_emitter=False,
                cinematic_tier=ctier,
                base_color_hex=base,
                secondary_color_hex=second,
                sound_cue_id=f"sfx_spell_{elem.value}_{tier_label.lower()}",
                light_emit_lux=lux,
            ))
            n += 1
    # Physical impact set — 12 entries.
    physicals = (
        ("blood_light", VfxKind.PHYS_BLOOD, 60, 0.6,
            "#a01010", "#400808", 0.0),
        ("blood_heavy", VfxKind.PHYS_BLOOD, 220, 1.2,
            "#c01010", "#500808", 0.0),
        ("spark_metal", VfxKind.PHYS_SPARK, 90, 0.5,
            "#fff080", "#ffa040", 80.0),
        ("spark_metal_heavy", VfxKind.PHYS_SPARK, 280, 0.8,
            "#fff080", "#ffa040", 200.0),
        ("smoke_burst", VfxKind.PHYS_SMOKE, 200, 2.5,
            "#404040", "#202020", 0.0),
        ("smoke_lingering", VfxKind.PHYS_SMOKE, 520, 5.0,
            "#404040", "#202020", 0.0),
        ("dust_kickup", VfxKind.PHYS_DUST, 150, 1.5,
            "#a08850", "#604030", 0.0),
        ("dust_explosion", VfxKind.PHYS_DUST, 700, 3.0,
            "#a08850", "#604030", 0.0),
        ("ember_drift", VfxKind.PHYS_EMBER, 80, 4.0,
            "#ff8030", "#ffd060", 200.0),
        ("ember_storm", VfxKind.PHYS_EMBER, 600, 5.0,
            "#ff8030", "#ffd060", 800.0),
        ("debris_wood", VfxKind.PHYS_DEBRIS, 40, 2.0,
            "#604020", "#302010", 0.0),
        ("debris_stone", VfxKind.PHYS_DEBRIS, 80, 2.5,
            "#806060", "#403030", 0.0),
    )
    for vfx_id, kind, pcount, dur, base, sec, lux in physicals:
        lib.register_effect(VfxEffect(
            vfx_id=vfx_id,
            name=vfx_id.replace("_", " ").title(),
            kind=kind,
            base_particle_count=pcount,
            duration_s=dur,
            compute=ComputeMode.GPU,
            follows_emitter=(kind == VfxKind.PHYS_SPARK),
            cinematic_tier=CinematicTier.MED,
            base_color_hex=base,
            secondary_color_hex=sec,
            sound_cue_id=f"sfx_phys_{vfx_id}",
            light_emit_lux=lux,
        ))
        n += 1
    # Environmental ambient.
    envs = (
        ("env_heat_haze_desert", VfxKind.ENV_HEAT_HAZE,
            300, 6.0, "#ffeec0", "#ffd080"),
        ("env_rain_splash_med", VfxKind.ENV_RAIN_SPLASH,
            200, 1.0, "#a0c0ff", "#ffffff"),
        ("env_rain_splash_heavy", VfxKind.ENV_RAIN_SPLASH,
            600, 1.0, "#a0c0ff", "#ffffff"),
    )
    for vfx_id, kind, pcount, dur, base, sec in envs:
        lib.register_effect(VfxEffect(
            vfx_id=vfx_id,
            name=vfx_id.replace("_", " ").title(),
            kind=kind,
            base_particle_count=pcount,
            duration_s=dur,
            compute=ComputeMode.GPU,
            follows_emitter=False,
            cinematic_tier=CinematicTier.LOW,
            base_color_hex=base,
            secondary_color_hex=sec,
            sound_cue_id=f"sfx_amb_{vfx_id}",
            light_emit_lux=0.0,
        ))
        n += 1
    # Gameplay overlays.
    overlays = (
        ("aoe_ring_small", VfxKind.AOE_TELEGRAPH_RING, 80, 2.5,
            "#ff4040", "#ffa040", 0.0),
        ("aoe_ring_large", VfxKind.AOE_TELEGRAPH_RING, 200, 3.5,
            "#ff4040", "#ffa040", 0.0),
        ("aoe_line_cleave", VfxKind.AOE_TELEGRAPH_LINE, 120, 2.0,
            "#ff4040", "#ffa040", 0.0),
        ("impact_flash_med", VfxKind.IMPACT_FLASH, 60, 0.25,
            "#ffffff", "#fff8a0", 4000.0),
        ("impact_flash_heavy", VfxKind.IMPACT_FLASH, 180, 0.4,
            "#ffffff", "#fff8a0", 12000.0),
        ("casting_circle_white", VfxKind.CASTING_CIRCLE, 240, 2.0,
            "#fff8a0", "#ffffff", 200.0),
        ("casting_circle_dark", VfxKind.CASTING_CIRCLE, 240, 2.0,
            "#3010a0", "#100020", 100.0),
        ("hand_glow_warm", VfxKind.HAND_GLOW, 30, 1.5,
            "#ffd060", "#ffa040", 50.0),
        ("hand_glow_cool", VfxKind.HAND_GLOW, 30, 1.5,
            "#a0d0ff", "#ffffff", 50.0),
        ("mb_halo_default", VfxKind.MB_HALO, 520, 1.6,
            "#ffffff", "#ffd0ff", 8000.0),
        ("ko_aura_grey", VfxKind.KO_AURA, 100, 4.0,
            "#404040", "#202020", 0.0),
        ("raise_glow_white", VfxKind.RAISE_GLOW, 320, 3.0,
            "#ffffff", "#fff8a0", 6000.0),
    )
    for vfx_id, kind, pcount, dur, base, sec, lux in overlays:
        lib.register_effect(VfxEffect(
            vfx_id=vfx_id,
            name=vfx_id.replace("_", " ").title(),
            kind=kind,
            base_particle_count=pcount,
            duration_s=dur,
            compute=ComputeMode.GPU,
            follows_emitter=(kind in (
                VfxKind.HAND_GLOW, VfxKind.MB_HALO,
                VfxKind.KO_AURA, VfxKind.RAISE_GLOW,
            )),
            cinematic_tier=(
                CinematicTier.HIGH if kind == VfxKind.MB_HALO
                else CinematicTier.MED
            ),
            base_color_hex=base,
            secondary_color_hex=sec,
            sound_cue_id=f"sfx_ovl_{vfx_id}",
            light_emit_lux=lux,
        ))
        n += 1
    return n


__all__ = [
    "VfxKind",
    "VfxElement",
    "CinematicTier",
    "ComputeMode",
    "VfxEffect",
    "VfxLibrary",
    "WARMUP_THRESHOLD",
    "populate_default_library",
]
