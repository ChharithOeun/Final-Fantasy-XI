"""Per-nation military deployment planner.

Once a real week each nation reads the zone-ranking output and
dispatches military NPCs to zones. Per-zone deployment scales with
status; total deployment per nation is capped to keep the simulation
bounded.

Per the doc:
    STABLE             -> 5-10 patrol NPCs (low-density)
    CONTESTED          -> 20-40 active military (mid-density, some officers)
    BEASTMAN_DOMINANT  -> 50-100 (full unit, officers + mages + archers)

Total deployment per nation per week is capped at 200-500 NPCs.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .zone_rankings import ZoneStatus


PER_NATION_DEPLOYMENT_CAP = 500   # ceiling across all zones
PER_NATION_DEPLOYMENT_MIN = 200   # floor — nations always deploy at least this many

# Recommended per-zone deployment by status. (lower, upper)
DEPLOYMENT_BAND = {
    ZoneStatus.STABLE: (5, 10),
    ZoneStatus.CONTESTED: (20, 40),
    ZoneStatus.BEASTMAN_DOMINANT: (50, 100),
}

# Per-nation military unit composition. Each entry is role -> base proportion.
# Composition adapts to zone status (officers + mages added at higher tiers).
NATION_MILITARY_COMPOSITIONS: dict[str, dict[str, float]] = {
    "bastok": {
        # Republican Guard: heavy infantry + musketeers + Galkan officers
        "heavy_infantry": 0.55,
        "musketeer": 0.25,
        "galkan_officer": 0.10,
        "field_medic": 0.10,
    },
    "sandoria": {
        # Royal Knights: cavalry + paladin captains + halberds
        "cavalry": 0.40,
        "halberdier": 0.35,
        "paladin_captain": 0.15,
        "white_mage_attendant": 0.10,
    },
    "windurst": {
        # Mithra mercenaries + Tarutaru mages + Star Sibyl mages
        "mithra_mercenary": 0.40,
        "tarutaru_mage": 0.30,
        "star_sibyl_mage": 0.15,
        "summoner_attendant": 0.15,
    },
    "ahturhgan": {
        # Salaheem mercenaries: ranged + corsairs + dancers
        "salaheem_ranger": 0.40,
        "corsair": 0.30,
        "dancer_medic": 0.20,
        "blue_mage_officer": 0.10,
    },
}


@dataclasses.dataclass
class DeploymentRecommendation:
    zone: str
    status: ZoneStatus
    npc_count: int
    composition: dict[str, int]   # role -> count


class MilitaryDeploymentPlanner:
    """Plans the weekly deployment for a single nation."""

    def __init__(self,
                  *,
                  nation: str,
                  cap: int = PER_NATION_DEPLOYMENT_CAP,
                  floor: int = PER_NATION_DEPLOYMENT_MIN) -> None:
        if nation not in NATION_MILITARY_COMPOSITIONS:
            raise ValueError(f"unknown nation: {nation}")
        self.nation = nation
        self.cap = cap
        self.floor = floor

    def plan(self,
              ranked_zones: list[tuple[str, ZoneStatus]],
              ) -> list[DeploymentRecommendation]:
        """Given sorted (zone, status) pairs (from ZoneRankingComputer),
        produce per-zone deployment recommendations summing to <= cap."""
        recommendations: list[DeploymentRecommendation] = []
        running_total = 0

        for zone, status in ranked_zones:
            target = self._zone_target(status)
            # Cap-aware allocation: don't overshoot
            remaining = self.cap - running_total
            if remaining <= 0:
                # Already at cap — minimum patrol presence per remaining zone
                npc_count = min(5, max(0, self.cap - running_total))
            else:
                npc_count = min(target, remaining)

            recommendations.append(DeploymentRecommendation(
                zone=zone,
                status=status,
                npc_count=npc_count,
                composition=self._compose(npc_count),
            ))
            running_total += npc_count

        # Floor enforcement: if we're under the floor, bump up CONTESTED
        # zones until we reach it. (Doesn't kick in for typical inputs.)
        if running_total < self.floor and recommendations:
            shortfall = self.floor - running_total
            for rec in recommendations:
                if rec.status == ZoneStatus.CONTESTED and shortfall > 0:
                    bump = min(shortfall,
                                DEPLOYMENT_BAND[ZoneStatus.CONTESTED][1]
                                - rec.npc_count)
                    if bump > 0:
                        rec.npc_count += bump
                        rec.composition = self._compose(rec.npc_count)
                        shortfall -= bump

        return recommendations

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _zone_target(self, status: ZoneStatus) -> int:
        lo, hi = DEPLOYMENT_BAND[status]
        # Use the upper band by default — nations deploy aggressively
        return hi

    def _compose(self, npc_count: int) -> dict[str, int]:
        """Distribute the npc_count across the nation's role mix."""
        if npc_count <= 0:
            return {}
        weights = NATION_MILITARY_COMPOSITIONS[self.nation]
        out: dict[str, int] = {}
        running = 0
        roles = list(weights.items())
        for i, (role, weight) in enumerate(roles):
            if i == len(roles) - 1:
                # Last role takes the remainder to ensure exact total
                out[role] = npc_count - running
            else:
                count = int(round(npc_count * weight))
                out[role] = count
                running += count
        return out
