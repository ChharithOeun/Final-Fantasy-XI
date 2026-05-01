"""Unlock cadence — 21 system introductions gated by player level.

Per PLAYER_PROGRESSION.md the gentle introduction: 'A first-day
player would drown if all of [Demoncore's systems] were active at
once. The progression introduces each system at a specific level.'

Each unlock is preceded by a tutorial NPC encounter (per
AI_WORLD_DENSITY.md Tier 2-3) that teaches the new mechanic.
Players don't read patch notes; they learn from Cid, Volker, Maat.
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class SystemUnlock:
    """One system reveal gated to a specific level."""
    system_id: str
    label: str
    tutorial_npc: t.Optional[str] = None   # who teaches this
    tutorial_zone: t.Optional[str] = None
    notes: str = ""


# Master cadence table — 21 entries from lvl 1 (visual_health) to
# lvl 99 (permadeath active).
UNLOCK_CADENCE: dict[int, tuple[SystemUnlock, ...]] = {
    1: (
        SystemUnlock("visual_health", "Visual Health (no HP bars; read posture)"),
        SystemUnlock("weight", "Weight & movement"),
    ),
    5: (
        SystemUnlock("check_command_basic", "/check command (vague descriptor only)",
                       tutorial_npc="cogley_brassgear",
                       tutorial_zone="bastok_mines"),
    ),
    8: (
        SystemUnlock("weapon_skill_first", "First weapon skill — chain marker visual + audible",
                       tutorial_npc="cid",
                       tutorial_zone="bastok_metalworks"),
    ),
    12: (
        SystemUnlock("skillchain_tutorial_lv1", "First skillchain (Level 1)",
                       tutorial_npc="volker",
                       tutorial_zone="bastok_mines",
                       notes="Tier-1 SC walkthrough fight"),
    ),
    15: (
        SystemUnlock("first_boss_test", "First boss test (Korroloka fomor)",
                       tutorial_npc="ayame",
                       tutorial_zone="korroloka_tunnel"),
    ),
    18: (
        SystemUnlock("magic_burst_window", "Magic Burst window awareness — visible halo",
                       tutorial_npc="ajido_marujido",
                       tutorial_zone="windurst_walls"),
    ),
    20: (
        SystemUnlock("first_reveal_skill", "First reveal skill (Scan / Drain — job-tied)",
                       tutorial_npc="yoran_oran",
                       tutorial_zone="windurst_woods"),
    ),
    25: (
        SystemUnlock("thf_mug_introduction", "THF/Mug introduction (job-gated)",
                       tutorial_npc="naji",
                       tutorial_zone="bastok_metalworks"),
    ),
    30: (
        SystemUnlock("nin_hand_signs", "Hand signs (full sign-system unlocks for NIN)",
                       tutorial_npc="iroha_pup",
                       tutorial_zone="norg",
                       notes="NIN-job-gated; the 12-zodiac seal system"),
    ),
    40: (
        SystemUnlock("skillchain_tier_2", "Tier-2 skillchain (Fusion/Distortion/Fragmentation/Gravitation)",
                       tutorial_npc="curilla",
                       tutorial_zone="crawlers_nest"),
    ),
    45: (
        SystemUnlock("intervention_mb", "Intervention MB window awareness (defensive twin)",
                       tutorial_npc="trion",
                       tutorial_zone="south_sandoria"),
    ),
    50: (
        SystemUnlock("genkai_1_unlocked", "Genkai 1 — Maat fight unlocks",
                       tutorial_npc="maat",
                       tutorial_zone="ru_lude_gardens"),
    ),
    55: (
        SystemUnlock("skillchain_tier_3", "Tier-3 skillchain (Light / Darkness)",
                       tutorial_npc="zeid",
                       tutorial_zone="garlaige_citadel",
                       notes="taught by NM hint encounter"),
    ),
    60: (
        SystemUnlock("boss_critic_llm", "Boss critic LLM unlocks for Genkai-tier bosses",
                       tutorial_npc="maat",
                       tutorial_zone="balgas_dais"),
    ),
    65: (
        SystemUnlock("dual_cast_reliable", "Dual-cast becomes reliable (RDM)",
                       tutorial_npc="kerutoto",
                       tutorial_zone="windurst_walls"),
    ),
    70: (
        SystemUnlock("outlaw_bounty_pvp", "Outlaw bounty + cross-faction PvP unlocks",
                       tutorial_npc="naja_salaheem",
                       tutorial_zone="aht_urhgan_whitegate"),
    ),
    75: (
        SystemUnlock("endgame_bcnm_limbus", "Endgame BCNM / Limbus content",
                       tutorial_npc="shantotto",
                       tutorial_zone="ru_aun_gardens"),
    ),
    85: (
        SystemUnlock("mythic_promathia_tier", "Mythic boss tier (Promathia) unlocks",
                       tutorial_npc="prishe",
                       tutorial_zone="empyreal_paradox"),
    ),
    99: (
        SystemUnlock("hardcore_permadeath", "Hardcore-death penalty active (1hr permadeath timer)",
                       tutorial_npc="anhauer_grimbold",
                       tutorial_zone="dynamis_jeuno"),
    ),
}


def system_unlocked(system_id: str, *, player_level: int) -> bool:
    """Is the named system unlocked at this player level?"""
    for level, unlocks in UNLOCK_CADENCE.items():
        if level <= player_level and any(u.system_id == system_id
                                            for u in unlocks):
            return True
    return False


def newly_unlocked_at(player_level: int) -> list[SystemUnlock]:
    """Return systems unlocked at exactly this level (for the
    'you just learned X' tutorial trigger)."""
    return list(UNLOCK_CADENCE.get(player_level, ()))


def all_unlocked_up_to(player_level: int) -> list[SystemUnlock]:
    """All systems unlocked at-or-below the given level."""
    out: list[SystemUnlock] = []
    for level, unlocks in sorted(UNLOCK_CADENCE.items()):
        if level <= player_level:
            out.extend(unlocks)
    return out


def next_unlock_after(player_level: int) -> t.Optional[tuple[int, SystemUnlock]]:
    """The next unlock the player will reach (for UI hints)."""
    for level in sorted(UNLOCK_CADENCE.keys()):
        if level > player_level:
            unlocks = UNLOCK_CADENCE[level]
            if unlocks:
                return (level, unlocks[0])
    return None
