"""Tests for telegraph_visibility_gate."""
from __future__ import annotations

from server.telegraph_visibility_gate import (
    TelegraphVisibilityGate,
    VisibilitySource,
)


def test_default_invisible():
    g = TelegraphVisibilityGate()
    assert g.is_visible(player_id="alice", now_seconds=0) is False


def test_grant_visibility():
    g = TelegraphVisibilityGate()
    ok = g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=10, expires_at=70,
    )
    assert ok is True
    assert g.is_visible(player_id="alice", now_seconds=20) is True


def test_blank_player_blocked():
    g = TelegraphVisibilityGate()
    ok = g.grant_visibility(
        player_id="", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=10, expires_at=70,
    )
    assert ok is False


def test_invalid_window_blocked():
    g = TelegraphVisibilityGate()
    ok = g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=70, expires_at=70,
    )
    assert ok is False


def test_visibility_expires():
    g = TelegraphVisibilityGate()
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.SKILLCHAIN_BONUS,
        granted_at=0, expires_at=8,
    )
    assert g.is_visible(player_id="alice", now_seconds=10) is False


def test_multiple_sources_stack():
    g = TelegraphVisibilityGate()
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=0, expires_at=120,
    )
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.BARD_FORESIGHT,
        granted_at=0, expires_at=180,
    )
    out = g.active_sources(player_id="alice", now_seconds=60)
    assert VisibilitySource.GEO_FORESIGHT in out
    assert VisibilitySource.BARD_FORESIGHT in out


def test_weaker_grant_doesnt_replace_stronger():
    g = TelegraphVisibilityGate()
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=0, expires_at=120,
    )
    ok = g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=0, expires_at=60,
    )
    assert ok is False


def test_stronger_grant_replaces_weaker():
    g = TelegraphVisibilityGate()
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=0, expires_at=60,
    )
    ok = g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=0, expires_at=120,
    )
    assert ok is True


def test_revoke_visibility():
    g = TelegraphVisibilityGate()
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=0, expires_at=120,
    )
    assert g.revoke_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
    ) is True
    assert g.is_visible(player_id="alice", now_seconds=30) is False


def test_revoke_unknown_returns_false():
    g = TelegraphVisibilityGate()
    assert g.revoke_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
    ) is False


def test_warning_bonus_zero_without_visibility():
    g = TelegraphVisibilityGate()
    bonus = g.effective_warning_bonus(
        player_id="alice", base_bonus_seconds=1.6,
        now_seconds=10,
    )
    assert bonus == 0.0


def test_warning_bonus_applies_with_visibility():
    g = TelegraphVisibilityGate()
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=0, expires_at=120,
    )
    bonus = g.effective_warning_bonus(
        player_id="alice", base_bonus_seconds=1.6,
        now_seconds=10,
    )
    assert bonus == 1.6


def test_partial_expiration():
    """If GEO expires but BARD still active, still visible."""
    g = TelegraphVisibilityGate()
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=0, expires_at=30,
    )
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.BARD_FORESIGHT,
        granted_at=0, expires_at=120,
    )
    assert g.is_visible(player_id="alice", now_seconds=60) is True
    out = g.active_sources(player_id="alice", now_seconds=60)
    assert VisibilitySource.GEO_FORESIGHT not in out
    assert VisibilitySource.BARD_FORESIGHT in out


def test_clear_player():
    g = TelegraphVisibilityGate()
    g.grant_visibility(
        player_id="alice", source=VisibilitySource.GEO_FORESIGHT,
        granted_at=0, expires_at=120,
    )
    g.clear(player_id="alice")
    assert g.is_visible(player_id="alice", now_seconds=30) is False


def test_active_sources_empty_for_unknown_player():
    g = TelegraphVisibilityGate()
    assert g.active_sources(
        player_id="ghost", now_seconds=10,
    ) == ()


def test_4_sources():
    """Four canonical sources."""
    assert len(list(VisibilitySource)) == 4
