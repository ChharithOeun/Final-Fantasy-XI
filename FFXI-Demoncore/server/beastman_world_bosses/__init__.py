"""Beastman world bosses — Shadowlands endgame open-world bosses.

These are the inverse-side equivalents of hume HNMs / Wildskeeper
Reives — massive overworld encounters that beastman alliances
must coordinate to take down. Each boss has a SPAWN WINDOW
(real-world hours after server reset / kill), a tier-locked
participation gate, an ALLIANCE_MIN size requirement, and a loot
pool of inverse-side relic shards.

Public surface
--------------
    BossTier enum     T1 / T2 / T3 / T4 / WORLD_FIRST
    BossState enum    DORMANT / WINDOW_OPEN / ENGAGED /
                      DEFEATED / COOLDOWN
    WorldBoss dataclass
    EngageResult / KillResult dataclasses
    BeastmanWorldBosses
        .register_boss(boss_id, tier, zone_id, alliance_min,
                       window_hours, cooldown_hours, level_required)
        .open_window(boss_id, now_seconds)
        .engage(boss_id, alliance_size, level_min, now_seconds)
        .record_kill(boss_id, killers, now_seconds)
        .claim_shard(player_id, boss_id, kill_index)
        .state_for(boss_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BossTier(str, enum.Enum):
    T1 = "tier_1"
    T2 = "tier_2"
    T3 = "tier_3"
    T4 = "tier_4"
    WORLD_FIRST = "world_first"


class BossState(str, enum.Enum):
    DORMANT = "dormant"
    WINDOW_OPEN = "window_open"
    ENGAGED = "engaged"
    DEFEATED = "defeated"
    COOLDOWN = "cooldown"


@dataclasses.dataclass
class WorldBoss:
    boss_id: str
    tier: BossTier
    zone_id: str
    alliance_min: int
    window_seconds: int
    cooldown_seconds: int
    level_required: int
    state: BossState = BossState.DORMANT
    window_opened_at: t.Optional[int] = None
    engaged_at: t.Optional[int] = None
    defeated_at: t.Optional[int] = None
    last_killers: tuple[str, ...] = ()
    kill_count: int = 0
    claimed_by: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass(frozen=True)
class EngageResult:
    accepted: bool
    state: BossState
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class KillResult:
    accepted: bool
    boss_id: str
    state: BossState
    kill_count: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ClaimResult:
    accepted: bool
    boss_id: str
    shard_id: str = ""
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanWorldBosses:
    _bosses: dict[str, WorldBoss] = dataclasses.field(
        default_factory=dict,
    )

    def register_boss(
        self, *, boss_id: str,
        tier: BossTier,
        zone_id: str,
        alliance_min: int,
        window_hours: int,
        cooldown_hours: int,
        level_required: int,
    ) -> t.Optional[WorldBoss]:
        if boss_id in self._bosses:
            return None
        if alliance_min <= 0 or alliance_min > 18:
            return None
        if window_hours <= 0 or cooldown_hours <= 0:
            return None
        if not (1 <= level_required <= 150):
            return None
        b = WorldBoss(
            boss_id=boss_id,
            tier=tier,
            zone_id=zone_id,
            alliance_min=alliance_min,
            window_seconds=window_hours * 3600,
            cooldown_seconds=cooldown_hours * 3600,
            level_required=level_required,
        )
        self._bosses[boss_id] = b
        return b

    def get_boss(self, boss_id: str) -> t.Optional[WorldBoss]:
        return self._bosses.get(boss_id)

    def open_window(
        self, *, boss_id: str, now_seconds: int,
    ) -> bool:
        b = self._bosses.get(boss_id)
        if b is None:
            return False
        if b.state == BossState.COOLDOWN and b.defeated_at is not None:
            cooldown_end = b.defeated_at + b.cooldown_seconds
            if now_seconds < cooldown_end:
                return False
        if b.state in (
            BossState.WINDOW_OPEN,
            BossState.ENGAGED,
        ):
            return False
        b.state = BossState.WINDOW_OPEN
        b.window_opened_at = now_seconds
        b.engaged_at = None
        return True

    def engage(
        self, *, boss_id: str,
        alliance_size: int,
        level_min: int,
        now_seconds: int,
    ) -> EngageResult:
        b = self._bosses.get(boss_id)
        if b is None:
            return EngageResult(
                False, BossState.DORMANT,
                reason="unknown boss",
            )
        if b.state != BossState.WINDOW_OPEN:
            return EngageResult(
                False, b.state,
                reason="window not open",
            )
        if alliance_size < b.alliance_min:
            return EngageResult(
                False, b.state,
                reason="alliance too small",
            )
        if level_min < b.level_required:
            return EngageResult(
                False, b.state,
                reason="level requirement not met",
            )
        # Check window has not expired
        if (
            b.window_opened_at is not None
            and now_seconds - b.window_opened_at > b.window_seconds
        ):
            b.state = BossState.DORMANT
            b.window_opened_at = None
            return EngageResult(
                False, b.state,
                reason="window expired",
            )
        b.state = BossState.ENGAGED
        b.engaged_at = now_seconds
        return EngageResult(accepted=True, state=b.state)

    def record_kill(
        self, *, boss_id: str,
        killers: tuple[str, ...],
        now_seconds: int,
    ) -> KillResult:
        b = self._bosses.get(boss_id)
        if b is None:
            return KillResult(
                False, boss_id, BossState.DORMANT,
                reason="unknown boss",
            )
        if b.state != BossState.ENGAGED:
            return KillResult(
                False, boss_id, b.state,
                reason="not engaged",
            )
        if len(killers) < b.alliance_min:
            return KillResult(
                False, boss_id, b.state,
                reason="killer count below alliance min",
            )
        b.state = BossState.DEFEATED
        b.defeated_at = now_seconds
        b.last_killers = tuple(killers)
        b.kill_count += 1
        b.claimed_by = set()
        # Defeated rolls into cooldown immediately
        b.state = BossState.COOLDOWN
        return KillResult(
            accepted=True, boss_id=boss_id,
            state=b.state, kill_count=b.kill_count,
        )

    def claim_shard(
        self, *, player_id: str, boss_id: str,
    ) -> ClaimResult:
        b = self._bosses.get(boss_id)
        if b is None:
            return ClaimResult(
                False, boss_id, reason="unknown boss",
            )
        if b.state != BossState.COOLDOWN:
            return ClaimResult(
                False, boss_id, reason="no recent kill",
            )
        if player_id not in b.last_killers:
            return ClaimResult(
                False, boss_id, reason="not in killer list",
            )
        if player_id in b.claimed_by:
            return ClaimResult(
                False, boss_id, reason="already claimed",
            )
        b.claimed_by.add(player_id)
        shard_id = f"{boss_id}_shard_k{b.kill_count}"
        return ClaimResult(
            accepted=True, boss_id=boss_id, shard_id=shard_id,
        )

    def state_for(
        self, *, boss_id: str, now_seconds: int,
    ) -> BossState:
        b = self._bosses.get(boss_id)
        if b is None:
            return BossState.DORMANT
        if (
            b.state == BossState.COOLDOWN
            and b.defeated_at is not None
            and now_seconds - b.defeated_at >= b.cooldown_seconds
        ):
            b.state = BossState.DORMANT
        if (
            b.state == BossState.WINDOW_OPEN
            and b.window_opened_at is not None
            and now_seconds - b.window_opened_at > b.window_seconds
        ):
            b.state = BossState.DORMANT
            b.window_opened_at = None
        return b.state

    def total_bosses(self) -> int:
        return len(self._bosses)


__all__ = [
    "BossTier", "BossState",
    "WorldBoss",
    "EngageResult", "KillResult", "ClaimResult",
    "BeastmanWorldBosses",
]
