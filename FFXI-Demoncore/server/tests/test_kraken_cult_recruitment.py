"""Tests for kraken cult recruitment."""
from __future__ import annotations

from server.kraken_cult_recruitment import (
    HookKind,
    KrakenCultRecruitment,
    SessionStage,
)


def test_approach_happy():
    r = KrakenCultRecruitment()
    s = r.approach(
        player_id="p", hook=HookKind.KRAKEN_FELLED,
        now_seconds=0,
    )
    assert s.accepted is True
    assert s.new_stage == SessionStage.PROPOSED


def test_approach_blank_player():
    r = KrakenCultRecruitment()
    s = r.approach(
        player_id="", hook=HookKind.KRAKEN_FELLED,
        now_seconds=0,
    )
    assert s.accepted is False


def test_approach_blocks_active_session():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.KRAKEN_FELLED, now_seconds=0,
    )
    s = r.approach(
        player_id="p", hook=HookKind.VOID_KILLER, now_seconds=10,
    )
    assert s.accepted is False
    assert s.reason == "session in progress"


def test_approach_after_refusal_succeeds():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.KRAKEN_FELLED, now_seconds=0,
    )
    r.refuse(player_id="p", now_seconds=10)
    # cult walked away — they may approach again later
    s = r.approach(
        player_id="p", hook=HookKind.VOID_KILLER, now_seconds=100,
    )
    assert s.accepted is True


def test_accept_step_advances_proposed_to_accepted():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.OUTLAW_TRIBUTARY, now_seconds=0,
    )
    s = r.accept_step(player_id="p", now_seconds=10)
    assert s.new_stage == SessionStage.ACCEPTED
    assert s.corruption_gained == 5


def test_accept_step_full_chain_to_pledge():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.KRAKEN_FELLED, now_seconds=0,
    )
    r.accept_step(player_id="p", now_seconds=1)   # ACCEPTED
    r.accept_step(player_id="p", now_seconds=2)   # ESCALATED
    s = r.accept_step(player_id="p", now_seconds=3)  # PLEDGED
    assert s.new_stage == SessionStage.PLEDGED
    assert s.pledge_unlocks_ritual is True
    assert s.corruption_gained == 30


def test_accept_step_without_session():
    r = KrakenCultRecruitment()
    s = r.accept_step(player_id="p", now_seconds=0)
    assert s.accepted is False


def test_refuse_at_proposed():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.KRAKEN_FELLED, now_seconds=0,
    )
    s = r.refuse(player_id="p", now_seconds=10)
    assert s.accepted is True
    assert s.new_stage == SessionStage.REFUSED
    assert r.session(player_id="p").cult_remembers is True


def test_refuse_after_partial_accept():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.KRAKEN_FELLED, now_seconds=0,
    )
    r.accept_step(player_id="p", now_seconds=10)
    s = r.refuse(player_id="p", now_seconds=20)
    assert s.accepted is True
    assert s.new_stage == SessionStage.REFUSED


def test_refuse_after_pledge_blocked():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.KRAKEN_FELLED, now_seconds=0,
    )
    r.accept_step(player_id="p", now_seconds=1)
    r.accept_step(player_id="p", now_seconds=2)
    r.accept_step(player_id="p", now_seconds=3)  # PLEDGED
    s = r.refuse(player_id="p", now_seconds=4)
    assert s.accepted is False
    assert s.reason == "cannot refuse after pledge"


def test_double_refuse_blocked():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.KRAKEN_FELLED, now_seconds=0,
    )
    r.refuse(player_id="p", now_seconds=10)
    s = r.refuse(player_id="p", now_seconds=20)
    assert s.accepted is False


def test_refuse_without_session():
    r = KrakenCultRecruitment()
    s = r.refuse(player_id="p", now_seconds=0)
    assert s.accepted is False


def test_session_records_hook():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.SUNKEN_CROWN_KILLER, now_seconds=42,
    )
    rec = r.session(player_id="p")
    assert rec.hook == HookKind.SUNKEN_CROWN_KILLER
    assert rec.proposed_at == 42


def test_corruption_only_on_acceptance():
    r = KrakenCultRecruitment()
    r.approach(
        player_id="p", hook=HookKind.KRAKEN_FELLED, now_seconds=0,
    )
    s = r.refuse(player_id="p", now_seconds=10)
    # refusal grants no corruption
    assert s.corruption_gained == 0
