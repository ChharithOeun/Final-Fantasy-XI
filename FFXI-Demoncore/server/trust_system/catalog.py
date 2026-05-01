"""Trust catalog — expanded roster across all 5 nations + outlaw-allies.

Per the user direction: 'maybe add more NPCs as trusts'. The OG
FFXI trust roster was limited; Demoncore expands it. We keep the
canonical heroes (Trion, Volker, Curilla, Cid, Ayame, Yoran-Oran,
Naja Salaheem) AND add:
    - More named hero NPCs from each nation
    - Tenshodo / Norg trusts (Yorisha, Joachim)
    - Outlaw-allied trusts that an outlaw player can summon
      (canonical FFXI didn't have these — Demoncore makes outlaws
      a real faction with its own trust pool)

Each trust has a primary role (TANK/HEALER/MELEE_DPS/...) that
drives the AI's default action selection. Behavior tuning knobs
let role-overlapping trusts diverge (Trion as a heal-y PLD vs
Volker as a damage WAR even though both are 'frontline').
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TrustRole(str, enum.Enum):
    TANK = "tank"
    HEALER = "healer"
    MELEE_DPS = "melee_dps"
    RANGED_DPS = "ranged_dps"
    SUPPORT = "support"        # buffs / songs / haste
    DEBUFFER = "debuffer"
    NUKER = "nuker"            # caster offense


@dataclasses.dataclass(frozen=True)
class TrustSpec:
    """The static definition of a trust."""
    trust_id: str
    name: str
    job: str
    sub_job: t.Optional[str]
    role: TrustRole
    nation: str                                 # "bastok" / "sandoria" / etc.
    abilities: tuple[str, ...]                  # named abilities the AI can fire
    canonical: bool = True                       # FFXI canonical or Demoncore-added
    outlaw_aligned: bool = False                # Demoncore outlaw-only trusts
    heal_threshold_override: t.Optional[float] = None
    sc_priority: bool = False                    # actively pushes for skillchains
    # Companion ids this trust can field. PUP -> automatons, SMN -> avatars,
    # BST -> jug pets / charmable beasts, BLU -> learned spell library.
    # Resolved against companions.COMPANION_CATALOG.
    companions: tuple[str, ...] = ()
    # Whether the AI should auto-activate companions on summon.
    auto_activate_companions: bool = False


# ----------------------------------------------------------------------
# The roster
# ----------------------------------------------------------------------

TRUST_CATALOG: dict[str, TrustSpec] = {
    # =================================================================
    # San d'Oria
    # =================================================================
    "trion": TrustSpec(
        trust_id="trion", name="Trion", job="PLD", sub_job="WAR",
        role=TrustRole.TANK, nation="sandoria",
        abilities=("provoke", "shield_bash", "flash", "cure_iii"),
        canonical=True,
    ),
    "curilla": TrustSpec(
        trust_id="curilla", name="Curilla", job="PLD", sub_job="WAR",
        role=TrustRole.TANK, nation="sandoria",
        abilities=("provoke", "savage_blade", "flash", "intervention_mb"),
        canonical=True,
    ),
    "excenmille": TrustSpec(
        trust_id="excenmille", name="Excenmille", job="PLD", sub_job="WAR",
        role=TrustRole.TANK, nation="sandoria",
        abilities=("sentinel", "shield_bash", "cure_ii"),
        canonical=True,
    ),
    "halver": TrustSpec(
        trust_id="halver", name="Halver", job="PLD", sub_job="WAR",
        role=TrustRole.TANK, nation="sandoria",
        abilities=("provoke", "shield_bash", "cure_iii", "majesty"),
        canonical=False,                # Demoncore extension
    ),

    # =================================================================
    # Bastok
    # =================================================================
    "volker": TrustSpec(
        trust_id="volker", name="Volker", job="WAR", sub_job=None,
        role=TrustRole.MELEE_DPS, nation="bastok",
        abilities=("provoke", "berserk", "rampage", "warcry"),
        canonical=True,
        sc_priority=True,
    ),
    "ayame": TrustSpec(
        trust_id="ayame", name="Ayame", job="SAM", sub_job="WAR",
        role=TrustRole.MELEE_DPS, nation="bastok",
        abilities=("meditate", "third_eye", "tachi_gekko", "tachi_kasha"),
        canonical=True,
        sc_priority=True,
    ),
    "naji": TrustSpec(
        trust_id="naji", name="Naji", job="THF", sub_job="WAR",
        role=TrustRole.MELEE_DPS, nation="bastok",
        abilities=("steal", "trick_attack", "sneak_attack"),
        canonical=True,
    ),
    "cid": TrustSpec(
        trust_id="cid", name="Cid", job="SMI", sub_job=None,
        role=TrustRole.SUPPORT, nation="bastok",
        abilities=("repair_call", "cure_ii", "stoneskin"),
        canonical=True,                # legendary smith, support+repair
    ),
    "iron_eater": TrustSpec(
        trust_id="iron_eater", name="Iron Eater", job="WAR", sub_job="MNK",
        role=TrustRole.MELEE_DPS, nation="bastok",
        abilities=("warcry", "boost", "raging_rush"),
        canonical=True,
        sc_priority=True,
    ),
    "zeid": TrustSpec(
        trust_id="zeid", name="Zeid", job="DRK", sub_job="WAR",
        role=TrustRole.MELEE_DPS, nation="bastok",
        abilities=("souleater", "absorb_str", "guillotine"),
        canonical=True,
        sc_priority=True,
    ),

    # =================================================================
    # Windurst
    # =================================================================
    "yoran_oran": TrustSpec(
        trust_id="yoran_oran", name="Yoran-Oran", job="WHM", sub_job="BLM",
        role=TrustRole.HEALER, nation="windurst",
        abilities=("cure_iv", "regen_iii", "barfira", "raise_iii"),
        canonical=True,
    ),
    "kerutoto": TrustSpec(
        trust_id="kerutoto", name="Kerutoto", job="WHM", sub_job="BLM",
        role=TrustRole.HEALER, nation="windurst",
        abilities=("cure_iii", "haste", "stoneskin", "regen_ii"),
        canonical=True,
    ),
    "shantotto": TrustSpec(
        trust_id="shantotto", name="Shantotto", job="BLM", sub_job="RDM",
        role=TrustRole.NUKER, nation="windurst",
        abilities=("firaga_iii", "thundaga_iii", "comet", "burst_ii"),
        canonical=True,
        sc_priority=True,
    ),
    "ajido_marujido": TrustSpec(
        trust_id="ajido_marujido", name="Ajido-Marujido",
        job="BLM", sub_job="RDM",
        role=TrustRole.NUKER, nation="windurst",
        abilities=("firaga_iii", "blizzaga_iii", "stun"),
        canonical=True,
    ),

    # =================================================================
    # Aht Urhgan / Salaheem
    # =================================================================
    "naja_salaheem": TrustSpec(
        trust_id="naja_salaheem", name="Naja Salaheem", job="COR", sub_job="WAR",
        role=TrustRole.SUPPORT, nation="ahturhgan",
        abilities=("hunters_roll", "wizards_roll", "quick_draw"),
        canonical=True,
    ),
    "aphmau": TrustSpec(
        trust_id="aphmau", name="Aphmau", job="PUP", sub_job="WHM",
        role=TrustRole.SUPPORT, nation="ahturhgan",
        abilities=("automaton_deploy", "cure_iii", "regen_ii",
                     "overdrive", "deactivate"),
        canonical=True,
        companions=("automaton_mnejing", "automaton_sharpshot"),
        auto_activate_companions=True,
    ),

    # =================================================================
    # Tenshodo (Norg) - Demoncore-flavored faction
    # =================================================================
    "yorisha": TrustSpec(
        trust_id="yorisha", name="Yorisha", job="MNK", sub_job="WAR",
        role=TrustRole.MELEE_DPS, nation="norg",
        abilities=("hundred_fists", "boost", "asuran_fists"),
        canonical=False,
        sc_priority=True,
    ),
    "joachim": TrustSpec(
        trust_id="joachim", name="Joachim", job="BRD", sub_job="WHM",
        role=TrustRole.SUPPORT, nation="norg",
        abilities=("minuet_iv", "march_iii", "ballad_ii", "lullaby"),
        canonical=False,
    ),

    # =================================================================
    # Outlaw-aligned trusts (Demoncore additions; outlaw-only)
    # =================================================================
    "shadow_wolf": TrustSpec(
        trust_id="shadow_wolf", name="Shadow Wolf", job="NIN", sub_job="WAR",
        role=TrustRole.MELEE_DPS, nation="norg",
        abilities=("utsusemi_ni", "katon_san", "blade_jin"),
        canonical=False, outlaw_aligned=True,
    ),
    "blackmaw_bandit": TrustSpec(
        trust_id="blackmaw_bandit", name="Blackmaw Bandit",
        job="DRK", sub_job="THF",
        role=TrustRole.MELEE_DPS, nation="norg",
        abilities=("absorb_str", "souleater", "torcleaver"),
        canonical=False, outlaw_aligned=True,
    ),

    # =================================================================
    # Pet-class trust expansion — per user direction
    # PUP / SMN / BLU / BST trusts that carry companions
    # =================================================================
    "mayakov_pup": TrustSpec(
        trust_id="mayakov_pup", name="Mayakov", job="PUP", sub_job="DNC",
        role=TrustRole.MELEE_DPS, nation="ahturhgan",
        abilities=("automaton_deploy", "haste_samba", "drain_samba"),
        canonical=False,
        companions=("automaton_valoredge",),
        auto_activate_companions=True,
    ),
    "iroha_pup": TrustSpec(
        trust_id="iroha_pup", name="Iroha-en-Eraz", job="PUP", sub_job="WHM",
        role=TrustRole.SUPPORT, nation="bastok",
        abilities=("automaton_deploy", "cure_iii", "stoneskin"),
        canonical=False,
        companions=("automaton_soulsoother", "automaton_spiritreaver"),
        auto_activate_companions=True,
    ),
    "sokoo_pup": TrustSpec(
        trust_id="sokoo_pup", name="Sokoo Mihgo", job="PUP", sub_job="THF",
        role=TrustRole.RANGED_DPS, nation="windurst",
        abilities=("automaton_deploy", "shadowbind", "mark_target"),
        canonical=False,
        companions=("automaton_stormwaker",),
        auto_activate_companions=True,
    ),
    "esha_smn": TrustSpec(
        trust_id="esha_smn", name="Esha'ntarl", job="SMN", sub_job="WHM",
        role=TrustRole.NUKER, nation="windurst",
        abilities=("summon_avatar", "release_avatar",
                     "astral_flow", "blood_pact_predict"),
        canonical=False,
        companions=("avatar_carbuncle", "avatar_ifrit",
                      "avatar_garuda", "avatar_titan",
                      "avatar_ramuh", "avatar_shiva",
                      "avatar_leviathan", "avatar_fenrir",
                      "avatar_diabolos"),
        auto_activate_companions=False,   # SMN picks the avatar manually
        sc_priority=True,
    ),
    "jakoh_blu": TrustSpec(
        trust_id="jakoh_blu", name="Jakoh Wahcondalo", job="BLU", sub_job="WAR",
        role=TrustRole.MELEE_DPS, nation="ahturhgan",
        abilities=("blue_magic", "azure_lore",
                     "chain_affinity", "burst_affinity"),
        canonical=False,
        companions=("blu_cocoon", "blu_filamented_hold",
                      "blu_1000_needles", "blu_blood_drain",
                      "blu_self_destruct", "blu_blank_gaze",
                      "blu_jettatura", "blu_hysteric_barrage",
                      # Self-SC + 3-stage MB capability per user direction
                      "blu_quad_continuum", "blu_disseverment",
                      "blu_chant_du_cygne", "blu_blastbomb",
                      "blu_thunderbolt", "blu_silent_storm",
                      "blu_azure_lore_sp"),
        auto_activate_companions=False,
        sc_priority=True,
    ),
    "max_bst": TrustSpec(
        trust_id="max_bst", name="Maximilian", job="BST", sub_job="WAR",
        role=TrustRole.MELEE_DPS, nation="bastok",
        abilities=("call_beast", "charm", "reward",
                     "tame_beast", "killer_instinct"),
        canonical=False,
        companions=("jug_carrie", "jug_dipper_yuly",
                      "jug_funguar_familiar", "jug_lifedrinker_lars",
                      "charmed_wild_target"),
        auto_activate_companions=True,
    ),
}


def trust_for(trust_id: str) -> t.Optional[TrustSpec]:
    """Lookup helper. Returns None for unknown trust IDs."""
    return TRUST_CATALOG.get(trust_id.lower())


def trusts_for_nation(nation: str,
                        *,
                        outlaw_summoner: bool = False) -> list[TrustSpec]:
    """Return all trusts the given nation can offer. Outlaw players
    ALSO see outlaw-aligned trusts; non-outlaws can't summon them."""
    out = []
    for spec in TRUST_CATALOG.values():
        if spec.outlaw_aligned and not outlaw_summoner:
            continue
        if spec.nation == nation.lower() or outlaw_summoner and spec.outlaw_aligned:
            out.append(spec)
    return out
