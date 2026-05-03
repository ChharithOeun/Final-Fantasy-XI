"""Tests for mob migration."""
from __future__ import annotations

from server.mob_migration import (
    MigrationEvent,
    MigrationTrigger,
    MobMigrationRegistry,
)


def test_seed_then_query_population():
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="ronfaure", mob_kind="orc", headcount=40,
    )
    assert reg.population(
        zone_id="ronfaure", mob_kind="orc",
    ) == 40


def test_unknown_zone_population_zero():
    reg = MobMigrationRegistry()
    assert reg.population(
        zone_id="ghost", mob_kind="orc",
    ) == 0


def test_observe_then_plan_creates_migration():
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="ronfaure", mob_kind="orc", headcount=40,
    )
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.SEASONAL,
        mob_kind="orc",
        source_zone_id="ronfaure",
        destination_zone_id="lakeland",
        fraction_of_source=0.25,
    ))
    plans = reg.plan_for_tick()
    assert len(plans) == 1
    # 40 * 0.25 = 10
    assert plans[0].headcount_moved == 10


def test_apply_plan_moves_headcount():
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="ronfaure", mob_kind="orc", headcount=40,
    )
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.SEASONAL,
        mob_kind="orc",
        source_zone_id="ronfaure",
        destination_zone_id="lakeland",
        fraction_of_source=0.25,
    ))
    plan = reg.plan_for_tick()[0]
    assert reg.apply_plan(plan=plan)
    assert reg.population(
        zone_id="ronfaure", mob_kind="orc",
    ) == 30
    assert reg.population(
        zone_id="lakeland", mob_kind="orc",
    ) == 10


def test_fraction_clamped_to_max():
    reg = MobMigrationRegistry(max_migration_fraction=0.4)
    reg.seed_population(
        zone_id="src", mob_kind="goblin", headcount=100,
    )
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.PLAYER_PRESSURE,
        mob_kind="goblin",
        source_zone_id="src",
        destination_zone_id="dst",
        fraction_of_source=0.9,    # asks for too much
    ))
    plans = reg.plan_for_tick()
    # Capped at 0.4 -> 40
    assert plans[0].headcount_moved == 40


def test_empty_source_makes_no_plan():
    reg = MobMigrationRegistry()
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.SEASONAL,
        mob_kind="orc",
        source_zone_id="ronfaure",
        destination_zone_id="lakeland",
        fraction_of_source=0.5,
    ))
    plans = reg.plan_for_tick()
    assert plans == ()


def test_zero_headcount_makes_no_plan():
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="src", mob_kind="orc", headcount=0,
    )
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.CONQUEST,
        mob_kind="orc",
        source_zone_id="src",
        destination_zone_id="dst",
    ))
    plans = reg.plan_for_tick()
    assert plans == ()


def test_priority_ordering():
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="src", mob_kind="orc", headcount=100,
    )
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.SEASONAL,
        mob_kind="orc",
        source_zone_id="src", destination_zone_id="d1",
    ))
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.PLAYER_PRESSURE,
        mob_kind="orc",
        source_zone_id="src", destination_zone_id="d2",
    ))
    plans = reg.plan_for_tick()
    # PLAYER_PRESSURE should come first (lower priority number)
    assert plans[0].trigger == MigrationTrigger.PLAYER_PRESSURE
    assert plans[1].trigger == MigrationTrigger.SEASONAL


def test_plan_clears_pending_queue():
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="src", mob_kind="orc", headcount=40,
    )
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.SEASONAL,
        mob_kind="orc",
        source_zone_id="src", destination_zone_id="dst",
    ))
    assert reg.total_pending() == 1
    reg.plan_for_tick()
    assert reg.total_pending() == 0


def test_apply_unknown_source_returns_false():
    reg = MobMigrationRegistry()
    from server.mob_migration import MigrationPlan
    plan = MigrationPlan(
        trigger=MigrationTrigger.SEASONAL,
        mob_kind="orc",
        source_zone_id="ghost",
        destination_zone_id="dst",
        headcount_moved=5,
    )
    assert not reg.apply_plan(plan=plan)


def test_apply_overdraft_rejected():
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="src", mob_kind="orc", headcount=5,
    )
    from server.mob_migration import MigrationPlan
    plan = MigrationPlan(
        trigger=MigrationTrigger.SEASONAL,
        mob_kind="orc",
        source_zone_id="src",
        destination_zone_id="dst",
        headcount_moved=10,
    )
    assert not reg.apply_plan(plan=plan)


def test_total_zones_and_pending():
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="z1", mob_kind="orc", headcount=10,
    )
    reg.seed_population(
        zone_id="z2", mob_kind="orc", headcount=10,
    )
    reg.seed_population(
        zone_id="z2", mob_kind="goblin", headcount=10,
    )
    assert reg.total_zones() == 2
    assert reg.total_pending() == 0


def test_destination_population_starts_at_zero():
    """Migration to a zone that's never been seeded should
    initialize the dest population at zero before adding."""
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="src", mob_kind="orc", headcount=20,
    )
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.WEATHER_DRIVEN,
        mob_kind="orc",
        source_zone_id="src",
        destination_zone_id="virgin_zone",
    ))
    plan = reg.plan_for_tick()[0]
    assert reg.apply_plan(plan=plan)
    assert reg.population(
        zone_id="virgin_zone", mob_kind="orc",
    ) > 0


def test_multiple_concurrent_migrations():
    reg = MobMigrationRegistry()
    reg.seed_population(
        zone_id="ronfaure", mob_kind="orc", headcount=40,
    )
    reg.seed_population(
        zone_id="zulkheim", mob_kind="goblin", headcount=30,
    )
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.HARVEST_FOLLOW,
        mob_kind="orc",
        source_zone_id="ronfaure",
        destination_zone_id="ranguemont",
    ))
    reg.observe(event=MigrationEvent(
        trigger=MigrationTrigger.PREDATOR_PRESSURE,
        mob_kind="goblin",
        source_zone_id="zulkheim",
        destination_zone_id="kuftal",
    ))
    plans = reg.plan_for_tick()
    assert len(plans) == 2
