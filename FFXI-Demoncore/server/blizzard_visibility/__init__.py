"""Blizzard visibility — visibility shrinks during heavy weather.

In a blizzard, fog, or sandstorm, you can't see far. Mob
detection ranges shrink. Players' minimap radius shrinks.
This module computes the *effective visibility radius* for
a (player, zone) given the active weather state.

Base baseline radius is 50 yalms. Weather scales it:
    CLEAR / RAIN / THUNDERSTORM / SNOW       -> 100% (no penalty)
    FOG (intensity-driven)                   -> 100 - intensity
    BLIZZARD (intensity-driven, max -70%)    -> 100 - 0.7*intensity
    SANDSTORM (intensity-driven, max -60%)   -> 100 - 0.6*intensity

Torch active boosts visible radius back up by torch_radius
yalms (capped at the baseline).

Public surface
--------------
    VisibilityCalculator
        .compute_radius(baseline, weather_kind, intensity,
                        torch_radius=0) -> int
"""
from __future__ import annotations

import dataclasses


_BLIZZARD_FACTOR = 0.7
_SANDSTORM_FACTOR = 0.6


@dataclasses.dataclass
class VisibilityCalculator:

    def compute_radius(
        self, *, baseline: int, weather_kind: str,
        intensity: int, torch_radius: int = 0,
    ) -> int:
        if baseline <= 0:
            return 0
        if intensity < 0:
            intensity = 0
        if intensity > 100:
            intensity = 100

        if weather_kind == "blizzard":
            penalty_pct = int(intensity * _BLIZZARD_FACTOR)
        elif weather_kind == "sandstorm":
            penalty_pct = int(intensity * _SANDSTORM_FACTOR)
        elif weather_kind == "fog":
            penalty_pct = intensity
        else:
            penalty_pct = 0

        # cap penalty at 95% so you always see at least a bit
        if penalty_pct > 95:
            penalty_pct = 95

        radius = baseline * (100 - penalty_pct) // 100

        if torch_radius > 0:
            # torch helps but never exceeds baseline
            radius = min(baseline, radius + torch_radius)

        return max(0, radius)


__all__ = ["VisibilityCalculator"]
