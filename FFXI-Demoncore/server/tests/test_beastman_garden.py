"""Tests for the beastman garden."""
from __future__ import annotations

from server.beastman_garden import (
    BeastmanGarden,
    GrowthPhase,
    SeedKind,
    TendAction,
)


def test_open_plot():
    g = BeastmanGarden()
    assert g.open_plot(player_id="kraw", plot_index=0)


def test_open_plot_negative_index():
    g = BeastmanGarden()
    assert not g.open_plot(player_id="kraw", plot_index=-1)


def test_open_plot_double_blocked():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    assert not g.open_plot(player_id="kraw", plot_index=0)


def test_plant_basic():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    res = g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    assert res.accepted
    assert res.phase == GrowthPhase.SEEDED


def test_plant_no_plot():
    g = BeastmanGarden()
    res = g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    assert not res.accepted


def test_plant_already_growing():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    res = g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.GRAIN,
        now_seconds=10,
    )
    assert not res.accepted


def test_check_phases_progress():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    # GOURD = 7200 sec to harvest
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.GOURD,
        now_seconds=0,
    )
    # at start
    assert g.check(
        player_id="kraw", plot_index=0, now_seconds=0,
    ).phase == GrowthPhase.SEEDED
    # >1/3 elapsed (2400s) → SPROUT
    assert g.check(
        player_id="kraw", plot_index=0, now_seconds=3000,
    ).phase == GrowthPhase.SPROUT
    # >2/3 elapsed (4800s) → MATURE
    assert g.check(
        player_id="kraw", plot_index=0, now_seconds=5500,
    ).phase == GrowthPhase.MATURE
    # past harvest_at → HARVEST_READY
    assert g.check(
        player_id="kraw", plot_index=0, now_seconds=8000,
    ).phase == GrowthPhase.HARVEST_READY


def test_check_unknown_plot():
    g = BeastmanGarden()
    res = g.check(
        player_id="ghost", plot_index=0, now_seconds=0,
    )
    assert not res.accepted


def test_tend_water_shrinks_grow_time():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    res = g.tend(
        player_id="kraw", plot_index=0,
        action=TendAction.WATER,
        now_seconds=10,
    )
    assert res.accepted
    # base 1800 - 300 = 1500 - 10 elapsed
    assert res.seconds_until_harvest == 1490


def test_tend_fertilize_shrinks_more():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    res = g.tend(
        player_id="kraw", plot_index=0,
        action=TendAction.FERTILIZE,
        now_seconds=10,
    )
    assert res.seconds_until_harvest == 1190


def test_tend_no_plot():
    g = BeastmanGarden()
    res = g.tend(
        player_id="ghost", plot_index=0,
        action=TendAction.WATER,
        now_seconds=0,
    )
    assert not res.accepted


def test_tend_after_ready_blocked():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    g.check(
        player_id="kraw", plot_index=0, now_seconds=2000,
    )
    res = g.tend(
        player_id="kraw", plot_index=0,
        action=TendAction.WATER,
        now_seconds=2000,
    )
    assert not res.accepted


def test_tend_cap():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.GOURD,
        now_seconds=0,
    )
    for _ in range(3):
        g.tend(
            player_id="kraw", plot_index=0,
            action=TendAction.WATER,
            now_seconds=10,
        )
    res = g.tend(
        player_id="kraw", plot_index=0,
        action=TendAction.WATER,
        now_seconds=10,
    )
    assert not res.accepted


def test_harvest_ready():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    res = g.harvest(
        player_id="kraw", plot_index=0, now_seconds=2000,
    )
    assert res.accepted
    assert res.item_id == "shadow_herb_bundle"


def test_harvest_too_early():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    res = g.harvest(
        player_id="kraw", plot_index=0, now_seconds=10,
    )
    assert not res.accepted


def test_harvest_empty():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    res = g.harvest(
        player_id="kraw", plot_index=0, now_seconds=0,
    )
    assert not res.accepted


def test_harvest_clears_plot():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    g.harvest(
        player_id="kraw", plot_index=0, now_seconds=2000,
    )
    # Re-plant succeeds
    res = g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.GRAIN,
        now_seconds=2010,
    )
    assert res.accepted


def test_wilt_after_grace_period():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    # HERB = 1800s grow + 14400s grace = 16200s
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    res = g.check(
        player_id="kraw", plot_index=0, now_seconds=20_000,
    )
    assert res.phase == GrowthPhase.WILTED


def test_harvest_wilted_returns_compost():
    g = BeastmanGarden()
    g.open_plot(player_id="kraw", plot_index=0)
    g.plant(
        player_id="kraw", plot_index=0,
        seed=SeedKind.HERB,
        now_seconds=0,
    )
    res = g.harvest(
        player_id="kraw", plot_index=0, now_seconds=20_000,
    )
    assert res.accepted
    assert res.item_id == "fertilizer_compost"
