"""Sub-variant catalog — per-family job specialization rows.

Each family has 3-6 sub-variants spanning level 1-90 per the doc.
Sub-variant defines level band, role tag, signature attack name +
AOE shape (per AOE_TELEGRAPH.md geometry).
"""
from __future__ import annotations

import dataclasses
import enum

from .families import FamilyId


class MobRole(str, enum.Enum):
    """Per-class role tag for encounter composition."""
    FRONTLINE = "frontline"
    TANK = "tank"
    LEADER = "leader"
    TRAP_LAYER = "trap_layer"
    HEALER = "healer"
    HIGH_TIER_TANK = "high_tier_tank"
    SCOUT = "scout"
    MID_BOSS = "mid_boss"
    HIGH_RANK = "high_rank"
    QUEST_GIVER = "quest_giver"
    SUICIDE_ATTACKER = "suicide_attacker"
    SLOW_PURSUIT = "slow_pursuit"
    NM = "nm"
    ENDGAME_NM = "endgame_nm"
    SPRINT_NIN = "sprint_nin"


@dataclasses.dataclass(frozen=True)
class SubVariant:
    """One row in a family's sub-variant table."""
    sub_variant_id: str
    family: FamilyId
    label: str
    level_min: int
    level_max: int
    role: MobRole
    signature_skill: str
    skill_aoe_shape: str           # 'cone' / 'circle' / 'line' / etc.
    notes: str = ""


# Doc-named sub-variants. Roughly 4-6 per family for the families
# the doc lists; the compressed families (Bee through Dragon) get
# 1-2 representatives each — more can be authored as level design
# reaches those zones.
SUB_VARIANTS: dict[str, SubVariant] = {}


def _add(sv: SubVariant) -> None:
    SUB_VARIANTS[sv.sub_variant_id] = sv


# Quadav (6)
_add(SubVariant("quadav_footsoldier", FamilyId.QUADAV,
                   "Quadav Footsoldier", 8, 15,
                   MobRole.FRONTLINE, "shield_bash", "cone"))
_add(SubVariant("quadav_roundshield", FamilyId.QUADAV,
                   "Quadav Roundshield", 12, 20,
                   MobRole.TANK, "tortoise_stomp", "circle"))
_add(SubVariant("quadav_helmsman", FamilyId.QUADAV,
                   "Quadav Helmsman", 18, 28,
                   MobRole.LEADER, "scaled_mail", "self_buff"))
_add(SubVariant("quadav_minelayer", FamilyId.QUADAV,
                   "Quadav Minelayer", 20, 30,
                   MobRole.TRAP_LAYER, "mine_trap", "placed_aoe"))
_add(SubVariant("quadav_healer", FamilyId.QUADAV,
                   "Quadav Healer", 25, 35,
                   MobRole.HEALER, "cure_intervention",
                   "single_target",
                   notes="mob-side intervention timing per INTERVENTION_MB"))
_add(SubVariant("quadav_lifeguard", FamilyId.QUADAV,
                   "Quadav Lifeguard", 30, 40,
                   MobRole.HIGH_TIER_TANK, "drainkiss",
                   "single_target"))

# Yagudo (5)
_add(SubVariant("yagudo_acolyte", FamilyId.YAGUDO,
                   "Yagudo Acolyte", 10, 18,
                   MobRole.FRONTLINE, "beak_lunge", "line"))
_add(SubVariant("yagudo_initiate", FamilyId.YAGUDO,
                   "Yagudo Initiate", 15, 25,
                   MobRole.SCOUT, "choke_breath", "cone"))
_add(SubVariant("yagudo_cleric", FamilyId.YAGUDO,
                   "Yagudo Cleric", 20, 30,
                   MobRole.HEALER, "banishga", "circle"))
_add(SubVariant("yagudo_avatar", FamilyId.YAGUDO,
                   "Yagudo Avatar", 30, 45,
                   MobRole.MID_BOSS, "hundred_wings", "multi_line"))
_add(SubVariant("yagudo_high_priest", FamilyId.YAGUDO,
                   "Yagudo High Priest", 40, 55,
                   MobRole.HIGH_RANK, "holy_cross", "donut"))

# Orc (4)
_add(SubVariant("orc_footsoldier", FamilyId.ORC,
                   "Orc Footsoldier", 10, 20,
                   MobRole.FRONTLINE, "cleaver", "line"))
_add(SubVariant("orc_trooper", FamilyId.ORC,
                   "Orc Trooper", 18, 28,
                   MobRole.FRONTLINE, "headbutt", "single_target"))
_add(SubVariant("orc_warmachine", FamilyId.ORC,
                   "Orc Warmachine", 30, 45,
                   MobRole.HIGH_TIER_TANK, "earth_crusher", "donut"))
_add(SubVariant("orc_crouchlear", FamilyId.ORC,
                   "Orc Crouchlear", 40, 55,
                   MobRole.MID_BOSS, "wolf_pack_positional", "circle",
                   notes="RL-policy positional pack"))

# Goblin (4)
_add(SubVariant("goblin_pickpocket", FamilyId.GOBLIN,
                   "Goblin Pickpocket", 5, 15,
                   MobRole.FRONTLINE, "pilfer", "single_target",
                   notes="Tutorial-tier; full YAML at "
                            "agents/goblin_pickpocket.yaml"))
_add(SubVariant("goblin_smithy", FamilyId.GOBLIN,
                   "Goblin Smithy", 10, 20,
                   MobRole.MID_BOSS, "hammer_slam", "cone",
                   notes="Tutorial boss per TUTORIAL_BASTOK_MINES"))
_add(SubVariant("goblin_bomber", FamilyId.GOBLIN,
                   "Goblin Bomber", 18, 28,
                   MobRole.SUICIDE_ATTACKER, "bomb_toss",
                   "placed_aoe"))
_add(SubVariant("goblin_trader", FamilyId.GOBLIN,
                   "Goblin Trader", 12, 22,
                   MobRole.QUEST_GIVER, "pilfer", "single_target"))

# Tonberry (3)
_add(SubVariant("tonberry_stalker", FamilyId.TONBERRY,
                   "Tonberry Stalker", 30, 45,
                   MobRole.SLOW_PURSUIT, "knife", "single_target"))
_add(SubVariant("tonberry_nm", FamilyId.TONBERRY,
                   "Tonberry NM", 60, 75,
                   MobRole.NM, "doton_ichi", "circle"))
_add(SubVariant("master_tonberry", FamilyId.TONBERRY,
                   "Master Tonberry", 80, 90,
                   MobRole.ENDGAME_NM, "everyones_grudge",
                   "arena_wide"))

# Naga (3)
_add(SubVariant("naga_renja", FamilyId.NAGA,
                   "Naga Renja", 25, 40,
                   MobRole.SPRINT_NIN, "hyoton_ichi",
                   "ranged_projectile"))
_add(SubVariant("naga_hatamoto", FamilyId.NAGA,
                   "Naga Hatamoto", 40, 55,
                   MobRole.MID_BOSS, "suiton_ichi_escape",
                   "single_target"))
_add(SubVariant("naga_houju", FamilyId.NAGA,
                   "Naga Houju", 60, 75,
                   MobRole.NM, "aisha_debuff_stack",
                   "circle"))

# Bee (1)
_add(SubVariant("bee_soldier", FamilyId.BEE,
                   "Bee Soldier", 12, 22,
                   MobRole.FRONTLINE, "honey_burst", "placed_aoe"))

# Slime (1)
_add(SubVariant("slime_blob", FamilyId.SLIME,
                   "Slime Blob", 10, 50,         # variable level
                   MobRole.FRONTLINE, "engulf", "single_target",
                   notes="Variable element; caller supplies at spawn"))

# Skeleton (1)
_add(SubVariant("skeleton_warrior", FamilyId.SKELETON,
                   "Skeleton Warrior", 25, 45,
                   MobRole.FRONTLINE, "bone_crusher", "line"))

# Sahagin (1)
_add(SubVariant("sahagin_swordsman", FamilyId.SAHAGIN,
                   "Sahagin Swordsman", 30, 50,
                   MobRole.FRONTLINE, "lariat", "cone"))

# Bug (1)
_add(SubVariant("bug_drone", FamilyId.BUG,
                   "Bug Drone", 15, 30,
                   MobRole.FRONTLINE, "pollen_burst", "donut"))

# Demon NM (1)
_add(SubVariant("demon_nm_archduke", FamilyId.DEMON,
                   "Demon NM (Archduke)", 75, 90,
                   MobRole.ENDGAME_NM, "soul_voice", "arena_wide"))

# Dragon NM (1)
_add(SubVariant("dragon_nm_wyrm", FamilyId.DRAGON,
                   "Dragon NM (Wyrm)", 65, 90,
                   MobRole.NM, "wing_beat", "cone"))


def get_sub_variant(sub_variant_id: str) -> SubVariant:
    return SUB_VARIANTS[sub_variant_id]


def variants_in_family(family: FamilyId) -> tuple[SubVariant, ...]:
    return tuple(sv for sv in SUB_VARIANTS.values()
                  if sv.family == family)


def all_sub_variants() -> tuple[SubVariant, ...]:
    return tuple(SUB_VARIANTS.values())


def sub_variant_count() -> int:
    return len(SUB_VARIANTS)
