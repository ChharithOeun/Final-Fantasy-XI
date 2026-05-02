"""Regen / resting — sit-to-rest HP/MP regen rates + zone modifiers.

Sitting (Heal command) ramps HP/MP regen over time. Cities heal
faster than wilderness. Food adds a regen bonus. Regen/Refresh
status effects stack additively with the base rates.

Public surface
--------------
    RestingState
        .start_resting(now)
        .stop_resting()
        .compute_tick(now, zone_modifier, food_bonus,
                      regen_status_bonus, refresh_status_bonus)
        -> tuple[hp_gain, mp_gain]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ZoneModifier(str, enum.Enum):
    CITY = "city"            # +50% rate
    OUTPOST = "outpost"      # +25% rate
    WILDERNESS = "wilderness"  # baseline
    DUNGEON = "dungeon"      # -25% rate


_ZONE_MULTIPLIER: dict[ZoneModifier, float] = {
    ZoneModifier.CITY: 1.5,
    ZoneModifier.OUTPOST: 1.25,
    ZoneModifier.WILDERNESS: 1.0,
    ZoneModifier.DUNGEON: 0.75,
}


# Base resting tick formula (per FFXI canonical):
# HP per tick = 12 + (level-10)/10  capped at 25
# MP per tick = 12 + (level-10)/10  capped at 25
def _base_per_tick(*, level: int) -> int:
    if level < 1:
        return 0
    raw = 12 + (level - 10) // 10
    return min(25, max(1, raw))


# Resting ramps up over the first 20 seconds — start at 50% rate.
RAMP_DURATION_SECONDS = 20
TICK_INTERVAL_SECONDS = 4    # heal tick every 4 sec retail


@dataclasses.dataclass
class RestingState:
    actor_id: str
    level: int
    is_resting: bool = False
    started_at_tick: int = 0
    last_tick_seen: int = 0

    def start_resting(self, *, now_tick: int) -> bool:
        if self.is_resting:
            return False
        self.is_resting = True
        self.started_at_tick = now_tick
        self.last_tick_seen = now_tick
        return True

    def stop_resting(self) -> bool:
        if not self.is_resting:
            return False
        self.is_resting = False
        return True

    def _ramp_factor(self, *, now_tick: int) -> float:
        elapsed = now_tick - self.started_at_tick
        if elapsed >= RAMP_DURATION_SECONDS:
            return 1.0
        if elapsed <= 0:
            return 0.5
        return 0.5 + 0.5 * (elapsed / RAMP_DURATION_SECONDS)

    def compute_tick(
        self, *,
        now_tick: int,
        zone: ZoneModifier = ZoneModifier.WILDERNESS,
        food_bonus_pct: int = 0,
        regen_status_bonus: int = 0,
        refresh_status_bonus: int = 0,
    ) -> tuple[int, int]:
        """Compute HP/MP gain for the next tick boundary. Returns
        (hp_gain, mp_gain). Returns (0, 0) when not resting."""
        if not self.is_resting:
            # Even while moving, regen/refresh status effects tick.
            return regen_status_bonus, refresh_status_bonus
        base = _base_per_tick(level=self.level)
        ramp = self._ramp_factor(now_tick=now_tick)
        zone_mul = _ZONE_MULTIPLIER[zone]
        food_mul = 1.0 + max(0, food_bonus_pct) / 100.0
        scaled = int(base * ramp * zone_mul * food_mul)
        hp_gain = scaled + regen_status_bonus
        mp_gain = scaled + refresh_status_bonus
        self.last_tick_seen = now_tick
        return hp_gain, mp_gain

    def time_resting(self, *, now_tick: int) -> int:
        if not self.is_resting:
            return 0
        return now_tick - self.started_at_tick


__all__ = [
    "ZoneModifier", "RAMP_DURATION_SECONDS",
    "TICK_INTERVAL_SECONDS",
    "RestingState",
]
