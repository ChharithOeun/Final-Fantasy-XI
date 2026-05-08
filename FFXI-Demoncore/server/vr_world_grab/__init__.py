"""VR world grab — physically pick up things in the world.

In flat-screen FFXI you press a button to "open chest"
or "loot mob". In VR you reach out, close your fist on
the chest lid, and lift it. This module is the server
side of that physicality.

Three Grabbable kinds we recognize:
    LOOT_CHEST      treasure chests, dropped loot
    LEVER           gates, dungeon switches
    SMALL_ITEM      gear stones, harvested mats, scrolls
                    that you can hold and inspect

Per-grabbable state:
    OPEN            visible, can be grabbed
    GRABBED         held by a specific player's hand
    CONSUMED        loot taken / lever pulled / item put
                    in inventory; removed from world

Grab interaction model:
    - Player calls request_grab(player, hand, grabbable)
      with a current hand position. Server checks the
      hand is within _GRAB_REACH_M (0.6m) of the
      grabbable's position.
    - If success: state -> GRABBED, owner = (player, hand).
      No other player can grab while it's held.
    - release(player, hand) un-grabs without consuming.
    - consume(player, hand) is the final action — opens
      chest / pulls lever / picks up item.

Two-hand interactions:
    Some grabbables (ALL except SMALL_ITEM by default)
    require TWO HANDS to consume. A chest is too heavy
    for one hand; a lever is meant to be cranked. The
    requires_two_hands flag forces same-player both-hands
    grab before consume() succeeds.

Public surface
--------------
    GrabbableKind enum
    Hand enum
    GrabState enum
    Grabbable dataclass (frozen)
    VrWorldGrab
        .register(grabbable) -> bool
        .request_grab(player_id, hand, grabbable_id, hand_x,
                      hand_y, hand_z) -> bool
        .release(player_id, hand, grabbable_id) -> bool
        .consume(player_id, grabbable_id) -> bool
        .state(grabbable_id) -> Optional[GrabState]
        .holder(grabbable_id) -> Optional[(player_id, Hand)]
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


_GRAB_REACH_M = 0.6


class GrabbableKind(str, enum.Enum):
    LOOT_CHEST = "loot_chest"
    LEVER = "lever"
    SMALL_ITEM = "small_item"


class Hand(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"


class GrabState(str, enum.Enum):
    OPEN = "open"
    GRABBED = "grabbed"
    CONSUMED = "consumed"


@dataclasses.dataclass(frozen=True)
class Grabbable:
    grabbable_id: str
    kind: GrabbableKind
    x: float
    y: float
    z: float
    requires_two_hands: bool = False


@dataclasses.dataclass
class _GrabInternal:
    grabbable: Grabbable
    state: GrabState = GrabState.OPEN
    # set of (player_id, Hand) currently holding it
    holders: set = dataclasses.field(default_factory=set)


def _dist(g, hx, hy, hz) -> float:
    return math.sqrt(
        (g.x - hx) ** 2 + (g.y - hy) ** 2
        + (g.z - hz) ** 2
    )


@dataclasses.dataclass
class VrWorldGrab:
    _items: dict[str, _GrabInternal] = dataclasses.field(
        default_factory=dict,
    )

    def register(self, grabbable: Grabbable) -> bool:
        if not grabbable.grabbable_id:
            return False
        if grabbable.grabbable_id in self._items:
            return False
        self._items[grabbable.grabbable_id] = _GrabInternal(
            grabbable=grabbable,
        )
        return True

    def request_grab(
        self, *, player_id: str, hand: Hand,
        grabbable_id: str, hand_x: float,
        hand_y: float, hand_z: float,
    ) -> bool:
        if grabbable_id not in self._items:
            return False
        if not player_id:
            return False
        item = self._items[grabbable_id]
        if item.state == GrabState.CONSUMED:
            return False
        # Check reach
        d = _dist(item.grabbable, hand_x, hand_y, hand_z)
        if d > _GRAB_REACH_M:
            return False
        key = (player_id, hand)
        # Already holding with this hand
        if key in item.holders:
            return False
        # SMALL_ITEM is single-owner — one player only
        # (can be either of their hands). LOOT_CHEST and
        # LEVER allow same player two hands but not other
        # player.
        if item.holders:
            existing_player = next(iter(item.holders))[0]
            if existing_player != player_id:
                return False
        item.holders.add(key)
        item.state = GrabState.GRABBED
        return True

    def release(
        self, *, player_id: str, hand: Hand,
        grabbable_id: str,
    ) -> bool:
        if grabbable_id not in self._items:
            return False
        item = self._items[grabbable_id]
        key = (player_id, hand)
        if key not in item.holders:
            return False
        item.holders.discard(key)
        if not item.holders:
            item.state = GrabState.OPEN
        return True

    def consume(
        self, *, player_id: str, grabbable_id: str,
    ) -> bool:
        if grabbable_id not in self._items:
            return False
        item = self._items[grabbable_id]
        if item.state != GrabState.GRABBED:
            return False
        # Holder must be this player
        holder_players = {h[0] for h in item.holders}
        if holder_players != {player_id}:
            return False
        if item.grabbable.requires_two_hands:
            holder_hands = {h[1] for h in item.holders}
            if holder_hands != {Hand.LEFT, Hand.RIGHT}:
                return False
        item.state = GrabState.CONSUMED
        item.holders.clear()
        return True

    def state(
        self, *, grabbable_id: str,
    ) -> t.Optional[GrabState]:
        if grabbable_id not in self._items:
            return None
        return self._items[grabbable_id].state

    def holder(
        self, *, grabbable_id: str,
    ) -> t.Optional[tuple[str, Hand]]:
        if grabbable_id not in self._items:
            return None
        h = self._items[grabbable_id].holders
        if not h:
            return None
        # Return the first holder; for two-handed items,
        # both holders are the same player
        return next(iter(h))


__all__ = [
    "GrabbableKind", "Hand", "GrabState", "Grabbable",
    "VrWorldGrab",
]
