"""Tests for player_farming."""
from __future__ import annotations

from server.player_farming import (
    PlayerFarmingSystem, Season, GrowthStage, Crop,
)


def _wheat():
    return Crop(
        crop_kind="wheat", days_to_germinate=2,
        days_to_grow=8,
        preferred_season=Season.SUMMER,
        tolerated_seasons=(
            Season.SPRING, Season.SUMMER,
        ),
        yield_units=10,
    )


def _rent(s, **overrides):
    args = dict(
        plot_id="bob_plot",
        owner_id="bob", zone_id="ronfaure",
        bed_capacity=4, soil_quality=8,
        rented_day=10,
    )
    args.update(overrides)
    return s.rent_plot(**args)


def test_register_crop():
    s = PlayerFarmingSystem()
    assert s.register_crop(crop=_wheat()) is True


def test_register_crop_invalid_season():
    s = PlayerFarmingSystem()
    bad = Crop(
        crop_kind="x", days_to_germinate=1,
        days_to_grow=1,
        preferred_season=Season.WINTER,
        tolerated_seasons=(Season.SUMMER,),
        yield_units=1,
    )
    assert s.register_crop(crop=bad) is False


def test_register_crop_dup():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    assert s.register_crop(crop=_wheat()) is False


def test_rent_happy():
    s = PlayerFarmingSystem()
    assert _rent(s) is True


def test_rent_invalid_soil():
    s = PlayerFarmingSystem()
    assert _rent(s, soil_quality=0) is False
    assert _rent(s, soil_quality=11) is False


def test_rent_dup_blocked():
    s = PlayerFarmingSystem()
    _rent(s)
    assert _rent(s) is False


def test_plant_happy():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    assert s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    ) is True


def test_plant_unknown_crop():
    s = PlayerFarmingSystem()
    _rent(s)
    assert s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="unknown", now_day=10,
    ) is False


def test_plant_out_of_range_bed():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s, bed_capacity=2)
    assert s.plant(
        plot_id="bob_plot", bed_index=5,
        crop_kind="wheat", now_day=10,
    ) is False


def test_plant_occupied_bed_blocked():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    assert s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=11,
    ) is False


def test_tick_planted_to_germinating():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    stage = s.tick_bed(
        plot_id="bob_plot", bed_index=0,
        now_day=11, current_season=Season.SUMMER,
    )
    assert stage == GrowthStage.GERMINATING


def test_tick_to_growing():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    s.tick_bed(
        plot_id="bob_plot", bed_index=0,
        now_day=13, current_season=Season.SUMMER,
    )
    b = s.bed(plot_id="bob_plot", bed_index=0)
    assert b.stage == GrowthStage.GROWING


def test_tick_to_harvestable():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    s.tick_bed(
        plot_id="bob_plot", bed_index=0,
        now_day=30, current_season=Season.SUMMER,
    )
    b = s.bed(plot_id="bob_plot", bed_index=0)
    assert b.stage == GrowthStage.HARVESTABLE


def test_tick_out_of_season_withers():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    stage = s.tick_bed(
        plot_id="bob_plot", bed_index=0,
        now_day=11, current_season=Season.WINTER,
    )
    assert stage == GrowthStage.WITHERED


def test_harvest_yields_units():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s, soil_quality=10)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    s.tick_bed(
        plot_id="bob_plot", bed_index=0,
        now_day=30, current_season=Season.SUMMER,
    )
    units = s.harvest(
        plot_id="bob_plot", bed_index=0,
        now_day=31,
    )
    # 10 yield * 10 soil / 10 = 10
    assert units == 10


def test_harvest_soil_scales_yield():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s, soil_quality=5)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    s.tick_bed(
        plot_id="bob_plot", bed_index=0,
        now_day=30, current_season=Season.SUMMER,
    )
    units = s.harvest(
        plot_id="bob_plot", bed_index=0,
        now_day=31,
    )
    # 10 * 5 / 10 = 5
    assert units == 5


def test_harvest_not_ready():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    units = s.harvest(
        plot_id="bob_plot", bed_index=0,
        now_day=11,
    )
    assert units == 0


def test_harvest_double_blocked():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    s.tick_bed(
        plot_id="bob_plot", bed_index=0,
        now_day=30, current_season=Season.SUMMER,
    )
    s.harvest(
        plot_id="bob_plot", bed_index=0, now_day=31,
    )
    assert s.harvest(
        plot_id="bob_plot", bed_index=0, now_day=32,
    ) == 0


def test_clear_after_harvest_allows_replant():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    s.tick_bed(
        plot_id="bob_plot", bed_index=0,
        now_day=30, current_season=Season.SUMMER,
    )
    s.harvest(
        plot_id="bob_plot", bed_index=0, now_day=31,
    )
    s.clear_bed(plot_id="bob_plot", bed_index=0)
    assert s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=32,
    ) is True


def test_clear_active_bed_blocked():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    assert s.clear_bed(
        plot_id="bob_plot", bed_index=0,
    ) is False


def test_replant_after_wither():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    s.tick_bed(
        plot_id="bob_plot", bed_index=0,
        now_day=11, current_season=Season.WINTER,
    )
    # Wither -> can replant
    assert s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=20,
    ) is True


def test_beds_in_plot():
    s = PlayerFarmingSystem()
    s.register_crop(crop=_wheat())
    _rent(s, bed_capacity=3)
    s.plant(
        plot_id="bob_plot", bed_index=0,
        crop_kind="wheat", now_day=10,
    )
    s.plant(
        plot_id="bob_plot", bed_index=1,
        crop_kind="wheat", now_day=10,
    )
    out = s.beds_in_plot(plot_id="bob_plot")
    assert len(out) == 2


def test_plot_unknown():
    s = PlayerFarmingSystem()
    assert s.plot(plot_id="ghost") is None


def test_bed_unknown():
    s = PlayerFarmingSystem()
    assert s.bed(
        plot_id="ghost", bed_index=0,
    ) is None


def test_crop_unknown():
    s = PlayerFarmingSystem()
    assert s.crop(crop_kind="ghost") is None


def test_enum_counts():
    assert len(list(Season)) == 4
    assert len(list(GrowthStage)) == 6
