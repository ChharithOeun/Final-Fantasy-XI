"""Friendship system — long-term bonds beyond the friend list.

friend_list (existing module) tracks "is this a friend
yes/no". friendship_system tracks DEPTH — how strong the
bond actually is, computed from shared experience over
time:

    party_time_minutes      time spent in the same party
    gifts_exchanged         delivery_box trades to/from
    tells_exchanged         /tell messages back and forth
    deaths_saved            raised them or they raised you
    quests_completed        finished side quests together
    dungeons_cleared        cleared an instance together

Each event adds a weighted point. The total maps to a
FriendshipTier:
    ACQUAINTANCE   0..50      "you've met"
    COMPANION      51..200    "regulars"
    CONFIDANT      201..500   "trusted close friend"
    BLOOD_BOND     501+       "I'd die for them"

Tiers unlock things — CONFIDANT lets you share a Trust
NPC slot, BLOOD_BOND grants a server-wide effect when
your friend dies (you get an automatic broadcast +
permanent memorial inscription).

Decay: friendships not exercised lose 1 point per game
day. A real friendship is one you keep up. Active play
together easily out-paces decay; if you stop playing
with someone for months, the bond fades.

Symmetric: bond(a, b) == bond(b, a). Events from EITHER
side credit the same bond.

Public surface
--------------
    EventKind enum
    FriendshipTier enum
    BondScore dataclass (frozen)
    FriendshipSystem
        .record_event(player_a, player_b, kind, count=1) -> bool
        .decay(now_day) -> int      # bonds decayed
        .bond(player_a, player_b) -> Optional[BondScore]
        .friends_at_tier(player_id, tier) -> list[str]
        .top_friends(player_id, n=10) -> list[(str, int)]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EventKind(str, enum.Enum):
    PARTY_HOUR = "party_hour"
    GIFT_EXCHANGED = "gift_exchanged"
    TELL_EXCHANGED = "tell_exchanged"
    DEATH_SAVED = "death_saved"
    QUEST_TOGETHER = "quest_together"
    DUNGEON_CLEARED = "dungeon_cleared"


_EVENT_WEIGHTS: dict[EventKind, int] = {
    EventKind.PARTY_HOUR: 2,        # easy to rack up
    EventKind.GIFT_EXCHANGED: 5,
    EventKind.TELL_EXCHANGED: 1,    # cheap signal
    EventKind.DEATH_SAVED: 15,      # rare, meaningful
    EventKind.QUEST_TOGETHER: 8,
    EventKind.DUNGEON_CLEARED: 12,
}


class FriendshipTier(str, enum.Enum):
    ACQUAINTANCE = "acquaintance"
    COMPANION = "companion"
    CONFIDANT = "confidant"
    BLOOD_BOND = "blood_bond"


_TIER_THRESHOLDS = (
    (FriendshipTier.ACQUAINTANCE, 0),
    (FriendshipTier.COMPANION, 51),
    (FriendshipTier.CONFIDANT, 201),
    (FriendshipTier.BLOOD_BOND, 501),
)


@dataclasses.dataclass(frozen=True)
class BondScore:
    player_a: str
    player_b: str
    points: int
    tier: FriendshipTier


def _key(a: str, b: str) -> tuple[str, str]:
    """Symmetric: order alphabetically for stable lookup."""
    return (a, b) if a <= b else (b, a)


def _classify(points: int) -> FriendshipTier:
    tier = FriendshipTier.ACQUAINTANCE
    for t_, threshold in _TIER_THRESHOLDS:
        if points >= threshold:
            tier = t_
    return tier


@dataclasses.dataclass
class FriendshipSystem:
    _bonds: dict[
        tuple[str, str], int,
    ] = dataclasses.field(default_factory=dict)
    _last_decay_day: int = -1

    def record_event(
        self, *, player_a: str, player_b: str,
        kind: EventKind, count: int = 1,
    ) -> bool:
        if not player_a or not player_b:
            return False
        if player_a == player_b:
            return False
        if count <= 0:
            return False
        weight = _EVENT_WEIGHTS[kind]
        key = _key(player_a, player_b)
        self._bonds[key] = (
            self._bonds.get(key, 0) + weight * count
        )
        return True

    def decay(self, *, now_day: int) -> int:
        """1 point per game-day; returns # of bonds touched."""
        if self._last_decay_day < 0:
            self._last_decay_day = now_day
            return 0
        days_elapsed = now_day - self._last_decay_day
        if days_elapsed <= 0:
            return 0
        touched = 0
        for key in list(self._bonds.keys()):
            old = self._bonds[key]
            new = max(0, old - days_elapsed)
            if new != old:
                self._bonds[key] = new
                touched += 1
            if new == 0:
                del self._bonds[key]
        self._last_decay_day = now_day
        return touched

    def bond(
        self, *, player_a: str, player_b: str,
    ) -> t.Optional[BondScore]:
        if player_a == player_b:
            return None
        key = _key(player_a, player_b)
        if key not in self._bonds:
            return None
        pts = self._bonds[key]
        return BondScore(
            player_a=key[0], player_b=key[1],
            points=pts, tier=_classify(pts),
        )

    def friends_at_tier(
        self, *, player_id: str, tier: FriendshipTier,
    ) -> list[str]:
        out = []
        for (a, b), pts in self._bonds.items():
            if _classify(pts) != tier:
                continue
            if a == player_id:
                out.append(b)
            elif b == player_id:
                out.append(a)
        return sorted(out)

    def top_friends(
        self, *, player_id: str, n: int = 10,
    ) -> list[tuple[str, int]]:
        partners = []
        for (a, b), pts in self._bonds.items():
            if a == player_id:
                partners.append((b, pts))
            elif b == player_id:
                partners.append((a, pts))
        partners.sort(key=lambda p: -p[1])
        return partners[:n]


__all__ = [
    "EventKind", "FriendshipTier", "BondScore",
    "FriendshipSystem",
]
