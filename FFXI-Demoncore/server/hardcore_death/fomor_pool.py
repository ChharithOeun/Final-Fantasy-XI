"""Fomor pool — pending + active sets with the doc's anti-grief rules.

Per HARDCORE_DEATH.md the safety rails:
    - Town safety: fomors do not enter Bastok / Sandy / Windy /
      Jeuno / Whitegate proper. Outpost zones are fair game.
    - Spawn rate cap: floor(zone_player_count * 1.5) fomors active
      per zone. Prevents server-load + screen-clutter explosions.
    - 24h cooldown: a character cannot become a fomor twice in 24h
      on the same account (anti rage-delete farming).
    - Active hours: night-cycle only (Vana'diel ~8pm-6am game time).
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t

from .snapshot import FomorSnapshot


# Doc: 'cannot become a fomor twice in 24h on the same account'.
ACCOUNT_COOLDOWN_SECONDS: int = 24 * 3600

# Doc: town safety zones.
TOWN_SAFE_ZONES: frozenset[str] = frozenset({
    "bastok_mines",
    "bastok_markets",
    "bastok_metalworks",
    "south_sandoria",
    "north_sandoria",
    "chateau_doraguille",
    "windurst_waters",
    "windurst_walls",
    "windurst_woods",
    "heavens_tower",
    "ru_lude_gardens",
    "lower_jeuno",
    "upper_jeuno",
    "port_jeuno",
    "aht_urhgan_whitegate",
})

# Doc: 'active hours: night-cycle only (Vana'diel time, ~8pm-6am
# game time). During day, fomors are dormant in their last-died
# zone.'
NIGHT_HOUR_RANGE: tuple[int, int] = (20, 6)    # 8pm to 6am wraparound


class FomorState(str, enum.Enum):
    PENDING = "pending"               # snapshot taken, waiting to spawn
    DORMANT = "dormant"               # daytime; spawned but inactive
    ACTIVE = "active"                 # nighttime + spawned + roaming
    DESPAWNED = "despawned"           # killed or culled


@dataclasses.dataclass
class FomorEntry:
    """One fomor in the pool."""
    fomor_id: str
    char_id: str
    account_id: str
    snapshot: FomorSnapshot
    current_zone_id: str
    state: FomorState = FomorState.PENDING
    spawned_at: t.Optional[float] = None
    last_active_at: t.Optional[float] = None


class FomorPool:
    """Per-server fomor registry. Owns town-safety + cap + cooldown."""

    def __init__(self) -> None:
        self._fomors: dict[str, FomorEntry] = {}
        # account_id -> last fomor-conversion timestamp (for cooldown)
        self._last_conversion: dict[str, float] = {}
        self._next_id = 1

    # ------------------------------------------------------------------
    # Conversion gate (24h cooldown)
    # ------------------------------------------------------------------

    def can_convert(self, *,
                       account_id: str,
                       now: float) -> tuple[bool, str]:
        """Has this account had a fomor in the last 24h?"""
        last = self._last_conversion.get(account_id)
        if last is None:
            return True, ""
        elapsed = now - last
        if elapsed < ACCOUNT_COOLDOWN_SECONDS:
            remaining = ACCOUNT_COOLDOWN_SECONDS - elapsed
            return False, (f"24h cooldown active; "
                              f"{int(remaining)}s remaining")
        return True, ""

    def convert_to_fomor(self,
                            *,
                            account_id: str,
                            snapshot: FomorSnapshot,
                            spawn_zone_id: str,
                            now: float
                            ) -> t.Optional[FomorEntry]:
        """Snapshot -> FomorEntry in PENDING state.

        Returns None if the cooldown blocks or the spawn zone is
        a sanctuary town.
        """
        ok, _ = self.can_convert(account_id=account_id, now=now)
        if not ok:
            return None
        if spawn_zone_id in TOWN_SAFE_ZONES:
            return None
        fomor_id = f"fomor_{self._next_id:08d}"
        self._next_id += 1
        entry = FomorEntry(
            fomor_id=fomor_id,
            char_id=snapshot.char_id,
            account_id=account_id,
            snapshot=snapshot,
            current_zone_id=spawn_zone_id,
        )
        self._fomors[fomor_id] = entry
        self._last_conversion[account_id] = now
        return entry

    # ------------------------------------------------------------------
    # Spawn caps
    # ------------------------------------------------------------------

    def zone_cap(self, *, zone_player_count: int) -> int:
        """Doc: 'floor(zone_player_count * 1.5)'."""
        if zone_player_count < 0:
            raise ValueError("zone_player_count must be non-negative")
        return math.floor(zone_player_count * 1.5)

    def fomors_in_zone(self, zone_id: str) -> tuple[FomorEntry, ...]:
        return tuple(f for f in self._fomors.values()
                      if f.current_zone_id == zone_id
                      and f.state != FomorState.DESPAWNED)

    def can_spawn_in_zone(self,
                              *,
                              zone_id: str,
                              zone_player_count: int) -> bool:
        if zone_id in TOWN_SAFE_ZONES:
            return False
        cap = self.zone_cap(zone_player_count=zone_player_count)
        active = sum(
            1 for f in self.fomors_in_zone(zone_id)
            if f.state in (FomorState.PENDING, FomorState.DORMANT,
                              FomorState.ACTIVE)
        )
        return active < cap

    # ------------------------------------------------------------------
    # Day/night cycle
    # ------------------------------------------------------------------

    @staticmethod
    def is_night_hour(vana_hour: int) -> bool:
        """Vana'diel hour-of-day: 8pm (20) to 6am (6) is night."""
        if vana_hour < 0 or vana_hour > 23:
            raise ValueError("vana_hour must be 0..23")
        # Wraparound window 20-23 OR 0-5
        return vana_hour >= NIGHT_HOUR_RANGE[0] or vana_hour < NIGHT_HOUR_RANGE[1]

    def tick_day_night(self, *, vana_hour: int, now: float) -> int:
        """Sweep all fomors and flip DORMANT <-> ACTIVE per the
        time-of-day rule. Returns count of state changes."""
        is_night = self.is_night_hour(vana_hour)
        changed = 0
        for f in self._fomors.values():
            if f.state == FomorState.DESPAWNED:
                continue
            if is_night and f.state == FomorState.DORMANT:
                f.state = FomorState.ACTIVE
                f.last_active_at = now
                changed += 1
            elif not is_night and f.state == FomorState.ACTIVE:
                f.state = FomorState.DORMANT
                changed += 1
            elif f.state == FomorState.PENDING:
                # First tick after conversion — promote to night/day
                f.state = FomorState.ACTIVE if is_night else FomorState.DORMANT
                f.spawned_at = now
                changed += 1
        return changed

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get(self, fomor_id: str) -> t.Optional[FomorEntry]:
        return self._fomors.get(fomor_id)

    def __len__(self) -> int:
        return len(self._fomors)

    def all_fomors(self) -> tuple[FomorEntry, ...]:
        return tuple(self._fomors.values())

    def active_count(self) -> int:
        return sum(1 for f in self._fomors.values()
                      if f.state == FomorState.ACTIVE)

    def despawn(self, fomor_id: str) -> bool:
        entry = self._fomors.get(fomor_id)
        if entry is None:
            return False
        entry.state = FomorState.DESPAWNED
        return True
