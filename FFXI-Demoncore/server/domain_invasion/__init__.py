"""Domain Invasion — Reisenjima scheduled open-world boss spawns.

Server-wide rotation: each Vana'diel hour, a Domain boss tier
spawns at one of the four Reisenjima open-world points. Domain
points are awarded for participation.

Tier rotation: T1 spawns hourly, T2 every 6 hours, T3 every
24 hours, T4 (capstone Sandworm) every 72 hours. Each tier
opens a wider participation reward.

Public surface
--------------
    DomainTier enum (T1..T4)
    DomainSpawnPoint enum (Reisenjima sites)
    DomainSchedule
        .next_spawn_for(tier, current_vana_hour) -> int
        .active_at(vana_hour) -> Iterable[(tier, point)]
    DomainPointsAward / award_for_kill(...)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Vana'diel day = 24 hours. We'll pin spawn windows to the same.
VANA_HOURS_PER_DAY = 24


class DomainTier(str, enum.Enum):
    T1 = "tier_1"   # hourly
    T2 = "tier_2"   # every 6 hours
    T3 = "tier_3"   # every 24 hours
    T4 = "tier_4"   # every 72 hours (capstone Sandworm)


class DomainSpawnPoint(str, enum.Enum):
    NORTH_REISEN = "north_reisenjima"
    EAST_REISEN = "east_reisenjima"
    SOUTH_REISEN = "south_reisenjima"
    WEST_REISEN = "west_reisenjima"


# Spawn period in Vana hours per tier
_TIER_PERIOD: dict[DomainTier, int] = {
    DomainTier.T1: 1,
    DomainTier.T2: 6,
    DomainTier.T3: 24,
    DomainTier.T4: 72,
}


# Domain-points base reward per tier
_TIER_DOMAIN_POINTS: dict[DomainTier, int] = {
    DomainTier.T1: 50,
    DomainTier.T2: 200,
    DomainTier.T3: 800,
    DomainTier.T4: 3000,
}


@dataclasses.dataclass(frozen=True)
class DomainSpawn:
    tier: DomainTier
    point: DomainSpawnPoint
    spawn_hour: int          # Vana hour (in absolute terms)


def next_spawn_for(*, tier: DomainTier, current_vana_hour: int
                    ) -> int:
    period = _TIER_PERIOD[tier]
    if current_vana_hour % period == 0:
        return current_vana_hour
    return ((current_vana_hour // period) + 1) * period


def active_at(*, current_vana_hour: int
               ) -> tuple[DomainSpawn, ...]:
    """Which tier+point pairs are active right now. Same point
    rotates by hour to spread spawns across Reisenjima."""
    out: list[DomainSpawn] = []
    points = list(DomainSpawnPoint)
    for tier in DomainTier:
        period = _TIER_PERIOD[tier]
        if current_vana_hour % period == 0:
            point = points[(current_vana_hour // period)
                            % len(points)]
            out.append(DomainSpawn(
                tier=tier, point=point,
                spawn_hour=current_vana_hour,
            ))
    return tuple(out)


@dataclasses.dataclass(frozen=True)
class DomainPointsAward:
    accepted: bool
    points: int = 0
    reason: t.Optional[str] = None


def award_for_kill(
    *, tier: DomainTier, contribution_pct: int = 100,
) -> DomainPointsAward:
    """Domain points for a successful Domain Invasion kill.
    contribution_pct (0-100) caps award proportional to your
    participation (1% min if you tagged the mob)."""
    if not (0 < contribution_pct <= 100):
        return DomainPointsAward(False, reason="contribution OOR")
    base = _TIER_DOMAIN_POINTS[tier]
    awarded = max(1, base * contribution_pct // 100)
    return DomainPointsAward(accepted=True, points=awarded)


@dataclasses.dataclass
class PlayerDomainProgress:
    player_id: str
    domain_points: int = 0
    tier_clears: dict[DomainTier, int] = dataclasses.field(
        default_factory=dict,
    )

    def grant_points(self, *, amount: int) -> bool:
        if amount <= 0:
            return False
        self.domain_points += amount
        return True

    def spend_points(self, *, amount: int) -> bool:
        if amount <= 0 or self.domain_points < amount:
            return False
        self.domain_points -= amount
        return True

    def record_clear(self, *, tier: DomainTier) -> None:
        self.tier_clears[tier] = self.tier_clears.get(tier, 0) + 1


__all__ = [
    "VANA_HOURS_PER_DAY",
    "DomainTier", "DomainSpawnPoint",
    "DomainSpawn", "DomainPointsAward",
    "next_spawn_for", "active_at", "award_for_kill",
    "PlayerDomainProgress",
]
