"""Tests for foresight_accessories."""
from __future__ import annotations

from server.foresight_accessories import (
    AccessoryKind,
    ForesightAccessories,
    LENS_DMG_TAKEN_PENALTY_PCT,
    PENDANT_COOLDOWN,
    PENDANT_WINDOW,
    RING_TRIGGER_WINDOW,
    SAGE_MOVE_GRACE_SECONDS,
)
from server.telegraph_visibility_gate import TelegraphVisibilityGate


def test_equip_lens_returns_penalty():
    f = ForesightAccessories()
    out = f.equip(
        player_id="alice", kind=AccessoryKind.FORESIGHT_LENS,
    )
    assert out.accepted is True
    assert out.damage_taken_penalty_pct == LENS_DMG_TAKEN_PENALTY_PCT


def test_equip_pendant_no_penalty():
    f = ForesightAccessories()
    out = f.equip(
        player_id="alice", kind=AccessoryKind.ORACLE_PENDANT,
    )
    assert out.damage_taken_penalty_pct == 0


def test_equip_dup_blocked():
    f = ForesightAccessories()
    f.equip(player_id="alice", kind=AccessoryKind.FORESIGHT_LENS)
    out = f.equip(
        player_id="alice", kind=AccessoryKind.FORESIGHT_LENS,
    )
    assert out.accepted is False


def test_unequip_happy():
    f = ForesightAccessories()
    f.equip(player_id="alice", kind=AccessoryKind.FORESIGHT_LENS)
    assert f.unequip(
        player_id="alice", kind=AccessoryKind.FORESIGHT_LENS,
    ) is True


def test_lens_passive_grants():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.equip(player_id="alice", kind=AccessoryKind.FORESIGHT_LENS)
    n = f.tick(
        player_id="alice", now_seconds=10, gate=gate,
    )
    assert n == 1
    assert gate.is_visible(player_id="alice", now_seconds=12) is True


def test_pendant_requires_activation():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.equip(player_id="alice", kind=AccessoryKind.ORACLE_PENDANT)
    # Tick without activating — no grant
    n = f.tick(
        player_id="alice", now_seconds=10, gate=gate,
    )
    assert n == 0


def test_pendant_activate_grants():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.equip(player_id="alice", kind=AccessoryKind.ORACLE_PENDANT)
    assert f.activate(
        player_id="alice", kind=AccessoryKind.ORACLE_PENDANT,
        now_seconds=10,
    ) is True
    n = f.tick(
        player_id="alice", now_seconds=15, gate=gate,
    )
    assert n == 1


def test_pendant_window_ends():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.equip(player_id="alice", kind=AccessoryKind.ORACLE_PENDANT)
    f.activate(
        player_id="alice", kind=AccessoryKind.ORACLE_PENDANT,
        now_seconds=10,
    )
    n = f.tick(
        player_id="alice", now_seconds=10 + PENDANT_WINDOW + 1,
        gate=gate,
    )
    assert n == 0


def test_pendant_cooldown_blocks_repeat():
    f = ForesightAccessories()
    f.equip(player_id="alice", kind=AccessoryKind.ORACLE_PENDANT)
    f.activate(
        player_id="alice", kind=AccessoryKind.ORACLE_PENDANT,
        now_seconds=10,
    )
    again = f.activate(
        player_id="alice", kind=AccessoryKind.ORACLE_PENDANT,
        now_seconds=20,
    )
    assert again is False
    later = f.activate(
        player_id="alice", kind=AccessoryKind.ORACLE_PENDANT,
        now_seconds=10 + PENDANT_COOLDOWN + 1,
    )
    assert later is True


def test_ring_grants_on_fatal_hit():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.equip(player_id="alice", kind=AccessoryKind.PROPHET_RING)
    f.on_fatal_hit(player_id="alice", now_seconds=10)
    n = f.tick(
        player_id="alice", now_seconds=12, gate=gate,
    )
    assert n == 1


def test_ring_window_ends():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.equip(player_id="alice", kind=AccessoryKind.PROPHET_RING)
    f.on_fatal_hit(player_id="alice", now_seconds=10)
    n = f.tick(
        player_id="alice",
        now_seconds=10 + RING_TRIGGER_WINDOW + 1,
        gate=gate,
    )
    assert n == 0


def test_sage_grants_when_still():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.equip(player_id="alice", kind=AccessoryKind.SAGE_BRACELET)
    # mark a stationary moment
    f.note_movement(player_id="alice", now_seconds=0)
    n = f.tick(
        player_id="alice",
        now_seconds=SAGE_MOVE_GRACE_SECONDS + 5,
        gate=gate, is_moving=False,
    )
    assert n == 1


def test_sage_blocked_when_moving():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.equip(player_id="alice", kind=AccessoryKind.SAGE_BRACELET)
    n = f.tick(
        player_id="alice", now_seconds=10, gate=gate,
        is_moving=True,
    )
    assert n == 0


def test_soothsayer_zone_gated():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.equip(
        player_id="alice", kind=AccessoryKind.SOOTHSAYER_KEY_ITEM,
    )
    no = f.tick(
        player_id="alice", now_seconds=10, gate=gate,
        current_zone="bastok_markets",
    )
    assert no == 0
    yes = f.tick(
        player_id="alice", now_seconds=11, gate=gate,
        current_zone="sea",
    )
    assert yes == 1


def test_not_equipped_no_grant():
    f = ForesightAccessories()
    gate = TelegraphVisibilityGate()
    f.activate(
        player_id="alice", kind=AccessoryKind.ORACLE_PENDANT,
        now_seconds=10,
    )
    n = f.tick(
        player_id="alice", now_seconds=15, gate=gate,
    )
    assert n == 0


def test_blank_player_blocked():
    f = ForesightAccessories()
    out = f.equip(
        player_id="", kind=AccessoryKind.FORESIGHT_LENS,
    )
    assert out.accepted is False


def test_equipped_listing():
    f = ForesightAccessories()
    f.equip(player_id="alice", kind=AccessoryKind.FORESIGHT_LENS)
    f.equip(player_id="alice", kind=AccessoryKind.PROPHET_RING)
    out = f.equipped(player_id="alice")
    assert AccessoryKind.FORESIGHT_LENS in out
    assert AccessoryKind.PROPHET_RING in out


def test_5_kinds_distinct():
    assert len(list(AccessoryKind)) == 5


def test_pendant_off_cooldown_at():
    f = ForesightAccessories()
    f.equip(player_id="alice", kind=AccessoryKind.ORACLE_PENDANT)
    f.activate(
        player_id="alice", kind=AccessoryKind.ORACLE_PENDANT,
        now_seconds=100,
    )
    assert f.pendant_off_cooldown_at(
        player_id="alice",
    ) == 100 + PENDANT_COOLDOWN
