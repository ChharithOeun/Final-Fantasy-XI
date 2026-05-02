"""Fishing — rod, bait, zone catch tables.

Each fishing zone has a catch table: list of (item_id, weight,
bait_compat, rod_compat). The cast roll picks a candidate via
weighted draw on the rng_pool encounter stream; if rod or bait
don't match, the rod might break or you snag junk.

Public surface
--------------
    Rod, Bait dataclasses
    CatchEntry / FishingZone
    CastResult dataclass
    FISHING_ZONES sample
    cast(rod, bait, zone, rng_pool)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_ENCOUNTER_GEN


class CastOutcome(str, enum.Enum):
    CATCH = "catch"
    SNAG_JUNK = "snag_junk"
    LOST_BAIT = "lost_bait"
    ROD_BROKE = "rod_broke"
    NO_BITE = "no_bite"


@dataclasses.dataclass(frozen=True)
class Rod:
    rod_id: str
    label: str
    skill_required: int          # min fishing skill
    durability: int              # break risk increases as it depletes


@dataclasses.dataclass(frozen=True)
class Bait:
    bait_id: str
    label: str


@dataclasses.dataclass(frozen=True)
class CatchEntry:
    item_id: str
    label: str
    weight: int                  # relative odds within the zone
    bait_compat: tuple[str, ...] # bait_ids that work
    rod_compat: tuple[str, ...]  # rod_ids that work


@dataclasses.dataclass(frozen=True)
class FishingZone:
    zone_id: str
    name: str
    catches: tuple[CatchEntry, ...]
    junk_chance: float = 0.15       # 15% chance to pull junk


# Sample catalog
ROD_BAMBOO = Rod("bamboo_rod", "Bamboo Fishing Rod",
                 skill_required=0, durability=50)
ROD_GLASS = Rod("glass_rod", "Glass Fiber Fishing Rod",
                skill_required=10, durability=100)
ROD_CARBON = Rod("carbon_rod", "Carbon Fishing Rod",
                 skill_required=30, durability=200)

BAIT_INSECT = Bait("insect_paste", "Insect Paste")
BAIT_LUGWORM = Bait("lugworm", "Lugworm")
BAIT_SHRIMP = Bait("shrimp_lure", "Shrimp Lure")
BAIT_MEATBALL = Bait("meatball", "Meatball")


SELBINA_DOCKS = FishingZone(
    zone_id="selbina_docks", name="Selbina Docks",
    catches=(
        CatchEntry("bluetail", "Bluetail Fish",
                   weight=40,
                   bait_compat=("lugworm", "shrimp_lure"),
                   rod_compat=("bamboo_rod", "glass_rod",
                               "carbon_rod")),
        CatchEntry("nebimonite", "Nebimonite",
                   weight=30,
                   bait_compat=("shrimp_lure",),
                   rod_compat=("glass_rod", "carbon_rod")),
        CatchEntry("titanictus", "Titanictus",
                   weight=2,           # the rare big fish
                   bait_compat=("meatball",),
                   rod_compat=("carbon_rod",)),
    ),
)

LOWER_DELKFUTTS_TOWER = FishingZone(
    zone_id="lower_delkfutts", name="Lower Delkfutt's Tower",
    catches=(
        CatchEntry("dark_bass", "Dark Bass", weight=50,
                   bait_compat=("insect_paste",),
                   rod_compat=("bamboo_rod", "glass_rod",
                               "carbon_rod")),
    ),
    junk_chance=0.30,
)


FISHING_ZONES: tuple[FishingZone, ...] = (
    SELBINA_DOCKS, LOWER_DELKFUTTS_TOWER,
)


@dataclasses.dataclass(frozen=True)
class CastResult:
    outcome: CastOutcome
    item_id: t.Optional[str] = None
    rod_durability_after: t.Optional[int] = None


def cast(
    *,
    rod: Rod,
    rod_durability_remaining: int,
    bait: Bait,
    zone: FishingZone,
    fishing_skill: int,
    rng_pool: RngPool,
    stream_name: str = STREAM_ENCOUNTER_GEN,
) -> CastResult:
    """Cast the line. Returns CastResult with outcome and item."""
    if fishing_skill < rod.skill_required:
        return CastResult(outcome=CastOutcome.LOST_BAIT)
    if rod_durability_remaining <= 0:
        return CastResult(outcome=CastOutcome.ROD_BROKE)
    rng = rng_pool.stream(stream_name)
    # 1) Junk roll first
    if rng.random() < zone.junk_chance:
        return CastResult(
            outcome=CastOutcome.SNAG_JUNK,
            item_id="junk",
            rod_durability_after=rod_durability_remaining - 1,
        )
    # 2) Compatible catches
    eligible = [
        c for c in zone.catches
        if bait.bait_id in c.bait_compat
        and rod.rod_id in c.rod_compat
    ]
    if not eligible:
        return CastResult(
            outcome=CastOutcome.NO_BITE,
            rod_durability_after=rod_durability_remaining - 1,
        )
    total = sum(c.weight for c in eligible)
    pick = rng.uniform(0, total)
    cum = 0.0
    chosen = eligible[0]
    for c in eligible:
        cum += c.weight
        if pick <= cum:
            chosen = c
            break
    return CastResult(
        outcome=CastOutcome.CATCH,
        item_id=chosen.item_id,
        rod_durability_after=rod_durability_remaining - 1,
    )


__all__ = [
    "CastOutcome", "Rod", "Bait",
    "CatchEntry", "FishingZone",
    "ROD_BAMBOO", "ROD_GLASS", "ROD_CARBON",
    "BAIT_INSECT", "BAIT_LUGWORM", "BAIT_SHRIMP", "BAIT_MEATBALL",
    "SELBINA_DOCKS", "LOWER_DELKFUTTS_TOWER",
    "FISHING_ZONES",
    "CastResult", "cast",
]
