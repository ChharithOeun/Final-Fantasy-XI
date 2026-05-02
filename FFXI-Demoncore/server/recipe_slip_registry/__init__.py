"""Recipe Slip registry — Ambuscade Repurpose recipe catalog.

A Recipe Slip is a single-use Rare/Ex item that, when loaded
into a Synergy Workbench, names exactly which Ambuscade
upgrade is being attempted. The slip resolves to:

* slot (head/body/hands/legs/feet/...)
* archetype (caster / melee / ranger — bundles compatible jobs
  to keep the slip count down. A few outlier jobs use job-locked
  slips: PUP, BST, BLU, COR, RUN, GEO).
* tier_axis (ILVL or QUALITY)
* target_step (which i-lvl tier or quality tier this advances to)

Drop sources
------------
* Each Shadow Genkai boss drops 1 slip on kill at low rate
  (~3% per drop slot, max 1 per kill)
* High-end Fomor elites in shadow zones drop common slips at
  ~0.5% rate

This module owns the slip catalog. The actual drop tables live
in loot_table; the synergy workbench checks slip presence and
resolves slip metadata via this registry.

Public surface
--------------
    Slot enum
    Archetype enum
    TierAxis enum
    RecipeSlip dataclass
    RECIPE_SLIP_CATALOG (sample slice)
    SLIP_BY_ID
    slip_for(slot, archetype, axis, target_step) -> Optional[Slip]
    slips_for_drop_source(source_id) -> tuple[RecipeSlip, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Slot(str, enum.Enum):
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    NECK = "neck"
    EARRING = "earring"
    RING = "ring"
    BACK = "back"
    WAIST = "waist"


class Archetype(str, enum.Enum):
    """Bundle of jobs that share gear roles. Cuts slip count
    dramatically — a 'Caster Head Slip' applies to RDM/BLM/WHM/
    SCH/BRD/SMN/GEO. PUP/BST etc use job-locked slips."""
    CASTER = "caster"            # RDM/BLM/WHM/SCH/BRD/SMN/GEO
    MELEE = "melee"              # WAR/MNK/THF/DRG/SAM/DRK/PLD
    RANGER = "ranger"            # RNG/COR/HUNTER variants
    NINJA = "ninja"              # NIN-specific gear
    BLUE_MAGE = "blue_mage"      # BLU mixed melee/caster
    PUPPET = "puppet"            # PUP — automaton attachments / H2H
    BEAST = "beast"              # BST — pet-feeding gear
    DANCER = "dancer"            # DNC
    RUNE = "rune"                # RUN


class TierAxis(str, enum.Enum):
    ILVL = "ilvl"          # advances i-lvl tier (T0..T11, 120..175)
    QUALITY = "quality"    # advances quality (NQ..+4)


# How many tiers there are on each axis. ILVL has 12 (T0=120..T11=175),
# QUALITY has 5 (NQ + 4 upgrades).
ILVL_TIERS = 12
QUALITY_TIERS = 5


def ilvl_for_tier(tier: int) -> int:
    """Map i-lvl tier index to the actual i-lvl: 120, 125, ..., 175."""
    if not (0 <= tier < ILVL_TIERS):
        raise ValueError(f"ilvl tier {tier} out of range")
    return 120 + 5 * tier


@dataclasses.dataclass(frozen=True)
class RecipeSlip:
    slip_id: str
    label: str
    slot: Slot
    archetype: Archetype
    axis: TierAxis
    target_step: int           # i-lvl tier (0-11) or quality (0-4)
    drop_source_id: str        # mob/boss/instance that drops this
    drop_rate_pct: float = 1.0  # per-kill chance per drop slot

    @property
    def target_ilvl(self) -> t.Optional[int]:
        """For ILVL slips, the resulting i-lvl. None for QUALITY slips."""
        if self.axis == TierAxis.ILVL:
            return ilvl_for_tier(self.target_step)
        return None


# ---------------------------------------------------------------------
# Sample slip catalog
# ---------------------------------------------------------------------
# Each (slot, archetype) gets 12 ILVL slips + 4 QUALITY slips.
# Demonstrating the full ladder for one (Caster Head) below; the
# rest of the catalog can be authored as a table-driven generator
# in a follow-up content batch.
# ---------------------------------------------------------------------

_SOURCE_BY_ILVL_TIER: dict[int, str] = {
    # T0-T4 use elite Fomor mobs (common slips, easier to farm)
    0: "fomor_elite_warlord",
    1: "fomor_elite_warlord",
    2: "fomor_elite_warlock",
    3: "fomor_elite_warlock",
    4: "fomor_elite_inquisitor",
    # T5-T11 use Shadow Genkai bosses (rare slips, focused content)
    5: "shadow_genkai_khaavex",
    6: "shadow_genkai_zharzag",
    7: "shadow_genkai_morrho",
    8: "shadow_genkai_skhalya",
    9: "shadow_genkai_trokhaeb",
    10: "shadow_genkai_kael_nox",
    11: "shadow_genkai_asmodeus",
}


_QUALITY_SOURCES: tuple[str, ...] = (
    "shadow_fragment_common",       # +1 slip
    "shadow_fragment_refined",      # +2 slip
    "shadow_fragment_pristine",     # +3 slip
    "shadow_fragment_eternal",      # +4 slip (drops only from Asmodeus)
)


def _build_slot_archetype_slips(
    slot: Slot, archetype: Archetype,
) -> list[RecipeSlip]:
    out: list[RecipeSlip] = []
    base_label = f"{archetype.value.title()} {slot.value.title()}"
    # ILVL ladder
    for tier in range(ILVL_TIERS):
        out.append(RecipeSlip(
            slip_id=f"slip_{archetype.value}_{slot.value}_t{tier}",
            label=f"Recipe Slip: {base_label} T{tier} (i-lvl {ilvl_for_tier(tier)})",
            slot=slot, archetype=archetype,
            axis=TierAxis.ILVL, target_step=tier,
            drop_source_id=_SOURCE_BY_ILVL_TIER[tier],
            drop_rate_pct=3.0 if tier >= 5 else 0.5,
        ))
    # QUALITY ladder
    for q in range(1, QUALITY_TIERS):
        out.append(RecipeSlip(
            slip_id=f"slip_{archetype.value}_{slot.value}_q{q}",
            label=f"Recipe Slip: {base_label} +{q} Polish",
            slot=slot, archetype=archetype,
            axis=TierAxis.QUALITY, target_step=q,
            drop_source_id=_QUALITY_SOURCES[q - 1],
            drop_rate_pct=2.0 if q < 4 else 0.5,
        ))
    return out


# Build the full sample catalog: every slot × every archetype.
# In production this expands to hundreds of slips; here we keep
# it complete-but-modest by covering all 10 slots and all 9
# archetypes (90 (slot, archetype) buckets * 16 slips = 1440).
RECIPE_SLIP_CATALOG: tuple[RecipeSlip, ...] = tuple(
    slip
    for slot in Slot
    for archetype in Archetype
    for slip in _build_slot_archetype_slips(slot, archetype)
)


SLIP_BY_ID: dict[str, RecipeSlip] = {
    s.slip_id: s for s in RECIPE_SLIP_CATALOG
}


def slip_for(*, slot: Slot, archetype: Archetype,
              axis: TierAxis, target_step: int
              ) -> t.Optional[RecipeSlip]:
    """Look up a slip by its semantic key."""
    for s in RECIPE_SLIP_CATALOG:
        if (s.slot == slot and s.archetype == archetype
                and s.axis == axis and s.target_step == target_step):
            return s
    return None


def slips_for_drop_source(source_id: str) -> tuple[RecipeSlip, ...]:
    """All slips that drop from a given mob/boss/instance."""
    return tuple(
        s for s in RECIPE_SLIP_CATALOG if s.drop_source_id == source_id
    )


__all__ = [
    "Slot", "Archetype", "TierAxis",
    "ILVL_TIERS", "QUALITY_TIERS",
    "ilvl_for_tier",
    "RecipeSlip", "RECIPE_SLIP_CATALOG", "SLIP_BY_ID",
    "slip_for", "slips_for_drop_source",
]
