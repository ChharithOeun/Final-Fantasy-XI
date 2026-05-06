"""Sahagin raids — surprise hits, sabotage, theft, vanish.

Sahagin don't fight wars. They run TERROR OPERATIONS:
small fast strike teams that appear out of nowhere, hit
something valuable, and vanish before defenders mobilize.
Each raid has a TARGET (a wreck being salvaged, a mermaid
shrine, a player crew's flagship at anchor, etc.), a
DURATION before the raid is over (whether or not it
succeeded), and a STRIKE_TEAM_SIZE that scales by raid
kind.

If players intervene before the timer expires, they can
DEFEND the target, kill the strike team, and earn bounty
+ loot. If nobody intervenes, the raid SUCCEEDS — the
target loses cargo / progress / reputation, and the
strike team disappears into the sea.

Public surface
--------------
    RaidKind enum
    RaidStatus enum
    RaidResult dataclass (frozen)
    SahaginRaid dataclass
    SahaginRaids
        .schedule(raid_id, kind, target_id, zone, band,
                  duration_seconds, now_seconds)
        .defend(raid_id, defender_count, now_seconds)
            -> RaidResult
        .resolve(raid_id, now_seconds) -> RaidResult
        .status_of(raid_id) -> RaidStatus
        .active_raids_in(zone_id) -> tuple[SahaginRaid, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RaidKind(str, enum.Enum):
    THEFT = "theft"                # steal cargo from wreck/inventory
    SABOTAGE = "sabotage"          # break a structure (mermaid shrine, dock)
    AMBUSH = "ambush"              # hit a moving party
    ASSASSINATION = "assassination" # kill a named NPC
    DESECRATION = "desecration"    # foul a holy site (mermaid temple)


class RaidStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    DEFENDED = "defended"
    SUCCEEDED = "succeeded"
    EXPIRED = "expired"


# strike-team size by kind (number of sahagin spawned)
STRIKE_TEAM_SIZE: dict[RaidKind, int] = {
    RaidKind.THEFT: 4,
    RaidKind.SABOTAGE: 6,
    RaidKind.AMBUSH: 5,
    RaidKind.ASSASSINATION: 3,    # smaller, deadlier
    RaidKind.DESECRATION: 8,
}

# how many defenders required to repel each kind
MIN_DEFENDERS: dict[RaidKind, int] = {
    RaidKind.THEFT: 2,
    RaidKind.SABOTAGE: 3,
    RaidKind.AMBUSH: 3,
    RaidKind.ASSASSINATION: 2,
    RaidKind.DESECRATION: 4,
}


@dataclasses.dataclass
class SahaginRaid:
    raid_id: str
    kind: RaidKind
    target_id: str
    zone_id: str
    band: int
    scheduled_at: int
    duration_seconds: int
    status: RaidStatus = RaidStatus.SCHEDULED


@dataclasses.dataclass(frozen=True)
class RaidResult:
    accepted: bool
    status: t.Optional[RaidStatus] = None
    bounty_paid: int = 0
    target_damaged: bool = False
    reason: t.Optional[str] = None


# bounty paid to defenders for a successful repel
DEFENSE_BOUNTY: dict[RaidKind, int] = {
    RaidKind.THEFT: 500,
    RaidKind.SABOTAGE: 800,
    RaidKind.AMBUSH: 600,
    RaidKind.ASSASSINATION: 1500,
    RaidKind.DESECRATION: 2000,
}


@dataclasses.dataclass
class SahaginRaids:
    _raids: dict[str, SahaginRaid] = dataclasses.field(default_factory=dict)

    def schedule(
        self, *, raid_id: str,
        kind: RaidKind,
        target_id: str,
        zone_id: str, band: int,
        duration_seconds: int,
        now_seconds: int,
    ) -> bool:
        if not raid_id or raid_id in self._raids:
            return False
        if not target_id or not zone_id:
            return False
        if duration_seconds <= 0:
            return False
        self._raids[raid_id] = SahaginRaid(
            raid_id=raid_id, kind=kind,
            target_id=target_id, zone_id=zone_id, band=band,
            scheduled_at=now_seconds,
            duration_seconds=duration_seconds,
        )
        return True

    def defend(
        self, *, raid_id: str,
        defender_count: int,
        now_seconds: int,
    ) -> RaidResult:
        r = self._raids.get(raid_id)
        if r is None:
            return RaidResult(False, reason="unknown raid")
        if r.status != RaidStatus.SCHEDULED:
            return RaidResult(False, reason="raid resolved")
        # too late?
        if (now_seconds - r.scheduled_at) >= r.duration_seconds:
            r.status = RaidStatus.SUCCEEDED
            return RaidResult(
                False, status=RaidStatus.SUCCEEDED,
                target_damaged=True,
                reason="too late",
            )
        # enough defenders?
        if defender_count < MIN_DEFENDERS[r.kind]:
            return RaidResult(
                False, status=RaidStatus.SCHEDULED,
                reason="not enough defenders",
            )
        r.status = RaidStatus.DEFENDED
        return RaidResult(
            accepted=True, status=RaidStatus.DEFENDED,
            bounty_paid=DEFENSE_BOUNTY[r.kind],
            target_damaged=False,
        )

    def resolve(
        self, *, raid_id: str, now_seconds: int,
    ) -> RaidResult:
        """Force resolve a raid; SCHEDULED past timer -> SUCCEEDED;
        SCHEDULED before timer -> EXPIRED (cancellation)."""
        r = self._raids.get(raid_id)
        if r is None:
            return RaidResult(False, reason="unknown raid")
        if r.status != RaidStatus.SCHEDULED:
            return RaidResult(
                False, status=r.status, reason="already resolved",
            )
        elapsed = now_seconds - r.scheduled_at
        if elapsed >= r.duration_seconds:
            r.status = RaidStatus.SUCCEEDED
            return RaidResult(
                accepted=True, status=RaidStatus.SUCCEEDED,
                target_damaged=True,
            )
        r.status = RaidStatus.EXPIRED
        return RaidResult(
            accepted=True, status=RaidStatus.EXPIRED,
        )

    def status_of(self, *, raid_id: str) -> t.Optional[RaidStatus]:
        r = self._raids.get(raid_id)
        return r.status if r else None

    def active_raids_in(
        self, *, zone_id: str,
    ) -> tuple[SahaginRaid, ...]:
        return tuple(
            r for r in self._raids.values()
            if r.zone_id == zone_id
            and r.status == RaidStatus.SCHEDULED
        )


__all__ = [
    "RaidKind", "RaidStatus", "RaidResult",
    "SahaginRaid", "SahaginRaids",
    "STRIKE_TEAM_SIZE", "MIN_DEFENDERS", "DEFENSE_BOUNTY",
]
