"""Rogue Automaton NM catalog.

Per the user direction: 'a bunch of Rogue Automatons with no master
roaming the world as Notorious Monsters that are extremely difficult
to kill, they always drop an insane reward, and each respawns every
24hrs earth time.'

Each rogue automaton is an apex-difficulty solo encounter (or
small-party kill) with a guaranteed apex reward. They wander
specific zones; some are stationary boss-types, others patrol
routes between zones.

Drop policy: 'always drop an insane reward'. We bias the drop_table
toward signed-tier / +V / unique-rare items + a guaranteed
high-tier currency drop.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RogueAutomatonClass(str, enum.Enum):
    """Frame archetype the rogue evolved from."""
    VALOREDGE = "valoredge"        # tank-frame gone rogue
    SHARPSHOT = "sharpshot"        # ranged frame
    STORMWAKER = "stormwaker"      # support/CC
    SOULSOOTHER = "soulsoother"    # healer; rarely rogue, unusually deadly
    SPIRITREAVER = "spiritreaver"  # nuker
    HYBRID = "hybrid"              # apex; multi-frame composite
    PROTOTYPE = "prototype"        # ancient experimental (apex+)


@dataclasses.dataclass(frozen=True)
class RogueAutomatonNM:
    """A Rogue Automaton Notorious Monster."""
    nm_id: str
    name: str
    level: int
    rogue_class: RogueAutomatonClass
    zone: str
    hp_pool: int
    primary_abilities: tuple[str, ...]
    drop_table: tuple[str, ...]
    guaranteed_drop: str           # apex reward; always drops
    notes: str = ""


# 10 Rogue Automaton NMs spanning the world.
ROGUE_AUTOMATON_NMS: dict[str, RogueAutomatonNM] = {
    # Bastok Mines area — the original frame factories
    "iron_widow": RogueAutomatonNM(
        nm_id="iron_widow", name="Iron Widow",
        level=85, rogue_class=RogueAutomatonClass.VALOREDGE,
        zone="palborough_mines",
        hp_pool=120000,
        primary_abilities=("provoke_chain", "hammer_smite",
                            "iron_palisade", "molten_kiss"),
        drop_table=("widow_chassis_v", "iron_heartstone",
                     "ancient_steam_valve"),
        guaranteed_drop="rogue_automaton_core",
        notes="black-market frame; first-evolved in Bastok 30 years ago",
    ),

    "the_unblinking_eye": RogueAutomatonNM(
        nm_id="the_unblinking_eye", name="The Unblinking Eye",
        level=88, rogue_class=RogueAutomatonClass.SHARPSHOT,
        zone="zeruhn_mines",
        hp_pool=95000,
        primary_abilities=("predictive_shot", "armor_piercer_x3",
                            "barrage_volley", "heat_seeker"),
        drop_table=("eye_optic_lens", "tungsten_bullets",
                     "sniper_lineage_pistol"),
        guaranteed_drop="rogue_automaton_core",
        notes="snipes from 80m; only deactivates at point-blank",
    ),

    # Garlaige / Crawler dungeons
    "rust_warden": RogueAutomatonNM(
        nm_id="rust_warden", name="Rust Warden",
        level=90, rogue_class=RogueAutomatonClass.VALOREDGE,
        zone="garlaige_citadel",
        hp_pool=180000,
        primary_abilities=("rust_breath", "iron_palisade",
                            "flame_jet", "warden_thump"),
        drop_table=("rust_plate_signed", "warden_attachment_set",
                     "ancient_clockwork"),
        guaranteed_drop="rogue_automaton_core",
        notes="patrols the citadel; ignores time of day",
    ),

    "the_misery_loop": RogueAutomatonNM(
        nm_id="the_misery_loop", name="The Misery Loop",
        level=92, rogue_class=RogueAutomatonClass.HYBRID,
        zone="crawlers_nest",
        hp_pool=210000,
        primary_abilities=("frame_swap", "barrier_tusk",
                            "flame_jet", "deactivation_field"),
        drop_table=("hybrid_chassis_v", "frame_swap_module",
                     "misery_resonator"),
        guaranteed_drop="rogue_automaton_core_apex",
        notes="apex hybrid; cycles between 3 frame profiles",
    ),

    # Aht Urhgan deserts
    "saharah_sentinel": RogueAutomatonNM(
        nm_id="saharah_sentinel", name="Saharah Sentinel",
        level=87, rogue_class=RogueAutomatonClass.STORMWAKER,
        zone="bhaflau_thickets",
        hp_pool=130000,
        primary_abilities=("sand_blast", "magic_finale",
                            "mass_haste_self_buff", "thunder_iv"),
        drop_table=("sentinel_pendant_v", "saharah_glass",
                     "stormwaker_legacy_module"),
        guaranteed_drop="rogue_automaton_core",
    ),

    # Sky / Tu'Lia
    "the_silver_thorn": RogueAutomatonNM(
        nm_id="the_silver_thorn", name="The Silver Thorn",
        level=95, rogue_class=RogueAutomatonClass.SHARPSHOT,
        zone="sky_ruaun",
        hp_pool=240000,
        primary_abilities=("piercing_volley", "celestial_lock_on",
                            "armor_piercer_x5", "evasive_dash"),
        drop_table=("thorn_visor_v", "celestial_silver_alloy",
                     "rare_mythic_blueprint"),
        guaranteed_drop="rogue_automaton_core_apex",
        notes="floats; melee fighters need to climb to it",
    ),

    # Sea / Al'Taieu
    "the_drowned_engineer": RogueAutomatonNM(
        nm_id="the_drowned_engineer", name="The Drowned Engineer",
        level=96, rogue_class=RogueAutomatonClass.SOULSOOTHER,
        zone="sea_ahriman",
        hp_pool=200000,
        primary_abilities=("benediction", "regen_v",
                            "stoneskin_pulse", "drown_call"),
        drop_table=("drowned_caparison_v", "alpha_repair_kit",
                     "soulsoother_legacy_module"),
        guaranteed_drop="rogue_automaton_core_apex",
        notes="self-heals indefinitely if not interrupted",
    ),

    # Dynamis-Bastok
    "the_brass_phoenix": RogueAutomatonNM(
        nm_id="the_brass_phoenix", name="The Brass Phoenix",
        level=99, rogue_class=RogueAutomatonClass.PROTOTYPE,
        zone="dynamis_bastok",
        hp_pool=380000,
        primary_abilities=("phoenix_flame_aoe", "rebirth_at_zero",
                            "molten_storm", "armageddon_protocol"),
        drop_table=("phoenix_chassis_relic", "brass_phoenix_feather",
                     "armageddon_protocol_blueprint",
                     "signed_relic_attachment"),
        guaranteed_drop="rogue_automaton_core_apex",
        notes="prototype frame; revives ONCE on first death, fight resumes",
    ),

    # Norg outskirts (outlaw-territory rogue)
    "the_keelhauler": RogueAutomatonNM(
        nm_id="the_keelhauler", name="The Keelhauler",
        level=88, rogue_class=RogueAutomatonClass.VALOREDGE,
        zone="sea_serpent_grotto",
        hp_pool=140000,
        primary_abilities=("pirate_stance", "hook_throw",
                            "barrage_volley", "smite_of_rage"),
        drop_table=("keelhauler_anchor", "pirate_chassis_v",
                     "salt_sea_wax"),
        guaranteed_drop="rogue_automaton_core",
        notes="outlaw-rogue; tenshodo veterans trade for its parts",
    ),

    # Promyvion / abyssea apex
    "the_witness_zero": RogueAutomatonNM(
        nm_id="the_witness_zero", name="The Witness, Zero",
        level=99, rogue_class=RogueAutomatonClass.PROTOTYPE,
        zone="promyvion_holla",
        hp_pool=420000,
        primary_abilities=("absolute_zero", "memory_purge",
                            "void_strike", "witness_glare"),
        drop_table=("witness_zero_lens", "memory_shard",
                     "void_clockwork_blueprint",
                     "signed_apex_attachment_set"),
        guaranteed_drop="rogue_automaton_core_apex",
        notes="ancient prototype; lore-tied to the Emptiness",
    ),
}


def rogue_automaton_for(nm_id: str) -> t.Optional[RogueAutomatonNM]:
    return ROGUE_AUTOMATON_NMS.get(nm_id.lower())


def rogue_automatons_in_zone(zone: str) -> list[RogueAutomatonNM]:
    z = zone.lower()
    return [nm for nm in ROGUE_AUTOMATON_NMS.values() if nm.zone == z]
