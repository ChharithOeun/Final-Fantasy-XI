"""Tests for sahagin raids."""
from __future__ import annotations

from server.sahagin_raids import (
    DEFENSE_BOUNTY,
    MIN_DEFENDERS,
    RaidKind,
    RaidStatus,
    SahaginRaids,
)


def test_schedule_happy():
    r = SahaginRaids()
    assert r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="wreck1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    ) is True


def test_schedule_blank_id():
    r = SahaginRaids()
    assert r.schedule(
        raid_id="", kind=RaidKind.THEFT,
        target_id="wreck1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    ) is False


def test_schedule_double_blocked():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="wreck1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    )
    assert r.schedule(
        raid_id="r1", kind=RaidKind.SABOTAGE,
        target_id="wreck1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=10,
    ) is False


def test_schedule_blank_target():
    r = SahaginRaids()
    assert r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    ) is False


def test_schedule_zero_duration():
    r = SahaginRaids()
    assert r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="t1", zone_id="reef", band=2,
        duration_seconds=0, now_seconds=0,
    ) is False


def test_defend_happy_with_enough_defenders():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="t1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    )
    out = r.defend(
        raid_id="r1",
        defender_count=MIN_DEFENDERS[RaidKind.THEFT],
        now_seconds=10,
    )
    assert out.accepted is True
    assert out.status == RaidStatus.DEFENDED
    assert out.bounty_paid == DEFENSE_BOUNTY[RaidKind.THEFT]


def test_defend_not_enough_defenders():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.SABOTAGE,
        target_id="t1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    )
    out = r.defend(
        raid_id="r1", defender_count=1,
        now_seconds=10,
    )
    assert out.accepted is False
    assert out.status == RaidStatus.SCHEDULED
    # raid still pending
    assert r.status_of(raid_id="r1") == RaidStatus.SCHEDULED


def test_defend_after_timer_succeeds_for_sahagin():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="t1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    )
    out = r.defend(
        raid_id="r1", defender_count=10,
        now_seconds=400,  # past timer
    )
    assert out.accepted is False
    assert out.status == RaidStatus.SUCCEEDED
    assert out.target_damaged is True


def test_defend_unknown_raid():
    r = SahaginRaids()
    out = r.defend(
        raid_id="ghost", defender_count=5, now_seconds=0,
    )
    assert out.accepted is False


def test_defend_already_resolved():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="t1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    )
    r.defend(
        raid_id="r1", defender_count=5, now_seconds=10,
    )
    # second defend attempt
    out = r.defend(
        raid_id="r1", defender_count=5, now_seconds=20,
    )
    assert out.accepted is False


def test_resolve_past_timer_succeeds():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="t1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    )
    out = r.resolve(raid_id="r1", now_seconds=400)
    assert out.accepted is True
    assert out.status == RaidStatus.SUCCEEDED


def test_resolve_before_timer_expires():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="t1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    )
    out = r.resolve(raid_id="r1", now_seconds=100)
    assert out.accepted is True
    assert out.status == RaidStatus.EXPIRED


def test_resolve_unknown():
    r = SahaginRaids()
    out = r.resolve(raid_id="ghost", now_seconds=0)
    assert out.accepted is False


def test_active_raids_in_zone():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="t1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    )
    r.schedule(
        raid_id="r2", kind=RaidKind.SABOTAGE,
        target_id="t2", zone_id="trench", band=3,
        duration_seconds=300, now_seconds=0,
    )
    out = r.active_raids_in(zone_id="reef")
    assert len(out) == 1
    assert out[0].raid_id == "r1"


def test_active_raids_excludes_resolved():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.THEFT,
        target_id="t1", zone_id="reef", band=2,
        duration_seconds=300, now_seconds=0,
    )
    r.defend(raid_id="r1", defender_count=5, now_seconds=10)
    out = r.active_raids_in(zone_id="reef")
    assert out == ()


def test_assassination_smaller_team_size():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.ASSASSINATION,
        target_id="curilla", zone_id="sandy", band=0,
        duration_seconds=120, now_seconds=0,
    )
    # 2 defenders is enough (MIN_DEFENDERS[ASSASSINATION] == 2)
    out = r.defend(
        raid_id="r1", defender_count=2, now_seconds=10,
    )
    assert out.accepted is True


def test_desecration_higher_bounty():
    r = SahaginRaids()
    r.schedule(
        raid_id="r1", kind=RaidKind.DESECRATION,
        target_id="mermaid_temple", zone_id="reef", band=3,
        duration_seconds=600, now_seconds=0,
    )
    out = r.defend(
        raid_id="r1", defender_count=10, now_seconds=10,
    )
    assert out.bounty_paid == DEFENSE_BOUNTY[RaidKind.DESECRATION]
    assert out.bounty_paid > DEFENSE_BOUNTY[RaidKind.THEFT]
