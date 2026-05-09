"""Tests for player_gossip_column."""
from __future__ import annotations

from server.player_gossip_column import (
    PlayerGossipColumnSystem, TipState,
)


def _start(s: PlayerGossipColumnSystem) -> str:
    return s.start_column(
        columnist_id="naji", name="The Whisper",
        byline="By Naji of Bastok",
    )


def test_start_happy():
    s = PlayerGossipColumnSystem()
    assert _start(s) is not None


def test_start_empty_byline_blocked():
    s = PlayerGossipColumnSystem()
    assert s.start_column(
        columnist_id="naji", name="x", byline="",
    ) is None


def test_submit_tip_happy():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="cara cheats at cards",
    )
    assert tid is not None


def test_submit_tip_columnist_as_tipster_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    assert s.submit_tip(
        column_id=cid, tipster_id="naji",
        subject_id="cara", claim="x",
    ) is None


def test_submit_tip_subject_equals_tipster_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    assert s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="bob", claim="x",
    ) is None


def test_submit_tip_subject_is_columnist_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    assert s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="naji", claim="x",
    ) is None


def test_submit_tip_empty_claim_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    assert s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="",
    ) is None


def test_publish_tip_happy():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    assert s.publish_tip(
        column_id=cid, tip_id=tid, columnist_id="naji",
    ) is True
    assert s.tip(
        column_id=cid, tip_id=tid,
    ).state == TipState.PUBLISHED


def test_publish_tip_wrong_columnist_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    assert s.publish_tip(
        column_id=cid, tip_id=tid, columnist_id="bob",
    ) is False


def test_publish_tip_after_reject_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    s.reject_tip(
        column_id=cid, tip_id=tid, columnist_id="naji",
    )
    assert s.publish_tip(
        column_id=cid, tip_id=tid, columnist_id="naji",
    ) is False


def test_reject_tip_happy():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    assert s.reject_tip(
        column_id=cid, tip_id=tid, columnist_id="naji",
    ) is True


def test_offer_hush_happy():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    assert s.offer_hush(
        column_id=cid, tip_id=tid,
        subject_id="cara", gil_offered=1000,
    ) is True
    assert s.tip(
        column_id=cid, tip_id=tid,
    ).state == TipState.SUPPRESSED


def test_offer_hush_pays_columnist():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    s.offer_hush(
        column_id=cid, tip_id=tid,
        subject_id="cara", gil_offered=1500,
    )
    assert s.column(
        column_id=cid,
    ).earnings_gil == 1500


def test_offer_hush_wrong_subject_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    assert s.offer_hush(
        column_id=cid, tip_id=tid,
        subject_id="bob", gil_offered=1000,
    ) is False


def test_offer_hush_below_floor_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    assert s.offer_hush(
        column_id=cid, tip_id=tid,
        subject_id="cara", gil_offered=100,
    ) is False


def test_offer_hush_after_publish_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    s.publish_tip(
        column_id=cid, tip_id=tid, columnist_id="naji",
    )
    assert s.offer_hush(
        column_id=cid, tip_id=tid,
        subject_id="cara", gil_offered=2000,
    ) is False


def test_publish_after_hush_blocked():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="bob",
        subject_id="cara", claim="x",
    )
    s.offer_hush(
        column_id=cid, tip_id=tid,
        subject_id="cara", gil_offered=1000,
    )
    assert s.publish_tip(
        column_id=cid, tip_id=tid, columnist_id="naji",
    ) is False


def test_tips_by_subject_lookup():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    s.submit_tip(
        column_id=cid, tipster_id="b", subject_id="c",
        claim="x",
    )
    s.submit_tip(
        column_id=cid, tipster_id="d", subject_id="c",
        claim="y",
    )
    s.submit_tip(
        column_id=cid, tipster_id="e", subject_id="f",
        claim="z",
    )
    assert len(s.tips_by_subject(
        column_id=cid, subject_id="c",
    )) == 2


def test_published_count():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    tid = s.submit_tip(
        column_id=cid, tipster_id="b", subject_id="c",
        claim="x",
    )
    s.publish_tip(
        column_id=cid, tip_id=tid, columnist_id="naji",
    )
    assert s.published_count(column_id=cid) == 1


def test_unknown_column():
    s = PlayerGossipColumnSystem()
    assert s.column(column_id="ghost") is None


def test_unknown_tip():
    s = PlayerGossipColumnSystem()
    cid = _start(s)
    assert s.tip(
        column_id=cid, tip_id="ghost",
    ) is None


def test_enum_count():
    assert len(list(TipState)) == 4
