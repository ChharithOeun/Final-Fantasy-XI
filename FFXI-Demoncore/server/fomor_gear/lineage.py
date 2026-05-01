"""Gear template + per-piece state + lineage history + tier scaling.

A piece of gear in Demoncore is a long-lived object that travels
between holders. Each piece remembers:
- which template it came from (the base item)
- its current tier (vanilla -> +V)
- who has held it through history (the lineage chain)
- who holds it now (player / fomor / vendor / etc.)

Tier scaling is uniform: every stat the piece has scales by
(1 + tier * 0.05). A +III Cobra Tunic has 15% more attack, 15% more
defense, 15% more of every proc — no random per-stat rolls.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GearTier(enum.IntEnum):
    """Purple-stat tier. Each step adds +5% to all stats; cap at +V."""
    VANILLA = 0
    PURPLE_I = 1
    PURPLE_II = 2
    PURPLE_III = 3
    PURPLE_IV = 4
    PURPLE_V = 5

    def label(self) -> str:
        return {
            0: "",
            1: "+I",
            2: "+II",
            3: "+III",
            4: "+IV",
            5: "+V",
        }[int(self)]

    def stat_multiplier(self) -> float:
        """Multiplier applied to all base stats. +V caps at 1.25."""
        return 1.0 + 0.05 * int(self)


class HolderType(str, enum.Enum):
    PLAYER = "player"
    FOMOR = "fomor"
    VENDOR = "vendor"
    BANK = "bank"
    DESTROYED = "destroyed"


@dataclasses.dataclass(frozen=True)
class GearRequirements:
    """Equip prereqs. Apply uniformly across vanilla and improved tiers."""
    min_level: int = 1
    job: t.Optional[str] = None              # job code (e.g. "WAR"); None = any
    sub_job: t.Optional[str] = None          # required sub
    race: t.Optional[str] = None             # restricted race; None = any
    elemental_affinity: t.Optional[str] = None  # element gating


@dataclasses.dataclass(frozen=True)
class GearTemplate:
    """The base definition of a piece. Templates are shared; instances
    (GearPiece) carry per-copy state."""
    base_id: str
    name: str
    base_stats: dict[str, float]
    requirements: GearRequirements = dataclasses.field(
        default_factory=GearRequirements)


@dataclasses.dataclass
class LineageEvent:
    """One step in a piece's history."""
    timestamp: float
    holder_id: str
    holder_type: HolderType
    event: str   # "crafted", "looted_from_fomor", "died_to_fomor",
                 # "destroyed_fomor_vs_fomor", "returned_to_world", ...
    detail: t.Optional[str] = None   # extra context for the lineage UI


@dataclasses.dataclass
class GearPiece:
    """Per-instance gear state."""
    gear_id: str                                # globally unique
    template: GearTemplate
    tier: GearTier = GearTier.VANILLA
    current_holder: t.Optional[str] = None
    current_holder_type: HolderType = HolderType.PLAYER
    lineage_history: list[LineageEvent] = dataclasses.field(default_factory=list)

    def is_at_cap(self) -> bool:
        return self.tier == GearTier.PURPLE_V

    def next_tier(self) -> GearTier:
        """Tier the piece would be at if it dropped from a fomor wearing it.
        +V stays at +V (capped)."""
        if self.is_at_cap():
            return GearTier.PURPLE_V
        return GearTier(int(self.tier) + 1)

    def append_lineage(self, event: LineageEvent) -> None:
        self.lineage_history.append(event)


def scaled_stats(piece: GearPiece) -> dict[str, float]:
    """Return the piece's effective stats at its current tier."""
    mult = piece.tier.stat_multiplier()
    return {k: v * mult for k, v in piece.template.base_stats.items()}
