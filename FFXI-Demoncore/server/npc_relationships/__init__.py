"""NPC relationships — the social graph between NPCs.

Two NPCs in the same town don't exist in isolation. The
shopkeeper's wife is the seamstress next door. The captain of
the guard had a falling out with the priest three years ago and
they avoid each other's neighborhoods. The barmaid is secretly
in love with the wandering bard.

This module models the directed relational graph between NPCs.
Each edge has a tag (FRIEND/RIVAL/MENTOR/LOVER/FAMILY/...) and
an intensity [0..100]. The orchestrator's prompt assembly pulls
relevant relationships when an NPC interacts with someone — if
the player asks the priest about the captain of the guard, the
priest's response is colored by their unresolved feud.

Beyond flavor, the graph drives:
* Side-quest hook generation (one NPC's mood event propagates
  through their relationships, surfacing new needs in others)
* Faction-internal politics (rivalries between guildmasters
  bias their faction-level decisions)
* Player-witnessed effects (helping one NPC raises rep with
  their FRIENDS and lowers rep with their RIVALS)

Public surface
--------------
    RelationshipKind enum
    Relationship dataclass
    RelationshipDelta enum (STRENGTHEN / WEAKEN / SEVER)
    NPCRelationshipGraph
        .add(npc_a, npc_b, kind, intensity)
        .relationships_of(npc_id)
        .relationships_between(npc_a, npc_b)
        .friends_of(npc_id) / .rivals_of(npc_id)
        .strengthen / .weaken / .sever
        .propagate_event(npc_id, event_kind) -> tuple[NPCEffect, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


INTENSITY_MIN = 0
INTENSITY_MAX = 100


class RelationshipKind(str, enum.Enum):
    """Directed edge label. A -> kind -> B."""
    FRIEND = "friend"
    BEST_FRIEND = "best_friend"
    RIVAL = "rival"
    NEMESIS = "nemesis"
    MENTOR = "mentor"          # A mentors B
    APPRENTICE = "apprentice"  # A is apprentice TO B
    LOVER = "lover"
    SPOUSE = "spouse"
    FAMILY = "family"          # parent/sibling/cousin
    SUSPICIOUS_OF = "suspicious_of"
    INDEBTED_TO = "indebted_to"     # A owes B
    EMPLOYER = "employer"      # A employs B
    EMPLOYEE = "employee"


# Pro/con flavor classification — used for event propagation.
_PRO_KINDS: frozenset[RelationshipKind] = frozenset({
    RelationshipKind.FRIEND, RelationshipKind.BEST_FRIEND,
    RelationshipKind.MENTOR, RelationshipKind.APPRENTICE,
    RelationshipKind.LOVER, RelationshipKind.SPOUSE,
    RelationshipKind.FAMILY, RelationshipKind.INDEBTED_TO,
    RelationshipKind.EMPLOYEE,
})

# SUSPICIOUS_OF and EMPLOYER are intentionally *informational* —
# they describe the relationship without coloring how an event to
# one NPC propagates emotional shifts to the other.
_CON_KINDS: frozenset[RelationshipKind] = frozenset({
    RelationshipKind.RIVAL, RelationshipKind.NEMESIS,
})


def is_pro(kind: RelationshipKind) -> bool:
    return kind in _PRO_KINDS


def is_con(kind: RelationshipKind) -> bool:
    return kind in _CON_KINDS


@dataclasses.dataclass
class Relationship:
    """Directed edge from src -> dst."""
    src_npc_id: str
    dst_npc_id: str
    kind: RelationshipKind
    intensity: int = 50
    notes: str = ""

    def __post_init__(self) -> None:
        if not (
            INTENSITY_MIN <= self.intensity <= INTENSITY_MAX
        ):
            raise ValueError(
                f"intensity {self.intensity} out of "
                f"{INTENSITY_MIN}..{INTENSITY_MAX}"
            )


# Event propagation — when something happens to one NPC, this
# describes how it spreads through their relationships.
class EventKind(str, enum.Enum):
    HELPED_BY_PLAYER = "helped_by_player"
    HARMED_BY_PLAYER = "harmed_by_player"
    RECEIVED_GIFT = "received_gift"
    DIED = "died"
    BECAME_OUTLAW = "became_outlaw"
    PROMOTED = "promoted"
    DISGRACED = "disgraced"


@dataclasses.dataclass(frozen=True)
class NPCEffect:
    """Result of propagating an event from npc_a to a related NPC."""
    affected_npc_id: str
    via_relationship: RelationshipKind
    via_intensity: int
    sentiment_shift: int   # +/- delta to apply to their player rep


# Sentiment shift table — how each event flavors the relationship.
# +N for PRO, -N for CON, scaled by relationship intensity.
_BASE_SENTIMENT_SHIFT: dict[EventKind, int] = {
    EventKind.HELPED_BY_PLAYER: 30,
    EventKind.HARMED_BY_PLAYER: -50,
    EventKind.RECEIVED_GIFT: 10,
    EventKind.DIED: -80,
    EventKind.BECAME_OUTLAW: -20,
    EventKind.PROMOTED: 15,
    EventKind.DISGRACED: -15,
}


@dataclasses.dataclass
class NPCRelationshipGraph:
    _edges: list[Relationship] = dataclasses.field(
        default_factory=list,
    )
    _by_src: dict[str, list[Relationship]] = dataclasses.field(
        default_factory=dict,
    )

    def add(
        self, *, src_npc_id: str, dst_npc_id: str,
        kind: RelationshipKind, intensity: int = 50,
        notes: str = "",
        bidirectional: bool = False,
        reciprocal_kind: t.Optional[RelationshipKind] = None,
    ) -> Relationship:
        rel = Relationship(
            src_npc_id=src_npc_id, dst_npc_id=dst_npc_id,
            kind=kind, intensity=intensity, notes=notes,
        )
        self._edges.append(rel)
        self._by_src.setdefault(src_npc_id, []).append(rel)
        if bidirectional:
            inverse_kind = reciprocal_kind or kind
            inverse = Relationship(
                src_npc_id=dst_npc_id, dst_npc_id=src_npc_id,
                kind=inverse_kind, intensity=intensity,
                notes=notes,
            )
            self._edges.append(inverse)
            self._by_src.setdefault(
                dst_npc_id, [],
            ).append(inverse)
        return rel

    def relationships_of(
        self, npc_id: str,
    ) -> tuple[Relationship, ...]:
        return tuple(self._by_src.get(npc_id, ()))

    def relationships_between(
        self, npc_a: str, npc_b: str,
    ) -> tuple[Relationship, ...]:
        return tuple(
            r for r in self._by_src.get(npc_a, [])
            if r.dst_npc_id == npc_b
        )

    def friends_of(self, npc_id: str) -> tuple[str, ...]:
        return tuple(
            r.dst_npc_id for r in self._by_src.get(npc_id, [])
            if is_pro(r.kind)
        )

    def rivals_of(self, npc_id: str) -> tuple[str, ...]:
        return tuple(
            r.dst_npc_id for r in self._by_src.get(npc_id, [])
            if is_con(r.kind)
        )

    def strengthen(
        self, *, src: str, dst: str, delta: int = 10,
    ) -> bool:
        for r in self._by_src.get(src, []):
            if r.dst_npc_id == dst:
                r.intensity = min(
                    INTENSITY_MAX, r.intensity + delta,
                )
                return True
        return False

    def weaken(
        self, *, src: str, dst: str, delta: int = 10,
    ) -> bool:
        for r in self._by_src.get(src, []):
            if r.dst_npc_id == dst:
                r.intensity = max(
                    INTENSITY_MIN, r.intensity - delta,
                )
                return True
        return False

    def sever(self, *, src: str, dst: str) -> int:
        before = len(self._edges)
        self._edges = [
            r for r in self._edges
            if not (r.src_npc_id == src and r.dst_npc_id == dst)
        ]
        if src in self._by_src:
            self._by_src[src] = [
                r for r in self._by_src[src]
                if r.dst_npc_id != dst
            ]
        return before - len(self._edges)

    def propagate_event(
        self, *, npc_id: str, event: EventKind,
    ) -> tuple[NPCEffect, ...]:
        """Spread an event affecting npc_id through their
        relationships. Returns effects to apply to related NPCs'
        opinion of the player.

        Friends amplify the player's standing on a HELPED event;
        rivals invert it (their friend's helper is, by some
        cracked logic, their enemy's friend's enemy)."""
        base = _BASE_SENTIMENT_SHIFT.get(event, 0)
        if base == 0:
            return ()
        out: list[NPCEffect] = []
        for r in self._by_src.get(npc_id, []):
            scale = r.intensity / 100.0
            if is_pro(r.kind):
                shift = int(round(base * scale))
            elif is_con(r.kind):
                shift = -int(round(base * scale))
            else:
                # Neutral / informational kinds (EMPLOYEE,
                # SUSPICIOUS_OF) — no propagation
                continue
            if shift == 0:
                continue
            out.append(NPCEffect(
                affected_npc_id=r.dst_npc_id,
                via_relationship=r.kind,
                via_intensity=r.intensity,
                sentiment_shift=shift,
            ))
        return tuple(out)

    def total_edges(self) -> int:
        return len(self._edges)


__all__ = [
    "INTENSITY_MIN", "INTENSITY_MAX",
    "RelationshipKind", "is_pro", "is_con",
    "Relationship", "EventKind", "NPCEffect",
    "NPCRelationshipGraph",
]
