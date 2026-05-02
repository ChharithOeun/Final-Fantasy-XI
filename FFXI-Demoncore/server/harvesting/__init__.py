"""Harvesting — mining, logging, harvesting, excavation.

Four professions, each tied to a tool type and a node family.
A node has a yield table (item_id -> weight). Tools have durability;
each successful gather drops durability by 1, with a chance to break
on top of that.

Public surface
--------------
    GatheringKind enum (mine/log/harvest/excavate)
    Tool dataclass with durability + break_chance per use
    GatheringNode dataclass with yields
    GatherResult: item_id (None on no-bite), tool_durability_after,
                  tool_broke
    NODES sample catalog
    gather(kind, tool_durability_remaining, node, rng_pool)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_ENCOUNTER_GEN


class GatheringKind(str, enum.Enum):
    MINE = "mine"            # mining (pickaxe)
    LOG = "log"              # logging (hatchet)
    HARVEST = "harvest"      # harvesting (sickle)
    EXCAVATE = "excavate"    # excavation (chocobo)


@dataclasses.dataclass(frozen=True)
class Tool:
    tool_id: str
    label: str
    kind: GatheringKind
    base_durability: int
    break_chance_per_use: float


PICKAXE = Tool("pickaxe", "Pickaxe", GatheringKind.MINE,
               base_durability=12, break_chance_per_use=0.10)
HATCHET = Tool("hatchet", "Hatchet", GatheringKind.LOG,
               base_durability=12, break_chance_per_use=0.10)
SICKLE = Tool("sickle", "Sickle", GatheringKind.HARVEST,
              base_durability=12, break_chance_per_use=0.10)
EXCAVATE_CHOCOBO = Tool("chocobo", "Trained Chocobo",
                        GatheringKind.EXCAVATE,
                        base_durability=20,
                        break_chance_per_use=0.05)


@dataclasses.dataclass(frozen=True)
class YieldEntry:
    item_id: str
    weight: int


@dataclasses.dataclass(frozen=True)
class GatheringNode:
    node_id: str
    label: str
    kind: GatheringKind
    zone_id: str
    yields: tuple[YieldEntry, ...]
    no_yield_chance: float = 0.20    # 20% nothing-found rate


# Sample nodes
ZERUHN_VEIN = GatheringNode(
    node_id="zeruhn_vein", label="Zeruhn Mining Vein",
    kind=GatheringKind.MINE, zone_id="zeruhn_mines",
    yields=(
        YieldEntry("copper_ore", weight=40),
        YieldEntry("zinc_ore", weight=30),
        YieldEntry("iron_ore", weight=20),
        YieldEntry("silver_ore", weight=8),
        YieldEntry("gold_ore", weight=2),
    ),
)

JUGNER_LOG = GatheringNode(
    node_id="jugner_log", label="Jugner Forest Log",
    kind=GatheringKind.LOG, zone_id="jugner_forest",
    yields=(
        YieldEntry("ash_log", weight=35),
        YieldEntry("oak_log", weight=30),
        YieldEntry("walnut_log", weight=25),
        YieldEntry("ebony_log", weight=8),
        YieldEntry("rosewood_log", weight=2),
    ),
)

ROLANBERRY_HARVEST = GatheringNode(
    node_id="rolanberry_harvest", label="Rolanberry Harvest",
    kind=GatheringKind.HARVEST,
    zone_id="rolanberry_fields",
    yields=(
        YieldEntry("rolanberry", weight=50),
        YieldEntry("apkallu_egg", weight=25),
        YieldEntry("blue_pepper", weight=15),
        YieldEntry("kazham_pineapple", weight=10),
    ),
)

ALTEPA_EXCAVATION = GatheringNode(
    node_id="altepa_excavation", label="Altepa Excavation",
    kind=GatheringKind.EXCAVATE, zone_id="western_altepa",
    yields=(
        YieldEntry("flint_stone", weight=40),
        YieldEntry("pebble", weight=30),
        YieldEntry("ancient_papyrus", weight=15),
        YieldEntry("luminian_tile", weight=10),
        YieldEntry("dragon_bone", weight=5),
    ),
)

NODES: tuple[GatheringNode, ...] = (
    ZERUHN_VEIN, JUGNER_LOG, ROLANBERRY_HARVEST, ALTEPA_EXCAVATION,
)


@dataclasses.dataclass(frozen=True)
class GatherResult:
    item_id: t.Optional[str]
    tool_durability_after: int
    tool_broke: bool


def gather(
    *,
    tool: Tool,
    tool_durability_remaining: int,
    node: GatheringNode,
    rng_pool: RngPool,
    stream_name: str = STREAM_ENCOUNTER_GEN,
) -> GatherResult:
    """Perform one gather. Returns the item gathered (or None) plus
    tool state after the swing."""
    if tool.kind != node.kind:
        return GatherResult(
            item_id=None,
            tool_durability_after=tool_durability_remaining,
            tool_broke=False,
        )
    if tool_durability_remaining <= 0:
        return GatherResult(
            item_id=None, tool_durability_after=0,
            tool_broke=True,
        )
    rng = rng_pool.stream(stream_name)
    # 1) No-yield roll
    if rng.random() < node.no_yield_chance:
        item = None
    else:
        # 2) Pick from yields
        total = sum(y.weight for y in node.yields)
        roll = rng.uniform(0, total)
        cum = 0.0
        item = node.yields[0].item_id
        for y in node.yields:
            cum += y.weight
            if roll <= cum:
                item = y.item_id
                break
    # 3) Tool damage
    new_durability = tool_durability_remaining - 1
    broke = False
    if rng.random() < tool.break_chance_per_use:
        new_durability = 0
        broke = True
    return GatherResult(
        item_id=item,
        tool_durability_after=new_durability,
        tool_broke=broke,
    )


__all__ = [
    "GatheringKind", "Tool",
    "PICKAXE", "HATCHET", "SICKLE", "EXCAVATE_CHOCOBO",
    "YieldEntry", "GatheringNode",
    "ZERUHN_VEIN", "JUGNER_LOG", "ROLANBERRY_HARVEST",
    "ALTEPA_EXCAVATION", "NODES",
    "GatherResult", "gather",
]
