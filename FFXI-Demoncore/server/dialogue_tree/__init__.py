"""Dialogue tree — branching NPC conversation engine.

A tree of nodes; each node has lines of NPC text and a list of
player choices. Choices may be gated by conditions (mission rank,
item held, friend rep) and lead to other nodes by id. The session
walker tracks where the player is in the tree.

Public surface
--------------
    Choice / DialogueNode
    DialogueTree (catalog of nodes by id)
    PlayerContext   - what the engine knows about the player
    DialogueSession - traversal state
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class PlayerContext:
    """Snapshot of the player state used to gate choices."""
    player_id: str = ""
    nation_rank: dict[str, int] = dataclasses.field(default_factory=dict)
    completed_quests: tuple[str, ...] = ()
    inventory_items: tuple[str, ...] = ()
    job: str = ""
    level: int = 1


# A predicate that returns True if the choice should be visible.
ChoicePredicate = t.Callable[[PlayerContext], bool]


@dataclasses.dataclass(frozen=True)
class Choice:
    label: str
    next_node_id: t.Optional[str]   # None -> end conversation
    predicate: t.Optional[ChoicePredicate] = None
    side_effect_event: t.Optional[str] = None   # event id to emit


@dataclasses.dataclass(frozen=True)
class DialogueNode:
    node_id: str
    npc_lines: tuple[str, ...]
    choices: tuple[Choice, ...] = ()
    auto_next_id: t.Optional[str] = None        # for monologue chains


@dataclasses.dataclass
class DialogueTree:
    tree_id: str
    nodes: dict[str, DialogueNode] = dataclasses.field(
        default_factory=dict,
    )

    def add(self, node: DialogueNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"node {node.node_id} already exists")
        self.nodes[node.node_id] = node

    def get(self, node_id: str) -> DialogueNode:
        return self.nodes[node_id]


@dataclasses.dataclass
class DialogueSession:
    tree: DialogueTree
    context: PlayerContext
    current_node_id: str
    finished: bool = False
    events_emitted: list[str] = dataclasses.field(default_factory=list)

    def current_node(self) -> DialogueNode:
        return self.tree.get(self.current_node_id)

    def visible_choices(self) -> tuple[Choice, ...]:
        node = self.current_node()
        out = []
        for c in node.choices:
            if c.predicate is None or c.predicate(self.context):
                out.append(c)
        return tuple(out)

    def choose(self, *, choice_index: int) -> bool:
        """Pick a choice by index in visible_choices(). Advances
        the session. Returns True if the conversation continues."""
        if self.finished:
            return False
        choices = self.visible_choices()
        if not 0 <= choice_index < len(choices):
            return False
        choice = choices[choice_index]
        if choice.side_effect_event is not None:
            self.events_emitted.append(choice.side_effect_event)
        if choice.next_node_id is None:
            self.finished = True
            return False
        self.current_node_id = choice.next_node_id
        return True

    def auto_advance(self) -> bool:
        """Walk through any auto_next_id chain. Returns True if
        we moved at least one step."""
        if self.finished:
            return False
        node = self.current_node()
        if node.auto_next_id is None:
            return False
        self.current_node_id = node.auto_next_id
        return True


__all__ = [
    "PlayerContext", "Choice", "DialogueNode",
    "DialogueTree", "DialogueSession",
]
