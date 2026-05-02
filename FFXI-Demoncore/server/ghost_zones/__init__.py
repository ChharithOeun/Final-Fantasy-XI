"""Ghost zones — registry of unused/unimplemented FFXI zones.

The retail FFXI client ships with a number of zones that exist in
its data files but were never given gameplay content. This module
catalogs them so Demoncore can re-implement them as expansion
content. The geometry already exists — we just need the gameplay
layer.

Sources: BG-Wiki Unused Maps, FFXIclopedia, The Cutting Room Floor,
Oculin's Box "Lost Town of Sel Phiner".

Public surface
--------------
    GhostKind enum        full / variant / partial / blocked /
                              referenced / placeholder_id
    GhostZone immutable   id, name, kind, theme, expansion hook,
                              variant_count, intended_purpose
    GHOST_ZONE_CATALOG    19 entries
    PLACEHOLDER_ZONE_IDS  9 retail placeholder zone IDs
    ghost_zones_by_kind(kind)
    expansion_candidates() - filter to "deserves a content drop"
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GhostKind(str, enum.Enum):
    """Why this zone is "unused"."""
    FULL_UNUSED = "full_unused"          # Complete zone never wired up
    VARIANT = "variant"                   # Alt layout of a shipped zone
    PARTIAL = "partial"                   # Geometry partial; doors locked
    BLOCKED = "blocked"                   # Reachable in theory; gated
    REFERENCED = "referenced"             # Signage points here, no zone
    PLACEHOLDER = "placeholder"           # Beta/dev-only feature


@dataclasses.dataclass(frozen=True)
class GhostZone:
    ghost_id: str
    name: str
    kind: GhostKind
    theme: str
    intended_purpose: str
    variant_count: int = 1
    expansion_candidate: bool = True
    notes: str = ""


GHOST_ZONE_CATALOG: tuple[GhostZone, ...] = (
    GhostZone(
        ghost_id="sel_phiner", name="Sel Phiner",
        kind=GhostKind.FULL_UNUSED,
        theme="lost monorail town",
        intended_purpose=(
            "Earliest abandoned dev town with monorail bisecting "
            "it. Three exits to non-existent areas including "
            "'Chocobo Wood' (FF3 reference)."
        ),
        notes=(
            "Visible in 2001 promotional trailer. Cut before launch."
        ),
    ),
    GhostZone(
        ghost_id="periqia", name="Periqia",
        kind=GhostKind.VARIANT, variant_count=5,
        theme="mission/combat arena",
        intended_purpose=(
            "Five complete map variants exist; only one used for "
            "ToAU Assault. Strongest candidate for an Aht Urhgan "
            "expansion content drop."
        ),
    ),
    GhostZone(
        ghost_id="castle_zvahl_keep", name="Castle Zvahl Keep",
        kind=GhostKind.VARIANT, variant_count=4,
        theme="shadow lord throne room alts",
        intended_purpose=(
            "Four unused variants beyond the canonical version. "
            "Likely planned multi-stage final boss / raid encounter."
        ),
        notes="Demonic theme aligns with Demoncore branding.",
    ),
    GhostZone(
        ghost_id="hall_of_transference", name="Hall of Transference",
        kind=GhostKind.VARIANT, variant_count=3,
        theme="magical transit hub",
        intended_purpose=(
            "Promyvion-style ascending hub with three layouts. "
            "Could anchor a planar-travel network connecting "
            "endgame zones."
        ),
    ),
    GhostZone(
        ghost_id="original_davoi", name="Original Davoi",
        kind=GhostKind.VARIANT,
        theme="pre-launch orc fortress",
        intended_purpose=(
            "Earlier layout of Davoi superseded by shipped version. "
            "Flashback / Wings of the Goddess past-version candidate."
        ),
    ),
    GhostZone(
        ghost_id="lebros_caverns", name="Lebros Caverns",
        kind=GhostKind.VARIANT, variant_count=2,
        theme="twin cavern dungeons",
        intended_purpose=(
            "Two complete cavern layouts. Canonical landed in ToAU "
            "Assault rotations; second variant never shipped."
        ),
    ),
    GhostZone(
        ghost_id="mamool_training_grounds",
        name="Mamool Ja Training Grounds",
        kind=GhostKind.VARIANT, variant_count=2,
        theme="beastman military camp",
        intended_purpose=(
            "Two map variants for Mamool Ja training facilities. "
            "Slots into siege_system as recurring beastman raid origin."
        ),
    ),
    GhostZone(
        ghost_id="cavern_of_flames", name="Cavern of Flames",
        kind=GhostKind.VARIANT, variant_count=2,
        theme="fire dungeon alts",
        intended_purpose=(
            "Two variants. Strong fit for fomor-gear / hardcore-death "
            "conversion content."
        ),
    ),
    GhostZone(
        ghost_id="leujaom_sanctum", name="Leujaom Sanctum",
        kind=GhostKind.FULL_UNUSED,
        theme="religious / holy structure",
        intended_purpose=(
            "Light/holy theme suggests a planned WHM-line storyline "
            "or AF questline that was scoped out."
        ),
    ),
    GhostZone(
        ghost_id="carpenters_landing_alt",
        name="Carpenter's Landing (alt)",
        kind=GhostKind.VARIANT,
        theme="crafting / lumberjack camp",
        intended_purpose=(
            "Plays nicely with harvesting + crafting modules. "
            "Anchor a logging-camp side activity."
        ),
    ),
    GhostZone(
        ghost_id="ifrits_cauldron_alt",
        name="Ifrit's Cauldron (alt)",
        kind=GhostKind.VARIANT,
        theme="volcanic dungeon alt",
        intended_purpose=(
            "Avatar-storyline content potential. Pairs with "
            "avatar_pacts module."
        ),
    ),
    GhostZone(
        ghost_id="korroloka_tunnel_alt",
        name="Korroloka Tunnel (alt)",
        kind=GhostKind.VARIANT,
        theme="underground passage alt",
        intended_purpose=(
            "NM placeholder route candidate. Smuggler-themed quest "
            "content opportunity."
        ),
    ),
    GhostZone(
        ghost_id="job_change_area", name="Job Change Area",
        kind=GhostKind.PLACEHOLDER,
        theme="beta-only Mog House feature",
        intended_purpose=(
            "Original Japanese beta high-res character preview area "
            "for job changes. Demoncore flagship hero-screen target."
        ),
        notes="Was high-res character model preview pre-launch.",
    ),
    GhostZone(
        ghost_id="mt_zhayolm_lonesome_island",
        name="Mt Zhayolm — Lonesome Island",
        kind=GhostKind.BLOCKED,
        theme="locked beyond pressurized door",
        intended_purpose=(
            "Visible at F-9 with path through Halvung. Pressurized "
            "door never opens. Caedarva-tier NM arena candidate."
        ),
    ),
    GhostZone(
        ghost_id="fort_karugo_narugo", name="Fort Karugo-Narugo",
        kind=GhostKind.FULL_UNUSED,
        theme="off-map Mhaura-side fort",
        intended_purpose=(
            "Complete fort assembly outside visible map bounds. "
            "Hidden assault target or pirate-faction questline."
        ),
    ),
    GhostZone(
        ghost_id="pashhow_s_blocked", name="Pashhow Marshlands [S] blocked path",
        kind=GhostKind.PARTIAL,
        theme="WotG zone partial",
        intended_purpose=(
            "Geometry exists for a path that never opens. "
            "Past-Bastok storyline expansion candidate."
        ),
    ),
    GhostZone(
        ghost_id="east_ronfaure_s_blocked",
        name="East Ronfaure [S] blocked path",
        kind=GhostKind.PARTIAL,
        theme="WotG zone partial",
        intended_purpose=(
            "Sister zone to Pashhow [S] — same pattern of "
            "geometry waiting for a door. Past-Sandy storyline."
        ),
    ),
    GhostZone(
        ghost_id="dummy_map", name="Dummy Map",
        kind=GhostKind.PLACEHOLDER,
        theme="generic test environment",
        intended_purpose=(
            "Featureless flat plane used during dev for testing. "
            "Demoncore tutorial training ground or holodeck stage."
        ),
        expansion_candidate=False,
    ),
    GhostZone(
        ghost_id="chocobo_wood", name="Chocobo Wood",
        kind=GhostKind.REFERENCED,
        theme="referenced, never built",
        intended_purpose=(
            "Sign in Sel Phiner points here. No matching zone "
            "exists. FF3-flavored chocobo-breeding habitat that "
            "ties back to chocobo_breeding."
        ),
    ),
)


# Placeholder zone IDs from retail client.
PLACEHOLDER_ZONE_IDS: dict[int, str] = {
    0: "Prototype",
    49: "Unknown",
    131: "Jail",
    133: "Character creation",
    189: "Unknown",
    199: "Unknown",
    210: "Debug environment",
    219: "Unknown",
    229: "Unknown",
}


GHOST_ZONE_BY_ID: dict[str, GhostZone] = {
    g.ghost_id: g for g in GHOST_ZONE_CATALOG
}


def ghost_zones_by_kind(kind: GhostKind) -> tuple[GhostZone, ...]:
    return tuple(g for g in GHOST_ZONE_CATALOG if g.kind == kind)


def expansion_candidates() -> tuple[GhostZone, ...]:
    """Ghost zones flagged as worth re-implementing as content."""
    return tuple(
        g for g in GHOST_ZONE_CATALOG if g.expansion_candidate
    )


def total_variant_count() -> int:
    """Sum of all individual map variants across the catalog."""
    return sum(g.variant_count for g in GHOST_ZONE_CATALOG)


def get_ghost(ghost_id: str) -> GhostZone:
    return GHOST_ZONE_BY_ID[ghost_id]


__all__ = [
    "GhostKind", "GhostZone",
    "GHOST_ZONE_CATALOG", "GHOST_ZONE_BY_ID",
    "PLACEHOLDER_ZONE_IDS",
    "ghost_zones_by_kind", "expansion_candidates",
    "total_variant_count", "get_ghost",
]
