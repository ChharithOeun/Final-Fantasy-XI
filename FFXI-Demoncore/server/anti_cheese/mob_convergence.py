"""Activity-driven mob convergence.

Per the user's design: "even if parties are waiting to enter an
instance mobs around the zone would start to gather near player
activities, to prevent bot farming and afk raising."

When a cluster of players camps in one location for a while, mobs
in adjacent areas slowly converge on the activity. The longer the
camp, the wider the gather radius. Anti-bot-farming for instance
entrances + AFK-raising prevention + general world-feels-alive.

This composes with `aggro_system` (mobs converge per the activity
hotspot, then engage normally per their sensory profile when they
arrive).
"""
from __future__ import annotations

import dataclasses
import math
import typing as t


@dataclasses.dataclass
class ActivityHotspot:
    """A cluster of player activity at a position."""
    zone: str
    x_cm: float
    y_cm: float
    z_cm: float
    detected_at: float                # when first detected
    last_observed_at: float            # most recent activity update
    player_count: int = 1
    strength: float = 1.0             # accumulated activity score


@dataclasses.dataclass
class _MobMovementHint:
    """Output of the convergence tick: mob X should walk toward hotspot."""
    mob_id: str
    target_x_cm: float
    target_y_cm: float
    target_z_cm: float
    walk_speed_pct: float = 0.5       # half-speed shamble


# Tuning
HOTSPOT_DETECTION_RADIUS_CM = 1500.0       # 15m clusters become hotspots
HOTSPOT_DECAY_SECONDS = 600.0              # 10 min without activity → fade
INITIAL_GATHER_RADIUS_CM = 3000.0          # 30m: nearby mobs start moving
GATHER_RADIUS_GROWTH_CM_PER_SEC = 5.0      # widens 5cm/sec while camped
MAX_GATHER_RADIUS_CM = 12000.0             # 120m cap


class MobConvergenceTracker:
    """Tracks player-activity hotspots in each zone and emits
    movement hints for nearby mobs."""

    def __init__(self):
        self._hotspots_by_zone: dict[str, list[ActivityHotspot]] = {}

    def observe_player_activity(self, *,
                                  player_id: str,
                                  zone: str,
                                  x_cm: float, y_cm: float, z_cm: float,
                                  now: float) -> None:
        """Player did something at this location. Update or create hotspot."""
        zone_hotspots = self._hotspots_by_zone.setdefault(zone, [])

        # Find nearby existing hotspot
        for h in zone_hotspots:
            d = self._distance(h.x_cm, h.y_cm, h.z_cm, x_cm, y_cm, z_cm)
            if d <= HOTSPOT_DETECTION_RADIUS_CM:
                # Merge into existing
                h.last_observed_at = now
                h.strength += 1.0
                return

        # New hotspot
        zone_hotspots.append(ActivityHotspot(
            zone=zone, x_cm=x_cm, y_cm=y_cm, z_cm=z_cm,
            detected_at=now, last_observed_at=now,
        ))

    def tick(self, now: float, *,
              mobs_in_zone: dict[str, list[dict]]) -> list[_MobMovementHint]:
        """Per zone, decay old hotspots + emit movement hints for mobs
        within the current gather radius.

        mobs_in_zone: zone -> list of {mob_id, x_cm, y_cm, z_cm, currently_aggressive}
        Returns list of movement hints. Mobs already in combat
        (currently_aggressive) skip the convergence path.
        """
        hints: list[_MobMovementHint] = []

        for zone, hotspots in self._hotspots_by_zone.items():
            # Decay old hotspots
            hotspots[:] = [h for h in hotspots
                            if (now - h.last_observed_at) < HOTSPOT_DECAY_SECONDS]
            if not hotspots:
                continue

            mobs = mobs_in_zone.get(zone, [])
            for h in hotspots:
                age = now - h.detected_at
                gather_radius = min(
                    INITIAL_GATHER_RADIUS_CM
                    + GATHER_RADIUS_GROWTH_CM_PER_SEC * age,
                    MAX_GATHER_RADIUS_CM,
                )
                for mob in mobs:
                    if mob.get("currently_aggressive"):
                        continue
                    d = self._distance(
                        h.x_cm, h.y_cm, h.z_cm,
                        mob["x_cm"], mob["y_cm"], mob["z_cm"],
                    )
                    if d <= gather_radius:
                        hints.append(_MobMovementHint(
                            mob_id=mob["mob_id"],
                            target_x_cm=h.x_cm,
                            target_y_cm=h.y_cm,
                            target_z_cm=h.z_cm,
                            walk_speed_pct=0.5,
                        ))
        return hints

    def get_hotspots(self, zone: str) -> list[ActivityHotspot]:
        return list(self._hotspots_by_zone.get(zone, []))

    @staticmethod
    def _distance(ax: float, ay: float, az: float,
                   bx: float, by: float, bz: float) -> float:
        return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)
