"""Tests for lottery NM trigger registry."""
from __future__ import annotations

from server.lottery_nm_triggers import (
    LotteryNMRegistry,
    TriggerOutcome,
    TriggerRecipe,
)


def _basic_recipe() -> TriggerRecipe:
    return TriggerRecipe(
        nm_id="naelos",
        zone_id="mhaura_altar",
        required_item_id="black_coral_scale",
        placement_position=(50, 50),
        tolerance_tiles=3,
        required_item_count=1,
        spawn_cooldown_seconds=60 * 60,  # 1 hour
    )


def test_register_and_lookup():
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    assert reg.recipe_for("naelos") is not None
    assert reg.total_recipes() == 1


def test_recipes_for_zone_filters():
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    reg.register_recipe(TriggerRecipe(
        nm_id="other_nm", zone_id="ronfaure_glade",
        required_item_id="lost_locket",
        placement_position=(10, 10),
    ))
    in_mhaura = reg.recipes_for_zone("mhaura_altar")
    assert len(in_mhaura) == 1
    assert in_mhaura[0].nm_id == "naelos"


def test_no_recipe_for_zone():
    reg = LotteryNMRegistry()
    res = reg.place_trigger(
        player_id="alice", zone_id="empty_zone",
        item_id="anything", item_count=1, position=(0, 0),
        now_seconds=0.0, hour=12,
    )
    assert res.outcome == TriggerOutcome.NO_RECIPE


def test_wrong_item_no_recipe():
    """No recipe in zone takes that item -> NO_RECIPE."""
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    res = reg.place_trigger(
        player_id="alice", zone_id="mhaura_altar",
        item_id="apple", item_count=1, position=(50, 50),
        now_seconds=0.0, hour=12,
    )
    assert res.outcome == TriggerOutcome.NO_RECIPE


def test_insufficient_items_rejected():
    reg = LotteryNMRegistry()
    reg.register_recipe(TriggerRecipe(
        nm_id="big_naelos", zone_id="mhaura_altar",
        required_item_id="black_coral_scale",
        placement_position=(50, 50),
        required_item_count=3,
    ))
    res = reg.place_trigger(
        player_id="alice", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=2,
        position=(50, 50), now_seconds=0.0, hour=12,
    )
    assert res.outcome == TriggerOutcome.INSUFFICIENT_ITEMS


def test_wrong_position_rejected():
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    res = reg.place_trigger(
        player_id="alice", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(100, 100), now_seconds=0.0, hour=12,
    )
    assert res.outcome == TriggerOutcome.WRONG_POSITION


def test_within_tolerance_accepted():
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    res = reg.place_trigger(
        player_id="alice", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        # 2 tiles away, within tolerance of 3
        position=(52, 50), now_seconds=0.0, hour=12,
    )
    assert res.outcome == TriggerOutcome.SPAWNED


def test_time_window_rejected_outside():
    reg = LotteryNMRegistry()
    reg.register_recipe(TriggerRecipe(
        nm_id="midnight_nm", zone_id="graveyard",
        required_item_id="bone_meal",
        placement_position=(0, 0),
        required_hour_start=0, required_hour_end=6,
    ))
    res = reg.place_trigger(
        player_id="alice", zone_id="graveyard",
        item_id="bone_meal", item_count=1,
        position=(0, 0), now_seconds=0.0, hour=14,
    )
    assert res.outcome == TriggerOutcome.WRONG_TIME


def test_time_window_accepted_inside():
    reg = LotteryNMRegistry()
    reg.register_recipe(TriggerRecipe(
        nm_id="midnight_nm", zone_id="graveyard",
        required_item_id="bone_meal",
        placement_position=(0, 0),
        required_hour_start=0, required_hour_end=6,
    ))
    res = reg.place_trigger(
        player_id="alice", zone_id="graveyard",
        item_id="bone_meal", item_count=1,
        position=(0, 0), now_seconds=0.0, hour=3,
    )
    assert res.outcome == TriggerOutcome.SPAWNED


def test_time_window_wraps_midnight():
    """Window 22..2 covers 22, 23, 0, 1."""
    reg = LotteryNMRegistry()
    reg.register_recipe(TriggerRecipe(
        nm_id="late_nm", zone_id="graveyard",
        required_item_id="bone_meal",
        placement_position=(0, 0),
        required_hour_start=22, required_hour_end=2,
    ))
    inside = reg.place_trigger(
        player_id="alice", zone_id="graveyard",
        item_id="bone_meal", item_count=1,
        position=(0, 0), now_seconds=0.0, hour=23,
    )
    assert inside.outcome == TriggerOutcome.SPAWNED
    reg.reset_cooldown("late_nm")
    inside_morning = reg.place_trigger(
        player_id="alice", zone_id="graveyard",
        item_id="bone_meal", item_count=1,
        position=(0, 0), now_seconds=100.0, hour=1,
    )
    assert inside_morning.outcome == TriggerOutcome.SPAWNED
    reg.reset_cooldown("late_nm")
    outside = reg.place_trigger(
        player_id="alice", zone_id="graveyard",
        item_id="bone_meal", item_count=1,
        position=(0, 0), now_seconds=200.0, hour=14,
    )
    assert outside.outcome == TriggerOutcome.WRONG_TIME


def test_cooldown_blocks_repeat():
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    first = reg.place_trigger(
        player_id="alice", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50), now_seconds=0.0, hour=12,
    )
    assert first.outcome == TriggerOutcome.SPAWNED
    second = reg.place_trigger(
        player_id="bob", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50), now_seconds=100.0, hour=12,
    )
    assert second.outcome == TriggerOutcome.ON_COOLDOWN


def test_cooldown_clears_after_window():
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    reg.place_trigger(
        player_id="alice", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50), now_seconds=0.0, hour=12,
    )
    later = reg.place_trigger(
        player_id="bob", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50),
        now_seconds=60 * 60 + 1, hour=12,
    )
    assert later.outcome == TriggerOutcome.SPAWNED


def test_reset_cooldown():
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    reg.place_trigger(
        player_id="alice", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50), now_seconds=0.0, hour=12,
    )
    assert reg.reset_cooldown("naelos")
    after = reg.place_trigger(
        player_id="bob", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50), now_seconds=10.0, hour=12,
    )
    assert after.outcome == TriggerOutcome.SPAWNED


def test_last_spawn_for_records_timestamp():
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    reg.place_trigger(
        player_id="alice", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50), now_seconds=300.0, hour=12,
    )
    assert reg.last_spawn_for("naelos") == 300.0


def test_consumed_items_returned():
    reg = LotteryNMRegistry()
    reg.register_recipe(TriggerRecipe(
        nm_id="big_nm", zone_id="altar",
        required_item_id="bone", required_item_count=3,
        placement_position=(0, 0),
    ))
    res = reg.place_trigger(
        player_id="alice", zone_id="altar",
        item_id="bone", item_count=5, position=(0, 0),
        now_seconds=0.0, hour=12,
    )
    assert res.outcome == TriggerOutcome.SPAWNED
    assert res.consumed_items == 3


def test_full_lifecycle_naelos_spawn_then_cooldown():
    reg = LotteryNMRegistry()
    reg.register_recipe(_basic_recipe())
    # Alice spawns it
    res = reg.place_trigger(
        player_id="alice", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50), now_seconds=0.0, hour=12,
    )
    assert res.outcome == TriggerOutcome.SPAWNED
    # Bob tries 30 min later — cooldown
    res2 = reg.place_trigger(
        player_id="bob", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50), now_seconds=1800.0, hour=12,
    )
    assert res2.outcome == TriggerOutcome.ON_COOLDOWN
    # Charlie waits past the window
    res3 = reg.place_trigger(
        player_id="charlie", zone_id="mhaura_altar",
        item_id="black_coral_scale", item_count=1,
        position=(50, 50), now_seconds=4000.0, hour=12,
    )
    assert res3.outcome == TriggerOutcome.SPAWNED
