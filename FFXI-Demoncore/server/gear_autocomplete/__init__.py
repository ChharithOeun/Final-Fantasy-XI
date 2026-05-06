"""Gear autocomplete — typeahead dropdown for builder UI.

Tart's insight: 90% of GearSwap errors are misspelled
item names. The fix: when the player types into a slot
field, the dropdown shows matching items filtered by
that slot. They pick from the list — no typing the full
name, no spelling errors, ever.

Three matching modes:
    PREFIX     "Mur" → starts-with match (Murgleis,
               Murasame, etc.)
    CONTAINS   "ring" → substring match (Stikini Ring +1,
               Eshmun's Ring, etc.)
    FUZZY      "demos" → typo tolerance for "Demers." etc.

Each match returns a (item_id, display_name, score)
tuple ranked by relevance. The UI shows the top N and
the player clicks to select. The selected item_id flows
into the IntentSpec's gear set assignment.

Built on top of gear_slot_filter — the candidate pool
is ALWAYS slot-restricted before matching, so the player
can't accidentally drop a Body item into a Head slot.

Public surface
--------------
    MatchMode enum (PREFIX/CONTAINS/FUZZY)
    Suggestion dataclass (frozen)
    GearAutocomplete
        .suggest(slot, query, mode, limit, owned_only,
                  owner_id) -> list[Suggestion]
        .recent_for_slot(player_id, slot) -> list[str]
        .record_pick(player_id, slot, item_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.gear_slot_filter import (
    GearItem, GearSlotFilter, Slot,
)


class MatchMode(str, enum.Enum):
    PREFIX = "prefix"
    CONTAINS = "contains"
    FUZZY = "fuzzy"


@dataclasses.dataclass(frozen=True)
class Suggestion:
    item_id: str
    display_name: str
    score: int       # higher = better match


def _fuzzy_score(query: str, name: str) -> int:
    """Coarse fuzzy score — character co-occurrence."""
    if not query:
        return 0
    q = query.lower()
    n = name.lower()
    if q in n:
        return 100 - n.index(q)   # earlier match scores higher
    # All query chars present in order anywhere?
    j = 0
    for ch in n:
        if j < len(q) and ch == q[j]:
            j += 1
    if j == len(q):
        return 50
    # Some chars present?
    overlap = sum(1 for ch in q if ch in n)
    return overlap * 5


@dataclasses.dataclass
class GearAutocomplete:
    _filter: GearSlotFilter
    # player_id → slot → ordered list of recently-picked item_ids
    _recent: dict[
        str, dict[Slot, list[str]],
    ] = dataclasses.field(default_factory=dict)

    _RECENT_MAX_PER_SLOT: t.ClassVar[int] = 5

    def suggest(
        self, *, slot: Slot, query: str,
        mode: MatchMode = MatchMode.PREFIX,
        limit: int = 10,
        owned_only: bool = False,
        owner_id: str = "",
    ) -> list[Suggestion]:
        if limit <= 0:
            return []
        # Empty query: surface recently-picked first, then
        # the alphabetic head of the slot pool.
        candidates = self._filter.candidates_for_slot(
            slot=slot, owned_only=owned_only,
            owner_id=owner_id,
        )
        if not query:
            recents = self._recent.get(owner_id, {}).get(slot, [])
            recent_ids = set(recents)
            ordered: list[GearItem] = []
            for rid in recents:
                item = self._filter.item_lookup(item_id=rid)
                if item is not None:
                    ordered.append(item)
            for item in candidates:
                if item.item_id not in recent_ids:
                    ordered.append(item)
            return [
                Suggestion(
                    item_id=i.item_id,
                    display_name=i.display_name,
                    score=0,
                ) for i in ordered[:limit]
            ]
        # With a query — filter and score.
        q = query.lower()
        scored: list[Suggestion] = []
        for item in candidates:
            n = item.display_name.lower()
            if mode == MatchMode.PREFIX:
                if n.startswith(q):
                    # earlier prefix = higher score
                    scored.append(Suggestion(
                        item_id=item.item_id,
                        display_name=item.display_name,
                        score=100,
                    ))
            elif mode == MatchMode.CONTAINS:
                if q in n:
                    # earlier match = higher score
                    scored.append(Suggestion(
                        item_id=item.item_id,
                        display_name=item.display_name,
                        score=100 - n.index(q),
                    ))
            else:  # FUZZY
                s = _fuzzy_score(q, item.display_name)
                if s > 0:
                    scored.append(Suggestion(
                        item_id=item.item_id,
                        display_name=item.display_name,
                        score=s,
                    ))
        scored.sort(
            key=lambda s: (-s.score, s.display_name),
        )
        return scored[:limit]

    def record_pick(
        self, *, player_id: str, slot: Slot,
        item_id: str,
    ) -> bool:
        if not player_id or not item_id:
            return False
        if not self._filter.can_equip(
            item_id=item_id, slot=slot,
        ):
            return False
        per_slot = self._recent.setdefault(player_id, {})
        recent = per_slot.setdefault(slot, [])
        # Move to front; cap length.
        if item_id in recent:
            recent.remove(item_id)
        recent.insert(0, item_id)
        if len(recent) > self._RECENT_MAX_PER_SLOT:
            del recent[self._RECENT_MAX_PER_SLOT:]
        return True

    def recent_for_slot(
        self, *, player_id: str, slot: Slot,
    ) -> list[str]:
        return list(
            self._recent.get(player_id, {}).get(slot, []),
        )

    def clear_recent(
        self, *, player_id: str, slot: t.Optional[Slot] = None,
    ) -> int:
        per_slot = self._recent.get(player_id)
        if per_slot is None:
            return 0
        if slot is None:
            count = sum(len(v) for v in per_slot.values())
            self._recent[player_id] = {}
            return count
        recent = per_slot.get(slot, [])
        count = len(recent)
        per_slot[slot] = []
        return count


__all__ = [
    "MatchMode", "Suggestion", "GearAutocomplete",
]
