"""Entity hobby buddies — paired NPCs who hobby together.

Some NPCs prefer company at their hobby. Volker fishes alone
some Tuesdays, but more often Naji shows up with a second
rod. The Goblin Smithy and the Mythril Madame Smith both work
metal — sometimes they share a forge. This module declares
buddy pairs and tracks how often they actually appear together
at their hobby. After enough joint sessions a pair is flagged
"best friends," which other systems use for dialog hooks and
quest gating (Volker won't share his secret fishing spot with
just anyone — only Naji).

Public surface
--------------
    BuddyTier enum
    BuddyPair dataclass (frozen)
    EntityHobbyBuddiesSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.entity_hobbies import HobbyKind


_TIER_THRESHOLDS = (
    (0, "acquaintance"),
    (5, "friend"),
    (15, "close_friend"),
    (40, "best_friend"),
)


class BuddyTier(str, enum.Enum):
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    BEST_FRIEND = "best_friend"


@dataclasses.dataclass(frozen=True)
class BuddyPair:
    pair_id: str
    entity_a: str
    entity_b: str
    hobby: HobbyKind
    joint_sessions: int


def _tier_for_count(count: int) -> BuddyTier:
    label = "acquaintance"
    for thresh, name in _TIER_THRESHOLDS:
        if count >= thresh:
            label = name
    return BuddyTier(label)


def _canonical(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


@dataclasses.dataclass
class EntityHobbyBuddiesSystem:
    _pairs: dict[str, BuddyPair] = dataclasses.field(
        default_factory=dict,
    )
    _index: dict[
        tuple[str, str, str], str
    ] = dataclasses.field(default_factory=dict)
    _next: int = 1

    def declare_pair(
        self, *, entity_a: str, entity_b: str,
        hobby: HobbyKind,
    ) -> t.Optional[str]:
        if not entity_a or not entity_b:
            return None
        if entity_a == entity_b:
            return None
        ca, cb = _canonical(entity_a, entity_b)
        key = (ca, cb, hobby.value)
        if key in self._index:
            return None
        pid = f"pair_{self._next}"
        self._next += 1
        self._pairs[pid] = BuddyPair(
            pair_id=pid, entity_a=ca, entity_b=cb,
            hobby=hobby, joint_sessions=0,
        )
        self._index[key] = pid
        return pid

    def record_joint_session(
        self, *, entity_a: str, entity_b: str,
        hobby: HobbyKind,
    ) -> bool:
        if entity_a == entity_b:
            return False
        ca, cb = _canonical(entity_a, entity_b)
        key = (ca, cb, hobby.value)
        if key not in self._index:
            return False
        pid = self._index[key]
        p = self._pairs[pid]
        self._pairs[pid] = dataclasses.replace(
            p, joint_sessions=p.joint_sessions + 1,
        )
        return True

    def tier(
        self, *, entity_a: str, entity_b: str,
        hobby: HobbyKind,
    ) -> t.Optional[BuddyTier]:
        ca, cb = _canonical(entity_a, entity_b)
        key = (ca, cb, hobby.value)
        if key not in self._index:
            return None
        pid = self._index[key]
        return _tier_for_count(
            self._pairs[pid].joint_sessions,
        )

    def is_best_friends(
        self, *, entity_a: str, entity_b: str,
        hobby: HobbyKind,
    ) -> bool:
        t_ = self.tier(
            entity_a=entity_a, entity_b=entity_b,
            hobby=hobby,
        )
        return t_ == BuddyTier.BEST_FRIEND

    def buddies_of(
        self, *, entity_id: str,
    ) -> list[BuddyPair]:
        return [
            p for p in self._pairs.values()
            if entity_id in (p.entity_a, p.entity_b)
        ]

    def pair(
        self, *, pair_id: str,
    ) -> t.Optional[BuddyPair]:
        return self._pairs.get(pair_id)

    def joint_sessions(
        self, *, entity_a: str, entity_b: str,
        hobby: HobbyKind,
    ) -> int:
        ca, cb = _canonical(entity_a, entity_b)
        key = (ca, cb, hobby.value)
        if key not in self._index:
            return 0
        return self._pairs[
            self._index[key]
        ].joint_sessions


__all__ = [
    "BuddyTier", "BuddyPair",
    "EntityHobbyBuddiesSystem",
]
