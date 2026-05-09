"""NPC dialogue routing — allegiance-aware dialogue.

When an NPC's faction changes, their dialogue trees
need to update so they don't keep saying "Welcome to
Bastok!" while standing in Windurst's Heaven's Tower.

This module manages PER-NPC DIALOGUE VARIANTS keyed by
the NPC's CURRENT faction. The caller registers a
variant for each (npc_id, faction) pair; on a defection,
the system swaps which variant is "active" by reading
the new faction. The result is allegiance-aware
dialogue without rebuilding the conversation tree.

A variant carries:
    npc_id, faction_key, greeting, dialogue_tree_id,
    voice_profile_id (so even the TTS preset shifts)

Public surface
--------------
    DialogueVariant dataclass (frozen)
    NPCDialogueRoutingSystem
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class DialogueVariant:
    npc_id: str
    faction_key: str
    greeting: str
    dialogue_tree_id: str
    voice_profile_id: str


@dataclasses.dataclass
class NPCDialogueRoutingSystem:
    _variants: dict[
        tuple[str, str], DialogueVariant
    ] = dataclasses.field(default_factory=dict)
    _current_faction: dict[str, str] = (
        dataclasses.field(default_factory=dict)
    )
    _default_variant: dict[str, str] = (
        dataclasses.field(default_factory=dict)
    )

    def register_variant(
        self, *, npc_id: str, faction_key: str,
        greeting: str, dialogue_tree_id: str,
        voice_profile_id: str,
        is_default: bool = False,
    ) -> bool:
        if not npc_id or not faction_key:
            return False
        if not greeting or not dialogue_tree_id:
            return False
        if not voice_profile_id:
            return False
        self._variants[(npc_id, faction_key)] = (
            DialogueVariant(
                npc_id=npc_id,
                faction_key=faction_key,
                greeting=greeting,
                dialogue_tree_id=dialogue_tree_id,
                voice_profile_id=voice_profile_id,
            )
        )
        if is_default:
            self._default_variant[npc_id] = (
                faction_key
            )
            self._current_faction.setdefault(
                npc_id, faction_key,
            )
        return True

    def update_npc_faction(
        self, *, npc_id: str, faction_key: str,
    ) -> bool:
        if not npc_id or not faction_key:
            return False
        # Allow setting to a faction even without
        # variant — caller may add it later.
        self._current_faction[npc_id] = faction_key
        return True

    def active_variant(
        self, *, npc_id: str,
    ) -> t.Optional[DialogueVariant]:
        if npc_id not in self._current_faction:
            # Fall back to default if available
            default = self._default_variant.get(npc_id)
            if default is not None:
                return self._variants.get(
                    (npc_id, default),
                )
            return None
        cur = self._current_faction[npc_id]
        v = self._variants.get((npc_id, cur))
        if v is not None:
            return v
        # Variant for current faction missing — fall
        # back to default
        default = self._default_variant.get(npc_id)
        if default is not None:
            return self._variants.get(
                (npc_id, default),
            )
        return None

    def has_variant(
        self, *, npc_id: str, faction_key: str,
    ) -> bool:
        return (
            (npc_id, faction_key) in self._variants
        )

    def variants_for(
        self, *, npc_id: str,
    ) -> list[DialogueVariant]:
        return [
            v for (nid, _), v in self._variants.items()
            if nid == npc_id
        ]

    def remove_variant(
        self, *, npc_id: str, faction_key: str,
    ) -> bool:
        key = (npc_id, faction_key)
        if key not in self._variants:
            return False
        del self._variants[key]
        # If we removed the default, clear default
        if (self._default_variant.get(npc_id)
                == faction_key):
            del self._default_variant[npc_id]
        return True

    def current_faction(
        self, *, npc_id: str,
    ) -> t.Optional[str]:
        return self._current_faction.get(npc_id)


__all__ = [
    "DialogueVariant", "NPCDialogueRoutingSystem",
]
