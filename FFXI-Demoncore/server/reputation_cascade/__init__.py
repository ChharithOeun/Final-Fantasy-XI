"""Reputation cascade — rep changes propagate to related factions.

A faction-rep change in one faction echoes into adjacent ones.
Earn 50 rep with the Yagudo and you'll lose ~25 rep with
Windurst (canonical FFXI: helping the rivals hurts your standing).
The cascade respects an alignment GRAPH where each edge declares
the propagation coefficient (positive = ally; negative = rival).

Public surface
--------------
    AlignmentEdge dataclass — coefficient -1.0..1.0
    CascadeChange dataclass — original delta + propagated deltas
    ReputationCascadeRegistry
        .add_alignment(src_faction, dst_faction, coefficient)
        .propagate(player_id, source_faction, delta, rep)
            -> CascadeChange
        .neighbors(faction)
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.faction_reputation import PlayerFactionReputation


# Coefficient bounds.
COEFFICIENT_MIN = -1.0
COEFFICIENT_MAX = 1.0


@dataclasses.dataclass(frozen=True)
class AlignmentEdge:
    src_faction_id: str
    dst_faction_id: str
    coefficient: float          # -1.0..1.0
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class CascadeChange:
    source_faction: str
    source_delta: int
    propagated: dict[str, int]    # faction -> propagated delta


@dataclasses.dataclass
class ReputationCascadeRegistry:
    _edges: list[AlignmentEdge] = dataclasses.field(
        default_factory=list,
    )

    def add_alignment(
        self, *, src: str, dst: str, coefficient: float,
        notes: str = "",
    ) -> AlignmentEdge:
        if not (COEFFICIENT_MIN <= coefficient <= COEFFICIENT_MAX):
            raise ValueError(
                f"coefficient {coefficient} out of "
                f"{COEFFICIENT_MIN}..{COEFFICIENT_MAX}",
            )
        edge = AlignmentEdge(
            src_faction_id=src, dst_faction_id=dst,
            coefficient=coefficient, notes=notes,
        )
        self._edges.append(edge)
        return edge

    def neighbors(
        self, faction_id: str,
    ) -> tuple[AlignmentEdge, ...]:
        return tuple(
            e for e in self._edges
            if e.src_faction_id == faction_id
        )

    def propagate(
        self, *, player_id: str, source_faction: str,
        source_delta: int,
        rep: PlayerFactionReputation,
    ) -> CascadeChange:
        # Apply the source change first
        rep.adjust(faction_id=source_faction, delta=source_delta)
        propagated: dict[str, int] = {}
        for edge in self._edges:
            if edge.src_faction_id != source_faction:
                continue
            scaled = int(round(source_delta * edge.coefficient))
            if scaled == 0:
                continue
            rep.adjust(
                faction_id=edge.dst_faction_id, delta=scaled,
            )
            propagated[edge.dst_faction_id] = (
                propagated.get(edge.dst_faction_id, 0) + scaled
            )
        return CascadeChange(
            source_faction=source_faction,
            source_delta=source_delta,
            propagated=propagated,
        )

    def total_edges(self) -> int:
        return len(self._edges)


# Default seed — canonical FFXI alignments.
def _default_edges() -> tuple[
    tuple[str, str, float], ...,
]:
    return (
        # Beastmen vs the nation they antagonize
        ("orc", "san_doria", -0.5),
        ("san_doria", "orc", -0.5),
        ("quadav", "bastok", -0.5),
        ("bastok", "quadav", -0.5),
        ("yagudo", "windurst", -0.5),
        ("windurst", "yagudo", -0.5),
        # Beastmen tribal frenemies
        ("orc", "goblin", -0.3),
        ("goblin", "sahagin", -0.3),
        ("sahagin", "merrow", -0.4),
        ("antica", "mamool_ja", -0.4),
        # Nation alliances (TripleA: positive among nations)
        ("bastok", "san_doria", 0.2),
        ("san_doria", "bastok", 0.2),
        ("bastok", "windurst", 0.2),
        ("windurst", "bastok", 0.2),
        ("san_doria", "windurst", 0.2),
        ("windurst", "san_doria", 0.2),
        # Jeuno is neutral mediator — small positive to all 3 nations
        ("jeuno", "bastok", 0.15),
        ("jeuno", "san_doria", 0.15),
        ("jeuno", "windurst", 0.15),
        ("bastok", "jeuno", 0.15),
        ("san_doria", "jeuno", 0.15),
        ("windurst", "jeuno", 0.15),
        # Tenshodo grey-market: helping them upsets nations slightly
        ("tenshodo", "bastok", -0.1),
        ("tenshodo", "san_doria", -0.1),
        ("tenshodo", "windurst", -0.1),
    )


def seed_default_alignment(
    registry: ReputationCascadeRegistry,
) -> ReputationCascadeRegistry:
    for src, dst, coef in _default_edges():
        registry.add_alignment(src=src, dst=dst, coefficient=coef)
    return registry


__all__ = [
    "COEFFICIENT_MIN", "COEFFICIENT_MAX",
    "AlignmentEdge", "CascadeChange",
    "ReputationCascadeRegistry",
    "seed_default_alignment",
]
