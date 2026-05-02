"""Ambuscade Repurpose progression — per-player per-piece tracker.

Holds the state for each Ambuscade-tier piece a player has
crafted. Two independent axes:

* i-lvl tier (0-11)  -> i-lvl 120, 125, ..., 175
* quality (0-4)      -> NQ, +1, +2, +3, +4

Either axis can advance independently. Upgrading from i-lvl T2 +1
to i-lvl T3 +1 only costs the T3 ILVL slip + materials, not a
fresh quality re-roll.

A player can hold multiple Ambuscade pieces in the same slot —
e.g. one for caster, one for melee — but a synth always advances
ONE specific piece (identified by piece_id).

Public surface
--------------
    AmbuscadePiece dataclass — single piece's tracker
    PlayerAmbuscadeProgression — collection per-player
    AdvanceResult / advance_piece(...)
    base_stat_block(slot) -> stat dict at NQ T0
    apply_tier_bonus(stats, ilvl_tier, quality) -> dict
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.recipe_slip_registry import (
    Archetype,
    Slot,
    TierAxis,
    ilvl_for_tier,
)


# Per-i-lvl-tier stat scaling. Each tier adds this much to each
# stat the piece carries (slot-specific). Tuned so a T11 +4 piece
# is meaningfully better than a T0 NQ but not 10x.
ILVL_STAT_BUMP_PER_TIER = 3

# Per-quality-tier stat bump (independent of i-lvl tier).
QUALITY_STAT_BUMP = 5


# Slot-specific base stat blocks. These are what an Ambuscade NQ
# T0 piece offers fresh out of the bench. Real stats are then
# scaled by tier + quality.
_BASE_STATS_BY_SLOT: dict[Slot, dict[str, int]] = {
    Slot.HEAD: {"str": 5, "dex": 5, "int": 5, "mnd": 5,
                 "hp": 30, "defense": 35},
    Slot.BODY: {"str": 8, "vit": 8, "int": 6, "mnd": 6,
                 "hp": 60, "defense": 70},
    Slot.HANDS: {"str": 5, "dex": 7, "int": 4, "mnd": 4,
                  "hp": 25, "defense": 30, "attack": 5},
    Slot.LEGS: {"str": 7, "vit": 7, "agi": 5, "mnd": 5,
                 "hp": 45, "defense": 55},
    Slot.FEET: {"agi": 8, "dex": 5, "vit": 4,
                 "hp": 25, "defense": 25, "evasion": 5},
    Slot.NECK: {"int": 4, "mnd": 4, "chr": 4, "hp": 15},
    Slot.EARRING: {"dex": 3, "agi": 3, "hp": 10},
    Slot.RING: {"str": 3, "dex": 3, "int": 3, "mnd": 3, "hp": 10},
    Slot.BACK: {"str": 4, "dex": 4, "agi": 4, "hp": 20},
    Slot.WAIST: {"str": 4, "vit": 4, "dex": 4, "hp": 15},
}


def base_stat_block(*, slot: Slot) -> dict[str, int]:
    """Return a copy of the slot's base (NQ T0) stat block."""
    return dict(_BASE_STATS_BY_SLOT[slot])


def apply_tier_bonus(
    *, base: dict[str, int], ilvl_tier: int, quality: int,
) -> dict[str, int]:
    """Apply tier + quality bumps to a base block. Each numeric
    stat gets +ilvl_tier*ILVL_STAT_BUMP + quality*QUALITY_STAT_BUMP."""
    if not (0 <= ilvl_tier < 12):
        raise ValueError(f"ilvl_tier {ilvl_tier} out of range 0-11")
    if not (0 <= quality < 5):
        raise ValueError(f"quality {quality} out of range 0-4")
    bump = ilvl_tier * ILVL_STAT_BUMP_PER_TIER + quality * QUALITY_STAT_BUMP
    return {k: v + bump for k, v in base.items()}


@dataclasses.dataclass
class AmbuscadePiece:
    piece_id: str
    slot: Slot
    archetype: Archetype
    ilvl_tier: int = 0    # 0..11
    quality: int = 0      # 0..4

    @property
    def ilvl(self) -> int:
        return ilvl_for_tier(self.ilvl_tier)

    @property
    def quality_label(self) -> str:
        return "NQ" if self.quality == 0 else f"+{self.quality}"

    def stats(self) -> dict[str, int]:
        return apply_tier_bonus(
            base=base_stat_block(slot=self.slot),
            ilvl_tier=self.ilvl_tier,
            quality=self.quality,
        )


@dataclasses.dataclass(frozen=True)
class AdvanceResult:
    accepted: bool
    new_ilvl_tier: int = 0
    new_quality: int = 0
    new_ilvl: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerAmbuscadeProgression:
    player_id: str
    _pieces: dict[str, AmbuscadePiece] = dataclasses.field(
        default_factory=dict,
    )

    @property
    def pieces(self) -> tuple[AmbuscadePiece, ...]:
        return tuple(self._pieces.values())

    def get(self, piece_id: str) -> t.Optional[AmbuscadePiece]:
        return self._pieces.get(piece_id)

    def craft_new(
        self, *, piece_id: str, slot: Slot, archetype: Archetype,
    ) -> AmbuscadePiece:
        """Synthesize a fresh NQ T0 piece (entry point — first synth)."""
        piece = AmbuscadePiece(
            piece_id=piece_id, slot=slot, archetype=archetype,
        )
        self._pieces[piece_id] = piece
        return piece

    def advance_ilvl(
        self, *, piece_id: str, target_step: int,
    ) -> AdvanceResult:
        """Advance the i-lvl tier on a piece. target_step must be
        the NEXT tier — no skipping. (Skipping enforced because
        each tier requires its own slip + bracket of input gear.)"""
        p = self._pieces.get(piece_id)
        if p is None:
            return AdvanceResult(False, reason="no such piece")
        if target_step != p.ilvl_tier + 1:
            return AdvanceResult(
                False, reason="must advance one tier at a time",
            )
        if target_step >= 12:
            return AdvanceResult(False, reason="already at max i-lvl")
        p.ilvl_tier = target_step
        return AdvanceResult(
            accepted=True,
            new_ilvl_tier=p.ilvl_tier,
            new_quality=p.quality,
            new_ilvl=p.ilvl,
        )

    def advance_quality(
        self, *, piece_id: str, target_step: int,
    ) -> AdvanceResult:
        """Bump the quality tier. Same one-step-at-a-time rule."""
        p = self._pieces.get(piece_id)
        if p is None:
            return AdvanceResult(False, reason="no such piece")
        if target_step != p.quality + 1:
            return AdvanceResult(
                False, reason="must advance one quality tier at a time",
            )
        if target_step >= 5:
            return AdvanceResult(False, reason="already at +4")
        p.quality = target_step
        return AdvanceResult(
            accepted=True,
            new_ilvl_tier=p.ilvl_tier,
            new_quality=p.quality,
            new_ilvl=p.ilvl,
        )

    def can_advance(self, *, piece_id: str,
                     axis: TierAxis) -> bool:
        p = self._pieces.get(piece_id)
        if p is None:
            return False
        if axis == TierAxis.ILVL:
            return p.ilvl_tier < 11
        return p.quality < 4


__all__ = [
    "ILVL_STAT_BUMP_PER_TIER", "QUALITY_STAT_BUMP",
    "base_stat_block", "apply_tier_bonus",
    "AmbuscadePiece", "AdvanceResult",
    "PlayerAmbuscadeProgression",
]
