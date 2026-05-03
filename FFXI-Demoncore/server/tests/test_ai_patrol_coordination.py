"""Tests for AI patrol coordination."""
from __future__ import annotations

from server.ai_patrol_coordination import (
    AIPatrolCoordination,
    AlertKind,
    Waypoint,
)


def _route(coord, route_id="r1", zone="bastok"):
    coord.register_route(
        route_id=route_id, zone_id=zone,
        waypoints=(
            Waypoint(x=0, y=0),
            Waypoint(x=100, y=0),
            Waypoint(x=100, y=100),
            Waypoint(x=0, y=100),
        ),
    )


def test_register_route():
    coord = AIPatrolCoordination()
    _route(coord)
    assert coord.total_routes() == 1


def test_register_too_few_waypoints_rejected():
    coord = AIPatrolCoordination()
    res = coord.register_route(
        route_id="r1", zone_id="z",
        waypoints=(Waypoint(x=0, y=0),),
    )
    assert res is None


def test_double_register_route_rejected():
    coord = AIPatrolCoordination()
    _route(coord)
    res = coord.register_route(
        route_id="r1", zone_id="z",
        waypoints=(
            Waypoint(x=0, y=0), Waypoint(x=1, y=1),
        ),
    )
    assert res is None


def test_assign_guard():
    coord = AIPatrolCoordination()
    _route(coord)
    assert coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="bastok_a",
    )
    g = coord.guard("g1")
    assert g.x == 0
    assert g.y == 0


def test_assign_guard_unknown_route():
    coord = AIPatrolCoordination()
    assert not coord.assign_guard(
        guard_id="g1", route_id="ghost", squad_id="x",
    )


def test_assign_double_guard_rejected():
    coord = AIPatrolCoordination()
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    assert not coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="b",
    )


def test_step_patrol_advances():
    coord = AIPatrolCoordination(patrol_speed=10.0)
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    coord.step_patrol(elapsed_seconds=2.0)
    g = coord.guard("g1")
    # Moved 20 units toward (100, 0)
    assert g.x == 20
    assert g.y == 0


def test_step_patrol_arrives_at_waypoint():
    coord = AIPatrolCoordination(patrol_speed=200.0)
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    coord.step_patrol(elapsed_seconds=1.0)
    g = coord.guard("g1")
    # Should have arrived at waypoint 1 (100, 0)
    assert g.x == 100
    assert g.y == 0
    assert g.waypoint_index == 1


def test_step_patrol_zero_no_move():
    coord = AIPatrolCoordination()
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    moved = coord.step_patrol(elapsed_seconds=0.0)
    assert moved == 0


def test_alert_propagates_to_nearby_squad():
    coord = AIPatrolCoordination(alert_reach=200.0)
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    alert = coord.raise_alert(
        reporter_id="witness", kind=AlertKind.PLAYER_CRIME,
        zone_id="bastok", x=50, y=50,
    )
    assert "a" in alert.responding_squads
    assert coord.guard("g1").on_alert


def test_alert_skips_far_guards():
    coord = AIPatrolCoordination(alert_reach=10.0)
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    alert = coord.raise_alert(
        reporter_id="witness", kind=AlertKind.OUTLAW_SPOTTED,
        zone_id="bastok", x=10000, y=10000,
    )
    assert alert.responding_squads == ()
    assert not coord.guard("g1").on_alert


def test_alert_skips_other_zone():
    coord = AIPatrolCoordination(alert_reach=10000.0)
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    alert = coord.raise_alert(
        reporter_id="x", kind=AlertKind.HOSTILE_MOB,
        zone_id="other_zone", x=0, y=0,
    )
    assert alert.responding_squads == ()


def test_on_alert_guard_does_not_step():
    coord = AIPatrolCoordination(
        alert_reach=200.0, patrol_speed=100.0,
    )
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    coord.raise_alert(
        reporter_id="x", kind=AlertKind.HOSTILE_MOB,
        zone_id="bastok", x=10, y=10,
    )
    coord.step_patrol(elapsed_seconds=1.0)
    g = coord.guard("g1")
    assert g.x == 0    # still at waypoint 0
    assert g.y == 0


def test_stand_down_clears_alert():
    coord = AIPatrolCoordination(alert_reach=200.0)
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    coord.raise_alert(
        reporter_id="x", kind=AlertKind.HOSTILE_MOB,
        zone_id="bastok", x=10, y=10,
    )
    cleared = coord.stand_down_squad(squad_id="a")
    assert cleared == 1
    assert not coord.guard("g1").on_alert


def test_alerts_for_squad():
    coord = AIPatrolCoordination(alert_reach=200.0)
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    coord.raise_alert(
        reporter_id="x", kind=AlertKind.HOSTILE_MOB,
        zone_id="bastok", x=10, y=10,
    )
    alerts = coord.alerts_for_squad("a")
    assert len(alerts) == 1


def test_total_counts():
    coord = AIPatrolCoordination()
    _route(coord)
    _route(coord, route_id="r2", zone="windurst")
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    coord.assign_guard(
        guard_id="g2", route_id="r2", squad_id="b",
    )
    assert coord.total_routes() == 2
    assert coord.total_guards() == 2
    assert coord.total_alerts() == 0


def test_route_loop_back_to_start():
    """Walk all the way around — guard should return to
    waypoint 0 eventually."""
    coord = AIPatrolCoordination(patrol_speed=200.0)
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    # 4 waypoints * 100 units each at 200 speed = 2 seconds total
    for _ in range(4):
        coord.step_patrol(elapsed_seconds=1.0)
    g = coord.guard("g1")
    assert g.waypoint_index == 0


def test_alert_with_z():
    """Verify 3D distance applies (z component matters)."""
    coord = AIPatrolCoordination(alert_reach=10.0)
    _route(coord)
    coord.assign_guard(
        guard_id="g1", route_id="r1", squad_id="a",
    )
    # Guard at (0,0,0); alert at (0,0,100) — out of range
    alert = coord.raise_alert(
        reporter_id="x", kind=AlertKind.HOSTILE_MOB,
        zone_id="bastok", x=0, y=0, z=100,
    )
    assert alert.responding_squads == ()
