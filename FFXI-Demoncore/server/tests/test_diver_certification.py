"""Tests for diver certification."""
from __future__ import annotations

from server.diver_certification import DiverCertification, DiverTier


def test_no_certs_zero_depth():
    d = DiverCertification()
    assert d.max_certified_depth(player_id="p") == 0
    assert d.can_descend_to(player_id="p", depth_yalms=10) is False


def test_grant_shallows_then_dive_50():
    d = DiverCertification()
    g = d.grant(
        player_id="p",
        tier=DiverTier.SHALLOWS_PERMIT,
        source="msq_intro",
        now_seconds=0,
    )
    assert g.accepted is True
    assert d.can_descend_to(player_id="p", depth_yalms=50) is True
    assert d.can_descend_to(player_id="p", depth_yalms=51) is False


def test_grant_deep_implies_shallower():
    d = DiverCertification()
    d.grant(
        player_id="p",
        tier=DiverTier.DEEP_PERMIT,
        source="brine_lozenge_quest",
        now_seconds=0,
    )
    assert d.can_descend_to(player_id="p", depth_yalms=300) is True
    assert d.can_descend_to(player_id="p", depth_yalms=200) is True


def test_grant_abyss_unlimited():
    d = DiverCertification()
    d.grant(
        player_id="p",
        tier=DiverTier.ABYSS_PERMIT,
        source="sunken_crown_sigils",
        now_seconds=0,
    )
    assert d.can_descend_to(player_id="p", depth_yalms=400) is True
    assert d.can_descend_to(player_id="p", depth_yalms=9_999) is True


def test_grant_duplicate_rejected():
    d = DiverCertification()
    d.grant(
        player_id="p",
        tier=DiverTier.SHALLOWS_PERMIT,
        source="x", now_seconds=0,
    )
    g = d.grant(
        player_id="p",
        tier=DiverTier.SHALLOWS_PERMIT,
        source="x", now_seconds=1,
    )
    assert g.accepted is False
    assert g.reason == "already granted"


def test_grant_blank_player():
    d = DiverCertification()
    g = d.grant(
        player_id="",
        tier=DiverTier.SHALLOWS_PERMIT,
        source="x", now_seconds=0,
    )
    assert g.accepted is False


def test_grant_blank_source():
    d = DiverCertification()
    g = d.grant(
        player_id="p",
        tier=DiverTier.SHALLOWS_PERMIT,
        source="", now_seconds=0,
    )
    assert g.accepted is False


def test_required_tier_for_depth():
    d = DiverCertification()
    assert d.required_tier_for(depth_yalms=0) == DiverTier.SHALLOWS_PERMIT
    assert d.required_tier_for(depth_yalms=50) == DiverTier.SHALLOWS_PERMIT
    assert d.required_tier_for(depth_yalms=100) == DiverTier.MID_DEPTH_PERMIT
    assert d.required_tier_for(depth_yalms=250) == DiverTier.DEEP_PERMIT
    assert d.required_tier_for(depth_yalms=400) == DiverTier.ABYSS_PERMIT


def test_required_tier_negative_none():
    d = DiverCertification()
    assert d.required_tier_for(depth_yalms=-1) is None


def test_max_depth_picks_highest_tier():
    d = DiverCertification()
    d.grant(
        player_id="p",
        tier=DiverTier.SHALLOWS_PERMIT,
        source="x", now_seconds=0,
    )
    d.grant(
        player_id="p",
        tier=DiverTier.MID_DEPTH_PERMIT,
        source="y", now_seconds=1,
    )
    assert d.max_certified_depth(player_id="p") == 150


def test_can_descend_negative_depth_rejected():
    d = DiverCertification()
    d.grant(
        player_id="p",
        tier=DiverTier.ABYSS_PERMIT,
        source="x", now_seconds=0,
    )
    assert d.can_descend_to(player_id="p", depth_yalms=-1) is False


def test_has_cert_negative_unknown_player():
    d = DiverCertification()
    assert d.has_cert(
        player_id="ghost", tier=DiverTier.ABYSS_PERMIT,
    ) is False


def test_has_cert_positive():
    d = DiverCertification()
    d.grant(
        player_id="p", tier=DiverTier.DEEP_PERMIT,
        source="x", now_seconds=0,
    )
    assert d.has_cert(
        player_id="p", tier=DiverTier.DEEP_PERMIT,
    ) is True
