"""Repair NPC economy hook — gil-sink for fast-forward healing.

Per DAMAGE_PHYSICS_HEALING.md every nation has 2-4 Repair NPCs that:
    - Stand near commonly-damaged areas (gates, lighthouses, mines).
    - Charge gil to fast-forward healing on a single structure.
    - Cost scales with HP missing:
          (HP_missing / HP_max) * gil_per_HP_max
    - Themselves level up via NPC progression - higher-skill repairers
      unlock special structures (e.g. only Voinaut's apprentice past
      lvl 60 can repair the Metalworks elevator).
"""
from __future__ import annotations

import dataclasses
import math
import typing as t

from .structure_state import (
    HealingStructure,
    VisibleState,
    resolve_visible_state,
)


@dataclasses.dataclass(frozen=True)
class RepairQuote:
    """Output of quote_repair — what the NPC charges and what gets done."""
    structure_id: str
    hp_missing: int
    hp_max: int
    gil_cost: int
    fully_repairable: bool
    refusal_reason: t.Optional[str] = None


@dataclasses.dataclass
class RepairNpc:
    """One per-nation repair NPC.

    Levels up via NPC progression. Has gating:
        - skill_level required to repair restricted_kinds
        - permanent damage requires unlock_permanent_repair=True
          (only set during city-wide gil-pool repair events)
    """
    npc_id: str
    name: str
    nation: str
    home_zone: str
    crafts_supported: tuple[str, ...]   # MaterialClass values they handle
    skill_level: int = 1
    gil_per_hp_max: int = 100
    restricted_kinds: tuple[str, ...] = ()
    restricted_kinds_min_skill: int = 60
    unlock_permanent_repair: bool = False

    def can_repair_kind(self, kind: str, *, material: str) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        if material not in self.crafts_supported:
            return False, f"{self.name} doesn't work {material}"
        if kind in self.restricted_kinds:
            if self.skill_level < self.restricted_kinds_min_skill:
                return False, (f"{self.name} can't repair {kind} until "
                                f"skill level {self.restricted_kinds_min_skill}")
        return True, ""


def quote_repair(
    npc: RepairNpc,
    structure: HealingStructure,
    *,
    material: str,
) -> RepairQuote:
    """Compute the gil cost to fully repair `structure`.

    Returns a RepairQuote. If the NPC can't service this structure
    (wrong material, insufficient skill, permanent without unlock),
    returns a quote with refusal_reason set and gil_cost=0.
    """
    allowed, reason = npc.can_repair_kind(structure.kind, material=material)
    if not allowed:
        return RepairQuote(
            structure_id=structure.structure_id,
            hp_missing=structure.hp_max - structure.hp_current,
            hp_max=structure.hp_max,
            gil_cost=0,
            fully_repairable=False,
            refusal_reason=reason,
        )
    if structure.permanent and not npc.unlock_permanent_repair:
        return RepairQuote(
            structure_id=structure.structure_id,
            hp_missing=structure.hp_max,
            hp_max=structure.hp_max,
            gil_cost=0,
            fully_repairable=False,
            refusal_reason=("permanent damage requires a city gil-pool "
                              "campaign before this NPC can repair"),
        )
    hp_missing = max(0, structure.hp_max - structure.hp_current)
    if hp_missing == 0:
        return RepairQuote(
            structure_id=structure.structure_id,
            hp_missing=0, hp_max=structure.hp_max,
            gil_cost=0, fully_repairable=True,
        )
    fraction = hp_missing / structure.hp_max
    gil_cost = max(1, math.ceil(fraction * npc.gil_per_hp_max))
    return RepairQuote(
        structure_id=structure.structure_id,
        hp_missing=hp_missing, hp_max=structure.hp_max,
        gil_cost=gil_cost, fully_repairable=True,
    )


def apply_repair(
    npc: RepairNpc,
    structure: HealingStructure,
    *,
    gil_paid: int,
    material: str,
    now: float,
) -> tuple[bool, str, int]:
    """Apply paid repair. Returns (success, reason, hp_restored).

    `gil_paid` may be less than the full quote — partial repair is
    allowed (the NPC heals proportionally). 0 gil_paid is rejected.
    """
    if gil_paid <= 0:
        return False, "must pay positive gil", 0
    quote = quote_repair(npc, structure, material=material)
    if quote.refusal_reason is not None:
        return False, quote.refusal_reason, 0
    if quote.gil_cost == 0:
        return False, "structure already at full HP", 0
    fraction_paid = min(1.0, gil_paid / quote.gil_cost)
    hp_restore = int(round(quote.hp_missing * fraction_paid))
    structure.hp_current = min(structure.hp_max,
                                  structure.hp_current + hp_restore)
    structure.visible_state = resolve_visible_state(structure.hp_current,
                                                       structure.hp_max)
    if structure.hp_current >= structure.hp_max:
        structure.last_hit_at = None    # full reset
    return True, "", hp_restore


# ----------------------------------------------------------------------
# Roster — three nations' anchors per the doc.
# ----------------------------------------------------------------------

REPAIR_NPC_ROSTER: dict[str, RepairNpc] = {
    "voinaut": RepairNpc(
        npc_id="voinaut",
        name="Voinaut",
        nation="bastok",
        home_zone="bastok_metalworks",
        crafts_supported=("stone_brick", "stone_carved",
                            "metal_industrial"),
        skill_level=72,
        gil_per_hp_max=120,
        restricted_kinds=("metalworks_elevator",
                            "bastok_city_gate"),
        restricted_kinds_min_skill=60,
    ),
    "pellah": RepairNpc(
        npc_id="pellah",
        name="Pellah",
        nation="san_doria",
        home_zone="south_sandoria",
        crafts_supported=("wood", "cloth_banner"),
        skill_level=68,
        gil_per_hp_max=110,
        restricted_kinds=("cathedral_buttress",),
    ),
    "mihli": RepairNpc(
        npc_id="mihli",
        name="Mihli",
        nation="windurst",
        home_zone="windurst_woods",
        crafts_supported=("wood", "stone_brick", "glass_window",
                            "cloth_banner"),
        skill_level=58,
        gil_per_hp_max=95,
    ),
}


def get_repair_npc(npc_id: str) -> t.Optional[RepairNpc]:
    return REPAIR_NPC_ROSTER.get(npc_id)
