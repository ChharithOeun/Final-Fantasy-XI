"""Tests for cult redemption quest."""
from __future__ import annotations

from server.cult_redemption_quest import (
    CultRedemptionQuest,
    RedemptionStage,
    SEAPEARL_TRIBUTE_REQUIRED,
    VIGIL_DURATION_SECONDS,
)


def test_petition_happy():
    q = CultRedemptionQuest()
    r = q.petition(player_id="p", hollowed=True, now_seconds=0)
    assert r.accepted is True
    assert r.new_stage == RedemptionStage.PETITIONED


def test_petition_not_hollowed():
    q = CultRedemptionQuest()
    r = q.petition(player_id="p", hollowed=False, now_seconds=0)
    assert r.accepted is False


def test_petition_blank_player():
    q = CultRedemptionQuest()
    r = q.petition(player_id="", hollowed=True, now_seconds=0)
    assert r.accepted is False


def test_pay_tribute_insufficient():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=0)
    r = q.pay_tribute(
        player_id="p", seapearls_paid=10, now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "insufficient tribute"


def test_pay_tribute_happy():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=0)
    r = q.pay_tribute(
        player_id="p",
        seapearls_paid=SEAPEARL_TRIBUTE_REQUIRED,
        now_seconds=10,
    )
    assert r.accepted is True
    assert r.pearls_consumed == SEAPEARL_TRIBUTE_REQUIRED


def test_pay_tribute_without_petition():
    q = CultRedemptionQuest()
    r = q.pay_tribute(
        player_id="p",
        seapearls_paid=SEAPEARL_TRIBUTE_REQUIRED,
        now_seconds=10,
    )
    assert r.accepted is False


def test_vigil_duration_required():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=0)
    q.pay_tribute(
        player_id="p",
        seapearls_paid=SEAPEARL_TRIBUTE_REQUIRED, now_seconds=1,
    )
    q.begin_vigil(player_id="p", now_seconds=2)
    # try to complete too soon
    r = q.complete_vigil(
        player_id="p", combat_during=False,
        now_seconds=2 + 100,
    )
    assert r.accepted is False
    assert r.reason == "vigil too short"


def test_vigil_complete_clean():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=0)
    q.pay_tribute(
        player_id="p",
        seapearls_paid=SEAPEARL_TRIBUTE_REQUIRED, now_seconds=1,
    )
    q.begin_vigil(player_id="p", now_seconds=2)
    r = q.complete_vigil(
        player_id="p", combat_during=False,
        now_seconds=2 + VIGIL_DURATION_SECONDS + 1,
    )
    assert r.accepted is True
    assert r.new_stage == RedemptionStage.CONFESSION_TWO


def test_vigil_broken_resets_to_petitioned():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=0)
    q.pay_tribute(
        player_id="p",
        seapearls_paid=SEAPEARL_TRIBUTE_REQUIRED, now_seconds=1,
    )
    q.begin_vigil(player_id="p", now_seconds=2)
    r = q.complete_vigil(
        player_id="p", combat_during=True,
        now_seconds=2 + VIGIL_DURATION_SECONDS + 1,
    )
    assert r.accepted is True
    assert r.new_stage == RedemptionStage.PETITIONED
    rec = q.status(player_id="p")
    assert rec.tribute_paid_at is None


def test_face_priest_requires_confession_stage():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=0)
    r = q.face_priest(
        player_id="p", priest_killed=True, now_seconds=10,
    )
    assert r.accepted is False


def test_purify_requires_confession_first():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=0)
    q.pay_tribute(
        player_id="p",
        seapearls_paid=SEAPEARL_TRIBUTE_REQUIRED, now_seconds=1,
    )
    q.begin_vigil(player_id="p", now_seconds=2)
    q.complete_vigil(
        player_id="p", combat_during=False,
        now_seconds=2 + VIGIL_DURATION_SECONDS + 1,
    )
    # at CONFESSION_TWO; purify requires face_priest first
    r = q.purify(player_id="p", now_seconds=100)
    assert r.accepted is False
    assert r.reason == "must face priest"


def test_full_redemption_chain():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=0)
    q.pay_tribute(
        player_id="p",
        seapearls_paid=SEAPEARL_TRIBUTE_REQUIRED, now_seconds=1,
    )
    q.begin_vigil(player_id="p", now_seconds=2)
    q.complete_vigil(
        player_id="p", combat_during=False,
        now_seconds=2 + VIGIL_DURATION_SECONDS + 1,
    )
    q.face_priest(
        player_id="p", priest_killed=True,
        now_seconds=2 + VIGIL_DURATION_SECONDS + 100,
    )
    r = q.purify(
        player_id="p",
        now_seconds=2 + VIGIL_DURATION_SECONDS + 200,
    )
    assert r.accepted is True
    assert r.new_stage == RedemptionStage.PURIFIED
    assert r.taint_cleansed == 100
    assert r.abilities_revoked is True


def test_petition_already_in_quest_blocked():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=0)
    r = q.petition(player_id="p", hollowed=True, now_seconds=10)
    assert r.accepted is False


def test_status_returns_record():
    q = CultRedemptionQuest()
    q.petition(player_id="p", hollowed=True, now_seconds=42)
    rec = q.status(player_id="p")
    assert rec is not None
    assert rec.petitioned_at == 42
