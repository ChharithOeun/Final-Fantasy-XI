"""Player farming — real farm plots with seasons.

Mog Garden is one pot per Mog House. Players who want
to actually farm at scale rent FARM PLOTS in the
countryside. Plots have soil quality, multi-bed
capacity, and are subject to SEASONS. A seed planted
in the wrong season germinates poorly or not at all.

Plot lifecycle per crop:
    PLANTED -> GERMINATING -> GROWING -> HARVESTABLE
    Failures: WITHERED (weather damage / neglect)

Seasons: SPRING / SUMMER / AUTUMN / WINTER.
The caller passes the current season at each tick;
each crop has a preferred season and tolerance set.

Public surface
--------------
    Season enum
    GrowthStage enum
    Crop dataclass (frozen)
    Bed dataclass (frozen)
    Plot dataclass (frozen)
    PlayerFarmingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Season(str, enum.Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class GrowthStage(str, enum.Enum):
    PLANTED = "planted"
    GERMINATING = "germinating"
    GROWING = "growing"
    HARVESTABLE = "harvestable"
    WITHERED = "withered"
    HARVESTED = "harvested"


@dataclasses.dataclass(frozen=True)
class Crop:
    crop_kind: str
    days_to_germinate: int
    days_to_grow: int
    preferred_season: Season
    tolerated_seasons: tuple[Season, ...]
    yield_units: int


@dataclasses.dataclass(frozen=True)
class Bed:
    plot_id: str
    bed_index: int
    crop_kind: str
    planted_day: int
    last_tick_day: int
    stage: GrowthStage
    days_in_stage: int


@dataclasses.dataclass(frozen=True)
class Plot:
    plot_id: str
    owner_id: str
    zone_id: str
    bed_capacity: int
    soil_quality: int  # 1..10
    rented_day: int
    upkeep_due_day: int


@dataclasses.dataclass
class PlayerFarmingSystem:
    _plots: dict[str, Plot] = dataclasses.field(
        default_factory=dict,
    )
    _beds: dict[tuple[str, int], Bed] = (
        dataclasses.field(default_factory=dict)
    )
    _crops: dict[str, Crop] = dataclasses.field(
        default_factory=dict,
    )

    def register_crop(
        self, *, crop: Crop,
    ) -> bool:
        if not crop.crop_kind:
            return False
        if (crop.days_to_germinate <= 0
                or crop.days_to_grow <= 0):
            return False
        if crop.yield_units <= 0:
            return False
        if (crop.preferred_season
                not in crop.tolerated_seasons):
            return False
        if crop.crop_kind in self._crops:
            return False
        self._crops[crop.crop_kind] = crop
        return True

    def rent_plot(
        self, *, plot_id: str, owner_id: str,
        zone_id: str, bed_capacity: int,
        soil_quality: int, rented_day: int,
        upkeep_interval_days: int = 30,
    ) -> bool:
        if not plot_id or not owner_id:
            return False
        if not zone_id:
            return False
        if bed_capacity <= 0:
            return False
        if not 1 <= soil_quality <= 10:
            return False
        if rented_day < 0:
            return False
        if upkeep_interval_days <= 0:
            return False
        if plot_id in self._plots:
            return False
        self._plots[plot_id] = Plot(
            plot_id=plot_id, owner_id=owner_id,
            zone_id=zone_id,
            bed_capacity=bed_capacity,
            soil_quality=soil_quality,
            rented_day=rented_day,
            upkeep_due_day=(
                rented_day + upkeep_interval_days
            ),
        )
        return True

    def plant(
        self, *, plot_id: str, bed_index: int,
        crop_kind: str, now_day: int,
    ) -> bool:
        if plot_id not in self._plots:
            return False
        if crop_kind not in self._crops:
            return False
        if now_day < 0:
            return False
        p = self._plots[plot_id]
        if not 0 <= bed_index < p.bed_capacity:
            return False
        key = (plot_id, bed_index)
        if key in self._beds:
            existing = self._beds[key]
            if existing.stage not in (
                GrowthStage.WITHERED,
                GrowthStage.HARVESTED,
            ):
                return False
        self._beds[key] = Bed(
            plot_id=plot_id, bed_index=bed_index,
            crop_kind=crop_kind,
            planted_day=now_day,
            last_tick_day=now_day,
            stage=GrowthStage.PLANTED,
            days_in_stage=0,
        )
        return True

    def tick_bed(
        self, *, plot_id: str, bed_index: int,
        now_day: int, current_season: Season,
    ) -> t.Optional[GrowthStage]:
        key = (plot_id, bed_index)
        if key not in self._beds:
            return None
        b = self._beds[key]
        if b.stage in (
            GrowthStage.HARVESTABLE,
            GrowthStage.WITHERED,
            GrowthStage.HARVESTED,
        ):
            return b.stage
        if now_day <= b.last_tick_day:
            return b.stage
        crop = self._crops[b.crop_kind]
        # Out-of-season -> wither risk
        if current_season not in (
            crop.tolerated_seasons
        ):
            self._beds[key] = dataclasses.replace(
                b, stage=GrowthStage.WITHERED,
                last_tick_day=now_day,
            )
            return GrowthStage.WITHERED
        elapsed = now_day - b.last_tick_day
        new_days_in_stage = b.days_in_stage + elapsed
        new_stage = b.stage
        if (b.stage == GrowthStage.PLANTED
                and new_days_in_stage >= 1):
            new_stage = GrowthStage.GERMINATING
        if (new_stage == GrowthStage.GERMINATING
                and new_days_in_stage
                >= crop.days_to_germinate):
            new_stage = GrowthStage.GROWING
            new_days_in_stage = (
                new_days_in_stage
                - crop.days_to_germinate
            )
        if (new_stage == GrowthStage.GROWING
                and new_days_in_stage
                >= crop.days_to_grow):
            new_stage = GrowthStage.HARVESTABLE
        self._beds[key] = dataclasses.replace(
            b, stage=new_stage,
            last_tick_day=now_day,
            days_in_stage=new_days_in_stage,
        )
        return new_stage

    def harvest(
        self, *, plot_id: str, bed_index: int,
        now_day: int,
    ) -> int:
        key = (plot_id, bed_index)
        if key not in self._beds:
            return 0
        b = self._beds[key]
        if b.stage != GrowthStage.HARVESTABLE:
            return 0
        if plot_id not in self._plots:
            return 0
        p = self._plots[plot_id]
        crop = self._crops[b.crop_kind]
        # Soil quality 1..10 scales yield by
        # soil_quality * yield / 10
        units = crop.yield_units * p.soil_quality // 10
        if units <= 0:
            units = 1
        self._beds[key] = dataclasses.replace(
            b, stage=GrowthStage.HARVESTED,
            last_tick_day=now_day,
        )
        return units

    def clear_bed(
        self, *, plot_id: str, bed_index: int,
    ) -> bool:
        key = (plot_id, bed_index)
        if key not in self._beds:
            return False
        b = self._beds[key]
        if b.stage not in (
            GrowthStage.WITHERED,
            GrowthStage.HARVESTED,
        ):
            return False
        del self._beds[key]
        return True

    def bed(
        self, *, plot_id: str, bed_index: int,
    ) -> t.Optional[Bed]:
        return self._beds.get(
            (plot_id, bed_index),
        )

    def plot(
        self, *, plot_id: str,
    ) -> t.Optional[Plot]:
        return self._plots.get(plot_id)

    def beds_in_plot(
        self, *, plot_id: str,
    ) -> list[Bed]:
        return [
            b for k, b in self._beds.items()
            if k[0] == plot_id
        ]

    def crop(
        self, *, crop_kind: str,
    ) -> t.Optional[Crop]:
        return self._crops.get(crop_kind)


__all__ = [
    "Season", "GrowthStage", "Crop", "Bed",
    "Plot", "PlayerFarmingSystem",
]
