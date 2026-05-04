"""Tests for floating damage numbers."""
from __future__ import annotations

from server.floating_damage_numbers import (
    DEFAULT_SIZE_PCT,
    ElementTint,
    FloatingDamageNumbers,
    MAX_LIFESPAN,
    MAX_SIZE_PCT,
    MIN_LIFESPAN,
    MIN_SIZE_PCT,
    PopupKind,
)


def test_emit_creates_popup():
    f = FloatingDamageNumbers()
    p = f.emit(
        target_id="orc_a",
        attacker_id="alice",
        kind=PopupKind.DAMAGE,
        amount=215,
        element=ElementTint.FIRE,
        zone_id="ronfaure",
        now_seconds=0.0,
    )
    assert p.amount == 215
    assert p.element == ElementTint.FIRE


def test_crit_emphasis_amps_size():
    f = FloatingDamageNumbers()
    normal = f.emit(
        target_id="x", zone_id="z",
        kind=PopupKind.DAMAGE, amount=100,
        size_pct=100, is_crit=False,
    )
    crit = f.emit(
        target_id="x", zone_id="z",
        kind=PopupKind.DAMAGE, amount=200,
        size_pct=100, is_crit=True,
    )
    assert crit.size_pct > normal.size_pct


def test_size_clamps_to_max():
    f = FloatingDamageNumbers()
    p = f.emit(
        target_id="x", zone_id="z",
        amount=10, size_pct=999,
    )
    assert p.size_pct == MAX_SIZE_PCT


def test_size_clamps_to_min():
    f = FloatingDamageNumbers()
    p = f.emit(
        target_id="x", zone_id="z",
        amount=10, size_pct=10,
    )
    assert p.size_pct == MIN_SIZE_PCT


def test_lifespan_clamps():
    f = FloatingDamageNumbers()
    p = f.emit(
        target_id="x", zone_id="z",
        amount=10, lifespan_seconds=999.0,
        now_seconds=0.0,
    )
    assert p.expires_at_seconds == MAX_LIFESPAN
    p2 = f.emit(
        target_id="x", zone_id="z",
        amount=10, lifespan_seconds=0.01,
        now_seconds=0.0,
    )
    assert p2.expires_at_seconds == MIN_LIFESPAN


def test_default_color_for_heal():
    f = FloatingDamageNumbers()
    p = f.emit(
        target_id="x", zone_id="z",
        kind=PopupKind.HEAL, amount=100,
    )
    assert p.color == "lime"


def test_default_color_for_miss():
    f = FloatingDamageNumbers()
    p = f.emit(
        target_id="x", zone_id="z",
        kind=PopupKind.MISS, amount=0,
    )
    assert p.color == "gray"


def test_default_color_for_resist():
    f = FloatingDamageNumbers()
    p = f.emit(
        target_id="x", zone_id="z",
        kind=PopupKind.RESIST, amount=0,
    )
    assert p.color == "blue"


def test_element_tint_for_damage():
    f = FloatingDamageNumbers()
    p = f.emit(
        target_id="x", zone_id="z",
        kind=PopupKind.DAMAGE, amount=100,
        element=ElementTint.ICE,
    )
    assert p.color.startswith("#") and "cc" in p.color


def test_explicit_color_overrides():
    f = FloatingDamageNumbers()
    p = f.emit(
        target_id="x", zone_id="z",
        amount=10, color="#deadbeef",
    )
    assert p.color == "#deadbeef"


def test_prefs_default():
    f = FloatingDamageNumbers()
    p = f.prefs_for(player_id="alice")
    assert p.enabled
    assert p.size_pct == DEFAULT_SIZE_PCT


def test_set_pref_size_clamps():
    f = FloatingDamageNumbers()
    f.set_pref(player_id="alice", size_pct=99999)
    assert f.prefs_for(
        player_id="alice",
    ).size_pct == MAX_SIZE_PCT


def test_disabled_prefs_returns_empty_popups():
    f = FloatingDamageNumbers()
    f.set_pref(player_id="alice", enabled=False)
    f.emit(
        target_id="alice", zone_id="z",
        amount=100,
    )
    popups = f.current_popups(
        viewer_id="alice", viewer_zone_id="z",
    )
    assert popups == ()


def test_show_others_off_hides_unrelated():
    f = FloatingDamageNumbers()
    f.set_pref(player_id="alice", show_others=False)
    f.emit(
        target_id="bob", attacker_id="carol",
        zone_id="z", amount=10,
    )
    popups = f.current_popups(
        viewer_id="alice", viewer_zone_id="z",
    )
    assert popups == ()


def test_show_others_off_keeps_self_target():
    f = FloatingDamageNumbers()
    f.set_pref(player_id="alice", show_others=False)
    f.emit(
        target_id="alice", attacker_id="orc",
        zone_id="z", amount=10,
    )
    popups = f.current_popups(
        viewer_id="alice", viewer_zone_id="z",
    )
    assert len(popups) == 1


def test_show_others_off_keeps_self_attacker():
    f = FloatingDamageNumbers()
    f.set_pref(player_id="alice", show_others=False)
    f.emit(
        target_id="orc", attacker_id="alice",
        zone_id="z", amount=10,
    )
    popups = f.current_popups(
        viewer_id="alice", viewer_zone_id="z",
    )
    assert len(popups) == 1


def test_other_zone_filtered():
    f = FloatingDamageNumbers()
    f.emit(
        target_id="orc", zone_id="other",
        amount=10,
    )
    popups = f.current_popups(
        viewer_id="alice", viewer_zone_id="z",
    )
    assert popups == ()


def test_tick_expires_old_popups():
    f = FloatingDamageNumbers()
    f.emit(
        target_id="orc", zone_id="z", amount=10,
        lifespan_seconds=1.0, now_seconds=0.0,
    )
    expired = f.tick(now_seconds=10.0)
    assert len(expired) == 1
    assert f.total_active() == 0


def test_popups_sorted_recent_first():
    f = FloatingDamageNumbers()
    f.emit(
        target_id="orc", zone_id="z", amount=10,
        now_seconds=0.0,
    )
    f.emit(
        target_id="orc", zone_id="z", amount=20,
        now_seconds=1.0,
    )
    popups = f.current_popups(
        viewer_id="alice", viewer_zone_id="z",
    )
    assert popups[0].amount == 20


def test_total_active():
    f = FloatingDamageNumbers()
    f.emit(target_id="x", zone_id="z", amount=1)
    f.emit(target_id="y", zone_id="z", amount=2)
    assert f.total_active() == 2
