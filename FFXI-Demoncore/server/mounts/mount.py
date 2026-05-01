"""Mount types + per-level stats.

Per MOUNTS.md, chocobo is the only mount at launch. Wyvern, Tiger,
Crystal Dragon, Demon Mount are post-v1 reservations — encoded as
enum values so the engine can cleanly add stat tables later.

Chocobo stats from the doc table:
    HP at level 20 = 2000; +200 per level past base
    Speed at level 20 = 12 m/s; +0.05/level
    Defense = player_level × 5 (scales with rider)
    Aggro range = 60% of player's
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MountType(str, enum.Enum):
    """All planned mount types. Chocobo is the only one with a stat
    table at launch; the rest exist as reservations (no stat scaling
    encoded yet)."""
    CHOCOBO = "chocobo"
    WYVERN = "wyvern"
    TIGER = "tiger"
    CRYSTAL_DRAGON = "crystal_dragon"
    DEMON_MOUNT = "demon_mount"


CHOCOBO_BASE_LEVEL = 20
CHOCOBO_BASE_HP = 2000
CHOCOBO_HP_PER_LEVEL = 200
CHOCOBO_BASE_SPEED_MS = 12.0
CHOCOBO_SPEED_PER_LEVEL = 0.05
CHOCOBO_AGGRO_RANGE_FRACTION = 0.60


@dataclasses.dataclass
class MountSnapshot:
    """Per-character mount state. Persisted between rides."""
    mount_id: str
    owner_id: str
    mount_type: MountType
    level: int = CHOCOBO_BASE_LEVEL
    xp: int = 0
    max_hp: int = 0
    current_hp: int = 0
    is_alive: bool = True
    is_lost: bool = False                 # permadeath: >= 3 deaths in 24h
    barding: list[str] = dataclasses.field(default_factory=list)
    abilities_unlocked: set[str] = dataclasses.field(default_factory=set)
    death_history: list[float] = dataclasses.field(default_factory=list)
    license_expires_at: t.Optional[float] = None   # 30-day license


def stats_for_level(mount_type: MountType,
                     level: int,
                     *,
                     rider_level: int = 1) -> dict[str, float]:
    """Resolve level-aware stats for a mount.

    Returns a dict with hp, speed_ms, defense, aggro_range_fraction.
    Only chocobo has a launch stat table — other types use the
    chocobo base curve as a reasonable placeholder.
    """
    if mount_type == MountType.CHOCOBO:
        levels_above_base = max(0, level - CHOCOBO_BASE_LEVEL)
        return {
            "hp": float(CHOCOBO_BASE_HP + CHOCOBO_HP_PER_LEVEL * levels_above_base),
            "speed_ms": (CHOCOBO_BASE_SPEED_MS
                          + CHOCOBO_SPEED_PER_LEVEL * levels_above_base),
            "defense": float(rider_level * 5),
            "aggro_range_fraction": CHOCOBO_AGGRO_RANGE_FRACTION,
        }

    # Placeholder for post-v1 mounts: same curve as chocobo but with
    # a small variation per type. Caller can override later.
    levels_above_base = max(0, level - CHOCOBO_BASE_LEVEL)
    type_hp_factor = {
        MountType.WYVERN: 0.85,        # flies: faster but fragile
        MountType.TIGER: 1.30,         # tankier
        MountType.CRYSTAL_DRAGON: 1.50,
        MountType.DEMON_MOUNT: 1.10,
    }.get(mount_type, 1.0)
    return {
        "hp": (CHOCOBO_BASE_HP + CHOCOBO_HP_PER_LEVEL * levels_above_base) * type_hp_factor,
        "speed_ms": (CHOCOBO_BASE_SPEED_MS
                       + CHOCOBO_SPEED_PER_LEVEL * levels_above_base),
        "defense": float(rider_level * 5),
        "aggro_range_fraction": CHOCOBO_AGGRO_RANGE_FRACTION,
    }


def spawn_chocobo(*,
                    mount_id: str,
                    owner_id: str,
                    level: int = CHOCOBO_BASE_LEVEL,
                    rider_level: int = 20,
                    license_expires_at: t.Optional[float] = None,
                    ) -> MountSnapshot:
    """Construct a fresh chocobo at the given level. Owner must be
    level 20+ to ride per the standard chocobo license rule."""
    stats = stats_for_level(MountType.CHOCOBO, level, rider_level=rider_level)
    snap = MountSnapshot(
        mount_id=mount_id,
        owner_id=owner_id,
        mount_type=MountType.CHOCOBO,
        level=level,
        max_hp=int(stats["hp"]),
        current_hp=int(stats["hp"]),
        is_alive=True,
        license_expires_at=license_expires_at,
    )
    # Level 30 chocobo unlocks Sprint per the doc
    if level >= 30:
        snap.abilities_unlocked.add("sprint")
    return snap
