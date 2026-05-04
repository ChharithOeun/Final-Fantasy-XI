"""Tests for the boss phase telegraph."""
from __future__ import annotations

from server.boss_phase_telegraph import (
    BossPhaseTelegraph,
    TelegraphKind,
    TelegraphSeverity,
)


def test_post_creates_telegraph():
    b = BossPhaseTelegraph()
    t = b.post_telegraph(
        boss_id="fafnir",
        kind=TelegraphKind.PHASE_SHIFT,
        severity=TelegraphSeverity.HIGH,
    )
    assert t is not None
    assert t.color == "orange"


def test_post_empty_boss_rejected():
    b = BossPhaseTelegraph()
    assert b.post_telegraph(
        boss_id="", kind=TelegraphKind.PHASE_SHIFT,
    ) is None


def test_default_title_from_kind():
    b = BossPhaseTelegraph()
    t = b.post_telegraph(
        boss_id="fafnir",
        kind=TelegraphKind.WS_WINDUP,
    )
    assert "Windup" in t.title


def test_severity_color_mapping():
    b = BossPhaseTelegraph()
    pairs = (
        (TelegraphSeverity.LOW, "white"),
        (TelegraphSeverity.MED, "yellow"),
        (TelegraphSeverity.HIGH, "orange"),
        (TelegraphSeverity.EXTREME, "red"),
    )
    for sev, color in pairs:
        b2 = BossPhaseTelegraph()
        t = b2.post_telegraph(
            boss_id="x",
            kind=TelegraphKind.PHASE_SHIFT,
            severity=sev,
        )
        assert t.color == color


def test_active_for_boss_filter():
    b = BossPhaseTelegraph()
    b.post_telegraph(
        boss_id="fafnir", kind=TelegraphKind.PHASE_SHIFT,
    )
    b.post_telegraph(
        boss_id="behemoth", kind=TelegraphKind.PHASE_SHIFT,
    )
    actives = b.active_for_boss("fafnir")
    assert len(actives) == 1


def test_visible_to_filters_acked():
    b = BossPhaseTelegraph()
    t = b.post_telegraph(
        boss_id="fafnir",
        kind=TelegraphKind.ADAPTATION_REVEAL,
    )
    b.ack(viewer_id="alice", telegraph_id=t.telegraph_id)
    visible = b.visible_to(
        viewer_id="alice", boss_id="fafnir",
    )
    assert visible == ()


def test_visible_to_ignores_other_bosses():
    b = BossPhaseTelegraph()
    b.post_telegraph(
        boss_id="other", kind=TelegraphKind.PHASE_SHIFT,
    )
    visible = b.visible_to(
        viewer_id="alice", boss_id="fafnir",
    )
    assert visible == ()


def test_visible_to_orders_extreme_first():
    b = BossPhaseTelegraph()
    b.post_telegraph(
        boss_id="fafnir",
        kind=TelegraphKind.PHASE_SHIFT,
        severity=TelegraphSeverity.LOW,
        now_seconds=10.0,
    )
    b.post_telegraph(
        boss_id="fafnir",
        kind=TelegraphKind.ENRAGE_INCOMING,
        severity=TelegraphSeverity.EXTREME,
        now_seconds=0.0,
    )
    visible = b.visible_to(
        viewer_id="alice", boss_id="fafnir",
    )
    assert visible[0].severity == TelegraphSeverity.EXTREME


def test_ack_unknown_returns_false():
    b = BossPhaseTelegraph()
    assert not b.ack(
        viewer_id="alice", telegraph_id="ghost",
    )


def test_ack_only_for_acker():
    b = BossPhaseTelegraph()
    t = b.post_telegraph(
        boss_id="fafnir",
        kind=TelegraphKind.WEAKPOINT_OPEN,
    )
    b.ack(viewer_id="alice", telegraph_id=t.telegraph_id)
    bob_view = b.visible_to(
        viewer_id="bob", boss_id="fafnir",
    )
    assert len(bob_view) == 1


def test_tick_expires_old():
    b = BossPhaseTelegraph()
    b.post_telegraph(
        boss_id="x", kind=TelegraphKind.PHASE_SHIFT,
        now_seconds=0.0,
    )
    expired = b.tick(now_seconds=100.0)
    assert len(expired) == 1
    assert b.total_active() == 0


def test_tick_keeps_fresh():
    b = BossPhaseTelegraph()
    b.post_telegraph(
        boss_id="x", kind=TelegraphKind.PHASE_SHIFT,
        now_seconds=0.0,
    )
    expired = b.tick(now_seconds=1.0)
    assert expired == ()


def test_explicit_duration_overrides():
    b = BossPhaseTelegraph()
    t = b.post_telegraph(
        boss_id="x", kind=TelegraphKind.PHASE_SHIFT,
        now_seconds=0.0,
        duration_seconds=999.0,
    )
    assert t.expires_at_seconds == 999.0


def test_get_unknown_returns_none():
    b = BossPhaseTelegraph()
    assert b.get("ghost") is None


def test_total_active():
    b = BossPhaseTelegraph()
    b.post_telegraph(
        boss_id="x", kind=TelegraphKind.PHASE_SHIFT,
    )
    b.post_telegraph(
        boss_id="y", kind=TelegraphKind.PHASE_SHIFT,
    )
    assert b.total_active() == 2


def test_explicit_title_used():
    b = BossPhaseTelegraph()
    t = b.post_telegraph(
        boss_id="x", kind=TelegraphKind.PHASE_SHIFT,
        title="Phase Two: The Inferno",
    )
    assert t.title == "Phase Two: The Inferno"
