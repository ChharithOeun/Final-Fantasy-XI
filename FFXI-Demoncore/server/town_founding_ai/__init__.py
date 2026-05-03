"""Town founding AI — NPCs build new settlements.

Over a long enough timeline, ambitious NPCs scout for and FOUND
new towns. The AI examines candidate sites and scores them on
five factors: water access, defensibility, trade-route
proximity, arable land, and beastman threat. Above a threshold,
the site progresses through CAMP -> HAMLET -> VILLAGE -> TOWN
in stages keyed by population growth.

A founded settlement gets entries in zone_atlas, npc_economy,
trade_routes, and (when grown enough) a Mog House anchor. The
world map gets denser over real time.

Public surface
--------------
    SettlementStage enum
    SiteScore dataclass
    Settlement dataclass
    TownFoundingAI
        .scout_site(zone_id, name, water/defense/trade/arable/threat)
        .charter(site_id, founder_npc_id) -> Settlement
        .grow(site_id, new_pop) -> stage progression
        .abandon(site_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Site scoring weights.
WATER_WEIGHT = 30
DEFENSE_WEIGHT = 20
TRADE_WEIGHT = 25
ARABLE_WEIGHT = 15
THREAT_PENALTY = 30          # subtracted, scaled by threat level
MIN_CHARTER_SCORE = 50       # below this, can't charter
# Population thresholds for stages.
HAMLET_POP = 50
VILLAGE_POP = 200
TOWN_POP = 800


class SettlementStage(str, enum.Enum):
    SCOUTED = "scouted"          # site survey only
    CAMP = "camp"                # founders moving in
    HAMLET = "hamlet"
    VILLAGE = "village"
    TOWN = "town"
    ABANDONED = "abandoned"


@dataclasses.dataclass(frozen=True)
class SiteScore:
    site_id: str
    zone_id: str
    name: str
    water_access: int            # 0..10
    defensibility: int           # 0..10
    trade_proximity: int         # 0..10
    arable_land: int             # 0..10
    beastman_threat: int         # 0..10
    composite_score: int


def _compute_composite(
    *, water: int, defense: int, trade: int,
    arable: int, threat: int,
) -> int:
    return (
        water * WATER_WEIGHT
        + defense * DEFENSE_WEIGHT
        + trade * TRADE_WEIGHT
        + arable * ARABLE_WEIGHT
        - threat * THREAT_PENALTY
    ) // 10


@dataclasses.dataclass
class Settlement:
    site_id: str
    zone_id: str
    name: str
    founder_npc_id: str
    stage: SettlementStage = SettlementStage.CAMP
    population: int = 0
    chartered_at_seconds: float = 0.0
    last_growth_at_seconds: float = 0.0
    note: str = ""


@dataclasses.dataclass(frozen=True)
class StageChange:
    site_id: str
    old_stage: SettlementStage
    new_stage: SettlementStage
    population: int


@dataclasses.dataclass
class TownFoundingAI:
    min_charter_score: int = MIN_CHARTER_SCORE
    _sites: dict[str, SiteScore] = dataclasses.field(
        default_factory=dict,
    )
    _settlements: dict[str, Settlement] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def scout_site(
        self, *, zone_id: str, name: str,
        water_access: int, defensibility: int,
        trade_proximity: int, arable_land: int,
        beastman_threat: int,
    ) -> SiteScore:
        sid = f"site_{self._next_id}"
        self._next_id += 1
        composite = _compute_composite(
            water=water_access, defense=defensibility,
            trade=trade_proximity, arable=arable_land,
            threat=beastman_threat,
        )
        score = SiteScore(
            site_id=sid, zone_id=zone_id, name=name,
            water_access=water_access,
            defensibility=defensibility,
            trade_proximity=trade_proximity,
            arable_land=arable_land,
            beastman_threat=beastman_threat,
            composite_score=composite,
        )
        self._sites[sid] = score
        return score

    def site(self, site_id: str) -> t.Optional[SiteScore]:
        return self._sites.get(site_id)

    def viable(self, site_id: str) -> bool:
        site = self._sites.get(site_id)
        if site is None:
            return False
        return site.composite_score >= self.min_charter_score

    def charter(
        self, *, site_id: str, founder_npc_id: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[Settlement]:
        site = self._sites.get(site_id)
        if site is None:
            return None
        if site.composite_score < self.min_charter_score:
            return None
        if site_id in self._settlements:
            return None
        s = Settlement(
            site_id=site_id, zone_id=site.zone_id,
            name=site.name, founder_npc_id=founder_npc_id,
            stage=SettlementStage.CAMP,
            population=1,
            chartered_at_seconds=now_seconds,
            last_growth_at_seconds=now_seconds,
        )
        self._settlements[site_id] = s
        return s

    def settlement(
        self, site_id: str,
    ) -> t.Optional[Settlement]:
        return self._settlements.get(site_id)

    def grow(
        self, *, site_id: str, new_pop: int,
        now_seconds: float = 0.0,
    ) -> t.Optional[StageChange]:
        s = self._settlements.get(site_id)
        if s is None or new_pop < 0:
            return None
        if s.stage == SettlementStage.ABANDONED:
            return None
        s.population = new_pop
        s.last_growth_at_seconds = now_seconds
        old_stage = s.stage
        if new_pop >= TOWN_POP:
            new_stage = SettlementStage.TOWN
        elif new_pop >= VILLAGE_POP:
            new_stage = SettlementStage.VILLAGE
        elif new_pop >= HAMLET_POP:
            new_stage = SettlementStage.HAMLET
        else:
            new_stage = SettlementStage.CAMP
        if new_stage == old_stage:
            return None
        s.stage = new_stage
        return StageChange(
            site_id=site_id, old_stage=old_stage,
            new_stage=new_stage, population=new_pop,
        )

    def abandon(
        self, *, site_id: str,
    ) -> bool:
        s = self._settlements.get(site_id)
        if s is None:
            return False
        if s.stage == SettlementStage.ABANDONED:
            return False
        s.stage = SettlementStage.ABANDONED
        return True

    def total_settlements(self) -> int:
        return len(self._settlements)

    def total_sites(self) -> int:
        return len(self._sites)


__all__ = [
    "WATER_WEIGHT", "DEFENSE_WEIGHT", "TRADE_WEIGHT",
    "ARABLE_WEIGHT", "THREAT_PENALTY",
    "MIN_CHARTER_SCORE",
    "HAMLET_POP", "VILLAGE_POP", "TOWN_POP",
    "SettlementStage", "SiteScore", "Settlement",
    "StageChange", "TownFoundingAI",
]
