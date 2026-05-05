"""Tests for abduction recovery quest."""
from __future__ import annotations

from server.abduction_recovery_quest import (
    AbductionRecoveryQuest,
    EXPIRY_SECONDS,
    QuestStage,
)


def test_post_accept_engage_extract_happy():
    q = AbductionRecoveryQuest()
    p = q.post(
        captive_spawn_id="argo#crew000",
        abductor_zone_id="abyss_trench",
        bounty_gil=5_000,
        now_seconds=0,
    )
    assert p.accepted is True
    a = q.accept(
        captive_spawn_id="argo#crew000",
        party_id="party_x",
        now_seconds=10,
    )
    assert a.new_stage == QuestStage.ACCEPTED
    e = q.engage(captive_spawn_id="argo#crew000", now_seconds=20)
    assert e.new_stage == QuestStage.ENGAGED
    x = q.extract(captive_spawn_id="argo#crew000", now_seconds=30)
    assert x.new_stage == QuestStage.EXTRACTED
    assert x.awarded_gil == 5_000


def test_post_rejects_blank_ids():
    q = AbductionRecoveryQuest()
    assert q.post(
        captive_spawn_id="",
        abductor_zone_id="z",
        bounty_gil=1, now_seconds=0,
    ).accepted is False
    assert q.post(
        captive_spawn_id="x",
        abductor_zone_id="",
        bounty_gil=1, now_seconds=0,
    ).accepted is False


def test_post_rejects_negative_bounty():
    q = AbductionRecoveryQuest()
    r = q.post(
        captive_spawn_id="x",
        abductor_zone_id="z",
        bounty_gil=-1, now_seconds=0,
    )
    assert r.accepted is False


def test_post_duplicate_rejected():
    q = AbductionRecoveryQuest()
    q.post(
        captive_spawn_id="x", abductor_zone_id="z",
        bounty_gil=10, now_seconds=0,
    )
    r = q.post(
        captive_spawn_id="x", abductor_zone_id="z",
        bounty_gil=10, now_seconds=0,
    )
    assert r.accepted is False


def test_accept_unknown_quest():
    q = AbductionRecoveryQuest()
    r = q.accept(
        captive_spawn_id="ghost", party_id="p", now_seconds=0,
    )
    assert r.accepted is False


def test_accept_wrong_stage():
    q = AbductionRecoveryQuest()
    q.post(
        captive_spawn_id="x", abductor_zone_id="z",
        bounty_gil=10, now_seconds=0,
    )
    q.accept(captive_spawn_id="x", party_id="p", now_seconds=1)
    # second accept should fail
    r = q.accept(captive_spawn_id="x", party_id="p", now_seconds=2)
    assert r.accepted is False


def test_extract_requires_engage():
    q = AbductionRecoveryQuest()
    q.post(
        captive_spawn_id="x", abductor_zone_id="z",
        bounty_gil=10, now_seconds=0,
    )
    q.accept(captive_spawn_id="x", party_id="p", now_seconds=1)
    # skipping engage
    r = q.extract(captive_spawn_id="x", now_seconds=2)
    assert r.accepted is False
    assert r.reason == "must engage first"


def test_engage_unknown():
    q = AbductionRecoveryQuest()
    r = q.engage(captive_spawn_id="ghost", now_seconds=0)
    assert r.accepted is False


def test_tick_expiry_marks_expired():
    q = AbductionRecoveryQuest()
    q.post(
        captive_spawn_id="x", abductor_zone_id="z",
        bounty_gil=10, now_seconds=0,
    )
    q.accept(captive_spawn_id="x", party_id="p", now_seconds=10)
    expired = q.tick_expiry(now_seconds=10 + EXPIRY_SECONDS + 1)
    assert "x" in expired
    rec = q.status(captive_spawn_id="x")
    assert rec.stage == QuestStage.EXPIRED


def test_tick_expiry_skips_extracted():
    q = AbductionRecoveryQuest()
    q.post(
        captive_spawn_id="x", abductor_zone_id="z",
        bounty_gil=10, now_seconds=0,
    )
    q.accept(captive_spawn_id="x", party_id="p", now_seconds=1)
    q.engage(captive_spawn_id="x", now_seconds=2)
    q.extract(captive_spawn_id="x", now_seconds=3)
    # even much later, no expiry change
    expired = q.tick_expiry(now_seconds=999_999)
    assert "x" not in expired


def test_open_quests_filters_terminal():
    q = AbductionRecoveryQuest()
    q.post(
        captive_spawn_id="a", abductor_zone_id="z",
        bounty_gil=10, now_seconds=0,
    )
    q.post(
        captive_spawn_id="b", abductor_zone_id="z",
        bounty_gil=10, now_seconds=0,
    )
    q.accept(captive_spawn_id="b", party_id="p", now_seconds=1)
    q.engage(captive_spawn_id="b", now_seconds=2)
    q.extract(captive_spawn_id="b", now_seconds=3)
    open_now = q.open_quests()
    ids = {r.captive_spawn_id for r in open_now}
    assert ids == {"a"}


def test_status_unknown_returns_none():
    q = AbductionRecoveryQuest()
    assert q.status(captive_spawn_id="ghost") is None


def test_held_by_party_recorded():
    q = AbductionRecoveryQuest()
    q.post(
        captive_spawn_id="x", abductor_zone_id="z",
        bounty_gil=10, now_seconds=0,
    )
    q.accept(captive_spawn_id="x", party_id="alpha", now_seconds=1)
    assert q.status(captive_spawn_id="x").held_by_party == "alpha"


def test_extract_preserves_bounty_gil_amount():
    q = AbductionRecoveryQuest()
    q.post(
        captive_spawn_id="x", abductor_zone_id="z",
        bounty_gil=12_345, now_seconds=0,
    )
    q.accept(captive_spawn_id="x", party_id="p", now_seconds=1)
    q.engage(captive_spawn_id="x", now_seconds=2)
    r = q.extract(captive_spawn_id="x", now_seconds=3)
    assert r.awarded_gil == 12_345
