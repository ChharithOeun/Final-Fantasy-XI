"""World PUP NPCs — wandering puppetmasters scattered across Vana'diel.

Per the user direction: PUP is the user's favorite job and a whole
bunch of them should live in the world. These are distinct from
trusts — they're zone-resident NPCs you encounter, fight alongside
(or against), trade automaton parts with, and quest from. Each
deploys its own automaton frame.

Coverage spans the level bands:
    Bastok / Mhaura ports        : 18-30
    Aht Urhgan deserts            : 30-50
    Crawler/Garlaige dungeons     : 45-65
    Ouryu Cave / Sea / Sky        : 70-99

Each PupNpcSpec carries:
    pup_id, name, level, zone
    automaton frames they deploy (companion ids from
        trust_system.companions)
    behavior tag ("vendor" / "questgiver" / "patrol" / "duelist")
    notes (flavor)
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class PupNpcSpec:
    """A wandering world PUP NPC."""
    pup_id: str
    name: str
    level: int
    zone: str
    automatons: tuple[str, ...]      # companion ids
    behavior: str                     # patrol / vendor / questgiver / duelist
    sub_job: t.Optional[str] = None
    nation: str = "neutral"
    notes: str = ""


PUP_NPC_CATALOG: dict[str, PupNpcSpec] = {
    # ------------------------------------------------------------------
    # Aht Urhgan / Salaheem (PUP's home faction)
    # ------------------------------------------------------------------
    "talgarazz_the_fixer": PupNpcSpec(
        pup_id="talgarazz_the_fixer", name="Talgarazz the Fixer",
        level=58, zone="aht_urhgan_whitegate",
        automatons=("automaton_valoredge",),
        behavior="vendor", sub_job="WHM", nation="ahturhgan",
        notes=("sells automaton attachments + repair parts. "
                 "(name 'Ovjang' was already taken by an existing NPC; "
                 "this is the rename per user direction)"),
    ),
    "marsianne": PupNpcSpec(
        pup_id="marsianne", name="Marsianne",
        level=72, zone="aht_urhgan_arrapago",
        automatons=("automaton_sharpshot",),
        behavior="patrol", sub_job="DNC", nation="ahturhgan",
        notes="patrols arrapago shores; veteran salaheem mercenary",
    ),

    # ------------------------------------------------------------------
    # Bastok / Mhaura
    # ------------------------------------------------------------------
    "cogley": PupNpcSpec(
        pup_id="cogley", name="Cogley Brassgear",
        level=22, zone="bastok_mines",
        automatons=("automaton_valoredge",),
        behavior="questgiver", sub_job="WAR", nation="bastok",
        notes="apprentice puppetmaster; quest hub for new PUPs",
    ),
    "ironring_jolla": PupNpcSpec(
        pup_id="ironring_jolla", name="Ironring Jolla",
        level=68, zone="palborough_mines",
        automatons=("automaton_valoredge", "automaton_stormwaker"),
        behavior="duelist", sub_job="MNK", nation="bastok",
        notes="dual-deployer; will duel any PUP who crosses them",
    ),
    "wendy_the_tinker": PupNpcSpec(
        pup_id="wendy_the_tinker", name="Wendy the Tinker",
        level=35, zone="south_gustaberg",
        automatons=("automaton_soulsoother",),
        behavior="vendor", sub_job="WHM", nation="bastok",
        notes="travelling tinker; sells healer-frame attachments",
    ),

    # ------------------------------------------------------------------
    # Windurst / Buburimu
    # ------------------------------------------------------------------
    "puhloh_apolloh": PupNpcSpec(
        pup_id="puhloh_apolloh", name="Puhloh-Apolloh",
        level=44, zone="windurst_woods",
        automatons=("automaton_spiritreaver",),
        behavior="questgiver", sub_job="BLM", nation="windurst",
        notes="taru tinkerer; offers nuker-frame upgrade quests",
    ),
    "miika_the_silent": PupNpcSpec(
        pup_id="miika_the_silent", name="Miika the Silent",
        level=80, zone="meriphataud_mountains",
        automatons=("automaton_stormwaker", "automaton_sharpshot"),
        behavior="patrol", sub_job="RNG", nation="windurst",
        notes="elite mithra patroller; deploys dual frames",
    ),

    # ------------------------------------------------------------------
    # San d'Oria
    # ------------------------------------------------------------------
    "bertieaux": PupNpcSpec(
        pup_id="bertieaux", name="Bertieaux Whitewing",
        level=50, zone="east_ronfaure",
        automatons=("automaton_valoredge",),
        behavior="duelist", sub_job="PLD", nation="sandoria",
        notes="paladin-blooded PUP; rare nation-aligned puppetmaster",
    ),

    # ------------------------------------------------------------------
    # Norg / Tenshodo (outlaw-friendly)
    # ------------------------------------------------------------------
    "kirin_kala": PupNpcSpec(
        pup_id="kirin_kala", name="Kirin-Kala",
        level=85, zone="norg",
        automatons=("automaton_sharpshot", "automaton_stormwaker"),
        behavior="vendor", sub_job="NIN", nation="norg",
        notes="black-market frame upgrades for outlaw-flagged PUPs",
    ),

    # ------------------------------------------------------------------
    # Apex zones — sky/sea/dungeons
    # ------------------------------------------------------------------
    "the_clockwork_sage": PupNpcSpec(
        pup_id="the_clockwork_sage", name="The Clockwork Sage",
        level=90, zone="garlaige_citadel",
        automatons=("automaton_valoredge", "automaton_soulsoother",
                      "automaton_spiritreaver"),
        behavior="duelist", sub_job="SCH", nation="neutral",
        notes="legendary PUP; deploys 3 frames simultaneously (unique)",
    ),
    "anhauer_grimbold": PupNpcSpec(
        pup_id="anhauer_grimbold", name="Anhauer Grimbold",
        level=99, zone="dynamis_jeuno",
        automatons=("automaton_valoredge", "automaton_spiritreaver"),
        behavior="questgiver", sub_job="DRK", nation="neutral",
        notes="apex PUP; gives the Master Puppeteer questline",
    ),
}


def pup_npcs_in_zone(zone: str) -> list[PupNpcSpec]:
    """Return all PUP NPCs that reside in the given zone."""
    z = zone.lower()
    return [npc for npc in PUP_NPC_CATALOG.values() if npc.zone == z]
