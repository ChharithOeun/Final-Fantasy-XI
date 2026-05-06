"""Menu tree — the canonical command hierarchy.

Magic > Black Magic > Elemental > Fire III. The menu
tree is the canonical breadcrumb path that the in-game
menu walks. Each node has a label, an optional command_id
(leaves are commands; internal nodes are categories),
and an ordered list of children.

The tree is per-job. White Mage's Magic submenu has
Curing/Enhancing/Enfeebling; Black Mage's has Elemental/
Dark/Enfeebling. Building the tree is the caller's job —
this module just structures the data and supports the
"open a node, list children, descend into one" loop.

Node addressing: by path tuple ("root", "magic", "black_magic",
"elemental", "fire_iii"). The empty tuple is the root.

Public surface
--------------
    MenuNode dataclass (mutable)
    MenuTree
        .define_root(job) -> bool
        .add_node(job, parent_path, node_id, label,
                  command_id) -> bool
        .children(job, path) -> list[MenuNode]
        .resolve(job, path) -> Optional[MenuNode]
        .breadcrumb(job, path) -> list[str]
            (labels from root to leaf)
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass
class MenuNode:
    node_id: str
    label: str
    command_id: str           # "" for category nodes
    children_ids: list[str]


# Internal storage: per (job, full_path_tuple) → MenuNode.
# Keeping a flat dict keyed by tuples is simpler than
# linked nodes and easier to test.


@dataclasses.dataclass
class MenuTree:
    _nodes: dict[tuple[str, tuple[str, ...]], MenuNode] = \
        dataclasses.field(default_factory=dict)

    def define_root(self, *, job: str) -> bool:
        if not job:
            return False
        key = (job, ())
        if key in self._nodes:
            return False
        self._nodes[key] = MenuNode(
            node_id="root", label="root",
            command_id="", children_ids=[],
        )
        return True

    def add_node(
        self, *, job: str, parent_path: tuple[str, ...],
        node_id: str, label: str,
        command_id: str = "",
    ) -> bool:
        if not job or not node_id or not label:
            return False
        parent_key = (job, parent_path)
        parent = self._nodes.get(parent_key)
        if parent is None:
            return False
        if node_id in parent.children_ids:
            return False
        full_path = parent_path + (node_id,)
        child_key = (job, full_path)
        if child_key in self._nodes:
            return False
        self._nodes[child_key] = MenuNode(
            node_id=node_id, label=label,
            command_id=command_id, children_ids=[],
        )
        parent.children_ids.append(node_id)
        return True

    def children(
        self, *, job: str, path: tuple[str, ...],
    ) -> list[MenuNode]:
        node = self._nodes.get((job, path))
        if node is None:
            return []
        out: list[MenuNode] = []
        for cid in node.children_ids:
            child = self._nodes.get((job, path + (cid,)))
            if child is not None:
                out.append(child)
        return out

    def resolve(
        self, *, job: str, path: tuple[str, ...],
    ) -> t.Optional[MenuNode]:
        return self._nodes.get((job, path))

    def breadcrumb(
        self, *, job: str, path: tuple[str, ...],
    ) -> list[str]:
        # walk down from root, collecting labels
        out: list[str] = []
        cumulative: tuple[str, ...] = ()
        # include root's label
        root = self._nodes.get((job, cumulative))
        if root is None:
            return []
        out.append(root.label)
        for piece in path:
            cumulative = cumulative + (piece,)
            node = self._nodes.get((job, cumulative))
            if node is None:
                return []
            out.append(node.label)
        return out

    def total_nodes(self, *, job: str) -> int:
        return sum(1 for k in self._nodes if k[0] == job)


__all__ = [
    "MenuNode", "MenuTree",
]
