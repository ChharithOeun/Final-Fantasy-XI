"""Tests for pirate crew charter."""
from __future__ import annotations

from server.pirate_crew_charter import (
    CharterFlag,
    CrewRole,
    MAX_CREW_SIZE,
    MAX_OFFICERS,
    PirateCrewCharter,
)


def test_found_charter_happy():
    p = PirateCrewCharter()
    r = p.found(
        charter_id="c1", founder_id="cap",
        charter_name="Sea Wolves",
        flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    assert r.accepted is True
    assert r.new_role == CrewRole.CAPTAIN


def test_found_blank_id_rejected():
    p = PirateCrewCharter()
    r = p.found(
        charter_id="", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    assert r.accepted is False


def test_found_duplicate_charter_id():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    r = p.found(
        charter_id="c1", founder_id="cap2",
        charter_name="y", flag=CharterFlag.MERCHANT,
        now_seconds=10,
    )
    assert r.accepted is False


def test_found_blocks_double_membership():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    r = p.found(
        charter_id="c2", founder_id="cap",
        charter_name="y", flag=CharterFlag.PIRATE,
        now_seconds=10,
    )
    assert r.accepted is False


def test_invite_and_accept():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    p.invite(
        charter_id="c1", captain_id="cap",
        recruit_id="r1",
    )
    r = p.accept_invite(charter_id="c1", recruit_id="r1")
    assert r.accepted is True
    assert r.new_role == CrewRole.CREW
    assert p.membership_of(player_id="r1") == "c1"


def test_invite_only_captain():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    r = p.invite(
        charter_id="c1", captain_id="not_cap",
        recruit_id="r1",
    )
    assert r.accepted is False


def test_invite_already_in_crew():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    p.invite(charter_id="c1", captain_id="cap", recruit_id="r1")
    p.accept_invite(charter_id="c1", recruit_id="r1")
    r = p.invite(
        charter_id="c1", captain_id="cap", recruit_id="r1",
    )
    assert r.accepted is False


def test_invite_full_crew_rejected():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    # fill crew to cap
    for i in range(MAX_CREW_SIZE - 1):
        p.invite(
            charter_id="c1", captain_id="cap",
            recruit_id=f"r{i}",
        )
        p.accept_invite(
            charter_id="c1", recruit_id=f"r{i}",
        )
    r = p.invite(
        charter_id="c1", captain_id="cap",
        recruit_id="overflow",
    )
    assert r.accepted is False


def test_accept_invite_unknown():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    r = p.accept_invite(charter_id="c1", recruit_id="ghost")
    assert r.accepted is False


def test_promote_to_officer():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    p.invite(charter_id="c1", captain_id="cap", recruit_id="r1")
    p.accept_invite(charter_id="c1", recruit_id="r1")
    r = p.promote(
        charter_id="c1", captain_id="cap",
        member_id="r1", role=CrewRole.OFFICER,
    )
    assert r.accepted is True
    assert r.new_role == CrewRole.OFFICER


def test_promote_officer_cap():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    # add 5 members; promote 4 -> 5th promote should fail
    for i in range(5):
        rid = f"r{i}"
        p.invite(charter_id="c1", captain_id="cap", recruit_id=rid)
        p.accept_invite(charter_id="c1", recruit_id=rid)
    for i in range(MAX_OFFICERS):
        p.promote(
            charter_id="c1", captain_id="cap",
            member_id=f"r{i}", role=CrewRole.OFFICER,
        )
    r = p.promote(
        charter_id="c1", captain_id="cap",
        member_id=f"r{MAX_OFFICERS}",
        role=CrewRole.OFFICER,
    )
    assert r.accepted is False


def test_promote_to_captain_transfers():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    p.invite(charter_id="c1", captain_id="cap", recruit_id="r1")
    p.accept_invite(charter_id="c1", recruit_id="r1")
    r = p.promote(
        charter_id="c1", captain_id="cap",
        member_id="r1", role=CrewRole.CAPTAIN,
    )
    assert r.accepted is True
    rec = p.charter_for(charter_id="c1")
    assert rec.captain_id == "r1"
    assert rec.members["cap"] == CrewRole.OFFICER


def test_demote_officer_to_crew():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    p.invite(charter_id="c1", captain_id="cap", recruit_id="r1")
    p.accept_invite(charter_id="c1", recruit_id="r1")
    p.promote(
        charter_id="c1", captain_id="cap",
        member_id="r1", role=CrewRole.OFFICER,
    )
    r = p.demote(
        charter_id="c1", captain_id="cap", member_id="r1",
    )
    assert r.accepted is True
    assert r.new_role == CrewRole.CREW


def test_demote_captain_blocked():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    r = p.demote(
        charter_id="c1", captain_id="cap", member_id="cap",
    )
    assert r.accepted is False


def test_leave_happy():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    p.invite(charter_id="c1", captain_id="cap", recruit_id="r1")
    p.accept_invite(charter_id="c1", recruit_id="r1")
    r = p.leave(charter_id="c1", member_id="r1")
    assert r.accepted is True
    assert p.membership_of(player_id="r1") is None


def test_captain_cannot_leave():
    p = PirateCrewCharter()
    p.found(
        charter_id="c1", founder_id="cap",
        charter_name="x", flag=CharterFlag.PIRATE,
        now_seconds=0,
    )
    r = p.leave(charter_id="c1", member_id="cap")
    assert r.accepted is False
