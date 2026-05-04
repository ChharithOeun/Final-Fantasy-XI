"""Tests for the world announcement banner."""
from __future__ import annotations

from server.world_announcement_banner import (
    AudienceScope,
    BannerTier,
    WorldAnnouncementBanner,
)


def test_post_creates_banner():
    w = WorldAnnouncementBanner()
    b = w.post(
        message="A great evil stirs.",
        tier=BannerTier.TIER_OMEN,
    )
    assert b is not None


def test_post_empty_rejected():
    w = WorldAnnouncementBanner()
    assert w.post(
        message="", tier=BannerTier.TIER_INFO,
    ) is None


def test_post_non_server_scope_requires_target():
    w = WorldAnnouncementBanner()
    assert w.post(
        message="raid imminent",
        tier=BannerTier.TIER_ALERT,
        scope=AudienceScope.NATION,
        target_id=None,
    ) is None


def test_pending_for_server_scope_visible_to_all():
    w = WorldAnnouncementBanner()
    w.post(
        message="server-first kill!",
        tier=BannerTier.TIER_NOTABLE,
    )
    pending = w.pending_for(viewer_id="alice")
    assert len(pending) == 1


def test_nation_scope_filters_correctly():
    w = WorldAnnouncementBanner()
    w.post(
        message="bastok rallies!",
        tier=BannerTier.TIER_ALERT,
        scope=AudienceScope.NATION,
        target_id="bastok",
    )
    pending_b = w.pending_for(
        viewer_id="alice", viewer_nation="bastok",
    )
    assert len(pending_b) == 1
    pending_w = w.pending_for(
        viewer_id="alice", viewer_nation="windurst",
    )
    assert len(pending_w) == 0


def test_linkshell_scope():
    w = WorldAnnouncementBanner()
    w.post(
        message="LS event!",
        tier=BannerTier.TIER_INFO,
        scope=AudienceScope.LINKSHELL,
        target_id="VanguardLS",
    )
    p = w.pending_for(
        viewer_id="alice",
        viewer_linkshells=("VanguardLS",),
    )
    assert len(p) == 1
    p2 = w.pending_for(
        viewer_id="alice",
        viewer_linkshells=("Other",),
    )
    assert len(p2) == 0


def test_personal_scope():
    w = WorldAnnouncementBanner()
    w.post(
        message="You ascended!",
        tier=BannerTier.TIER_NOTABLE,
        scope=AudienceScope.PERSONAL,
        target_id="alice",
    )
    p_a = w.pending_for(viewer_id="alice")
    p_b = w.pending_for(viewer_id="bob")
    assert len(p_a) == 1
    assert len(p_b) == 0


def test_higher_tier_comes_first():
    w = WorldAnnouncementBanner()
    w.post(
        message="info",
        tier=BannerTier.TIER_INFO,
    )
    w.post(
        message="critical",
        tier=BannerTier.TIER_CRITICAL,
    )
    pending = w.pending_for(viewer_id="alice")
    assert pending[0].tier == BannerTier.TIER_CRITICAL


def test_ack_hides_banner():
    w = WorldAnnouncementBanner()
    b = w.post(
        message="x", tier=BannerTier.TIER_INFO,
    )
    assert w.ack(viewer_id="alice", banner_id=b.banner_id)
    pending = w.pending_for(viewer_id="alice")
    assert len(pending) == 0


def test_ack_unknown_returns_false():
    w = WorldAnnouncementBanner()
    assert not w.ack(
        viewer_id="alice", banner_id="ghost",
    )


def test_ack_only_for_acker():
    w = WorldAnnouncementBanner()
    b = w.post(
        message="x", tier=BannerTier.TIER_INFO,
    )
    w.ack(viewer_id="alice", banner_id=b.banner_id)
    pending_b = w.pending_for(viewer_id="bob")
    assert len(pending_b) == 1


def test_tick_expires_banners():
    w = WorldAnnouncementBanner()
    w.post(
        message="x", tier=BannerTier.TIER_INFO,
        now_seconds=0.0,
    )
    expired = w.tick(now_seconds=100.0)
    assert len(expired) == 1
    assert w.total_active() == 0


def test_tick_keeps_active():
    w = WorldAnnouncementBanner()
    w.post(
        message="x", tier=BannerTier.TIER_INFO,
        now_seconds=0.0,
    )
    expired = w.tick(now_seconds=1.0)
    assert expired == ()


def test_explicit_duration_overrides():
    w = WorldAnnouncementBanner()
    b = w.post(
        message="x", tier=BannerTier.TIER_INFO,
        now_seconds=0.0, duration_seconds=999.0,
    )
    assert b.expires_at_seconds == 999.0


def test_default_duration_per_tier():
    w = WorldAnnouncementBanner()
    info = w.post(
        message="i", tier=BannerTier.TIER_INFO,
        now_seconds=0.0,
    )
    crit = w.post(
        message="c", tier=BannerTier.TIER_CRITICAL,
        now_seconds=0.0,
    )
    assert (
        crit.expires_at_seconds > info.expires_at_seconds
    )


def test_total_active():
    w = WorldAnnouncementBanner()
    w.post(message="a", tier=BannerTier.TIER_INFO)
    w.post(message="b", tier=BannerTier.TIER_INFO)
    assert w.total_active() == 2
