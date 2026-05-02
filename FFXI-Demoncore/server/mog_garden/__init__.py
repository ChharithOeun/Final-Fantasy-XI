"""Mog Garden — gardening pots with growth cycle.

Plant a seed in a pot. Stages:
    EMPTY -> PLANTED -> SPROUTING -> MATURE -> WITHERED

Each stage takes Vana'diel time to advance; watering accelerates
growth past the SPROUTING gate. MATURE pots can be harvested for
yields keyed to the seed type.

Public surface
--------------
    GrowthStage enum
    SeedSpec catalog
    GardenPot per-pot state
        .plant(seed_id, now_tick)
        .water(now_tick)
        .tick(now_tick) advances stage
        .harvest(rng_pool) -> tuple[item_id, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_ENCOUNTER_GEN


class GrowthStage(str, enum.Enum):
    EMPTY = "empty"
    PLANTED = "planted"
    SPROUTING = "sprouting"
    MATURE = "mature"
    WITHERED = "withered"


# Seconds it takes each stage to advance, base rate.
STAGE_DURATION_SECONDS: dict[GrowthStage, int] = {
    GrowthStage.PLANTED: 3 * 60 * 60,        # 3 hours
    GrowthStage.SPROUTING: 6 * 60 * 60,      # 6 hours
    GrowthStage.MATURE: 12 * 60 * 60,        # before withering
}

WATERING_BONUS_SECONDS = 30 * 60        # 30 min trim per water


@dataclasses.dataclass(frozen=True)
class YieldEntry:
    item_id: str
    weight: int


@dataclasses.dataclass(frozen=True)
class SeedSpec:
    seed_id: str
    label: str
    yields: tuple[YieldEntry, ...]
    yield_count_min: int = 1
    yield_count_max: int = 3


# Sample catalog
SEED_CATALOG: tuple[SeedSpec, ...] = (
    SeedSpec("herb_seeds", "Herb Seeds",
             yields=(
                 YieldEntry("dried_marjoram", weight=40),
                 YieldEntry("rosemary", weight=30),
                 YieldEntry("sage", weight=20),
                 YieldEntry("eastern_pansy_seeds", weight=10),
             )),
    SeedSpec("crystal_cluster", "Crystal Cluster",
             yields=(
                 YieldEntry("fire_crystal", weight=12),
                 YieldEntry("ice_crystal", weight=12),
                 YieldEntry("wind_crystal", weight=12),
                 YieldEntry("earth_crystal", weight=12),
                 YieldEntry("lightning_crystal", weight=12),
                 YieldEntry("water_crystal", weight=12),
                 YieldEntry("light_crystal", weight=14),
                 YieldEntry("dark_crystal", weight=14),
             ),
             yield_count_max=5),
    SeedSpec("tree_cuttings", "Tree Cuttings",
             yields=(
                 YieldEntry("oak_log", weight=40),
                 YieldEntry("walnut_log", weight=30),
                 YieldEntry("ebony_log", weight=20),
                 YieldEntry("rosewood_log", weight=10),
             )),
)

SEED_BY_ID: dict[str, SeedSpec] = {s.seed_id: s for s in SEED_CATALOG}


@dataclasses.dataclass
class GardenPot:
    pot_id: str
    owner_id: str
    stage: GrowthStage = GrowthStage.EMPTY
    seed_id: t.Optional[str] = None
    planted_at_tick: t.Optional[int] = None
    water_bonus_seconds: int = 0
    last_tick_seen: int = 0

    def plant(self, *, seed_id: str, now_tick: int) -> bool:
        if self.stage != GrowthStage.EMPTY:
            return False
        if seed_id not in SEED_BY_ID:
            return False
        self.stage = GrowthStage.PLANTED
        self.seed_id = seed_id
        self.planted_at_tick = now_tick
        self.last_tick_seen = now_tick
        self.water_bonus_seconds = 0
        return True

    def water(self, *, now_tick: int) -> bool:
        if self.stage in (GrowthStage.EMPTY, GrowthStage.WITHERED):
            return False
        # Apply water bonus once per "tick visit".
        self.water_bonus_seconds += WATERING_BONUS_SECONDS
        return True

    def tick(self, *, now_tick: int) -> GrowthStage:
        """Advance growth based on elapsed time."""
        if self.stage == GrowthStage.EMPTY:
            return self.stage
        if self.planted_at_tick is None:
            return self.stage
        elapsed = (now_tick - self.planted_at_tick) + \
            self.water_bonus_seconds
        if self.stage == GrowthStage.PLANTED:
            if elapsed >= STAGE_DURATION_SECONDS[GrowthStage.PLANTED]:
                self.stage = GrowthStage.SPROUTING
        if self.stage == GrowthStage.SPROUTING:
            if elapsed >= (
                STAGE_DURATION_SECONDS[GrowthStage.PLANTED]
                + STAGE_DURATION_SECONDS[GrowthStage.SPROUTING]
            ):
                self.stage = GrowthStage.MATURE
        if self.stage == GrowthStage.MATURE:
            wither_at = (
                STAGE_DURATION_SECONDS[GrowthStage.PLANTED]
                + STAGE_DURATION_SECONDS[GrowthStage.SPROUTING]
                + STAGE_DURATION_SECONDS[GrowthStage.MATURE]
            )
            if elapsed >= wither_at:
                self.stage = GrowthStage.WITHERED
        self.last_tick_seen = now_tick
        return self.stage

    def harvest(
        self, *, rng_pool: RngPool,
        stream_name: str = STREAM_ENCOUNTER_GEN,
    ) -> tuple[str, ...]:
        if self.stage != GrowthStage.MATURE:
            return ()
        if self.seed_id is None:
            return ()
        seed = SEED_BY_ID[self.seed_id]
        rng = rng_pool.stream(stream_name)
        count = rng.randint(seed.yield_count_min,
                             seed.yield_count_max)
        out: list[str] = []
        total_weight = sum(y.weight for y in seed.yields)
        for _ in range(count):
            roll = rng.uniform(0, total_weight)
            cum = 0.0
            for y in seed.yields:
                cum += y.weight
                if roll <= cum:
                    out.append(y.item_id)
                    break
        # After harvest, pot resets to EMPTY
        self.stage = GrowthStage.EMPTY
        self.seed_id = None
        self.planted_at_tick = None
        self.water_bonus_seconds = 0
        return tuple(out)


__all__ = [
    "GrowthStage", "STAGE_DURATION_SECONDS",
    "WATERING_BONUS_SECONDS",
    "YieldEntry", "SeedSpec",
    "SEED_CATALOG", "SEED_BY_ID",
    "GardenPot",
]
