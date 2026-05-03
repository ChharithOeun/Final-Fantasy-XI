"""Tests for the economy regulator (drop-rate balancer)."""
from __future__ import annotations

from server.economy_demand_signal import (
    DemandKind,
    EconomyDemandTracker,
)
from server.economy_regulator import (
    BoostLevel,
    CRITICAL_BOOST,
    EconomyRegulator,
    HEAVY_BOOST,
    LIGHT_BOOST,
)
from server.economy_supply_index import (
    EconomySupplyIndex,
    SupplySource,
)
from server.mat_essentiality_registry import (
    EssentialityTier,
    MatEssentialityRegistry,
    seed_default_essentials,
)


def _build_regulator() -> EconomyRegulator:
    supply = EconomySupplyIndex()
    demand = EconomyDemandTracker()
    essentiality = seed_default_essentials(MatEssentialityRegistry())
    return EconomyRegulator(
        supply=supply, demand=demand, essentiality=essentiality,
    )


def test_default_multiplier_is_one():
    reg = _build_regulator()
    assert reg.drop_rate_multiplier("iron_ore") == 1.0


def test_luxury_never_boosted_even_under_pressure():
    reg = _build_regulator()
    reg.essentiality.register(
        item_id="painting", tier=EssentialityTier.LUXURY,
    )
    # Hammer demand
    for _ in range(200):
        reg.demand.record(
            item_id="painting", kind=DemandKind.PURCHASE_AH,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=200.0)
    assert reg.drop_rate_multiplier("painting") == 1.0


def test_unregistered_never_boosted():
    reg = _build_regulator()
    for _ in range(200):
        reg.demand.record(
            item_id="ghost_item", kind=DemandKind.PURCHASE_AH,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=200.0)
    assert reg.drop_rate_multiplier("ghost_item") == 1.0


def test_essential_with_high_demand_low_supply_boosted():
    reg = _build_regulator()
    # Iron ore — very low supply, very high demand
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=10, now_seconds=0.0,
    )
    for _ in range(100):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=3700.0)
    mult = reg.drop_rate_multiplier("iron_ore")
    assert mult > 1.0


def test_well_supplied_essential_not_boosted():
    reg = _build_regulator()
    # Iron ore — huge supply, modest demand
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=10000, now_seconds=0.0,
    )
    for _ in range(5):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=3700.0)
    assert reg.drop_rate_multiplier("iron_ore") == 1.0


def test_supply_dropping_amplifies_score():
    """Same end-state supply, but one trending down should
    score higher than one stable."""
    reg = _build_regulator()
    # Falling: 1000 -> 100
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=1000, now_seconds=0.0,
    )
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=3600.0,
    )
    # Heavy demand
    for _ in range(50):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=3600.0,
        )
    decisions = reg.recompute(now_seconds=4000.0)
    iron = next(d for d in decisions if d.item_id == "iron_ore")
    assert iron.scarcity_score > 0


def test_demand_rising_amplifies_score():
    reg = _build_regulator()
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=200, now_seconds=0.0,
    )
    # Previous window: 5 events
    for i in range(5):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=float(i * 60),
        )
    # Current window: 50 events (10x growth)
    for i in range(50):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=float(3700 + i * 60),
        )
    reg.recompute(now_seconds=7200.0)
    mult = reg.drop_rate_multiplier("iron_ore")
    assert mult > 1.0


def test_critical_boost_reaches_3x():
    reg = _build_regulator()
    # Extreme scarcity
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=1, now_seconds=0.0,
    )
    for _ in range(500):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=3700.0)
    mult = reg.drop_rate_multiplier("iron_ore")
    assert mult == CRITICAL_BOOST


def test_light_boost_reaches_1_5x_for_modest_pressure():
    reg = _build_regulator()
    # Moderate scarcity — CRAFT_INPUT priority is 75
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=200, now_seconds=0.0,
    )
    # ~10/hr demand -> raw = 10 - 2 = 8 -> weighted = 6
    # Should hit LIGHT_BOOST (5..15)
    for _ in range(10):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=3700.0)
    mult = reg.drop_rate_multiplier("iron_ore")
    assert mult in (LIGHT_BOOST, HEAVY_BOOST)


def test_decisions_decay_when_scarcity_resolves():
    """Once supply rebuilds, the multiplier decays back toward 1.0."""
    reg = _build_regulator()
    # Crisis tick
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=1, now_seconds=0.0,
    )
    for _ in range(500):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=3700.0)
    crisis_mult = reg.drop_rate_multiplier("iron_ore")
    assert crisis_mult == CRITICAL_BOOST
    # Resolution: stockpile rebuilt, demand normalized
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=10000, now_seconds=8000.0,
    )
    # Run several ticks — multiplier should decay
    for tick_offset in range(15):
        reg.recompute(
            now_seconds=8000.0 + tick_offset * 100,
        )
    final_mult = reg.drop_rate_multiplier("iron_ore")
    assert final_mult < crisis_mult


def test_multiplier_snaps_up_immediately():
    """When a crisis appears, the multiplier hits max immediately
    (no slow ramp). Only the DOWN side decays."""
    reg = _build_regulator()
    # Cool start
    reg.recompute(now_seconds=0.0)
    assert reg.drop_rate_multiplier("iron_ore") == 1.0
    # Crisis hits
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=1, now_seconds=100.0,
    )
    for _ in range(500):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=200.0,
        )
    reg.recompute(now_seconds=3800.0)
    assert reg.drop_rate_multiplier("iron_ore") == CRITICAL_BOOST


def test_decisions_for_top_ranked_by_scarcity():
    reg = _build_regulator()
    # iron_ore: severe pressure
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=5, now_seconds=0.0,
    )
    for _ in range(200):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    # cotton: mild pressure
    reg.supply.publish(
        item_id="cotton_thread",
        source=SupplySource.PLAYER_INVENTORY,
        count=200, now_seconds=0.0,
    )
    for _ in range(15):
        reg.demand.record(
            item_id="cotton_thread", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=3700.0)
    top = reg.decisions_for_top(top_n=2)
    assert top[0].item_id == "iron_ore"


def test_boosted_items_lists_only_above_one():
    reg = _build_regulator()
    reg.supply.publish(
        item_id="iron_ore",
        source=SupplySource.PLAYER_INVENTORY,
        count=1, now_seconds=0.0,
    )
    for _ in range(500):
        reg.demand.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=3700.0)
    boosted = set(reg.boosted_items())
    assert "iron_ore" in boosted


def test_full_lifecycle_world_balances_itself():
    """The headline scenario: cure_potion supply collapses,
    regulator boosts drop rate, world refills, regulator backs off."""
    reg = _build_regulator()
    # Phase 1: healthy supply
    reg.supply.publish(
        item_id="cure_potion",
        source=SupplySource.PLAYER_INVENTORY,
        count=2000, now_seconds=0.0,
    )
    for _ in range(20):
        reg.demand.record(
            item_id="cure_potion",
            kind=DemandKind.USED_CONSUMABLE,
            now_seconds=100.0,
        )
    reg.recompute(now_seconds=3700.0)
    assert reg.drop_rate_multiplier("cure_potion") == 1.0
    # Phase 2: massive raid wipes pots; demand spikes too
    reg.supply.publish(
        item_id="cure_potion",
        source=SupplySource.PLAYER_INVENTORY,
        count=20, now_seconds=4000.0,
    )
    for _ in range(300):
        reg.demand.record(
            item_id="cure_potion",
            kind=DemandKind.USED_CONSUMABLE,
            now_seconds=4500.0,
        )
    reg.recompute(now_seconds=8000.0)
    crisis = reg.drop_rate_multiplier("cure_potion")
    assert crisis > 1.0
    # Phase 3: world responds — supply rebuilds, demand normalizes
    reg.supply.publish(
        item_id="cure_potion",
        source=SupplySource.PLAYER_INVENTORY,
        count=5000, now_seconds=14000.0,
    )
    for tick in range(20):
        reg.recompute(now_seconds=14000.0 + tick * 200)
    final = reg.drop_rate_multiplier("cure_potion")
    assert final < crisis
