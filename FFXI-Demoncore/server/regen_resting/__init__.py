"""Regen / resting — sit-to-rest HP/MP regen rates + zone modifiers.

Sitting (/heal) ramps HP/MP regen over time. Cities heal faster
than wilderness. Food adds a regen bonus. Regen/Refresh status
effects stack additively with the base rates.

Demoncore tempo
---------------
The base FFXI rates are too slow for Demoncore's tempo (10x mob
density, faster auto-attacks, higher respawn). The healing rate
has been pumped to keep up:

* TEMPO_MULTIPLIER = 3.0 applied to the base per-tick formula.
  At level 30 this takes a wilderness rest from ~12 HP/tick
  retail up to ~36 HP/tick.
* Tick interval 4s -> 2s — twice as often.
* Ramp 20s -> 6s — full speed by the time the second tick lands.
* Zone floors raised: wilderness +25%, dungeons no longer punished.

Net effect: a 50% HP loss after a fight clears in roughly 12-15
seconds in a wilderness zone, vs. retail's ~60s. Combat-to-
combat downtime feels like the rest of the game's tempo.

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


# Demoncore tempo multiplier. Single knob to keep the canonical
# FFXI ratios while making everything proportionally faster.
TEMPO_MULTIPLIER = 3.0

# Per-tick cap. Bumped from 25 retail to 75 to leave room for the
# tempo multiplier without bottlenecking high-level rests.
PER_TICK_CAP = 75


class ZoneModifier(str, enum.Enum):
    CITY = "city"              # safest haven, fastest rest
    OUTPOST = "outpost"
    WILDERNESS = "wilderness"  # most common rest spot
    DUNGEON = "dungeon"


_ZONE_MULTIPLIER: dict[ZoneModifier, float] = {
    ZoneModifier.CITY: 2.0,
    ZoneModifier.OUTPOST: 1.5,
    ZoneModifier.WILDERNESS: 1.25,
    # Dungeons no longer punish resting — the punishment is the
    # mob density, not the heal rate. Floor raised from 0.75 -> 1.0.
    ZoneModifier.DUNGEON: 1.0,
}


# Base resting tick formula (FFXI canonical pre-tempo bump):
#   raw = 12 + (level-10)/10
# Demoncore applies TEMPO_MULTIPLIER on top, capped at PER_TICK_CAP.
def _base_per_tick(*, level: int) -> int:
    if level < 1:
        return 0
    raw = 12 + (level - 10) // 10
    boosted = int(round(raw * TEMPO_MULTIPLIER))
    return min(PER_TICK_CAP, max(1, boosted))


# Resting ramps up over the first 6 seconds — start at 50% rate.
# Faster than retail's 20s so the heal feels responsive.
RAMP_DURATION_SECONDS = 6
TICK_INTERVAL_SECONDS = 2    # heal tick every 2 sec (retail = 4)


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
    "TEMPO_MULTIPLIER", "PER_TICK_CAP",
    "ZoneModifier", "RAMP_DURATION_SECONDS",
    "TICK_INTERVAL_SECONDS",
    "RestingState",
]
