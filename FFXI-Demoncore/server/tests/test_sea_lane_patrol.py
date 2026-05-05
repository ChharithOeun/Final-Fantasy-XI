"""Tests for sea lane patrol."""
from __future__ import annotations

from server.sea_lane_patrol import LaneStatus, SeaLanePatrol


def test_register_lane_happy():
    p = SeaLanePatrol()
    ok = p.register_lane(
        lane_id="bastok_norg",
        zone_a="bastok_port",
        zone_b="norg_port",
    )
    assert ok is True
    assert p.total_lanes() == 1


def test_register_lane_rejects_same_zone():
    p = SeaLanePatrol()
    assert p.register_lane(
        lane_id="x", zone_a="a", zone_b="a",
    ) is False


def test_register_lane_rejects_blank():
    p = SeaLanePatrol()
    assert p.register_lane(
        lane_id="", zone_a="a", zone_b="b",
    ) is False
    assert p.register_lane(
        lane_id="x", zone_a="", zone_b="b",
    ) is False


def test_register_duplicate_rejected():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    assert p.register_lane(
        lane_id="x", zone_a="a", zone_b="b",
    ) is False


def test_status_default_secure():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    assert p.get_lane_status(
        lane_id="x", now_seconds=0,
    ) == LaneStatus.SECURE


def test_pirate_sighted_pushes_to_watchful():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    p.pirate_sighted(lane_id="x", severity=40, now_seconds=0)
    assert p.get_lane_status(
        lane_id="x", now_seconds=10,
    ) == LaneStatus.WATCHFUL


def test_pirate_sighted_pushes_to_dangerous():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    p.pirate_sighted(lane_id="x", severity=80, now_seconds=0)
    assert p.get_lane_status(
        lane_id="x", now_seconds=10,
    ) == LaneStatus.DANGEROUS


def test_patrol_pass_lowers_threat():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    p.pirate_sighted(lane_id="x", severity=80, now_seconds=0)
    p.patrol_pass(lane_id="x", sweep_strength=60, now_seconds=10)
    assert p.get_lane_status(
        lane_id="x", now_seconds=20,
    ) == LaneStatus.SECURE


def test_decay_over_time():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    p.pirate_sighted(lane_id="x", severity=40, now_seconds=0)
    # 8 hours of decay at 5/hr = 40 threat removed -> SECURE
    assert p.get_lane_status(
        lane_id="x", now_seconds=8 * 3_600,
    ) == LaneStatus.SECURE


def test_threat_score_floor_zero():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    p.pirate_sighted(lane_id="x", severity=10, now_seconds=0)
    p.patrol_pass(lane_id="x", sweep_strength=999, now_seconds=10)
    assert p.threat_score(lane_id="x", now_seconds=20) == 0


def test_threat_score_capped_at_100():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    p.pirate_sighted(lane_id="x", severity=999, now_seconds=0)
    assert p.threat_score(lane_id="x", now_seconds=10) == 100


def test_pirate_sighted_unknown_lane():
    p = SeaLanePatrol()
    assert p.pirate_sighted(
        lane_id="ghost", severity=10, now_seconds=0,
    ) is False


def test_patrol_pass_unknown_lane():
    p = SeaLanePatrol()
    assert p.patrol_pass(
        lane_id="ghost", sweep_strength=10, now_seconds=0,
    ) is False


def test_pirate_sighted_zero_severity_rejected():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    assert p.pirate_sighted(
        lane_id="x", severity=0, now_seconds=0,
    ) is False


def test_patrol_pass_zero_strength_rejected():
    p = SeaLanePatrol()
    p.register_lane(lane_id="x", zone_a="a", zone_b="b")
    assert p.patrol_pass(
        lane_id="x", sweep_strength=0, now_seconds=0,
    ) is False
