"""Tests for the spell timer display."""
from __future__ import annotations

from server.spell_timer_display import (
    EffectKind,
    SpellTimerDisplay,
)


def test_apply_creates_effect():
    s = SpellTimerDisplay()
    assert s.apply(
        player_id="alice", effect_id="protect",
        label="Protect IV",
        kind=EffectKind.BUFF,
        remaining_seconds=1800.0,
    )


def test_apply_zero_remaining_rejected():
    s = SpellTimerDisplay()
    assert not s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=0,
    )


def test_apply_negative_remaining_rejected():
    s = SpellTimerDisplay()
    assert not s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=-5,
    )


def test_apply_overwrites_existing():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=100,
    )
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=300,
    )
    timers = s.timers_for(player_id="alice")
    assert timers[0].remaining_seconds == 300
    assert timers[0].initial_seconds == 300


def test_extend_adds_time():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=100,
    )
    s.extend(
        player_id="alice", effect_id="x",
        by_seconds=50,
    )
    timers = s.timers_for(player_id="alice")
    assert timers[0].remaining_seconds == 150


def test_extend_unknown():
    s = SpellTimerDisplay()
    assert not s.extend(
        player_id="alice", effect_id="ghost",
        by_seconds=10,
    )


def test_extend_zero_rejected():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=100,
    )
    assert not s.extend(
        player_id="alice", effect_id="x",
        by_seconds=0,
    )


def test_remove_effect():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=100,
    )
    assert s.remove(
        player_id="alice", effect_id="x",
    )
    assert s.total_effects(player_id="alice") == 0


def test_remove_unknown():
    s = SpellTimerDisplay()
    assert not s.remove(
        player_id="alice", effect_id="ghost",
    )


def test_tick_decrements():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=100,
    )
    s.tick(player_id="alice", elapsed_seconds=10)
    timers = s.timers_for(player_id="alice")
    assert timers[0].remaining_seconds == 90


def test_tick_expires_below_zero():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=10,
    )
    expired = s.tick(
        player_id="alice", elapsed_seconds=20,
    )
    assert "x" in expired
    assert s.total_effects(player_id="alice") == 0


def test_tick_zero_no_change():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=100,
    )
    expired = s.tick(
        player_id="alice", elapsed_seconds=0,
    )
    assert expired == ()


def test_warning_flag_when_low():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=3,
        warning_at_remaining=5.0,
    )
    timers = s.timers_for(player_id="alice")
    assert timers[0].is_warning
    assert timers[0].color_hint == "red"


def test_debuff_purple_color():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="poison",
        label="Poison",
        kind=EffectKind.DEBUFF,
        remaining_seconds=180,
        warning_at_remaining=5.0,
    )
    timers = s.timers_for(player_id="alice")
    assert timers[0].color_hint == "purple"


def test_debuffs_sort_before_buffs():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="b",
        label="Buff",
        kind=EffectKind.BUFF,
        remaining_seconds=300,
    )
    s.apply(
        player_id="alice", effect_id="d",
        label="Debuff",
        kind=EffectKind.DEBUFF,
        remaining_seconds=300,
    )
    timers = s.timers_for(player_id="alice")
    assert timers[0].kind == EffectKind.DEBUFF


def test_within_group_sorted_soon_first():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="long",
        label="long", kind=EffectKind.BUFF,
        remaining_seconds=600,
    )
    s.apply(
        player_id="alice", effect_id="short",
        label="short", kind=EffectKind.BUFF,
        remaining_seconds=30,
    )
    timers = s.timers_for(player_id="alice")
    # Within BUFF group, "short" comes first (sooner expiry)
    buff_timers = [t for t in timers if t.kind == EffectKind.BUFF]
    assert buff_timers[0].effect_id == "short"


def test_priority_override_floats():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="long",
        label="long", kind=EffectKind.BUFF,
        remaining_seconds=600,
    )
    s.apply(
        player_id="alice", effect_id="rr",
        label="Reraise", kind=EffectKind.BUFF,
        remaining_seconds=999,
        priority_override=True,
    )
    timers = s.timers_for(player_id="alice")
    buff_timers = [t for t in timers if t.kind == EffectKind.BUFF]
    # rr (override) shows first despite longer remaining
    assert buff_timers[0].effect_id == "rr"


def test_pct_remaining():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=100,
    )
    s.tick(player_id="alice", elapsed_seconds=25)
    timers = s.timers_for(player_id="alice")
    assert timers[0].pct_remaining == 75


def test_color_band_changes_with_pct():
    s = SpellTimerDisplay()
    # Full
    s.apply(
        player_id="alice", effect_id="full",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=100,
        warning_at_remaining=5.0,
    )
    full_color = s.timers_for(
        player_id="alice",
    )[0].color_hint
    assert full_color == "lime"
    # Drop to ~50%
    s.tick(player_id="alice", elapsed_seconds=50)
    mid_color = s.timers_for(
        player_id="alice",
    )[0].color_hint
    assert mid_color == "yellow"


def test_total_effects():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="a",
        label="a", kind=EffectKind.BUFF,
        remaining_seconds=10,
    )
    s.apply(
        player_id="alice", effect_id="b",
        label="b", kind=EffectKind.DEBUFF,
        remaining_seconds=10,
    )
    assert s.total_effects(player_id="alice") == 2


def test_per_player_isolation():
    s = SpellTimerDisplay()
    s.apply(
        player_id="alice", effect_id="x",
        label="x", kind=EffectKind.BUFF,
        remaining_seconds=10,
    )
    assert s.total_effects(player_id="bob") == 0
