"""Tests for net_party_sync."""
from __future__ import annotations

import pytest

from server.net_party_sync import (
    DD_FLANK_M,
    DEFAULT_FOLLOWING_RADIUS_M,
    HEAL_BACK_M,
    NetPartySyncSystem,
    PartyMemberRole,
    PartyMemberState,
    PartySyncPayload,
    SYNC_HZ_CROSS_ZONE,
    SYNC_HZ_SAME_ZONE,
    TANK_FORWARD_M,
)


def _state(
    pid="p1",
    hp=1.0,
    mp=1.0,
    tp=0,
    zone="bastok",
    pos=(0.0, 0.0, 0.0),
    flags=0,
    target="",
    pulling=False,
    role=PartyMemberRole.DD,
):
    return PartyMemberState(
        player_id=pid,
        hp_pct=hp,
        mp_pct=mp,
        tp=tp,
        zone_id=zone,
        position_xyz=pos,
        status_effects_bitmap=flags,
        current_target_id=target,
        is_pulling=pulling,
        role=role,
    )


# ---- enum ----

def test_party_role_count():
    assert len(list(PartyMemberRole)) == 5


def test_party_role_has_tank():
    assert PartyMemberRole.TANK in list(PartyMemberRole)


def test_party_role_has_utility():
    assert PartyMemberRole.UTILITY in list(PartyMemberRole)


# ---- constants ----

def test_sync_hz_same_zone():
    assert SYNC_HZ_SAME_ZONE == 5.0


def test_sync_hz_cross_zone():
    assert SYNC_HZ_CROSS_ZONE == 1.0


def test_default_follow_radius():
    assert DEFAULT_FOLLOWING_RADIUS_M == 5.0


def test_formation_offsets():
    assert TANK_FORWARD_M == 8.0
    assert HEAL_BACK_M == 8.0
    assert DD_FLANK_M == 4.0


# ---- register party ----

def test_register_party():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    assert s.party_count() == 1
    assert s.leader_of("party1") == "leader1"


def test_register_party_empty_id():
    s = NetPartySyncSystem()
    with pytest.raises(ValueError):
        s.register_party("", "leader1")


def test_register_party_empty_leader():
    s = NetPartySyncSystem()
    with pytest.raises(ValueError):
        s.register_party("party1", "")


def test_register_party_duplicate():
    s = NetPartySyncSystem()
    s.register_party("party1", "l1")
    with pytest.raises(ValueError):
        s.register_party("party1", "l2")


# ---- member state ----

def test_update_member_state():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state("party1", _state())
    assert s.member_count("party1") == 1
    assert s.member_state("party1", "p1").hp_pct == 1.0


def test_update_member_unknown_party():
    s = NetPartySyncSystem()
    with pytest.raises(KeyError):
        s.update_member_state("nope", _state())


def test_update_member_invalid_hp():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    with pytest.raises(ValueError):
        s.update_member_state("party1", _state(hp=1.5))


def test_update_member_invalid_mp():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    with pytest.raises(ValueError):
        s.update_member_state("party1", _state(mp=-0.1))


def test_update_member_overwrites():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state("party1", _state(hp=1.0))
    s.update_member_state("party1", _state(hp=0.5))
    assert s.member_state("party1", "p1").hp_pct == 0.5


# ---- sync payloads ----

def test_sync_same_zone_is_full():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state("party1", _state(pos=(5, 0, 0)))
    p = s.sync_payload_for("party1", "leader1", zone_match=True)
    assert p.is_full
    assert p.members[0].position_xyz == (5, 0, 0)


def test_sync_cross_zone_strips_position():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state(
        "party1", _state(pos=(5, 0, 0), target="mob1"),
    )
    p = s.sync_payload_for("party1", "leader1", zone_match=False)
    assert not p.is_full
    assert p.members[0].position_xyz == (0.0, 0.0, 0.0)
    assert p.members[0].current_target_id == ""


def test_sync_cross_zone_keeps_hp():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state("party1", _state(hp=0.5, mp=0.3, tp=600))
    p = s.sync_payload_for("party1", "leader1", zone_match=False)
    assert p.members[0].hp_pct == 0.5
    assert p.members[0].mp_pct == 0.3
    assert p.members[0].tp == 600


def test_sync_unknown_party():
    s = NetPartySyncSystem()
    with pytest.raises(KeyError):
        s.sync_payload_for("nope", "v", zone_match=True)


def test_sync_hz_helper():
    s = NetPartySyncSystem()
    assert s.sync_hz(zone_match=True) == 5.0
    assert s.sync_hz(zone_match=False) == 1.0


# ---- follow ----

def test_set_following():
    s = NetPartySyncSystem()
    s.set_following("p2", "leader1")
    assert s.following_of("p2") == "leader1"


def test_clear_following():
    s = NetPartySyncSystem()
    s.set_following("p2", "leader1")
    s.clear_following("p2")
    assert s.following_of("p2") == ""


def test_set_following_self_raises():
    s = NetPartySyncSystem()
    with pytest.raises(ValueError):
        s.set_following("p2", "p2")


def test_set_following_empty_raises():
    s = NetPartySyncSystem()
    with pytest.raises(ValueError):
        s.set_following("", "leader1")


def test_set_following_radius():
    s = NetPartySyncSystem()
    s.set_following_radius("party1", 10.0)
    assert s.following_radius("party1") == 10.0


def test_set_following_radius_zero_raises():
    s = NetPartySyncSystem()
    with pytest.raises(ValueError):
        s.set_following_radius("party1", 0.0)


def test_should_break_follow_not_following():
    s = NetPartySyncSystem()
    assert not s.should_break_follow("p2", 100.0)


def test_should_break_follow_outside_radius():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state("party1", _state(pid="p2"))
    s.set_following("p2", "leader1")
    assert s.should_break_follow("p2", 6.0)


def test_should_keep_follow_inside_radius():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state("party1", _state(pid="p2"))
    s.set_following("p2", "leader1")
    assert not s.should_break_follow("p2", 3.0)


# ---- formation ----

def test_formation_disabled_returns_own_pos():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state(
        "party1",
        _state(pid="t1", pos=(3, 0, 4), role=PartyMemberRole.TANK),
    )
    pos = s.formation_target_for("t1", "party1")
    # Formation disabled by default → own pos.
    assert pos == (3, 0, 4)


def test_formation_enabled_tank_forward():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.set_formation_enabled("party1", True)
    s.update_member_state(
        "party1",
        _state(pid="t1", pos=(0, 0, 0), role=PartyMemberRole.TANK),
    )
    # Group center is just the tank → (0,0,0); facing 0deg = +X.
    pos = s.formation_target_for("t1", "party1", 0.0)
    assert abs(pos[0] - TANK_FORWARD_M) < 1e-6
    assert abs(pos[2]) < 1e-6


def test_formation_heal_behind():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.set_formation_enabled("party1", True)
    s.update_member_state(
        "party1",
        _state(pid="h1", pos=(0, 0, 0), role=PartyMemberRole.HEAL),
    )
    pos = s.formation_target_for("h1", "party1", 0.0)
    assert abs(pos[0] + HEAL_BACK_M) < 1e-6


def test_formation_unknown_party():
    s = NetPartySyncSystem()
    with pytest.raises(KeyError):
        s.formation_target_for("p1", "nope")


def test_formation_unknown_member():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    with pytest.raises(KeyError):
        s.formation_target_for("ghost", "party1")


# ---- health summary ----

def test_party_health_summary_leader_first():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state(
        "party1",
        _state(pid="aa_member", hp=0.4, mp=0.3, tp=100),
    )
    s.update_member_state(
        "party1",
        _state(pid="leader1", hp=1.0, mp=0.9, tp=300),
    )
    summary = s.party_health_summary("party1")
    assert summary[0][0] == "leader1"
    assert summary[0][1] == 1.0


def test_party_health_summary_unknown():
    s = NetPartySyncSystem()
    with pytest.raises(KeyError):
        s.party_health_summary("nope")


def test_party_health_summary_tuples():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.update_member_state(
        "party1",
        _state(pid="leader1", hp=0.8, mp=0.6, tp=500),
    )
    summary = s.party_health_summary("party1")
    assert summary[0] == ("leader1", 0.8, 0.6, 500)


# ---- formation toggle ----

def test_formation_toggle_default_off():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    assert not s.formation_enabled("party1")


def test_formation_toggle_on():
    s = NetPartySyncSystem()
    s.register_party("party1", "leader1")
    s.set_formation_enabled("party1", True)
    assert s.formation_enabled("party1")
