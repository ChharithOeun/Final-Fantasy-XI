"""Tests for nation_treaty."""
from __future__ import annotations

from server.nation_treaty import (
    NationTreatySystem, TreatyKind, TreatyState,
)


def _draft(s, **overrides):
    args = dict(
        treaty_id="trt_1", kind=TreatyKind.PEACE,
        parties=["bastok", "windy"],
        terms="No declared war.", drafted_day=10,
        expiry_day=1000,
    )
    args.update(overrides)
    return s.draft(**args)


def test_draft_happy():
    s = NationTreatySystem()
    assert _draft(s) is True


def test_draft_blank_id():
    s = NationTreatySystem()
    assert _draft(s, treaty_id="") is False


def test_draft_dup_blocked():
    s = NationTreatySystem()
    _draft(s)
    assert _draft(s) is False


def test_draft_one_party_blocked():
    s = NationTreatySystem()
    assert _draft(s, parties=["bastok"]) is False


def test_draft_dup_parties():
    s = NationTreatySystem()
    assert _draft(
        s, parties=["bastok", "bastok"],
    ) is False


def test_draft_blank_terms():
    s = NationTreatySystem()
    assert _draft(s, terms="") is False


def test_draft_inverted_dates():
    s = NationTreatySystem()
    assert _draft(
        s, drafted_day=20, expiry_day=10,
    ) is False


def test_sign_happy():
    s = NationTreatySystem()
    _draft(s)
    assert s.sign(
        treaty_id="trt_1", party="bastok",
        now_day=11,
    ) is True


def test_sign_unknown_party():
    s = NationTreatySystem()
    _draft(s)
    assert s.sign(
        treaty_id="trt_1", party="omega",
        now_day=11,
    ) is False


def test_double_sign_blocked():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    assert s.sign(
        treaty_id="trt_1", party="bastok",
        now_day=12,
    ) is False


def test_sign_advances_to_signed_when_full():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    s.sign(treaty_id="trt_1", party="windy",
           now_day=12)
    assert s.treaty(
        treaty_id="trt_1",
    ).state == TreatyState.SIGNED


def test_ratify_happy():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    s.sign(treaty_id="trt_1", party="windy",
           now_day=12)
    assert s.ratify(
        treaty_id="trt_1", now_day=13,
    ) is True


def test_ratify_when_not_signed_blocked():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    assert s.ratify(
        treaty_id="trt_1", now_day=13,
    ) is False


def test_breach_happy():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    s.sign(treaty_id="trt_1", party="windy",
           now_day=12)
    s.ratify(treaty_id="trt_1", now_day=13)
    assert s.declare_breach(
        treaty_id="trt_1",
        breaching_party="windy",
        now_day=20, evidence="raid documented",
    ) is True


def test_breach_unknown_party():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    s.sign(treaty_id="trt_1", party="windy",
           now_day=12)
    s.ratify(treaty_id="trt_1", now_day=13)
    assert s.declare_breach(
        treaty_id="trt_1",
        breaching_party="omega", now_day=20,
        evidence="x",
    ) is False


def test_breach_blank_evidence():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    s.sign(treaty_id="trt_1", party="windy",
           now_day=12)
    s.ratify(treaty_id="trt_1", now_day=13)
    assert s.declare_breach(
        treaty_id="trt_1",
        breaching_party="windy", now_day=20,
        evidence="",
    ) is False


def test_terminate_happy():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    s.sign(treaty_id="trt_1", party="windy",
           now_day=12)
    s.ratify(treaty_id="trt_1", now_day=13)
    assert s.terminate(
        treaty_id="trt_1", now_day=20,
        reason="mutual_dissolution",
    ) is True


def test_terminate_blank_reason():
    s = NationTreatySystem()
    _draft(s)
    assert s.terminate(
        treaty_id="trt_1", now_day=20, reason="",
    ) is False


def test_double_terminate_blocked():
    s = NationTreatySystem()
    _draft(s)
    s.terminate(
        treaty_id="trt_1", now_day=20,
        reason="x",
    )
    assert s.terminate(
        treaty_id="trt_1", now_day=21, reason="y",
    ) is False


def test_tick_auto_expires():
    s = NationTreatySystem()
    _draft(s, expiry_day=20)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    s.sign(treaty_id="trt_1", party="windy",
           now_day=12)
    s.ratify(treaty_id="trt_1", now_day=13)
    changes = s.tick(now_day=20)
    assert (
        ("trt_1", TreatyState.TERMINATED) in changes
    )


def test_active_between_happy():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    s.sign(treaty_id="trt_1", party="windy",
           now_day=12)
    s.ratify(treaty_id="trt_1", now_day=13)
    out = s.active_between(
        party_a="bastok", party_b="windy",
        now_day=20,
    )
    assert len(out) == 1


def test_active_between_excludes_breached():
    s = NationTreatySystem()
    _draft(s)
    s.sign(treaty_id="trt_1", party="bastok",
           now_day=11)
    s.sign(treaty_id="trt_1", party="windy",
           now_day=12)
    s.ratify(treaty_id="trt_1", now_day=13)
    s.declare_breach(
        treaty_id="trt_1",
        breaching_party="windy",
        now_day=20, evidence="raid",
    )
    out = s.active_between(
        party_a="bastok", party_b="windy",
        now_day=21,
    )
    assert out == []


def test_treaty_unknown():
    s = NationTreatySystem()
    assert s.treaty(treaty_id="ghost") is None


def test_enum_counts():
    assert len(list(TreatyKind)) == 7
    assert len(list(TreatyState)) == 5
