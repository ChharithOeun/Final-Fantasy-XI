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


# =====================================================================
# Zombie Dragon DI — persistent server-wide bosses in unreleased zones
# =====================================================================
#
# A second Domain Invasion layer running in PARALLEL with the tier-1..4
# rotation above. Distinct rules:
#
#   - One-at-a-time: only one Zombie Dragon is up server-wide.
#   - Persistent 7-day window OR until defeated.
#   - When no players are aggro'd, the dragon REGENS slowly toward
#     full HP. Even at full server contribution, 7 days is rarely
#     enough — these are designed as multi-week endurance fights.
#   - Reward distribution is contribution-tracked PER JOB used. A
#     player who switches RDM -> WHM mid-fight earns rewards on
#     both job ledgers proportional to their contribution while
#     wearing each job.
#
# Rotation: when one dragon is defeated, the next in the queue spawns
# at a new shadow-zone spawn point.

ZOMBIE_DRAGON_WINDOW_SECONDS = 7 * 24 * 60 * 60      # 7 real days
ZOMBIE_DRAGON_REGEN_PCT_PER_HOUR_NO_AGGRO = 5        # slow regen
ZOMBIE_DRAGON_BASE_HP = 100_000_000                  # 100M HP
DRAGON_DOMAIN_POINTS_POOL = 250_000


class ZombieDragon(str, enum.Enum):
    """Three Fomor/zombie variants on the canonical Reisenjima
    domain dragons. Each lives in an unreleased shadow zone."""
    PUTREFAX = "putrefax"        # decay-aspect, shadow_charnel_ridge
    OSSIDRAKE = "ossidrake"      # bone-aspect, shadow_marrow_steppes
    GANGREL = "gangrel"          # blood-aspect, shadow_crimson_marsh


@dataclasses.dataclass(frozen=True)
class ZombieDragonDef:
    dragon_id: ZombieDragon
    label: str
    zone: str
    base_hp: int = ZOMBIE_DRAGON_BASE_HP
    drop_pool: tuple[str, ...] = ()


ZOMBIE_DRAGON_CATALOG: tuple[ZombieDragonDef, ...] = (
    ZombieDragonDef(
        ZombieDragon.PUTREFAX, "Putrefax, the Necrotic Wing",
        zone="shadow_charnel_ridge",
        drop_pool=(
            "putrefax_corrupted_scale",
            "putrefax_decay_eye",
            "shadow_genkai_progress_marker",
            "domain_card_putrefax",
        ),
    ),
    ZombieDragonDef(
        ZombieDragon.OSSIDRAKE, "Ossidrake, the Marrow Hunter",
        zone="shadow_marrow_steppes",
        drop_pool=(
            "ossidrake_marrow_fragment",
            "ossidrake_femur_chunk",
            "shadow_fragment_eternal",
            "domain_card_ossidrake",
        ),
    ),
    ZombieDragonDef(
        ZombieDragon.GANGREL, "Gangrel, the Bloodless Wyrm",
        zone="shadow_crimson_marsh",
        drop_pool=(
            "gangrel_clotted_blood",
            "gangrel_hollow_heart",
            "shadow_fragment_eternal",
            "domain_card_gangrel",
        ),
    ),
)


DRAGON_BY_ID: dict[ZombieDragon, ZombieDragonDef] = {
    d.dragon_id: d for d in ZOMBIE_DRAGON_CATALOG
}


@dataclasses.dataclass
class _PerJobContribution:
    job_id: str
    damage: int = 0


@dataclasses.dataclass
class _PlayerLedger:
    """Per-player contribution split across the jobs they used during
    the encounter. A player switching jobs mid-fight gets credited
    on each."""
    player_id: str
    by_job: dict[str, int] = dataclasses.field(default_factory=dict)

    def total(self) -> int:
        return sum(self.by_job.values())

    def add(self, *, job_id: str, damage: int) -> None:
        self.by_job[job_id] = self.by_job.get(job_id, 0) + damage


@dataclasses.dataclass
class ZombieDragonEncounter:
    """A live or recently-resolved Zombie Dragon DI."""
    dragon: ZombieDragon
    spawn_time_seconds: float
    hp_remaining: int = 0
    state: str = "active"      # active / defeated / despawned
    last_aggro_time_seconds: float = 0.0
    ledger: dict[str, _PlayerLedger] = dataclasses.field(default_factory=dict)
    defeated_at: t.Optional[float] = None

    def __post_init__(self) -> None:
        if self.hp_remaining == 0:
            d = DRAGON_BY_ID[self.dragon]
            self.hp_remaining = d.base_hp

    @property
    def is_active(self) -> bool:
        return self.state == "active"

    def expires_at(self) -> float:
        return self.spawn_time_seconds + ZOMBIE_DRAGON_WINDOW_SECONDS

    def record_damage(
        self, *, player_id: str, job_id: str, damage: int,
        now_seconds: float,
    ) -> bool:
        if not self.is_active or damage <= 0:
            return False
        self.last_aggro_time_seconds = now_seconds
        self.hp_remaining = max(0, self.hp_remaining - damage)
        ledger = self.ledger.get(player_id)
        if ledger is None:
            ledger = _PlayerLedger(player_id=player_id)
            self.ledger[player_id] = ledger
        ledger.add(job_id=job_id, damage=damage)
        if self.hp_remaining == 0:
            self.state = "defeated"
            self.defeated_at = now_seconds
        return True

    def tick(self, *, now_seconds: float) -> str:
        """Advance encounter state. Returns 'still_active', 'expired',
        or 'defeated'."""
        if not self.is_active:
            return self.state
        if now_seconds >= self.expires_at():
            self.state = "despawned"
            return "expired"
        # Regen if no aggro for 1+ hour
        idle_seconds = now_seconds - self.last_aggro_time_seconds
        if idle_seconds >= 3600 and self.hp_remaining > 0:
            d = DRAGON_BY_ID[self.dragon]
            hours_idle = int(idle_seconds // 3600)
            regen_per_hour = (
                d.base_hp * ZOMBIE_DRAGON_REGEN_PCT_PER_HOUR_NO_AGGRO
                // 100
            )
            self.hp_remaining = min(
                d.base_hp,
                self.hp_remaining + hours_idle * regen_per_hour,
            )
        return "still_active"


@dataclasses.dataclass(frozen=True)
class DragonRewardForJob:
    job_id: str
    damage_contribution: int
    points: int
    drops_eligible: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class DragonRewardForPlayer:
    player_id: str
    total_damage: int
    per_job: tuple[DragonRewardForJob, ...]
    points_total: int


def settle_dragon_rewards(
    *, encounter: ZombieDragonEncounter,
) -> dict[str, DragonRewardForPlayer]:
    """Distribute Domain points + drop eligibility to every
    contributing player, broken down PER JOB they used."""
    if encounter.state != "defeated":
        return {}
    d = DRAGON_BY_ID[encounter.dragon]
    total_damage = sum(l.total() for l in encounter.ledger.values())
    if total_damage <= 0:
        return {}
    pool = DRAGON_DOMAIN_POINTS_POOL
    out: dict[str, DragonRewardForPlayer] = {}
    for player_id, ledger in encounter.ledger.items():
        per_job_rewards: list[DragonRewardForJob] = []
        player_total_pts = 0
        for job_id, dmg in ledger.by_job.items():
            pts = pool * dmg // total_damage
            player_total_pts += pts
            # Drop eligibility scales with damage % on this job
            damage_pct = dmg * 100 // total_damage
            drops = d.drop_pool if damage_pct >= 5 else ()
            per_job_rewards.append(DragonRewardForJob(
                job_id=job_id, damage_contribution=dmg,
                points=pts, drops_eligible=drops,
            ))
        out[player_id] = DragonRewardForPlayer(
            player_id=player_id,
            total_damage=ledger.total(),
            per_job=tuple(per_job_rewards),
            points_total=player_total_pts,
        )
    return out


@dataclasses.dataclass
class ZombieDragonScheduler:
    """Server-wide queue: only one dragon up at a time."""
    queue: list[ZombieDragon] = dataclasses.field(
        default_factory=lambda: list(ZombieDragon),
    )
    current: t.Optional[ZombieDragonEncounter] = None

    def has_active(self) -> bool:
        return self.current is not None and self.current.is_active

    def spawn_next(self, *, now_seconds: float
                    ) -> t.Optional[ZombieDragonEncounter]:
        if self.has_active():
            return None
        if not self.queue:
            return None
        nxt = self.queue.pop(0)
        # Cycle the queue so it never empties — each kill puts that
        # dragon at the back of the line.
        self.queue.append(nxt)
        self.current = ZombieDragonEncounter(
            dragon=nxt, spawn_time_seconds=now_seconds,
            last_aggro_time_seconds=now_seconds,
        )
        return self.current

    def tick(self, *, now_seconds: float) -> str:
        if self.current is None:
            return "idle"
        status = self.current.tick(now_seconds=now_seconds)
        if status in ("expired", "still_active"):
            if status == "expired":
                self.current = None
            return status
        # Defeated -> hold reference for reward settlement, then clear
        return status


__all__ = [
    "VANA_HOURS_PER_DAY",
    "DomainTier", "DomainSpawnPoint",
    "DomainSpawn", "DomainPointsAward",
    "next_spawn_for", "active_at", "award_for_kill",
    "PlayerDomainProgress",
    # ---- Zombie Dragon layer
    "ZOMBIE_DRAGON_WINDOW_SECONDS",
    "ZOMBIE_DRAGON_REGEN_PCT_PER_HOUR_NO_AGGRO",
    "ZOMBIE_DRAGON_BASE_HP", "DRAGON_DOMAIN_POINTS_POOL",
    "ZombieDragon", "ZombieDragonDef",
    "ZOMBIE_DRAGON_CATALOG", "DRAGON_BY_ID",
    "ZombieDragonEncounter",
    "DragonRewardForJob", "DragonRewardForPlayer",
    "settle_dragon_rewards",
    "ZombieDragonScheduler",
]
