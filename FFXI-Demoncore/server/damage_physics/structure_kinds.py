"""Structure kinds — preset HP / heal-rate / material tables.

Anchored to the table in DAMAGE_PHYSICS_HEALING.md. Each preset names
the typical world prop, its hit points, the heal rate (HP per
real-world second), and the material class that drives Niagara VFX.

Heal rates use a tempo curve: stuff that breaks frequently (barrels,
lanterns) heals fast so the city looks normal between encounters.
Stuff that breaks rarely (gates, walls) heals slowly so a defended
siege still matters.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MaterialClass(str, enum.Enum):
    """Material drives the break/heal VFX preset."""
    WOOD = "wood"
    STONE_BRICK = "stone_brick"
    STONE_CARVED = "stone_carved"
    METAL_INDUSTRIAL = "metal_industrial"
    CLOTH_BANNER = "cloth_banner"
    GLASS_WINDOW = "glass_window"


@dataclasses.dataclass(frozen=True)
class VfxPreset:
    """Niagara VFX preset for a material class."""
    material: MaterialClass
    break_vfx: str
    heal_vfx: str
    break_sfx: str


VFX_PRESETS: dict[MaterialClass, VfxPreset] = {
    MaterialClass.WOOD: VfxPreset(
        material=MaterialClass.WOOD,
        break_vfx="splinters_plus_dust",
        heal_vfx="sap_shimmer_grain_glow",
        break_sfx="wood_crack",
    ),
    MaterialClass.STONE_BRICK: VfxPreset(
        material=MaterialClass.STONE_BRICK,
        break_vfx="rocks_plus_dust",
        heal_vfx="white_mineral_shimmer",
        break_sfx="stone_shatter",
    ),
    MaterialClass.STONE_CARVED: VfxPreset(
        material=MaterialClass.STONE_CARVED,
        break_vfx="rocks_plus_dust",
        heal_vfx="rune_shimmer_bastok",
        break_sfx="heavy_stone",
    ),
    MaterialClass.METAL_INDUSTRIAL: VfxPreset(
        material=MaterialClass.METAL_INDUSTRIAL,
        break_vfx="sparks_plus_smoke",
        heal_vfx="molten_weld_glow",
        break_sfx="metal_clang",
    ),
    MaterialClass.CLOTH_BANNER: VfxPreset(
        material=MaterialClass.CLOTH_BANNER,
        break_vfx="shred_fragments",
        heal_vfx="weave_loom_shimmer",
        break_sfx="cloth_tear",
    ),
    MaterialClass.GLASS_WINDOW: VfxPreset(
        material=MaterialClass.GLASS_WINDOW,
        break_vfx="shards",
        heal_vfx="crystalline_regrow",
        break_sfx="glass_shatter",
    ),
}


@dataclasses.dataclass(frozen=True)
class StructurePreset:
    """One row in the heal-rate tuning table."""
    kind: str
    hp_max: int
    heal_rate: float                    # HP per real-world second
    heal_delay_s: float                 # 'no damage taken' before heal starts
    material: MaterialClass
    permanent_threshold: float = 1.0    # 1.0 = never permanent
    label: str = ""

    @property
    def full_heal_seconds(self) -> float:
        """Time to fully heal from 0 HP. Only meaningful for tuning;
        actual play time is rarely this long because most damage tops
        out below max."""
        if self.heal_rate <= 0:
            return float("inf")
        return self.hp_max / self.heal_rate


# Default heal_delay tuning per material — stone takes longer to start
# stitching than wood splinters. Doc says 8-15 s typical.
DEFAULT_HEAL_DELAY_S: dict[MaterialClass, float] = {
    MaterialClass.WOOD: 8.0,
    MaterialClass.CLOTH_BANNER: 8.0,
    MaterialClass.GLASS_WINDOW: 10.0,
    MaterialClass.METAL_INDUSTRIAL: 12.0,
    MaterialClass.STONE_BRICK: 15.0,
    MaterialClass.STONE_CARVED: 15.0,
}


# Master preset table from the doc's tuning anchors block.
STRUCTURE_PRESETS: dict[str, StructurePreset] = {
    "barrel": StructurePreset(
        kind="barrel", hp_max=100, heal_rate=5.0,
        heal_delay_s=8.0, material=MaterialClass.WOOD,
        label="Barrel",
    ),
    "crate_stack": StructurePreset(
        kind="crate_stack", hp_max=200, heal_rate=5.0,
        heal_delay_s=8.0, material=MaterialClass.WOOD,
        label="Crate stack",
    ),
    "wooden_cart": StructurePreset(
        kind="wooden_cart", hp_max=500, heal_rate=5.0,
        heal_delay_s=8.0, material=MaterialClass.WOOD,
        label="Wooden cart",
    ),
    "lantern_post": StructurePreset(
        kind="lantern_post", hp_max=80, heal_rate=4.0,
        heal_delay_s=8.0, material=MaterialClass.METAL_INDUSTRIAL,
        label="Lantern post",
    ),
    "vendor_stall_awning": StructurePreset(
        kind="vendor_stall_awning", hp_max=300, heal_rate=3.0,
        heal_delay_s=8.0, material=MaterialClass.CLOTH_BANNER,
        label="Vendor stall awning",
    ),
    "wooden_palisade_segment": StructurePreset(
        kind="wooden_palisade_segment", hp_max=2_000, heal_rate=8.0,
        heal_delay_s=10.0, material=MaterialClass.WOOD,
        label="Wooden palisade segment",
    ),
    "stone_wall_section": StructurePreset(
        kind="stone_wall_section", hp_max=50_000, heal_rate=30.0,
        heal_delay_s=15.0, material=MaterialClass.STONE_BRICK,
        permanent_threshold=0.05,    # iconic-tier scarable
        label="Stone wall section",
    ),
    "bastok_city_gate": StructurePreset(
        kind="bastok_city_gate", hp_max=200_000, heal_rate=50.0,
        heal_delay_s=15.0, material=MaterialClass.STONE_CARVED,
        permanent_threshold=0.05,
        label="Bastok city gate",
    ),
    "castle_tower": StructurePreset(
        kind="castle_tower", hp_max=1_000_000, heal_rate=80.0,
        heal_delay_s=15.0, material=MaterialClass.STONE_CARVED,
        permanent_threshold=0.05,
        label="Castle tower",
    ),
}


def get_preset(kind: str) -> t.Optional[StructurePreset]:
    """Look up a preset by kind name."""
    return STRUCTURE_PRESETS.get(kind)


def is_iconic(kind: str) -> bool:
    """Iconic structures (gates, walls, towers) can scar permanently
    via low permanent_threshold. Doc: '~1% of structures'."""
    preset = STRUCTURE_PRESETS.get(kind)
    if preset is None:
        return False
    return preset.permanent_threshold < 1.0
