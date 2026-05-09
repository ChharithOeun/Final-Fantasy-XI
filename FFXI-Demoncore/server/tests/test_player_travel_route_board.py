"""Tests for player_travel_route_board."""
from __future__ import annotations

from server.player_travel_route_board import (
    PlayerTravelRouteBoardSystem, RouteState,
)


def _publish(s: PlayerTravelRouteBoardSystem) -> str:
    return s.publish(
        publisher_id="alice",
        origin_zone="bastok",
        destination_zone="san_doria",
        waypoints=["zulkheim", "ronfaure_west"],
    )


def test_publish_happy():
    s = PlayerTravelRouteBoardSystem()
    assert _publish(s) is not None


def test_publish_same_zone_blocked():
    s = PlayerTravelRouteBoardSystem()
    assert s.publish(
        publisher_id="a", origin_zone="z",
        destination_zone="z", waypoints=[],
    ) is None


def test_publish_empty_zone_blocked():
    s = PlayerTravelRouteBoardSystem()
    assert s.publish(
        publisher_id="a", origin_zone="",
        destination_zone="z", waypoints=[],
    ) is None


def test_endorse_happy():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    assert s.endorse(
        route_id=rid, traveler_id="bob",
    ) is True


def test_endorse_publisher_self_blocked():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    assert s.endorse(
        route_id=rid, traveler_id="alice",
    ) is False


def test_endorse_dup_blocked():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    s.endorse(route_id=rid, traveler_id="bob")
    assert s.endorse(
        route_id=rid, traveler_id="bob",
    ) is False


def test_flag_dangerous_happy():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    assert s.flag_dangerous(
        route_id=rid, traveler_id="cara",
    ) is True


def test_endorse_then_flag_blocked():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    s.endorse(route_id=rid, traveler_id="bob")
    assert s.flag_dangerous(
        route_id=rid, traveler_id="bob",
    ) is False


def test_5_endorsements_recommend():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    for w in ("a", "b", "c", "d", "e"):
        s.endorse(route_id=rid, traveler_id=w)
    assert s.route(
        route_id=rid,
    ).state == RouteState.RECOMMENDED


def test_3_dangers_hazardous():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    for w in ("a", "b", "c"):
        s.flag_dangerous(
            route_id=rid, traveler_id=w,
        )
    assert s.route(
        route_id=rid,
    ).state == RouteState.HAZARDOUS


def test_mixed_majority_endorse():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    for w in ("a", "b", "c", "d", "e", "f"):
        s.endorse(route_id=rid, traveler_id=w)
    s.flag_dangerous(
        route_id=rid, traveler_id="g",
    )
    assert s.route(
        route_id=rid,
    ).state == RouteState.RECOMMENDED


def test_few_endorsements_still_posted():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    for w in ("a", "b", "c"):
        s.endorse(route_id=rid, traveler_id=w)
    assert s.route(
        route_id=rid,
    ).state == RouteState.POSTED


def test_endorsement_count_tracked():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    s.endorse(route_id=rid, traveler_id="a")
    s.endorse(route_id=rid, traveler_id="b")
    assert s.route(
        route_id=rid,
    ).endorsement_count == 2


def test_danger_count_tracked():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    s.flag_dangerous(
        route_id=rid, traveler_id="a",
    )
    assert s.route(
        route_id=rid,
    ).danger_count == 1


def test_withdraw_happy():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    assert s.withdraw(
        route_id=rid, publisher_id="alice",
    ) is True


def test_withdraw_wrong_publisher_blocked():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    assert s.withdraw(
        route_id=rid, publisher_id="bob",
    ) is False


def test_endorse_after_withdraw_blocked():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    s.withdraw(
        route_id=rid, publisher_id="alice",
    )
    assert s.endorse(
        route_id=rid, traveler_id="bob",
    ) is False


def test_waypoints_listing():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    assert s.waypoints(
        route_id=rid,
    ) == ["zulkheim", "ronfaure_west"]


def test_routes_to_lookup():
    s = PlayerTravelRouteBoardSystem()
    s.publish(
        publisher_id="a", origin_zone="bastok",
        destination_zone="san_doria", waypoints=[],
    )
    s.publish(
        publisher_id="a", origin_zone="windurst",
        destination_zone="san_doria", waypoints=[],
    )
    s.publish(
        publisher_id="a", origin_zone="bastok",
        destination_zone="windurst", waypoints=[],
    )
    assert len(s.routes_to(
        destination_zone="san_doria",
    )) == 2


def test_recommended_routes_filter():
    s = PlayerTravelRouteBoardSystem()
    rid = _publish(s)
    for w in ("a", "b", "c", "d", "e"):
        s.endorse(route_id=rid, traveler_id=w)
    assert len(s.recommended_routes()) == 1


def test_unknown_route():
    s = PlayerTravelRouteBoardSystem()
    assert s.route(route_id="ghost") is None


def test_state_count():
    assert len(list(RouteState)) == 4
