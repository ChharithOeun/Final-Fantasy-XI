"""Sea lane patrol — naval status of each shipping route.

Each NAVAL LANE (zone-pair shipping route) carries a STATUS
that reflects how dangerous it currently is. Pirate sightings
push the status toward DANGEROUS; nation patrols push it back
toward SECURE.

Lane status:
  SECURE     - patrolled recently; no unanswered sightings
  WATCHFUL   - sightings reported; nation has not yet responded
  DANGEROUS  - active fleet presence; warn ferries

Each lane has a THREAT_SCORE that decays toward 0 over time.
Pirate sightings (from sea_pirate_factions) ADD to the score.
Patrol passes SUBTRACT from the score. Status is a band over
the score: 0..29 SECURE, 30..69 WATCHFUL, 70+ DANGEROUS.

The airship_ferry uses get_lane_status() to decide whether to
sail, slow-sail (with escorts), or cancel. The ferry already
knows about pirate encounters; this module is the lane-level
aggregate that turns sightings into a posture.

Public surface
--------------
    LaneStatus enum
    LaneRecord dataclass
    SeaLanePatrol
        .register_lane(lane_id, zone_a, zone_b)
        .pirate_sighted(lane_id, severity, now_seconds)
        .patrol_pass(lane_id, sweep_strength, now_seconds)
        .get_lane_status(lane_id, now_seconds) -> LaneStatus
        .threat_score(lane_id, now_seconds) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LaneStatus(str, enum.Enum):
    SECURE = "secure"
    WATCHFUL = "watchful"
    DANGEROUS = "dangerous"


# threat decays at _DECAY_PER_HOUR per hour
_DECAY_PER_HOUR = 5

_SECURE_CEILING = 30
_WATCHFUL_CEILING = 70
# >= 70 -> DANGEROUS

_THREAT_FLOOR = 0
_THREAT_CEILING = 100


@dataclasses.dataclass
class LaneRecord:
    lane_id: str
    zone_a: str
    zone_b: str
    threat_score: int = 0
    last_observed_at: int = 0


@dataclasses.dataclass
class SeaLanePatrol:
    _lanes: dict[str, LaneRecord] = dataclasses.field(default_factory=dict)

    def register_lane(
        self, *, lane_id: str, zone_a: str, zone_b: str,
    ) -> bool:
        if not lane_id or not zone_a or not zone_b or zone_a == zone_b:
            return False
        if lane_id in self._lanes:
            return False
        self._lanes[lane_id] = LaneRecord(
            lane_id=lane_id, zone_a=zone_a, zone_b=zone_b,
        )
        return True

    def _decay_in_place(
        self, *, rec: LaneRecord, now_seconds: int,
    ) -> None:
        elapsed = now_seconds - rec.last_observed_at
        if elapsed <= 0:
            return
        hours = elapsed // 3_600
        if hours <= 0:
            return
        rec.threat_score = max(
            _THREAT_FLOOR,
            rec.threat_score - _DECAY_PER_HOUR * hours,
        )
        rec.last_observed_at = now_seconds

    def pirate_sighted(
        self, *, lane_id: str,
        severity: int,
        now_seconds: int,
    ) -> bool:
        rec = self._lanes.get(lane_id)
        if rec is None or severity <= 0:
            return False
        self._decay_in_place(rec=rec, now_seconds=now_seconds)
        rec.threat_score = min(
            _THREAT_CEILING, rec.threat_score + severity,
        )
        rec.last_observed_at = now_seconds
        return True

    def patrol_pass(
        self, *, lane_id: str,
        sweep_strength: int,
        now_seconds: int,
    ) -> bool:
        rec = self._lanes.get(lane_id)
        if rec is None or sweep_strength <= 0:
            return False
        self._decay_in_place(rec=rec, now_seconds=now_seconds)
        rec.threat_score = max(
            _THREAT_FLOOR, rec.threat_score - sweep_strength,
        )
        rec.last_observed_at = now_seconds
        return True

    def threat_score(
        self, *, lane_id: str, now_seconds: int,
    ) -> int:
        rec = self._lanes.get(lane_id)
        if rec is None:
            return 0
        # snapshot decay without mutating last_observed_at if no time
        elapsed = now_seconds - rec.last_observed_at
        hours = max(0, elapsed // 3_600)
        return max(
            _THREAT_FLOOR,
            rec.threat_score - _DECAY_PER_HOUR * hours,
        )

    def get_lane_status(
        self, *, lane_id: str, now_seconds: int,
    ) -> LaneStatus:
        score = self.threat_score(
            lane_id=lane_id, now_seconds=now_seconds,
        )
        if score < _SECURE_CEILING:
            return LaneStatus.SECURE
        if score < _WATCHFUL_CEILING:
            return LaneStatus.WATCHFUL
        return LaneStatus.DANGEROUS

    def total_lanes(self) -> int:
        return len(self._lanes)


__all__ = [
    "LaneStatus", "LaneRecord", "SeaLanePatrol",
]
