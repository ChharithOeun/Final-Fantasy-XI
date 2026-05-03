"""Tests for harvest competitor AI."""
from __future__ import annotations

from server.harvest_competitor_ai import (
    HarvestCompetitorRegistry,
    HarvestNode,
    NPCHarvester,
    NodeKind,
    NodeStatus,
)


def _basic_node(
    node_id: str = "copper_vein",
    capacity_max: int = 100,
    capacity_current: int = 100,
) -> HarvestNode:
    return HarvestNode(
        node_id=node_id, kind=NodeKind.MINING,
        item_id="copper_ore", zone_id="palborough_mines",
        capacity_max=capacity_max,
        capacity_current=capacity_current,
        regen_rate_per_hour=10.0,
    )


def test_register_node():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node())
    assert reg.node_for("copper_vein") is not None
    assert reg.total_nodes() == 1


def test_node_status_healthy_strained_depleted():
    node = _basic_node()
    assert node.status() == NodeStatus.HEALTHY
    node.capacity_current = 30
    assert node.status() == NodeStatus.STRAINED
    node.capacity_current = 0
    assert node.status() == NodeStatus.DEPLETED


def test_player_harvest_decrements_capacity():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node())
    res = reg.player_harvest(
        player_id="alice", node_id="copper_vein",
        units=10, now_seconds=0.0,
    )
    assert res.accepted
    assert res.units == 10
    assert res.new_capacity == 90


def test_player_harvest_zero_or_negative_rejected():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node())
    res = reg.player_harvest(
        player_id="alice", node_id="copper_vein",
        units=0, now_seconds=0.0,
    )
    assert not res.accepted


def test_player_harvest_unknown_node_rejected():
    reg = HarvestCompetitorRegistry()
    res = reg.player_harvest(
        player_id="alice", node_id="ghost", units=1,
    )
    assert not res.accepted


def test_player_harvest_caps_at_capacity():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node(capacity_current=5))
    res = reg.player_harvest(
        player_id="alice", node_id="copper_vein",
        units=20, now_seconds=0.0,
    )
    assert res.units == 5
    assert res.new_capacity == 0


def test_player_harvest_depleted_rejected():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node(capacity_current=0))
    res = reg.player_harvest(
        player_id="alice", node_id="copper_vein",
        units=1,
    )
    assert not res.accepted


def test_add_npc_harvester():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node())
    ok = reg.add_npc_harvester(
        node_id="copper_vein",
        harvester=NPCHarvester(npc_id="quadav_1", units_per_hour=2),
    )
    assert ok
    assert reg.npc_harvester_count("copper_vein") == 1


def test_add_npc_harvester_unknown_node_rejected():
    reg = HarvestCompetitorRegistry()
    ok = reg.add_npc_harvester(
        node_id="ghost",
        harvester=NPCHarvester(npc_id="x", units_per_hour=1),
    )
    assert not ok


def test_tick_regenerates_capacity():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node(capacity_current=50))
    counters = reg.tick(now_seconds=3600.0)   # 1 hour
    # 10/hr regen * 1hr = 10
    assert counters["regenerated"] == 10
    assert reg.node_for("copper_vein").capacity_current == 60


def test_tick_caps_regen_at_max():
    reg = HarvestCompetitorRegistry()
    reg.register_node(
        _basic_node(capacity_max=100, capacity_current=95),
    )
    reg.tick(now_seconds=3600.0)
    assert reg.node_for("copper_vein").capacity_current == 100


def test_tick_npcs_extract():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node(capacity_current=100))
    reg.add_npc_harvester(
        node_id="copper_vein",
        harvester=NPCHarvester(npc_id="quadav_1", units_per_hour=15),
    )
    counters = reg.tick(now_seconds=3600.0)
    assert counters["npc_extracted"] >= 5
    # capacity = 100 + 10 (regen) - 15 (npc) = 95
    assert reg.node_for("copper_vein").capacity_current <= 95


def test_tick_npcs_can_deplete():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node(capacity_current=10))
    reg.add_npc_harvester(
        node_id="copper_vein",
        harvester=NPCHarvester(
            npc_id="quadav_1", units_per_hour=200,
        ),
    )
    reg.tick(now_seconds=3600.0)
    node = reg.node_for("copper_vein")
    assert node.status() == NodeStatus.DEPLETED


def test_output_for_tracks_lifetime():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node())
    reg.player_harvest(
        player_id="alice", node_id="copper_vein", units=5,
    )
    reg.player_harvest(
        player_id="alice", node_id="copper_vein", units=3,
    )
    assert reg.output_for("copper_vein") == 8


def test_events_logged_on_each_action():
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node())
    reg.player_harvest(
        player_id="alice", node_id="copper_vein", units=5,
    )
    events = reg.events_at_node("copper_vein")
    assert len(events) == 1
    assert events[0].actor_id == "alice"
    assert events[0].units == 5


def test_full_lifecycle_competition_for_node():
    """A copper vein in Palborough Mines: 2 Quadav harvesters
    work it. Player jumps in. After several hours, output is
    distributed across all three actors."""
    reg = HarvestCompetitorRegistry()
    reg.register_node(_basic_node(capacity_current=100))
    reg.add_npc_harvester(
        node_id="copper_vein",
        harvester=NPCHarvester(npc_id="quadav_1", units_per_hour=8),
    )
    reg.add_npc_harvester(
        node_id="copper_vein",
        harvester=NPCHarvester(npc_id="quadav_2", units_per_hour=6),
    )
    # Player gets 10 units before NPCs tick
    reg.player_harvest(
        player_id="alice", node_id="copper_vein",
        units=10, now_seconds=0.0,
    )
    # NPCs tick for 2 hours
    counters = reg.tick(now_seconds=7200.0)
    assert counters["npc_extracted"] > 0
    events = reg.events_at_node("copper_vein")
    actor_ids = {e.actor_id for e in events}
    assert "alice" in actor_ids
    assert "quadav_1" in actor_ids
    assert "quadav_2" in actor_ids
    # Total output spans both player + NPCs
    assert reg.output_for("copper_vein") >= 10
