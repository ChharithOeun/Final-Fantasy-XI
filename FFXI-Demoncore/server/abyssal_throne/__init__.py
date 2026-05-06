"""Abyssal Throne — 7-tier underwater boss ladder.

The capstone of underwater progression. Seven boss tiers,
each gated on the prior. The final tier is THE DROWNED
KING, the lich-king-equivalent of the deep — a server-wide
event that takes a coordinated alliance to attempt and
weeks of preparation per attempt.

Tiers:
    T1  KRAKEN_SPAWN      - solo, ~20m fight
    T2  TIDE_WURM          - 6-person, kraken cult lair
    T3  GULF_LEVIATHAN     - 18-person alliance, ToD window
    T4  SUNKEN_HIERARCH    - 18-person, drowned-pact gated
    T5  ABYSS_HARBINGER    - 24-person, T4 + cult redemption
    T6  DEPTH_TYRANT       - 36-person, T5 + abyssal gear i171+
    T7  THE_DROWNED_KING   - 64-person world-first race;
                              only spawnable once per ToD
                              window; clears reset weekly

Each kill writes to the world-first leaderboard with
timestamp + crew/alliance ID. The first kill of T7 unlocks
the SERVER-WIDE Abyssal Throne reward — a permanent
plaque on the Bastok statue and a unique title.

Public surface
--------------
    BossTier int enum
    BossKill dataclass (frozen)
    AbyssalThrone
        .register_player_kill(player_id, tier, now_seconds,
                              crew_id, alliance_size)
        .has_killed(player_id, tier) -> bool
        .can_attempt(player_id, tier) -> (bool, reason)
        .world_first(tier) -> Optional[BossKill]
        .total_kills(tier) -> int
        .progression_for(player_id) -> tuple[BossTier, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BossTier(int, enum.Enum):
    KRAKEN_SPAWN = 1
    TIDE_WURM = 2
    GULF_LEVIATHAN = 3
    SUNKEN_HIERARCH = 4
    ABYSS_HARBINGER = 5
    DEPTH_TYRANT = 6
    THE_DROWNED_KING = 7


# minimum alliance size required for each tier
MIN_PARTY_SIZE: dict[BossTier, int] = {
    BossTier.KRAKEN_SPAWN: 1,
    BossTier.TIDE_WURM: 6,
    BossTier.GULF_LEVIATHAN: 18,
    BossTier.SUNKEN_HIERARCH: 18,
    BossTier.ABYSS_HARBINGER: 24,
    BossTier.DEPTH_TYRANT: 36,
    BossTier.THE_DROWNED_KING: 64,
}


@dataclasses.dataclass(frozen=True)
class BossKill:
    player_id: str
    tier: BossTier
    crew_id: t.Optional[str]
    alliance_size: int
    killed_at: int


@dataclasses.dataclass
class AbyssalThrone:
    # player_id -> set of tiers killed
    _kills: dict[str, set[BossTier]] = dataclasses.field(default_factory=dict)
    # tier -> list of BossKill (in registration order)
    _kills_by_tier: dict[BossTier, list[BossKill]] = dataclasses.field(
        default_factory=dict,
    )

    def register_player_kill(
        self, *, player_id: str,
        tier: BossTier,
        now_seconds: int,
        crew_id: t.Optional[str] = None,
        alliance_size: int = 1,
    ) -> bool:
        if not player_id:
            return False
        ok, _ = self.can_attempt(player_id=player_id, tier=tier)
        if not ok:
            return False
        if alliance_size < MIN_PARTY_SIZE[tier]:
            return False
        self._kills.setdefault(player_id, set()).add(tier)
        kill = BossKill(
            player_id=player_id, tier=tier,
            crew_id=crew_id, alliance_size=alliance_size,
            killed_at=now_seconds,
        )
        self._kills_by_tier.setdefault(tier, []).append(kill)
        return True

    def has_killed(
        self, *, player_id: str, tier: BossTier,
    ) -> bool:
        return tier in self._kills.get(player_id, set())

    def can_attempt(
        self, *, player_id: str, tier: BossTier,
    ) -> tuple[bool, t.Optional[str]]:
        if tier == BossTier.KRAKEN_SPAWN:
            return True, None
        prev = BossTier(tier.value - 1)
        if not self.has_killed(player_id=player_id, tier=prev):
            return False, f"missing prerequisite {prev.name}"
        return True, None

    def world_first(self, *, tier: BossTier) -> t.Optional[BossKill]:
        kills = self._kills_by_tier.get(tier, [])
        return kills[0] if kills else None

    def total_kills(self, *, tier: BossTier) -> int:
        return len(self._kills_by_tier.get(tier, []))

    def progression_for(
        self, *, player_id: str,
    ) -> tuple[BossTier, ...]:
        tiers = sorted(self._kills.get(player_id, set()), key=lambda t: t.value)
        return tuple(tiers)


__all__ = [
    "BossTier", "BossKill", "AbyssalThrone",
    "MIN_PARTY_SIZE",
]
