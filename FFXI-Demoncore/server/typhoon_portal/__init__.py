"""Typhoon Portal — gateway to the Royal Palace.

When all 3 conquest alliances finish both phases, a
TYPHOON PORTAL forms in the open sea. The whole raid (up
to 64 players) has a short window to step through; once
the portal closes the Royal Palace fight begins on its
own 1-hour timer. Anyone who didn't transit before the
portal closed is locked out.

Only the raid that actually completed the conquest may
open this portal. Each portal is single-use.

Public surface
--------------
    PortalState enum
    TyphoonPortal
        .open(raid_id, now_seconds)
        .transit(raid_id, player_id, now_seconds) -> bool
        .close(raid_id, now_seconds)
        .start_royal_fight(raid_id, now_seconds)
        .state_of(raid_id) -> Optional[PortalState]
        .transited_count(raid_id) -> int
        .royal_fight_deadline(raid_id) -> Optional[int]
        .royal_fight_in_progress(raid_id, now_seconds) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PortalState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    ROYAL_FIGHT = "royal_fight"
    EXPIRED = "expired"


# how long the portal stays open for transit
PORTAL_OPEN_SECONDS = 90
# duration of the royal fight after portal closes
ROYAL_FIGHT_SECONDS = 60 * 60      # 1 hour cap
# raid roster cap
MAX_RAID_TRANSIT = 64


@dataclasses.dataclass
class _Portal:
    raid_id: str
    state: PortalState
    opened_at: int
    closed_at: t.Optional[int] = None
    fight_deadline: t.Optional[int] = None
    transited: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class TyphoonPortal:
    _portals: dict[str, _Portal] = dataclasses.field(default_factory=dict)

    def open(
        self, *, raid_id: str, now_seconds: int,
    ) -> bool:
        if not raid_id or raid_id in self._portals:
            return False
        self._portals[raid_id] = _Portal(
            raid_id=raid_id,
            state=PortalState.OPEN,
            opened_at=now_seconds,
        )
        return True

    def transit(
        self, *, raid_id: str, player_id: str,
        now_seconds: int,
    ) -> bool:
        p = self._portals.get(raid_id)
        if p is None or p.state != PortalState.OPEN:
            return False
        # auto-close if window elapsed
        if (now_seconds - p.opened_at) > PORTAL_OPEN_SECONDS:
            p.state = PortalState.CLOSED
            p.closed_at = now_seconds
            return False
        if not player_id or player_id in p.transited:
            return False
        if len(p.transited) >= MAX_RAID_TRANSIT:
            return False
        p.transited.add(player_id)
        return True

    def close(
        self, *, raid_id: str, now_seconds: int,
    ) -> bool:
        p = self._portals.get(raid_id)
        if p is None or p.state != PortalState.OPEN:
            return False
        p.state = PortalState.CLOSED
        p.closed_at = now_seconds
        return True

    def start_royal_fight(
        self, *, raid_id: str, now_seconds: int,
    ) -> bool:
        p = self._portals.get(raid_id)
        if p is None or p.state != PortalState.CLOSED:
            return False
        if not p.transited:
            return False
        p.state = PortalState.ROYAL_FIGHT
        p.fight_deadline = now_seconds + ROYAL_FIGHT_SECONDS
        return True

    def state_of(
        self, *, raid_id: str,
    ) -> t.Optional[PortalState]:
        p = self._portals.get(raid_id)
        return p.state if p else None

    def transited_count(self, *, raid_id: str) -> int:
        p = self._portals.get(raid_id)
        return len(p.transited) if p else 0

    def royal_fight_deadline(
        self, *, raid_id: str,
    ) -> t.Optional[int]:
        p = self._portals.get(raid_id)
        if p is None:
            return None
        return p.fight_deadline

    def royal_fight_in_progress(
        self, *, raid_id: str, now_seconds: int,
    ) -> bool:
        p = self._portals.get(raid_id)
        if p is None or p.state != PortalState.ROYAL_FIGHT:
            return False
        if p.fight_deadline is None:
            return False
        if now_seconds >= p.fight_deadline:
            p.state = PortalState.EXPIRED
            return False
        return True


__all__ = [
    "PortalState", "TyphoonPortal",
    "PORTAL_OPEN_SECONDS", "ROYAL_FIGHT_SECONDS",
    "MAX_RAID_TRANSIT",
]
