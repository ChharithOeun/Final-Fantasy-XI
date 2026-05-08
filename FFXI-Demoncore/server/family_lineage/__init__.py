"""Family lineage — descendant trees across permadeath.

When a permadeath player has named an heir (player_legacy
already does this), their descendant takes over. But
across multiple deaths and multiple generations, you
build a TREE — grandparent → parent → you → child →
grandchild. family_lineage tracks that tree and grants
LINEAGE BONUSES for inheriting from a deep line:

    GENERATION 1 (founder) — base stats
    GENERATION 2 (child)   — +1 to all base stats
    GENERATION 3 (gchild)  — +2
    GENERATION 4 (ggchild) — +3 (cap)

Plus a HEIRLOOM_SLOT — one piece of equipment from the
ancestor passes to the heir intact (any item in their
inventory marked heirloom_eligible). The heir starts
with that item in their inventory.

Family ties in the world: NPCs in the founder's home
city remember the family name and react slightly more
positively (small fame bonus) — the npc_dialogue_system
reads the lineage_known() flag.

You can disinherit a designated heir before you die.
After your death the heir is locked in.

Public surface
--------------
    LineageNode dataclass (frozen)
    Heirloom dataclass (frozen)
    FamilyLineage
        .register_founder(player_id, family_name) -> bool
        .designate_heir(parent, heir_candidate) -> bool
        .disinherit(parent) -> bool
        .record_death(parent, item_id_heirloom=None)
            -> Optional[Heirloom]
        .generation(player_id) -> int
        .ancestors(player_id) -> list[str]
        .lineage_known(player_id, city_id) -> bool
        .family_name(player_id) -> Optional[str]
"""
from __future__ import annotations

import dataclasses
import typing as t


_MAX_GENERATION_BONUS = 3


@dataclasses.dataclass(frozen=True)
class LineageNode:
    player_id: str
    family_name: str
    parent_id: t.Optional[str]
    generation: int
    is_alive: bool


@dataclasses.dataclass(frozen=True)
class Heirloom:
    from_ancestor: str
    to_heir: str
    item_id: str


@dataclasses.dataclass
class _Player:
    family_name: str
    parent_id: t.Optional[str]
    generation: int
    is_alive: bool = True
    designated_heir: t.Optional[str] = None
    home_city: t.Optional[str] = None


@dataclasses.dataclass
class FamilyLineage:
    _players: dict[str, _Player] = dataclasses.field(
        default_factory=dict,
    )

    def register_founder(
        self, *, player_id: str, family_name: str,
        home_city: t.Optional[str] = None,
    ) -> bool:
        if not player_id or not family_name:
            return False
        if player_id in self._players:
            return False
        self._players[player_id] = _Player(
            family_name=family_name,
            parent_id=None,
            generation=1,
            home_city=home_city,
        )
        return True

    def designate_heir(
        self, *, parent: str, heir_candidate: str,
    ) -> bool:
        if not heir_candidate:
            return False
        if parent == heir_candidate:
            return False
        if parent not in self._players:
            return False
        p = self._players[parent]
        if not p.is_alive:
            return False
        # The heir candidate must NOT already be in
        # someone else's lineage tree (no double parents)
        if heir_candidate in self._players:
            return False
        p.designated_heir = heir_candidate
        return True

    def disinherit(self, *, parent: str) -> bool:
        if parent not in self._players:
            return False
        p = self._players[parent]
        if not p.is_alive:
            return False
        if p.designated_heir is None:
            return False
        p.designated_heir = None
        return True

    def record_death(
        self, *, parent: str,
        heirloom_item_id: t.Optional[str] = None,
    ) -> t.Optional[Heirloom]:
        if parent not in self._players:
            return None
        p = self._players[parent]
        if not p.is_alive:
            return None
        if p.designated_heir is None:
            # Death with no heir — line ends but still
            # mark the parent dead.
            p.is_alive = False
            return None
        heir_id = p.designated_heir
        new_gen = min(
            p.generation + 1,
            p.generation + _MAX_GENERATION_BONUS + 1,
        )
        # Don't cap generation — we cap the BONUS, not
        # the depth.
        new_gen = p.generation + 1
        self._players[heir_id] = _Player(
            family_name=p.family_name,
            parent_id=parent,
            generation=new_gen,
            is_alive=True,
            home_city=p.home_city,
        )
        p.is_alive = False
        if heirloom_item_id:
            return Heirloom(
                from_ancestor=parent, to_heir=heir_id,
                item_id=heirloom_item_id,
            )
        return None

    def generation(self, *, player_id: str) -> int:
        if player_id not in self._players:
            return 0
        return self._players[player_id].generation

    def lineage_bonus(self, *, player_id: str) -> int:
        gen = self.generation(player_id=player_id)
        if gen <= 0:
            return 0
        return min(gen - 1, _MAX_GENERATION_BONUS)

    def ancestors(self, *, player_id: str) -> list[str]:
        out: list[str] = []
        cur = player_id
        while cur in self._players:
            parent = self._players[cur].parent_id
            if parent is None:
                break
            out.append(parent)
            cur = parent
        return out

    def lineage_known(
        self, *, player_id: str, city_id: str,
    ) -> bool:
        if player_id not in self._players:
            return False
        p = self._players[player_id]
        return p.home_city == city_id and p.generation > 1

    def family_name(
        self, *, player_id: str,
    ) -> t.Optional[str]:
        if player_id not in self._players:
            return None
        return self._players[player_id].family_name

    def node(
        self, *, player_id: str,
    ) -> t.Optional[LineageNode]:
        if player_id not in self._players:
            return None
        p = self._players[player_id]
        return LineageNode(
            player_id=player_id,
            family_name=p.family_name,
            parent_id=p.parent_id,
            generation=p.generation,
            is_alive=p.is_alive,
        )


__all__ = [
    "LineageNode", "Heirloom", "FamilyLineage",
]
