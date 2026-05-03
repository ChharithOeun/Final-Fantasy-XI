"""Treasure chests — zone-spawned chests with locks, traps, mimics.

Some Demoncore zones spawn treasure chests on a respawn timer.
Each chest has a lock tier, a trap tier, and a mimic chance.
Players approach with one of:
* a key (tier-matched) — opens cleanly
* a lockpick — skill check
* brute force — guaranteed but loud (alert mobs)

Open outcomes
-------------
    LOOTED       chest opened, loot rolled
    TRAPPED      trap fired (poison cloud, magic burst, alarm)
    MIMIC        the "chest" was a Mimic NM — combat begins
    EMPTY        nothing inside (rare safety net)
    LOCKED       attempt failed, chest still locked

Public surface
--------------
    LockTier enum (NONE / STANDARD / MASTER / ARCANE)
    TrapTier enum (NONE / POISON / EXPLOSIVE / SILENCE / SUMMON)
    OpenMethod enum (KEY / LOCKPICK / BRUTE_FORCE / DECIPHER)
    OpenOutcome enum
    Chest dataclass — one chest in the world
    OpenResult dataclass
    TreasureChestRegistry
        .spawn_chest(...)
        .open(player_id, chest_id, method, key_id, skill, rng)
        .reset_chest(chest_id) — for respawn
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


# Default lockpick skill required at each lock tier (out of 200).
_LOCK_DC: dict["LockTier", int] = {}
# Default mimic spawn chance (out of 100) per tier.
_MIMIC_CHANCE: dict["LockTier", int] = {}


class LockTier(str, enum.Enum):
    NONE = "none"
    STANDARD = "standard"
    MASTER = "master"
    ARCANE = "arcane"


class TrapTier(str, enum.Enum):
    NONE = "none"
    POISON = "poison"
    EXPLOSIVE = "explosive"
    SILENCE = "silence"
    SUMMON = "summon"             # spawns a mob


class OpenMethod(str, enum.Enum):
    KEY = "key"
    LOCKPICK = "lockpick"
    BRUTE_FORCE = "brute_force"
    DECIPHER = "decipher"          # arcane locks only


class OpenOutcome(str, enum.Enum):
    LOOTED = "looted"
    TRAPPED = "trapped"
    MIMIC = "mimic"
    EMPTY = "empty"
    LOCKED = "locked"


_LOCK_DC = {
    LockTier.NONE: 0,
    LockTier.STANDARD: 50,
    LockTier.MASTER: 120,
    LockTier.ARCANE: 999,        # only DECIPHER works
}

_MIMIC_CHANCE = {
    LockTier.NONE: 0,
    LockTier.STANDARD: 2,
    LockTier.MASTER: 5,
    LockTier.ARCANE: 10,
}


@dataclasses.dataclass
class Chest:
    chest_id: str
    zone_id: str
    position_tile: tuple[int, int]
    lock_tier: LockTier
    trap_tier: TrapTier = TrapTier.NONE
    matching_key_id: t.Optional[str] = None
    loot_table_id: str = ""
    is_open: bool = False
    last_opened_at_seconds: t.Optional[float] = None
    spawned_at_seconds: float = 0.0
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class OpenResult:
    outcome: OpenOutcome
    chest_id: str
    method_used: OpenMethod
    loot_roll_seed: t.Optional[int] = None
    trap_kind: t.Optional[TrapTier] = None
    mimic_id: t.Optional[str] = None
    reason: str = ""


@dataclasses.dataclass
class TreasureChestRegistry:
    _chests: dict[str, Chest] = dataclasses.field(
        default_factory=dict,
    )
    _opened_log: list[OpenResult] = dataclasses.field(
        default_factory=list,
    )

    def spawn_chest(self, chest: Chest) -> Chest:
        self._chests[chest.chest_id] = chest
        return chest

    def chest(self, chest_id: str) -> t.Optional[Chest]:
        return self._chests.get(chest_id)

    def chests_in_zone(
        self, zone_id: str,
    ) -> tuple[Chest, ...]:
        return tuple(
            c for c in self._chests.values()
            if c.zone_id == zone_id
        )

    def reset_chest(
        self, *, chest_id: str, now_seconds: float = 0.0,
    ) -> bool:
        c = self._chests.get(chest_id)
        if c is None:
            return False
        c.is_open = False
        c.last_opened_at_seconds = None
        c.spawned_at_seconds = now_seconds
        return True

    def open(
        self, *, player_id: str, chest_id: str,
        method: OpenMethod,
        key_id: t.Optional[str] = None,
        lockpick_skill: int = 0,
        decipher_skill: int = 0,
        now_seconds: float = 0.0,
        rng: t.Optional[random.Random] = None,
    ) -> OpenResult:
        chest = self._chests.get(chest_id)
        if chest is None:
            return OpenResult(
                outcome=OpenOutcome.LOCKED,
                chest_id=chest_id, method_used=method,
                reason="no such chest",
            )
        if chest.is_open:
            return OpenResult(
                outcome=OpenOutcome.EMPTY,
                chest_id=chest_id, method_used=method,
                reason="already opened",
            )
        rng = rng or random.Random()
        # 1) Mimic preempts everything — this thing was never a
        #    chest to begin with.
        mimic_pct = _MIMIC_CHANCE[chest.lock_tier]
        if mimic_pct > 0 and rng.randint(1, 100) <= mimic_pct:
            chest.is_open = True
            chest.last_opened_at_seconds = now_seconds
            result = OpenResult(
                outcome=OpenOutcome.MIMIC,
                chest_id=chest_id, method_used=method,
                mimic_id=f"{chest.chest_id}_mimic",
                reason="it was a mimic all along",
            )
            self._opened_log.append(result)
            return result
        # 2) Resolve lock attempt
        opened_lock = False
        lock_reason = ""
        if method == OpenMethod.KEY:
            if (
                chest.matching_key_id is not None
                and key_id == chest.matching_key_id
            ):
                opened_lock = True
            else:
                lock_reason = "wrong key"
        elif method == OpenMethod.LOCKPICK:
            dc = _LOCK_DC[chest.lock_tier]
            if chest.lock_tier == LockTier.ARCANE:
                lock_reason = "arcane lock — needs Decipher"
            elif lockpick_skill >= dc:
                opened_lock = True
            else:
                lock_reason = (
                    f"skill {lockpick_skill} < DC {dc}"
                )
        elif method == OpenMethod.BRUTE_FORCE:
            if chest.lock_tier == LockTier.ARCANE:
                lock_reason = "arcane lock can't be forced"
            else:
                opened_lock = True
        elif method == OpenMethod.DECIPHER:
            # Decipher works on arcane locks; threshold = 100
            if chest.lock_tier == LockTier.ARCANE:
                if decipher_skill >= 100:
                    opened_lock = True
                else:
                    lock_reason = "decipher skill insufficient"
            elif chest.lock_tier == LockTier.NONE:
                opened_lock = True
            else:
                # Decipher CAN open lower locks too
                opened_lock = True
        if not opened_lock:
            return OpenResult(
                outcome=OpenOutcome.LOCKED,
                chest_id=chest_id, method_used=method,
                reason=lock_reason or "lock did not yield",
            )
        # 3) Trap check — fires after lock is bypassed; brute
        #    force rattles it loose, lockpick can disarm it.
        triggers_trap = chest.trap_tier != TrapTier.NONE and (
            method == OpenMethod.BRUTE_FORCE
            or (
                method == OpenMethod.LOCKPICK
                and lockpick_skill < _LOCK_DC[chest.lock_tier] + 30
            )
            or method == OpenMethod.KEY        # keys don't disarm
        )
        if triggers_trap:
            chest.is_open = True
            chest.last_opened_at_seconds = now_seconds
            result = OpenResult(
                outcome=OpenOutcome.TRAPPED,
                chest_id=chest_id, method_used=method,
                trap_kind=chest.trap_tier,
                reason="trap triggered",
            )
            self._opened_log.append(result)
            return result
        # 4) Loot
        chest.is_open = True
        chest.last_opened_at_seconds = now_seconds
        result = OpenResult(
            outcome=OpenOutcome.LOOTED,
            chest_id=chest_id, method_used=method,
            loot_roll_seed=rng.randint(1, 10**9),
            reason="loot rolled",
        )
        self._opened_log.append(result)
        return result

    def open_log(self) -> tuple[OpenResult, ...]:
        return tuple(self._opened_log)

    def total_chests(self) -> int:
        return len(self._chests)


__all__ = [
    "LockTier", "TrapTier", "OpenMethod", "OpenOutcome",
    "Chest", "OpenResult", "TreasureChestRegistry",
]
