"""NPC quest anchor — quests follow defected NPCs.

The wiki problem: "Volker's Lost Sword" starts in
Bastok at NPC volker. Then Volker defects to Windurst.
A player who looks up the wiki and walks to Bastok
finds an empty plot square. The quest needs to FOLLOW
the NPC.

This module is the registry that, for each quest,
declares which NPC roles it needs (giver, turn_in,
witness, etc.) and which NPC IDs fill those roles. When
an NPC's faction changes, we re-resolve the LOCATION
of the quest to the NPC's current city/zone.

A QuestAnchor:
    quest_id, role -> npc_id mapping
    fallback_role: which role's NPC location is the
        canonical "where the quest currently happens"
    locked: if True, treat as immovable (story-locked
        quest that can't migrate)

Roles (free-form strings, but conventional ones):
    GIVER, TURN_IN, WITNESS, OBSTACLE, REWARD_GIVER,
    CUTSCENE_NPC

Public surface
--------------
    QuestAnchor dataclass (frozen)
    AnchorBinding dataclass (frozen)
    NPCQuestAnchorSystem
        .register_quest(quest_id, fallback_role,
                        locked) -> bool
        .bind_role(quest_id, role, npc_id) -> bool
        .unbind_role(quest_id, role) -> bool
        .resolve_quest_location(quest_id,
                                npc_locations) ->
                                Optional[str]
        .quests_for_npc(npc_id) -> list[str]
        .anchor(quest_id) -> Optional[QuestAnchor]
        .all_quests() -> list[QuestAnchor]
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class AnchorBinding:
    quest_id: str
    role: str
    npc_id: str


@dataclasses.dataclass(frozen=True)
class QuestAnchor:
    quest_id: str
    fallback_role: str
    locked: bool
    bindings: tuple[AnchorBinding, ...]


@dataclasses.dataclass
class NPCQuestAnchorSystem:
    _anchors: dict[str, QuestAnchor] = (
        dataclasses.field(default_factory=dict)
    )

    def register_quest(
        self, *, quest_id: str,
        fallback_role: str, locked: bool = False,
    ) -> bool:
        if not quest_id or not fallback_role:
            return False
        if quest_id in self._anchors:
            return False
        self._anchors[quest_id] = QuestAnchor(
            quest_id=quest_id,
            fallback_role=fallback_role,
            locked=locked, bindings=(),
        )
        return True

    def bind_role(
        self, *, quest_id: str, role: str,
        npc_id: str,
    ) -> bool:
        if quest_id not in self._anchors:
            return False
        if not role or not npc_id:
            return False
        anc = self._anchors[quest_id]
        # Replace existing binding for the same role
        new_bindings = tuple(
            b for b in anc.bindings
            if b.role != role
        ) + (AnchorBinding(
            quest_id=quest_id, role=role,
            npc_id=npc_id,
        ),)
        self._anchors[quest_id] = (
            dataclasses.replace(
                anc, bindings=new_bindings,
            )
        )
        return True

    def unbind_role(
        self, *, quest_id: str, role: str,
    ) -> bool:
        if quest_id not in self._anchors:
            return False
        anc = self._anchors[quest_id]
        if not any(
            b.role == role for b in anc.bindings
        ):
            return False
        new_bindings = tuple(
            b for b in anc.bindings
            if b.role != role
        )
        self._anchors[quest_id] = (
            dataclasses.replace(
                anc, bindings=new_bindings,
            )
        )
        return True

    def resolve_quest_location(
        self, *, quest_id: str,
        npc_locations: t.Mapping[str, str],
    ) -> t.Optional[str]:
        """Return the current zone of the
        fallback_role NPC. If quest is locked, the
        caller must handle relocation refusal — we
        still return the location for display
        purposes.
        """
        if quest_id not in self._anchors:
            return None
        anc = self._anchors[quest_id]
        for b in anc.bindings:
            if b.role == anc.fallback_role:
                return npc_locations.get(b.npc_id)
        return None

    def quests_for_npc(
        self, *, npc_id: str,
    ) -> list[str]:
        out: list[str] = []
        for anc in self._anchors.values():
            if any(
                b.npc_id == npc_id
                for b in anc.bindings
            ):
                out.append(anc.quest_id)
        return out

    def role_npc(
        self, *, quest_id: str, role: str,
    ) -> t.Optional[str]:
        if quest_id not in self._anchors:
            return None
        for b in self._anchors[quest_id].bindings:
            if b.role == role:
                return b.npc_id
        return None

    def anchor(
        self, *, quest_id: str,
    ) -> t.Optional[QuestAnchor]:
        return self._anchors.get(quest_id)

    def all_quests(self) -> list[QuestAnchor]:
        return list(self._anchors.values())

    def is_locked(self, *, quest_id: str) -> bool:
        if quest_id not in self._anchors:
            return False
        return self._anchors[quest_id].locked


__all__ = [
    "AnchorBinding", "QuestAnchor",
    "NPCQuestAnchorSystem",
]
