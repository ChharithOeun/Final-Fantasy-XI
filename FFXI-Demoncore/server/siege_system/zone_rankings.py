"""Per-zone control classifier + weekly ranking.

Once per real week the system computes per-zone metrics and assigns
each zone a status: STABLE / CONTESTED / BEASTMAN_DOMINANT. The
status drives the deployment recommendation — how many military NPCs
the nation sends in.

The control_percentage axis is the headline number (0-100, higher =
nation-friendlier). Thresholds:
    >= 70  -> STABLE          nation has firm grip, low patrol density
    30-70  -> CONTESTED       active war; medium-density military
    < 30   -> BEASTMAN_DOMINANT  campaign-push territory
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ZoneStatus(str, enum.Enum):
    STABLE = "stable"
    CONTESTED = "contested"
    BEASTMAN_DOMINANT = "beastman_dominant"


# Threshold percentages (control_percentage axis: 0-100)
STABLE_THRESHOLD = 70.0
BEASTMAN_DOMINANT_THRESHOLD = 30.0


@dataclasses.dataclass
class ZoneMetrics:
    """Per-zone weekly summary."""
    zone: str
    beastman_activity: int            # 0-1000+; kills + NM spawns + pressure
    player_presence_hours: float      # cumulative player-hours in the zone
    nation_interest: int              # 0-100; strategic value (proximity, resources)
    control_percentage: float         # 0-100; computed externally OR via compute_control


def compute_control_percentage(*,
                                nation_kills: int,
                                beastman_kills: int,
                                player_presence_hours: float,
                                nation_interest: int) -> float:
    """Synthesize a control percentage from the underlying signals.

    Higher when the nation is winning the kill war + players are
    engaged + the nation cares about the zone strategically.
    """
    if nation_kills + beastman_kills == 0:
        kill_axis = 50.0   # No combat data: assume contested mid-point
    else:
        kill_axis = 100.0 * nation_kills / (nation_kills + beastman_kills)

    # Player presence boosts control (logged-in defenders = nation pressure)
    presence_axis = min(100.0, player_presence_hours * 2.0)

    # Strategic interest tilts the result toward the nation when high
    interest_axis = float(nation_interest)

    # Weighted average: kill axis dominates, presence + interest tweak
    return max(0.0, min(100.0, (
        kill_axis * 0.6
        + presence_axis * 0.25
        + interest_axis * 0.15
    )))


class ZoneRankingComputer:
    """Classifies zones by status + sorts them by criticality."""

    def classify(self, metrics: ZoneMetrics) -> ZoneStatus:
        if metrics.control_percentage >= STABLE_THRESHOLD:
            return ZoneStatus.STABLE
        if metrics.control_percentage < BEASTMAN_DOMINANT_THRESHOLD:
            return ZoneStatus.BEASTMAN_DOMINANT
        return ZoneStatus.CONTESTED

    def rank_zones(self,
                    all_metrics: list[ZoneMetrics],
                    ) -> list[tuple[str, ZoneStatus]]:
        """Return zones sorted by descending vulnerability + nation interest.
        The first entry is the place a nation should be deploying first."""
        scored = []
        for m in all_metrics:
            status = self.classify(m)
            # Vulnerability score: more vulnerable + higher interest = sort first
            vulnerability = 100.0 - m.control_percentage
            sort_key = vulnerability + (m.nation_interest * 0.5)
            scored.append((sort_key, m.zone, status))
        scored.sort(key=lambda x: -x[0])
        return [(zone, status) for _, zone, status in scored]
