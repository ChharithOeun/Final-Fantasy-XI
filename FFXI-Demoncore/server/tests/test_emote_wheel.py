"""Tests for the emote wheel system."""
from __future__ import annotations

from server.emote_wheel import (
    EmoteKind,
    EmoteWheelSystem,
    SLOTS_PER_WHEEL,
)


def test_register_emote():
    e = EmoteWheelSystem()
    em = e.register_emote(
        emote_id="wave", label="/wave",
    )
    assert em is not None


def test_double_register_rejected():
    e = EmoteWheelSystem()
    e.register_emote(emote_id="wave", label="/wave")
    second = e.register_emote(
        emote_id="wave", label="/wave",
    )
    assert second is None


def test_default_unlocked_for_all():
    e = EmoteWheelSystem()
    e.register_emote(emote_id="wave", label="/wave")
    assert e.is_unlocked(
        player_id="alice", emote_id="wave",
    )


def test_gated_locked_by_default():
    e = EmoteWheelSystem()
    e.register_emote(
        emote_id="maatlevel", label="/maatlevel",
        kind=EmoteKind.GATED, gated_by="defeat_maat",
    )
    assert not e.is_unlocked(
        player_id="alice", emote_id="maatlevel",
    )


def test_unlock_gated():
    e = EmoteWheelSystem()
    e.register_emote(
        emote_id="maatlevel", label="/maatlevel",
        kind=EmoteKind.GATED,
    )
    assert e.unlock(
        player_id="alice", emote_id="maatlevel",
    )
    assert e.is_unlocked(
        player_id="alice", emote_id="maatlevel",
    )


def test_unlock_unknown_emote():
    e = EmoteWheelSystem()
    assert not e.unlock(
        player_id="alice", emote_id="ghost",
    )


def test_bind_default_succeeds():
    e = EmoteWheelSystem()
    e.register_emote(emote_id="wave", label="/wave")
    assert e.bind(
        player_id="alice", slot_index=0,
        emote_id="wave",
    )


def test_bind_unknown_emote():
    e = EmoteWheelSystem()
    assert not e.bind(
        player_id="alice", slot_index=0,
        emote_id="ghost",
    )


def test_bind_invalid_slot():
    e = EmoteWheelSystem()
    e.register_emote(emote_id="wave", label="/wave")
    assert not e.bind(
        player_id="alice", slot_index=99,
        emote_id="wave",
    )


def test_bind_locked_emote_rejected():
    e = EmoteWheelSystem()
    e.register_emote(
        emote_id="maatlevel", label="/maatlevel",
        kind=EmoteKind.GATED,
    )
    assert not e.bind(
        player_id="alice", slot_index=0,
        emote_id="maatlevel",
    )


def test_bind_after_unlock_succeeds():
    e = EmoteWheelSystem()
    e.register_emote(
        emote_id="maatlevel", label="/maatlevel",
        kind=EmoteKind.GATED,
    )
    e.unlock(player_id="alice", emote_id="maatlevel")
    assert e.bind(
        player_id="alice", slot_index=0,
        emote_id="maatlevel",
    )


def test_clear_slot():
    e = EmoteWheelSystem()
    e.register_emote(emote_id="wave", label="/wave")
    e.bind(
        player_id="alice", slot_index=0,
        emote_id="wave",
    )
    assert e.clear_slot(
        player_id="alice", slot_index=0,
    )


def test_clear_empty_slot_returns_false():
    e = EmoteWheelSystem()
    e.register_emote(emote_id="wave", label="/wave")
    e.bind(
        player_id="alice", slot_index=0,
        emote_id="wave",
    )
    e.clear_slot(player_id="alice", slot_index=0)
    assert not e.clear_slot(
        player_id="alice", slot_index=0,
    )


def test_point_to_slot():
    e = EmoteWheelSystem()
    e.register_emote(emote_id="wave", label="/wave")
    e.bind(
        player_id="alice", slot_index=5,
        emote_id="wave",
    )
    assert e.point(
        player_id="alice", slot_index=5,
    )
    assert e.wheel(
        player_id="alice",
    ).highlighted_index == 5


def test_point_invalid_slot():
    e = EmoteWheelSystem()
    assert not e.point(
        player_id="alice", slot_index=99,
    )


def test_cycle_next_wraps():
    e = EmoteWheelSystem()
    w = e.wheel(player_id="alice")
    w.highlighted_index = SLOTS_PER_WHEEL - 1
    new_idx = e.cycle_next(player_id="alice")
    assert new_idx == 0


def test_cycle_prev_wraps():
    e = EmoteWheelSystem()
    new_idx = e.cycle_prev(player_id="alice")
    assert new_idx == SLOTS_PER_WHEEL - 1


def test_activate_returns_emote():
    e = EmoteWheelSystem()
    e.register_emote(emote_id="wave", label="/wave")
    e.bind(
        player_id="alice", slot_index=0,
        emote_id="wave",
    )
    res = e.activate(player_id="alice")
    assert res.accepted
    assert res.emote_id == "wave"


def test_activate_empty_slot():
    e = EmoteWheelSystem()
    e.wheel(player_id="alice")
    res = e.activate(player_id="alice")
    assert not res.accepted
    assert "empty" in res.reason


def test_activate_no_wheel():
    e = EmoteWheelSystem()
    res = e.activate(player_id="ghost")
    assert not res.accepted


def test_activate_after_unbind_relocks():
    """Bind then revoke gated unlock — activation should drop
    if the emote becomes locked. Edge case for moderation."""
    e = EmoteWheelSystem()
    e.register_emote(
        emote_id="naughty", label="/naughty",
        kind=EmoteKind.GATED,
    )
    e.unlock(player_id="alice", emote_id="naughty")
    e.bind(
        player_id="alice", slot_index=0,
        emote_id="naughty",
    )
    # Revoke
    e._unlocks["alice"].discard("naughty")
    res = e.activate(player_id="alice")
    assert not res.accepted
    assert "locked" in res.reason


def test_total_emotes():
    e = EmoteWheelSystem()
    e.register_emote(emote_id="a", label="/a")
    e.register_emote(emote_id="b", label="/b")
    assert e.total_emotes() == 2
