"""Fomor wardrobe — what a fomor is wearing right now.

When a player permadeaths into a fomor, their equipped gear migrates
into a FomorWardrobe. The wardrobe is then the loot pool: each
attempt_drops() roll iterates these pieces.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .lineage import GearPiece, HolderType, LineageEvent


@dataclasses.dataclass
class FomorWardrobe:
    """Per-fomor equipped-gear state."""
    fomor_id: str
    fomor_level: int
    pieces: list[GearPiece] = dataclasses.field(default_factory=list)

    def remove(self, piece: GearPiece) -> None:
        """Remove a piece from the wardrobe. Used after a successful
        drop or when the piece is destroyed."""
        try:
            self.pieces.remove(piece)
        except ValueError:
            pass

    def destroy_all(self, *, now: float, killer_fomor_id: str) -> list[GearPiece]:
        """Fomor-vs-fomor kill: every piece is permanently destroyed.
        Returns the destroyed pieces (with lineage stamped)."""
        destroyed = list(self.pieces)
        for piece in destroyed:
            piece.current_holder = None
            piece.current_holder_type = HolderType.DESTROYED
            piece.append_lineage(LineageEvent(
                timestamp=now,
                holder_id=killer_fomor_id,
                holder_type=HolderType.FOMOR,
                event="destroyed_fomor_vs_fomor",
                detail=f"killed by fomor {killer_fomor_id}",
            ))
        self.pieces.clear()
        return destroyed

    def return_to_world(self, piece: GearPiece, *, now: float,
                         reason: str = "recursion_miss") -> None:
        """The piece is removed from this wardrobe but NOT destroyed —
        it returns to the live world (drops to the killer's loot pool
        OR vanishes from gear pool if no one is around to receive it).

        Per the design doc this happens when a recursion miss occurs:
        wearer permadeaths into a fomor, killer rolls and the 3% per
        piece doesn't hit — the piece returns from the fomor wardrobe.
        """
        self.remove(piece)
        piece.current_holder = None
        piece.current_holder_type = HolderType.BANK
        piece.append_lineage(LineageEvent(
            timestamp=now,
            holder_id=self.fomor_id,
            holder_type=HolderType.FOMOR,
            event="returned_to_world",
            detail=reason,
        ))
