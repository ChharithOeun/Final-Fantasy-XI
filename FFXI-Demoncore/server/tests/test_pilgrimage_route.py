"""Tests for pilgrimage_route."""
from __future__ import annotations

from server.pilgrimage_route import (
    PilgrimageRouteRegistry,
    VisitOutcomeKind,
    Waypoint,
)


def _setup_route(ordered=True):
    r = PilgrimageRouteRegistry()
    r.define_route(
        route_id="hero_path", name="The Hero's Path",
        waypoints=[
            Waypoint(zone_id="bastok", monument_id="m1"),
            Waypoint(zone_id="sandy", monument_id="m2"),
            Waypoint(zone_id="windy", monument_id="m3"),
        ],
        ordered=ordered, completion_reward="ki_pilgrim_seal",
    )
    return r


def test_define_route_happy():
    r = _setup_route()
    assert r.get_route(route_id="hero_path") is not None


def test_define_blank_id_blocked():
    r = PilgrimageRouteRegistry()
    out = r.define_route(
        route_id="", name="X",
        waypoints=[Waypoint(zone_id="z", monument_id="m")],
    )
    assert out is False


def test_define_no_waypoints_blocked():
    r = PilgrimageRouteRegistry()
    out = r.define_route(
        route_id="x", name="X", waypoints=[],
    )
    assert out is False


def test_duplicate_route_blocked():
    r = _setup_route()
    again = r.define_route(
        route_id="hero_path", name="dup",
        waypoints=[Waypoint(zone_id="z", monument_id="m")],
    )
    assert again is False


def test_visit_unknown_route():
    r = PilgrimageRouteRegistry()
    out = r.visit_waypoint(
        player_id="alice", route_id="ghost",
        zone_id="z", monument_id="m", visited_at=10,
    )
    assert out.kind == VisitOutcomeKind.UNKNOWN_ROUTE


def test_visit_unknown_waypoint():
    r = _setup_route()
    out = r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="nowhere", monument_id="x", visited_at=10,
    )
    assert out.kind == VisitOutcomeKind.UNKNOWN_WAYPOINT


def test_visit_first_waypoint_progresses():
    r = _setup_route()
    out = r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=10,
    )
    assert out.kind == VisitOutcomeKind.PROGRESSED
    assert out.progress_count == 1
    assert out.total_waypoints == 3


def test_visit_in_order_completes():
    r = _setup_route()
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=10,
    )
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="sandy", monument_id="m2", visited_at=20,
    )
    out = r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="windy", monument_id="m3", visited_at=30,
    )
    assert out.kind == VisitOutcomeKind.COMPLETED
    assert out.completion_reward == "ki_pilgrim_seal"


def test_visit_out_of_order_rejected_when_ordered():
    r = _setup_route()
    out = r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="windy", monument_id="m3", visited_at=10,
    )
    assert out.kind == VisitOutcomeKind.OUT_OF_ORDER


def test_unordered_route_allows_any_sequence():
    r = _setup_route(ordered=False)
    o1 = r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="windy", monument_id="m3", visited_at=10,
    )
    o2 = r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=20,
    )
    o3 = r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="sandy", monument_id="m2", visited_at=30,
    )
    assert o1.kind == VisitOutcomeKind.PROGRESSED
    assert o2.kind == VisitOutcomeKind.PROGRESSED
    assert o3.kind == VisitOutcomeKind.COMPLETED


def test_revisit_same_waypoint_dedup():
    r = _setup_route()
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=10,
    )
    out = r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=20,
    )
    assert out.kind == VisitOutcomeKind.DUPLICATE


def test_visits_after_completion_dedup():
    r = _setup_route()
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=10,
    )
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="sandy", monument_id="m2", visited_at=20,
    )
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="windy", monument_id="m3", visited_at=30,
    )
    out = r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=40,
    )
    assert out.kind == VisitOutcomeKind.DUPLICATE


def test_progress_for_player():
    r = _setup_route()
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=10,
    )
    p = r.progress_for(player_id="alice", route_id="hero_path")
    assert p is not None
    assert len(p.visited_indexes) == 1


def test_completed_routes_for():
    r = _setup_route()
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=1,
    )
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="sandy", monument_id="m2", visited_at=2,
    )
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="windy", monument_id="m3", visited_at=3,
    )
    completed = r.completed_routes_for(player_id="alice")
    assert "hero_path" in completed


def test_blank_player_unknown_waypoint():
    r = _setup_route()
    out = r.visit_waypoint(
        player_id="", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=10,
    )
    assert out.kind == VisitOutcomeKind.UNKNOWN_WAYPOINT


def test_per_player_progress_independent():
    r = _setup_route()
    r.visit_waypoint(
        player_id="alice", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=10,
    )
    out = r.visit_waypoint(
        player_id="bob", route_id="hero_path",
        zone_id="bastok", monument_id="m1", visited_at=20,
    )
    assert out.kind == VisitOutcomeKind.PROGRESSED
    assert out.progress_count == 1
