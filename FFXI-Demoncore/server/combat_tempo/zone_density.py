"""Per-zone-type spawn-density anchors.

Per COMBAT_TEMPO.md the doc names four zone tiers and gives a
spawn-count band for each:

    Newbie      Ronfaure / Sarutabaruta / Gustaberg     500-800
    Mid-tier    Jugner / Yhoator / Pashhow              800-1500
    High-tier   Beadeaux / Ifrit's Cauldron             1500-2500
    End-game    Sky / Sea / Dynamis / Limbus            2000+, NM 5x

This is mob spawn count per zone — distinct from
server.ai_density.density_budget which budgets AI-tier brains.
The two systems compose: a high-tier zone runs 1500-2500 mobs
total, of which some count comes from each AiTier.
"""
from __future__ import annotations

import dataclasses
import enum


class ZoneTier(str, enum.Enum):
    """The four tiers the doc names."""
    NEWBIE = "newbie"
    MID_TIER = "mid_tier"
    HIGH_TIER = "high_tier"
    END_GAME = "end_game"


@dataclasses.dataclass(frozen=True)
class ZoneDensityBand:
    """One row from the doc's zone-density table."""
    tier: ZoneTier
    min_mobs: int
    max_mobs: int
    nm_density_multiplier: float    # 5.0 for end-game, 1.0 elsewhere
    rationale: str

    @property
    def midpoint(self) -> int:
        return (self.min_mobs + self.max_mobs) // 2

    def contains(self, mob_count: int) -> bool:
        return self.min_mobs <= mob_count <= self.max_mobs


ZONE_DENSITY_BANDS: dict[ZoneTier, ZoneDensityBand] = {
    ZoneTier.NEWBIE: ZoneDensityBand(
        tier=ZoneTier.NEWBIE,
        min_mobs=500, max_mobs=800,
        nm_density_multiplier=1.0,
        rationale=("Lots of trash to feel alive; XP is plentiful"),
    ),
    ZoneTier.MID_TIER: ZoneDensityBand(
        tier=ZoneTier.MID_TIER,
        min_mobs=800, max_mobs=1500,
        nm_density_multiplier=1.0,
        rationale="Bigger, denser, more variety",
    ),
    ZoneTier.HIGH_TIER: ZoneDensityBand(
        tier=ZoneTier.HIGH_TIER,
        min_mobs=1500, max_mobs=2500,
        nm_density_multiplier=1.0,
        rationale="Hostile, oppressive, players move slowly",
    ),
    ZoneTier.END_GAME: ZoneDensityBand(
        tier=ZoneTier.END_GAME,
        min_mobs=2000, max_mobs=4000,    # 'with NM density 5x'
        nm_density_multiplier=5.0,
        rationale="The reason you go there",
    ),
}


# Doc-named zones per tier (level-design hint; not exhaustive).
TIER_ANCHOR_ZONES: dict[ZoneTier, tuple[str, ...]] = {
    ZoneTier.NEWBIE: ("ronfaure", "sarutabaruta", "gustaberg"),
    ZoneTier.MID_TIER: ("jugner", "yhoator", "pashhow"),
    ZoneTier.HIGH_TIER: ("beadeaux", "ifrits_cauldron"),
    ZoneTier.END_GAME: ("sky", "sea", "dynamis", "limbus"),
}


def get_band(tier: ZoneTier) -> ZoneDensityBand:
    return ZONE_DENSITY_BANDS[tier]


def density_target(tier: ZoneTier) -> int:
    """Default spawn count to aim for — band midpoint."""
    return get_band(tier).midpoint


def is_in_band(tier: ZoneTier, mob_count: int) -> bool:
    """Diagnostic: does this zone's actual spawn count match its tier?"""
    return get_band(tier).contains(mob_count)


def nm_target_count(tier: ZoneTier, *, base_nm_count: int) -> int:
    """Apply the tier's NM density multiplier to a base count.

    Doc: end-game zones run 5x normal NM density.
    """
    if base_nm_count < 0:
        raise ValueError("base_nm_count must be non-negative")
    band = get_band(tier)
    return int(round(base_nm_count * band.nm_density_multiplier))


def tier_for_zone(zone_id: str) -> ZoneTier:
    """Best-effort lookup. Falls back to MID_TIER for unknown zones."""
    for tier, zones in TIER_ANCHOR_ZONES.items():
        for prefix in zones:
            if zone_id.startswith(prefix):
                return tier
    return ZoneTier.MID_TIER
