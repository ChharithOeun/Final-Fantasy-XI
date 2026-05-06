"""Tests for multimodal travel planner."""
from __future__ import annotations

from server.multimodal_travel_planner import (
    MultimodalTravelPlanner,
    TravelMode,
)


def test_add_leg_happy():
    p = MultimodalTravelPlanner()
    assert p.add_leg(
        from_node="bastok", to_node="north_gustaberg",
        mode=TravelMode.WALK, cost_seconds=120,
    ) is True


def test_add_leg_blank_from():
    p = MultimodalTravelPlanner()
    assert p.add_leg(
        from_node="", to_node="x",
        mode=TravelMode.WALK, cost_seconds=10,
    ) is False


def test_add_leg_self_loop_blocked():
    p = MultimodalTravelPlanner()
    assert p.add_leg(
        from_node="bastok", to_node="bastok",
        mode=TravelMode.WALK, cost_seconds=10,
    ) is False


def test_add_leg_negative_cost():
    p = MultimodalTravelPlanner()
    assert p.add_leg(
        from_node="a", to_node="b",
        mode=TravelMode.WALK, cost_seconds=-5,
    ) is False


def test_plan_same_node():
    p = MultimodalTravelPlanner()
    r = p.plan(start_node="bastok", end_node="bastok")
    assert r is not None
    assert r.legs == ()
    assert r.total_cost_seconds == 0


def test_plan_simple_one_hop():
    p = MultimodalTravelPlanner()
    p.add_leg(
        from_node="bastok", to_node="korroloka",
        mode=TravelMode.WALK, cost_seconds=300,
    )
    r = p.plan(start_node="bastok", end_node="korroloka")
    assert r is not None
    assert len(r.legs) == 1
    assert r.total_cost_seconds == 300


def test_plan_picks_cheapest():
    p = MultimodalTravelPlanner()
    # walking: 600
    p.add_leg(
        from_node="bastok", to_node="jeuno",
        mode=TravelMode.WALK, cost_seconds=600,
    )
    # airship: 120
    p.add_leg(
        from_node="bastok", to_node="jeuno",
        mode=TravelMode.AIRSHIP, cost_seconds=120,
    )
    r = p.plan(start_node="bastok", end_node="jeuno")
    assert r.total_cost_seconds == 120
    assert TravelMode.AIRSHIP in r.modes_used


def test_plan_multi_hop():
    p = MultimodalTravelPlanner()
    p.add_leg(
        from_node="bastok", to_node="harbor",
        mode=TravelMode.WALK, cost_seconds=60,
    )
    p.add_leg(
        from_node="harbor", to_node="norg",
        mode=TravelMode.SHIP, cost_seconds=600,
    )
    p.add_leg(
        from_node="norg", to_node="sub_bay",
        mode=TravelMode.SUBMARINE, cost_seconds=300,
    )
    r = p.plan(start_node="bastok", end_node="sub_bay")
    assert r is not None
    assert len(r.legs) == 3
    assert r.total_cost_seconds == 60 + 600 + 300
    assert TravelMode.SHIP in r.modes_used
    assert TravelMode.SUBMARINE in r.modes_used


def test_plan_unreachable():
    p = MultimodalTravelPlanner()
    p.add_leg(
        from_node="bastok", to_node="harbor",
        mode=TravelMode.WALK, cost_seconds=60,
    )
    r = p.plan(start_node="bastok", end_node="ghost")
    assert r is None


def test_plan_allowed_modes_filter():
    p = MultimodalTravelPlanner()
    p.add_leg(
        from_node="bastok", to_node="jeuno",
        mode=TravelMode.WALK, cost_seconds=600,
    )
    p.add_leg(
        from_node="bastok", to_node="jeuno",
        mode=TravelMode.AIRSHIP, cost_seconds=120,
    )
    r = p.plan(
        start_node="bastok", end_node="jeuno",
        allowed_modes={TravelMode.WALK},
    )
    assert r is not None
    assert r.total_cost_seconds == 600
    assert TravelMode.AIRSHIP not in r.modes_used


def test_plan_filter_blocks_path():
    p = MultimodalTravelPlanner()
    p.add_leg(
        from_node="bastok", to_node="jeuno",
        mode=TravelMode.AIRSHIP, cost_seconds=120,
    )
    r = p.plan(
        start_node="bastok", end_node="jeuno",
        allowed_modes={TravelMode.WALK},
    )
    assert r is None


def test_plan_modes_used_set():
    p = MultimodalTravelPlanner()
    p.add_leg(
        from_node="a", to_node="b",
        mode=TravelMode.WALK, cost_seconds=10,
    )
    p.add_leg(
        from_node="b", to_node="c",
        mode=TravelMode.AIRSHIP, cost_seconds=10,
    )
    r = p.plan(start_node="a", end_node="c")
    assert r.modes_used == frozenset(
        {TravelMode.WALK, TravelMode.AIRSHIP},
    )


def test_plan_picks_3hop_over_2hop_if_cheaper():
    p = MultimodalTravelPlanner()
    # direct: cost 1000
    p.add_leg(
        from_node="a", to_node="d",
        mode=TravelMode.WALK, cost_seconds=1000,
    )
    # indirect: a -> b -> c -> d for 100+100+100=300
    p.add_leg(
        from_node="a", to_node="b",
        mode=TravelMode.AIRSHIP, cost_seconds=100,
    )
    p.add_leg(
        from_node="b", to_node="c",
        mode=TravelMode.AIRSHIP, cost_seconds=100,
    )
    p.add_leg(
        from_node="c", to_node="d",
        mode=TravelMode.AIRSHIP, cost_seconds=100,
    )
    r = p.plan(start_node="a", end_node="d")
    assert r.total_cost_seconds == 300
    assert len(r.legs) == 3
