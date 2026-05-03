"""Wanted poster — notoriety + bounty posters in towns.

Distinct from outlaw_system (free-fire PvP) and bounty_payout
(payout-on-kill). This is the PUBLICITY layer: notoriety
accumulates from in-region crimes; once it crosses TIER, the
town crier posts a wanted poster across nation noticeboards.
Posters escalate (TIER_1 -> TIER_5) and add a visible bounty.
The posters live in zone-specific noticeboards.

Crimes -> notoriety:
  THEFT      +5
  MURDER     +50
  ARSON      +30
  KIDNAP     +25
  TREASON    +200

Tiers:
  TIER_1    50 notoriety   visible in home nation
  TIER_2    150            posted across all 3 nations
  TIER_3    400            beastman bounties added
  TIER_4    900            outlaw flag auto-attached
  TIER_5   1800            kill-on-sight standing army order

Public surface
--------------
    CrimeKind enum
    NotorietyTier enum
    WantedPoster dataclass
    CrimeReport dataclass
    WantedPosterRegistry
        .report_crime(player_id, kind, magnitude)
        .clear_notoriety(player_id) — paid pardon
        .poster_for(player_id) -> Optional[WantedPoster]
        .posters_in_zone(zone_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Tier thresholds.
TIER_1_NOTORIETY = 50
TIER_2_NOTORIETY = 150
TIER_3_NOTORIETY = 400
TIER_4_NOTORIETY = 900
TIER_5_NOTORIETY = 1800


class CrimeKind(str, enum.Enum):
    THEFT = "theft"
    MURDER = "murder"
    ARSON = "arson"
    KIDNAP = "kidnap"
    TREASON = "treason"
    ASSAULT = "assault"
    SMUGGLING = "smuggling"


class NotorietyTier(str, enum.Enum):
    NONE = "none"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    TIER_4 = "tier_4"
    TIER_5 = "tier_5"


# Notoriety per crime.
_NOTORIETY_PER_CRIME: dict[CrimeKind, int] = {
    CrimeKind.THEFT: 5,
    CrimeKind.MURDER: 50,
    CrimeKind.ARSON: 30,
    CrimeKind.KIDNAP: 25,
    CrimeKind.TREASON: 200,
    CrimeKind.ASSAULT: 8,
    CrimeKind.SMUGGLING: 15,
}


# Bounty-gil per tier.
_BOUNTY_BY_TIER: dict[NotorietyTier, int] = {
    NotorietyTier.NONE: 0,
    NotorietyTier.TIER_1: 1_000,
    NotorietyTier.TIER_2: 5_000,
    NotorietyTier.TIER_3: 25_000,
    NotorietyTier.TIER_4: 100_000,
    NotorietyTier.TIER_5: 500_000,
}


@dataclasses.dataclass
class CrimeReport:
    player_id: str
    kind: CrimeKind
    zone_id: str
    notoriety_added: int
    note: str = ""


@dataclasses.dataclass
class WantedPoster:
    player_id: str
    notoriety: int
    tier: NotorietyTier
    bounty_gil: int
    posted_zones: list[str] = dataclasses.field(
        default_factory=list,
    )
    crimes_logged: list[CrimeKind] = dataclasses.field(
        default_factory=list,
    )
    last_updated_seconds: float = 0.0


def _tier_for_notoriety(score: int) -> NotorietyTier:
    if score >= TIER_5_NOTORIETY:
        return NotorietyTier.TIER_5
    if score >= TIER_4_NOTORIETY:
        return NotorietyTier.TIER_4
    if score >= TIER_3_NOTORIETY:
        return NotorietyTier.TIER_3
    if score >= TIER_2_NOTORIETY:
        return NotorietyTier.TIER_2
    if score >= TIER_1_NOTORIETY:
        return NotorietyTier.TIER_1
    return NotorietyTier.NONE


# Where posters appear per tier.
_POSTING_ZONES_BY_TIER: dict[
    NotorietyTier, tuple[str, ...],
] = {
    NotorietyTier.NONE: (),
    NotorietyTier.TIER_1: ("home_nation",),
    NotorietyTier.TIER_2: (
        "bastok", "san_doria", "windurst",
    ),
    NotorietyTier.TIER_3: (
        "bastok", "san_doria", "windurst",
        "beastman_camp",
    ),
    NotorietyTier.TIER_4: (
        "bastok", "san_doria", "windurst",
        "beastman_camp", "jeuno",
    ),
    NotorietyTier.TIER_5: (
        "bastok", "san_doria", "windurst",
        "beastman_camp", "jeuno", "norg", "tavnazia",
    ),
}


@dataclasses.dataclass
class WantedPosterRegistry:
    _posters: dict[str, WantedPoster] = dataclasses.field(
        default_factory=dict,
    )

    def report_crime(
        self, *, player_id: str, kind: CrimeKind,
        zone_id: str, magnitude: float = 1.0,
        now_seconds: float = 0.0,
    ) -> CrimeReport:
        added = int(_NOTORIETY_PER_CRIME[kind] * magnitude)
        poster = self._posters.get(player_id)
        if poster is None:
            poster = WantedPoster(
                player_id=player_id, notoriety=0,
                tier=NotorietyTier.NONE, bounty_gil=0,
            )
            self._posters[player_id] = poster
        poster.notoriety += added
        poster.crimes_logged.append(kind)
        poster.tier = _tier_for_notoriety(poster.notoriety)
        poster.bounty_gil = _BOUNTY_BY_TIER[poster.tier]
        poster.posted_zones = list(
            _POSTING_ZONES_BY_TIER[poster.tier],
        )
        poster.last_updated_seconds = now_seconds
        return CrimeReport(
            player_id=player_id, kind=kind, zone_id=zone_id,
            notoriety_added=added,
        )

    def poster_for(
        self, player_id: str,
    ) -> t.Optional[WantedPoster]:
        return self._posters.get(player_id)

    def posters_in_zone(
        self, zone_id: str,
    ) -> tuple[WantedPoster, ...]:
        return tuple(
            p for p in self._posters.values()
            if zone_id in p.posted_zones
        )

    def clear_notoriety(
        self, *, player_id: str,
    ) -> bool:
        poster = self._posters.get(player_id)
        if poster is None:
            return False
        if poster.notoriety == 0:
            return False
        poster.notoriety = 0
        poster.tier = NotorietyTier.NONE
        poster.bounty_gil = 0
        poster.posted_zones = []
        return True

    def reduce_notoriety(
        self, *, player_id: str, amount: int,
    ) -> t.Optional[int]:
        if amount <= 0:
            return None
        poster = self._posters.get(player_id)
        if poster is None:
            return None
        poster.notoriety = max(0, poster.notoriety - amount)
        poster.tier = _tier_for_notoriety(poster.notoriety)
        poster.bounty_gil = _BOUNTY_BY_TIER[poster.tier]
        poster.posted_zones = list(
            _POSTING_ZONES_BY_TIER[poster.tier],
        )
        return poster.notoriety

    def total_posters(self) -> int:
        return len(self._posters)


__all__ = [
    "TIER_1_NOTORIETY", "TIER_2_NOTORIETY",
    "TIER_3_NOTORIETY", "TIER_4_NOTORIETY",
    "TIER_5_NOTORIETY",
    "CrimeKind", "NotorietyTier",
    "CrimeReport", "WantedPoster",
    "WantedPosterRegistry",
]
