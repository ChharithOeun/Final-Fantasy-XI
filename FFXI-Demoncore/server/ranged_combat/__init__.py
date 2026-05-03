"""Ranged combat — bow / gun / throwing weapon timing.

Distinct from melee auto_attack. Ranged attacks have:
* a SNAPSHOT phase (the windup before the projectile fires)
  — gear and JAs reduce snapshot frames
* a separate RECYCLE roll (chance to NOT consume ammo on hit)
* INTERRUPT on movement during snapshot (canonical)
* a longer base recast than melee swings
* WS chain that consumes TP just like melee

Snapshot tiers (simplified canonical curve):
  0%   — base
  10%  — RNG/COR JA "Rapid Shot" first tier
  20%  — gear sets at i-lvl 119
  35%  — capped snapshot stack

Public surface
--------------
    RangedWeaponKind enum (BOW / CROSSBOW / GUN / THROWING)
    RangedShot dataclass — single attempt
    snapshot_remaining(ms_into_shot, snapshot_pct) -> int
    snapshot_interrupted_by_movement(...) -> bool
    recycle_roll(recycle_pct, rng_pool) -> bool
    PlayerRangedState
        .start_shot(now_ms)
        .complete_shot(now_ms, recycle_pct, rng_pool) -> ShotResult
        .interrupt_shot()
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import STREAM_BOSS_CRITIC, RngPool


# Base snapshot duration per weapon kind (milliseconds)
_BASE_SNAPSHOT_MS: dict["RangedWeaponKind", int] = {}

# Base recast (delay between shots) per weapon kind (milliseconds)
_BASE_RECAST_MS: dict["RangedWeaponKind", int] = {}

SNAPSHOT_CAP_PCT = 35       # canonical hard cap
INTERRUPT_GRACE_MS = 100    # movement within first 100ms doesn't kill the shot


class RangedWeaponKind(str, enum.Enum):
    BOW = "bow"               # archer-classic
    CROSSBOW = "crossbow"     # heavier, slower
    GUN = "gun"               # COR signature
    THROWING = "throwing"     # NIN/THF — knives, shuriken


_BASE_SNAPSHOT_MS = {
    RangedWeaponKind.BOW: 1500,
    RangedWeaponKind.CROSSBOW: 2000,
    RangedWeaponKind.GUN: 1800,
    RangedWeaponKind.THROWING: 800,
}


_BASE_RECAST_MS = {
    RangedWeaponKind.BOW: 6000,
    RangedWeaponKind.CROSSBOW: 7500,
    RangedWeaponKind.GUN: 7000,
    RangedWeaponKind.THROWING: 3000,
}


def base_snapshot_ms(kind: RangedWeaponKind) -> int:
    return _BASE_SNAPSHOT_MS[kind]


def base_recast_ms(kind: RangedWeaponKind) -> int:
    return _BASE_RECAST_MS[kind]


def effective_snapshot_ms(*, kind: RangedWeaponKind,
                            snapshot_pct: int) -> int:
    """Snapshot duration after gear/JA reduction. Capped at
    SNAPSHOT_CAP_PCT (35%)."""
    pct = max(0, min(snapshot_pct, SNAPSHOT_CAP_PCT))
    base = _BASE_SNAPSHOT_MS[kind]
    return base * (100 - pct) // 100


def snapshot_remaining(
    *, kind: RangedWeaponKind, snapshot_pct: int,
    ms_into_shot: int,
) -> int:
    """How many ms remain on the snapshot windup."""
    total = effective_snapshot_ms(
        kind=kind, snapshot_pct=snapshot_pct,
    )
    return max(0, total - max(0, ms_into_shot))


def snapshot_interrupted_by_movement(
    *, ms_into_shot: int, last_movement_ms: int,
) -> bool:
    """If the player moved AFTER the grace window, the shot is
    interrupted."""
    if last_movement_ms <= INTERRUPT_GRACE_MS:
        return False
    return last_movement_ms <= ms_into_shot


def recycle_roll(*, recycle_pct: int, rng_pool: RngPool) -> bool:
    """True iff the ammo was preserved on this shot."""
    if recycle_pct <= 0:
        return False
    if recycle_pct >= 100:
        return True
    rng = rng_pool.stream(STREAM_BOSS_CRITIC)
    roll = rng.randint(1, 100)
    return roll <= recycle_pct


@dataclasses.dataclass(frozen=True)
class ShotResult:
    accepted: bool
    fired: bool = False
    interrupted: bool = False
    ammo_preserved: bool = False
    snapshot_actual_ms: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerRangedState:
    player_id: str
    weapon_kind: RangedWeaponKind = RangedWeaponKind.BOW
    snapshot_pct: int = 0
    in_snapshot: bool = False
    snapshot_started_at_ms: int = 0
    last_movement_ms: int = 0
    last_shot_completed_at_ms: int = 0

    @property
    def can_start_shot(self) -> bool:
        # Recast not yet elapsed?
        recast = _BASE_RECAST_MS[self.weapon_kind]
        return (not self.in_snapshot
                and (
                    self.last_shot_completed_at_ms == 0
                    or recast >= 0   # recast handled by caller's clock
                ))

    def start_shot(self, *, now_ms: int) -> bool:
        if self.in_snapshot:
            return False
        self.in_snapshot = True
        self.snapshot_started_at_ms = now_ms
        return True

    def report_movement(self, *, ms_into_shot: int) -> None:
        self.last_movement_ms = ms_into_shot

    def interrupt_shot(self) -> bool:
        if not self.in_snapshot:
            return False
        self.in_snapshot = False
        self.snapshot_started_at_ms = 0
        return True

    def complete_shot(
        self, *, now_ms: int, recycle_pct: int = 0,
        rng_pool: t.Optional[RngPool] = None,
    ) -> ShotResult:
        if not self.in_snapshot:
            return ShotResult(False, reason="not in snapshot")
        ms_in = now_ms - self.snapshot_started_at_ms
        # Did movement break it?
        if snapshot_interrupted_by_movement(
            ms_into_shot=ms_in,
            last_movement_ms=self.last_movement_ms,
        ):
            self.in_snapshot = False
            return ShotResult(
                accepted=True, fired=False, interrupted=True,
                snapshot_actual_ms=ms_in,
            )
        required = effective_snapshot_ms(
            kind=self.weapon_kind, snapshot_pct=self.snapshot_pct,
        )
        if ms_in < required:
            return ShotResult(
                False, reason="snapshot incomplete",
                snapshot_actual_ms=ms_in,
            )
        # Fire
        ammo_kept = False
        if rng_pool is not None and recycle_pct > 0:
            ammo_kept = recycle_roll(
                recycle_pct=recycle_pct, rng_pool=rng_pool,
            )
        self.in_snapshot = False
        self.last_shot_completed_at_ms = now_ms
        return ShotResult(
            accepted=True, fired=True,
            ammo_preserved=ammo_kept,
            snapshot_actual_ms=ms_in,
        )


__all__ = [
    "SNAPSHOT_CAP_PCT", "INTERRUPT_GRACE_MS",
    "RangedWeaponKind",
    "base_snapshot_ms", "base_recast_ms",
    "effective_snapshot_ms", "snapshot_remaining",
    "snapshot_interrupted_by_movement", "recycle_roll",
    "ShotResult", "PlayerRangedState",
]
