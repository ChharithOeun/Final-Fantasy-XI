"""Mount XP progression + 3-deaths-in-24h permadeath.

Per MOUNTS.md mount progression:
    XP gain: ridden through hostile territory + survived encounters
              + race wins
    Per-level: +200 HP, +1% speed, occasional ability unlock
              (level 30 chocobo: 'Sprint')
    Mount death does NOT reset progression
    Mount can be killed permanently (>=3 deaths in 24h -> 'lost')
"""
from __future__ import annotations

import typing as t

from .mount import (
    CHOCOBO_BASE_HP,
    CHOCOBO_HP_PER_LEVEL,
    MountSnapshot,
    MountType,
    stats_for_level,
)


XP_PER_HOSTILE_ZONE_RIDE = 50
XP_PER_RACE_WIN = 200
XP_PER_SURVIVED_ENCOUNTER = 25

# 3 deaths in 24h = mount permanently lost
MOUNT_LOSS_THRESHOLD = 3
MOUNT_LOSS_WINDOW_SECONDS = 24 * 3600


def xp_required_for_level(level: int) -> int:
    """Cumulative XP into a level. level n requires n*100 XP into the
    previous level."""
    if level <= 1:
        return 0
    return level * 100


class MountProgression:
    """Owns mount XP curve + level-up + permadeath logic."""

    def grant_xp(self,
                  mount: MountSnapshot,
                  *,
                  xp: int,
                  rider_level: int = 20) -> int:
        """Add XP, roll up levels as thresholds are crossed. Returns
        the new level."""
        if not mount.is_alive or mount.is_lost or xp <= 0:
            return mount.level

        accumulated = mount.xp + xp
        new_level = mount.level
        # Walk through levels until we run out of pool
        while True:
            threshold = xp_required_for_level(new_level + 1)
            if accumulated < threshold:
                break
            accumulated -= threshold
            new_level += 1
            self._apply_level_up_rewards(mount, new_level, rider_level)

        mount.level = new_level
        mount.xp = accumulated

        # Refresh max_hp based on new level so the level-up bonus is
        # visible immediately (also tops up current_hp to new max)
        stats = stats_for_level(mount.mount_type, mount.level,
                                  rider_level=rider_level)
        mount.max_hp = int(stats["hp"])
        mount.current_hp = mount.max_hp
        return mount.level

    def notify_death(self,
                      mount: MountSnapshot,
                      *,
                      now: float) -> bool:
        """Record a mount death timestamp. If the rolling 24-hour count
        hits MOUNT_LOSS_THRESHOLD, the mount becomes 'lost' (permanent).
        Returns True if the mount just became lost."""
        if mount.is_lost:
            return False
        mount.is_alive = False
        # Prune old deaths first
        cutoff = now - MOUNT_LOSS_WINDOW_SECONDS
        mount.death_history = [t for t in mount.death_history if t >= cutoff]
        mount.death_history.append(now)
        if len(mount.death_history) >= MOUNT_LOSS_THRESHOLD:
            mount.is_lost = True
            return True
        return False

    def attempt_revive_via_stable(self,
                                     mount: MountSnapshot,
                                     *,
                                     rider_level: int = 20,
                                     ) -> bool:
        """Stable Re-Raise quest brings the mount back. Doesn't work
        if the mount is permanently lost."""
        if mount.is_lost:
            return False
        if mount.is_alive:
            return True
        mount.is_alive = True
        stats = stats_for_level(mount.mount_type, mount.level,
                                  rider_level=rider_level)
        mount.max_hp = int(stats["hp"])
        mount.current_hp = mount.max_hp
        return True

    def deaths_in_window(self,
                          mount: MountSnapshot,
                          *,
                          now: float) -> int:
        cutoff = now - MOUNT_LOSS_WINDOW_SECONDS
        return sum(1 for t in mount.death_history if t >= cutoff)

    # ------------------------------------------------------------------
    # Internal: per-level rewards
    # ------------------------------------------------------------------

    def _apply_level_up_rewards(self,
                                  mount: MountSnapshot,
                                  level: int,
                                  rider_level: int) -> None:
        """Doc: '+200 HP, +1% speed, occasional ability unlock'.
        HP/speed are read from stats_for_level on the next stat refresh.
        We just stamp ability unlocks here."""
        if level == 30 and mount.mount_type == MountType.CHOCOBO:
            mount.abilities_unlocked.add("sprint")
        if level == 50 and mount.mount_type == MountType.CHOCOBO:
            mount.abilities_unlocked.add("kick_attack")
        if level == 75 and mount.mount_type == MountType.CHOCOBO:
            mount.abilities_unlocked.add("choco_cure")
