"""13-family bestiary catalog from MOB_CLASS_LIBRARY.md.

Each MobFamily is the parent of 4-6 sub-variants. Element affinity
follows MOB_RESISTANCES.md: matching = 0.5x, weak-to = 1.25x,
strong-vs = 0.75x, neutral = 1.0x.

Boss authors pick a family, override specifics in BOSS_GRAMMAR.md
Layer 1, and ship a new boss in 4-6 hours.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Element(str, enum.Enum):
    FIRE = "fire"
    ICE = "ice"
    WATER = "water"
    LIGHTNING = "lightning"
    EARTH = "earth"
    WIND = "wind"
    LIGHT = "light"
    DARK = "dark"
    VARIABLE = "variable"          # Slime, Dragon — per-individual
    NONE = "none"                   # Demon NM resists_all


class FamilyId(str, enum.Enum):
    """The 13 doc-named families."""
    QUADAV = "quadav"
    YAGUDO = "yagudo"
    ORC = "orc"
    GOBLIN = "goblin"
    TONBERRY = "tonberry"
    NAGA = "naga"
    BEE = "bee"
    SLIME = "slime"
    SKELETON = "skeleton"
    SAHAGIN = "sahagin"
    BUG = "bug"
    DEMON = "demon"
    DRAGON = "dragon"


@dataclasses.dataclass(frozen=True)
class MobFamily:
    """One row of the 13-family table."""
    family: FamilyId
    label: str
    home_zone: str                 # canonical FFXI home (e.g. Beadeaux)
    affinity: Element              # element the family casts
    weak_to: tuple[Element, ...]   # elements that hit hard
    strong_vs: tuple[Element, ...] # elements they resist
    voice_tone: str                # 'gruff_croaking' / 'high_chittering'
    voice_punctuation: str         # e.g. 'Quadav-shell click'
    rl_policy_archetype: str       # ONNX policy class name
    notes: str = ""


FAMILIES: dict[FamilyId, MobFamily] = {
    FamilyId.QUADAV: MobFamily(
        family=FamilyId.QUADAV, label="Quadav (turtle-folk)",
        home_zone="beadeaux",
        affinity=Element.LIGHTNING,
        weak_to=(Element.WATER,),
        strong_vs=(Element.WIND,),
        voice_tone="gruff_croaking",
        voice_punctuation="quadav_shell_click",
        rl_policy_archetype="heavy_armor_close_combat",
        notes="Slow to start, devastating up close",
    ),
    FamilyId.YAGUDO: MobFamily(
        family=FamilyId.YAGUDO, label="Yagudo (bird-folk)",
        home_zone="castle_oztroja",
        affinity=Element.WATER,
        weak_to=(Element.LIGHTNING,),
        strong_vs=(Element.FIRE,),
        voice_tone="high_chittering",
        voice_punctuation="feather_rustle",
        rl_policy_archetype="religious_caster_ranged",
        notes="Religious order; cast spells; well-organized",
    ),
    FamilyId.ORC: MobFamily(
        family=FamilyId.ORC, label="Orc (warrior-people)",
        home_zone="davoi",
        affinity=Element.FIRE,
        weak_to=(Element.ICE,),
        strong_vs=(Element.WIND,),
        voice_tone="deep_guttural",
        voice_punctuation="chest_beat",
        rl_policy_archetype="heavy_weapon_blood_knight",
        notes="Heavy weapons + heavy armor + blood-knight aesthetic",
    ),
    FamilyId.GOBLIN: MobFamily(
        family=FamilyId.GOBLIN, label="Goblin (opportunist-people)",
        home_zone="ronfaure",
        affinity=Element.EARTH,
        weak_to=(Element.WIND,),
        strong_vs=(Element.LIGHTNING,),
        voice_tone="high_cackle",
        voice_punctuation="heh_heh_heh",
        rl_policy_archetype="opportunist_pickpocket",
        notes="Bombs, pickpockets, smiths, traders",
    ),
    FamilyId.TONBERRY: MobFamily(
        family=FamilyId.TONBERRY, label="Tonberry (creep-people)",
        home_zone="kuftal_tunnel",
        affinity=Element.DARK,
        weak_to=(Element.LIGHT,),
        strong_vs=(),
        voice_tone="whispered_shuffling",
        voice_punctuation="step_creak_silence",
        rl_policy_archetype="slow_pursuit_lethal",
        notes="Slow, lethal, terrifying. The knife and lantern iconic mob.",
    ),
    FamilyId.NAGA: MobFamily(
        family=FamilyId.NAGA, label="Naga (NIN serpent-folk)",
        home_zone="phomiuna_aqueducts",
        affinity=Element.WATER,
        weak_to=(Element.LIGHTNING,),
        strong_vs=(),
        voice_tone="hissing",
        voice_punctuation="chakra_flow",
        rl_policy_archetype="ninja_sprint_caster",
        notes="Sprinting NIN casters using hand signs (NIN_HAND_SIGNS)",
    ),
    FamilyId.BEE: MobFamily(
        family=FamilyId.BEE, label="Bee",
        home_zone="ronfaure",
        affinity=Element.WIND,
        weak_to=(Element.ICE,),
        strong_vs=(),
        voice_tone="buzzing",
        voice_punctuation="wing_thrum",
        rl_policy_archetype="aerial_swarm",
    ),
    FamilyId.SLIME: MobFamily(
        family=FamilyId.SLIME, label="Slime",
        home_zone="korroloka_tunnel",
        affinity=Element.VARIABLE,    # rotates per-zone
        weak_to=(),                    # variable
        strong_vs=(),
        voice_tone="wet_squelch",
        voice_punctuation="goo_drip",
        rl_policy_archetype="bouncing_engulf",
        notes="Element rotates per zone; caller supplies at spawn",
    ),
    FamilyId.SKELETON: MobFamily(
        family=FamilyId.SKELETON, label="Skeleton",
        home_zone="kingdom_dynamis",
        affinity=Element.DARK,
        weak_to=(Element.LIGHT,),
        strong_vs=(),
        voice_tone="bone_clatter",
        voice_punctuation="jaw_crack",
        rl_policy_archetype="undead_close_combat",
    ),
    FamilyId.SAHAGIN: MobFamily(
        family=FamilyId.SAHAGIN, label="Sahagin",
        home_zone="sea_serpent_grotto",
        affinity=Element.WATER,
        weak_to=(Element.LIGHTNING,),
        strong_vs=(Element.FIRE,),
        voice_tone="gurgled_speech",
        voice_punctuation="water_splash",
        rl_policy_archetype="amphibious_lariat",
    ),
    FamilyId.BUG: MobFamily(
        family=FamilyId.BUG, label="Bug",
        home_zone="korroloka_tunnel",
        affinity=Element.EARTH,
        weak_to=(Element.WIND,),
        strong_vs=(),
        voice_tone="chitin_clicks",
        voice_punctuation="mandible_snap",
        rl_policy_archetype="swarm_pollen",
    ),
    FamilyId.DEMON: MobFamily(
        family=FamilyId.DEMON, label="Demon NM",
        home_zone="dynamis_xarcabard",
        affinity=Element.DARK,
        weak_to=(Element.LIGHT,),
        strong_vs=(Element.FIRE, Element.ICE, Element.WATER,
                      Element.LIGHTNING, Element.EARTH, Element.WIND,
                      Element.DARK),    # resists_all except light
        voice_tone="commanding_baritone",
        voice_punctuation="hellfire_breath",
        rl_policy_archetype="apex_caster_arena_aoe",
        notes="resists_all flag — only Light cuts through",
    ),
    FamilyId.DRAGON: MobFamily(
        family=FamilyId.DRAGON, label="Dragon NM",
        home_zone="dragons_aery",
        affinity=Element.VARIABLE,
        weak_to=(),                    # per-individual
        strong_vs=(),
        voice_tone="rumbling_roar",
        voice_punctuation="wingbeat_thunder",
        rl_policy_archetype="dragon_telegraph_wide",
        notes="Variable affinity per individual; caller supplies at spawn",
    ),
}


def get_family(family: FamilyId) -> MobFamily:
    return FAMILIES[family]


def all_families() -> tuple[MobFamily, ...]:
    return tuple(FAMILIES.values())


def family_count() -> int:
    return len(FAMILIES)
