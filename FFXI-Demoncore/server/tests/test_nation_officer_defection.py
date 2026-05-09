"""Tests for nation_officer_defection."""
from __future__ import annotations

from server.nation_officer_defection import (
    NationOfficerDefectionSystem, GrievanceKind,
    AttemptState,
)


def test_record_grievance_happy():
    s = NationOfficerDefectionSystem()
    gid = s.record_grievance(
        officer_id="off_volker",
        kind=GrievanceKind.PAY_ARREARS,
        note="3 months unpaid", occurred_day=10,
    )
    assert gid is not None


def test_record_blank_officer():
    s = NationOfficerDefectionSystem()
    gid = s.record_grievance(
        officer_id="",
        kind=GrievanceKind.PAY_ARREARS,
        note="x", occurred_day=10,
    )
    assert gid is None


def test_record_blank_note():
    s = NationOfficerDefectionSystem()
    gid = s.record_grievance(
        officer_id="off_volker",
        kind=GrievanceKind.PAY_ARREARS,
        note="", occurred_day=10,
    )
    assert gid is None


def test_record_negative_day():
    s = NationOfficerDefectionSystem()
    gid = s.record_grievance(
        officer_id="off_volker",
        kind=GrievanceKind.PAY_ARREARS,
        note="x", occurred_day=-1,
    )
    assert gid is None


def test_grievance_total_sums_weights():
    s = NationOfficerDefectionSystem()
    s.record_grievance(
        officer_id="o", kind=GrievanceKind.PAY_ARREARS,
        note="x", occurred_day=10,
    )
    s.record_grievance(
        officer_id="o",
        kind=GrievanceKind.PUBLICLY_SHAMED,
        note="y", occurred_day=11,
    )
    # 8 + 12 = 20
    assert s.grievance_total(officer_id="o") == 20


def test_grievance_total_unknown_zero():
    s = NationOfficerDefectionSystem()
    assert s.grievance_total(
        officer_id="ghost",
    ) == 0


def test_grievances_for():
    s = NationOfficerDefectionSystem()
    s.record_grievance(
        officer_id="o", kind=GrievanceKind.PAY_ARREARS,
        note="x", occurred_day=10,
    )
    s.record_grievance(
        officer_id="o",
        kind=GrievanceKind.PERSONAL_INSULT,
        note="y", occurred_day=11,
    )
    out = s.grievances_for(officer_id="o")
    assert len(out) == 2


def test_approach_happy():
    s = NationOfficerDefectionSystem()
    aid = s.approach(
        officer_id="off_volker",
        suitor_nation="windy", offer_gil=100_000,
        offer_post="ARMY_COMMAND",
        approach_day=20,
    )
    assert aid is not None


def test_approach_blank():
    s = NationOfficerDefectionSystem()
    aid = s.approach(
        officer_id="", suitor_nation="windy",
        offer_gil=100_000, offer_post="x",
        approach_day=20,
    )
    assert aid is None


def test_approach_dup_pending_blocked():
    s = NationOfficerDefectionSystem()
    s.approach(
        officer_id="off_volker",
        suitor_nation="windy", offer_gil=100_000,
        offer_post="x", approach_day=20,
    )
    aid = s.approach(
        officer_id="off_volker",
        suitor_nation="windy", offer_gil=200_000,
        offer_post="y", approach_day=21,
    )
    assert aid is None


def test_approach_different_suitor_ok():
    s = NationOfficerDefectionSystem()
    s.approach(
        officer_id="off_volker",
        suitor_nation="windy", offer_gil=100_000,
        offer_post="x", approach_day=20,
    )
    aid = s.approach(
        officer_id="off_volker",
        suitor_nation="sandy", offer_gil=200_000,
        offer_post="y", approach_day=21,
    )
    assert aid is not None


def test_resolve_low_loyalty_high_offer_defects():
    s = NationOfficerDefectionSystem()
    s.record_grievance(
        officer_id="off_volker",
        kind=GrievanceKind.ALLY_EXECUTED,
        note="brother killed", occurred_day=10,
    )
    s.record_grievance(
        officer_id="off_volker",
        kind=GrievanceKind.PUBLICLY_SHAMED,
        note="dressed down at court",
        occurred_day=11,
    )
    aid = s.approach(
        officer_id="off_volker",
        suitor_nation="windy", offer_gil=200_000,
        offer_post="ARMY_COMMAND",
        approach_day=20,
    )
    res = s.resolve_attempt(
        attempt_id=aid, current_loyalty=20,
        seed=15, now_day=25,
    )
    assert res == AttemptState.DEFECTED


def test_resolve_high_loyalty_no_grievance_reports():
    s = NationOfficerDefectionSystem()
    aid = s.approach(
        officer_id="off_volker",
        suitor_nation="windy", offer_gil=10_000,
        offer_post="x", approach_day=20,
    )
    res = s.resolve_attempt(
        attempt_id=aid, current_loyalty=95,
        seed=1, now_day=25,
    )
    assert res == AttemptState.REPORTED


def test_resolve_middle_rejected():
    s = NationOfficerDefectionSystem()
    s.record_grievance(
        officer_id="off_volker",
        kind=GrievanceKind.PAY_ARREARS,
        note="x", occurred_day=10,
    )
    aid = s.approach(
        officer_id="off_volker",
        suitor_nation="windy", offer_gil=100_000,
        offer_post="x", approach_day=20,
    )
    # loyalty=50, griev=8, offer_pull=40, entropy=5
    # defection_score = 50+8+40+5 = 103
    # loyalty_score = 50 + (50-8) = 92
    # |103-92|=11, neither passes 30 -> REJECTED
    res = s.resolve_attempt(
        attempt_id=aid, current_loyalty=50,
        seed=5, now_day=25,
    )
    assert res == AttemptState.REJECTED


def test_resolve_invalid_loyalty():
    s = NationOfficerDefectionSystem()
    aid = s.approach(
        officer_id="o", suitor_nation="windy",
        offer_gil=10_000, offer_post="x",
        approach_day=20,
    )
    res = s.resolve_attempt(
        attempt_id=aid, current_loyalty=200,
        seed=0, now_day=25,
    )
    assert res is None


def test_resolve_unknown():
    s = NationOfficerDefectionSystem()
    res = s.resolve_attempt(
        attempt_id="ghost", current_loyalty=50,
        seed=0, now_day=25,
    )
    assert res is None


def test_resolve_double_blocked():
    s = NationOfficerDefectionSystem()
    aid = s.approach(
        officer_id="o", suitor_nation="windy",
        offer_gil=10_000, offer_post="x",
        approach_day=20,
    )
    s.resolve_attempt(
        attempt_id=aid, current_loyalty=50,
        seed=0, now_day=25,
    )
    res = s.resolve_attempt(
        attempt_id=aid, current_loyalty=50,
        seed=0, now_day=26,
    )
    assert res is None


def test_resolve_reported_bumps_loyalty():
    s = NationOfficerDefectionSystem()
    aid = s.approach(
        officer_id="o", suitor_nation="windy",
        offer_gil=5_000, offer_post="x",
        approach_day=20,
    )
    s.resolve_attempt(
        attempt_id=aid, current_loyalty=90,
        seed=0, now_day=25,
    )
    a = s.attempt(attempt_id=aid)
    assert a.new_loyalty == 95


def test_attempts_for_officer():
    s = NationOfficerDefectionSystem()
    s.approach(
        officer_id="o", suitor_nation="windy",
        offer_gil=10_000, offer_post="x",
        approach_day=20,
    )
    s.approach(
        officer_id="o", suitor_nation="sandy",
        offer_gil=15_000, offer_post="y",
        approach_day=21,
    )
    s.approach(
        officer_id="other", suitor_nation="windy",
        offer_gil=10_000, offer_post="x",
        approach_day=20,
    )
    out = s.attempts_for(officer_id="o")
    assert len(out) == 2


def test_attempt_unknown():
    s = NationOfficerDefectionSystem()
    assert s.attempt(attempt_id="ghost") is None


def test_resolve_deterministic_same_seed():
    s = NationOfficerDefectionSystem()
    aid_a = s.approach(
        officer_id="a", suitor_nation="windy",
        offer_gil=50_000, offer_post="x",
        approach_day=20,
    )
    res_a = s.resolve_attempt(
        attempt_id=aid_a, current_loyalty=60,
        seed=42, now_day=25,
    )
    s2 = NationOfficerDefectionSystem()
    aid_b = s2.approach(
        officer_id="b", suitor_nation="windy",
        offer_gil=50_000, offer_post="x",
        approach_day=20,
    )
    res_b = s2.resolve_attempt(
        attempt_id=aid_b, current_loyalty=60,
        seed=42, now_day=25,
    )
    assert res_a == res_b


def test_enum_counts():
    assert len(list(GrievanceKind)) == 8
    assert len(list(AttemptState)) == 4
