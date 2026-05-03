"""Tests for resource depletion."""
from __future__ import annotations

from server.resource_depletion import (
    NodeKind,
    NodeStatus,
    ResourceDepletionRegistry,
)


def test_register_node_creates_state():
    reg = ResourceDepletionRegistry()
    node = reg.register_node(
        zone_id="gusgen", node_id="vein_a",
        kind=NodeKind.MINING, capacity=100,
        recovery_per_second=1.0,
    )
    assert node is not None
    assert node.current_supply == 100
    assert node.status == NodeStatus.HEALTHY


def test_double_register_rejected():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="gusgen", node_id="vein_a",
        kind=NodeKind.MINING, capacity=100,
        recovery_per_second=1.0,
    )
    second = reg.register_node(
        zone_id="gusgen", node_id="vein_a",
        kind=NodeKind.MINING, capacity=100,
        recovery_per_second=1.0,
    )
    assert second is None


def test_invalid_capacity_rejected():
    reg = ResourceDepletionRegistry()
    assert reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.LOGGING,
        capacity=0, recovery_per_second=1.0,
    ) is None


def test_harvest_draws_supply():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="gusgen", node_id="vein_a",
        kind=NodeKind.MINING, capacity=100,
        recovery_per_second=1.0,
    )
    res = reg.harvest(
        zone_id="gusgen", node_id="vein_a", amount=10,
    )
    assert res.accepted
    assert res.yielded == 10
    assert res.remaining == 90


def test_harvest_partial_when_low():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.MINING,
        capacity=10, recovery_per_second=0.0,
    )
    reg.harvest(zone_id="z", node_id="n", amount=8)
    res = reg.harvest(zone_id="z", node_id="n", amount=10)
    # only 2 left, partial yield
    assert res.accepted
    assert res.yielded == 2


def test_harvest_unknown_node():
    reg = ResourceDepletionRegistry()
    res = reg.harvest(
        zone_id="ghost", node_id="x", amount=1,
    )
    assert not res.accepted


def test_harvest_zero_amount_rejected():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.MINING,
        capacity=100, recovery_per_second=0.0,
    )
    res = reg.harvest(
        zone_id="z", node_id="n", amount=0,
    )
    assert not res.accepted


def test_critical_drop_marks_damaged():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.LOGGING,
        capacity=100, recovery_per_second=2.0,
    )
    # Drain to 5% capacity (5 < 10 critical)
    reg.harvest(zone_id="z", node_id="n", amount=95)
    state = reg.state(zone_id="z", node_id="n")
    assert state.status == NodeStatus.DAMAGED


def test_damaged_node_reduces_capacity_and_recovery():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.LOGGING,
        capacity=100, recovery_per_second=2.0,
    )
    reg.harvest(zone_id="z", node_id="n", amount=95)
    state = reg.state(zone_id="z", node_id="n")
    # Capacity halved to 70 (0.7 default penalty)
    assert state.capacity == 70
    # Recovery halved
    assert state.recovery_per_second == 1.0


def test_drain_damaged_to_zero_kills_permanently():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.LOGGING,
        capacity=100, recovery_per_second=2.0,
    )
    # Drain to damaged
    reg.harvest(zone_id="z", node_id="n", amount=95)
    state = reg.state(zone_id="z", node_id="n")
    # Now drain damaged supply to 0
    reg.harvest(
        zone_id="z", node_id="n",
        amount=state.current_supply,
    )
    state = reg.state(zone_id="z", node_id="n")
    assert state.status == NodeStatus.EXHAUSTED
    assert reg.is_exhausted(zone_id="z", node_id="n")


def test_exhausted_node_rejects_harvest():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.LOGGING,
        capacity=100, recovery_per_second=2.0,
    )
    reg.harvest(zone_id="z", node_id="n", amount=95)
    state = reg.state(zone_id="z", node_id="n")
    reg.harvest(
        zone_id="z", node_id="n",
        amount=state.current_supply,
    )
    res = reg.harvest(
        zone_id="z", node_id="n", amount=1,
    )
    assert not res.accepted
    assert res.new_status == NodeStatus.EXHAUSTED


def test_tick_recovers_supply():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.MINING,
        capacity=100, recovery_per_second=2.0,
    )
    reg.harvest(zone_id="z", node_id="n", amount=50)
    affected = reg.tick(elapsed_seconds=10.0)
    assert affected == 1
    assert reg.state(
        zone_id="z", node_id="n",
    ).current_supply == 70


def test_tick_caps_at_capacity():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.MINING,
        capacity=100, recovery_per_second=10.0,
    )
    reg.harvest(zone_id="z", node_id="n", amount=10)
    reg.tick(elapsed_seconds=100.0)
    assert reg.state(
        zone_id="z", node_id="n",
    ).current_supply == 100


def test_tick_skips_exhausted():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.LOGGING,
        capacity=100, recovery_per_second=2.0,
    )
    reg.harvest(zone_id="z", node_id="n", amount=95)
    state = reg.state(zone_id="z", node_id="n")
    reg.harvest(
        zone_id="z", node_id="n",
        amount=state.current_supply,
    )
    reg.tick(elapsed_seconds=1000.0)
    assert reg.state(
        zone_id="z", node_id="n",
    ).status == NodeStatus.EXHAUSTED
    assert reg.state(
        zone_id="z", node_id="n",
    ).current_supply == 0


def test_total_nodes_count():
    reg = ResourceDepletionRegistry()
    reg.register_node(
        zone_id="z1", node_id="a", kind=NodeKind.MINING,
        capacity=100, recovery_per_second=1.0,
    )
    reg.register_node(
        zone_id="z2", node_id="b", kind=NodeKind.MINING,
        capacity=100, recovery_per_second=1.0,
    )
    assert reg.total_nodes() == 2


def test_starting_supply_clamped():
    reg = ResourceDepletionRegistry()
    node = reg.register_node(
        zone_id="z", node_id="n", kind=NodeKind.MINING,
        capacity=100, recovery_per_second=1.0,
        starting_supply=200,
    )
    assert node.current_supply == 100
    node2 = reg.register_node(
        zone_id="z", node_id="n2", kind=NodeKind.MINING,
        capacity=100, recovery_per_second=1.0,
        starting_supply=-5,
    )
    assert node2.current_supply == 0
