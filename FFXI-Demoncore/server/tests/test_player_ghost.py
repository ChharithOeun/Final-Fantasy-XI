"""Tests for the player ghost system."""
from __future__ import annotations

from server.player_ghost import (
    DEFAULT_HAUNT_WINDOW_SECONDS,
    GhostState,
    HauntKind,
    MAX_HAUNT_INTENSITY,
    PlayerGhostRegistry,
)


def test_summon_ghost_creates_record():
    reg = PlayerGhostRegistry()
    g = reg.summon_ghost(
        deceased_player_id="alice", killer_id="orc_chief",
        death_zone_id="batallia",
    )
    assert g is not None
    assert g.state == GhostState.LINGERING
    assert g.killer_id == "orc_chief"


def test_double_summon_for_same_player_rejected():
    reg = PlayerGhostRegistry()
    reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
    )
    second = reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
    )
    assert second is None


def test_ghost_for_player_lookup():
    reg = PlayerGhostRegistry()
    reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
    )
    g = reg.ghost_for_player("alice")
    assert g is not None
    assert g.deceased_player_id == "alice"


def test_apply_haunt_changes_state():
    reg = PlayerGhostRegistry()
    g = reg.summon_ghost(
        deceased_player_id="alice", killer_id="bob",
        death_zone_id="batallia",
    )
    h = reg.apply_haunt(
        ghost_id=g.ghost_id, victim_id="bob",
        kind=HauntKind.DEBUFF_AURA, intensity=50,
    )
    assert h is not None
    assert h.intensity == 50
    assert reg.get(g.ghost_id).state == GhostState.HAUNTING
    assert reg.get(g.ghost_id).haunts_applied == 1


def test_haunt_intensity_clamped():
    reg = PlayerGhostRegistry()
    g = reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
    )
    h = reg.apply_haunt(
        ghost_id=g.ghost_id, victim_id="bob",
        kind=HauntKind.NIGHTMARE, intensity=999,
    )
    assert h.intensity == MAX_HAUNT_INTENSITY


def test_haunt_zero_intensity_rejected():
    reg = PlayerGhostRegistry()
    g = reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
    )
    h = reg.apply_haunt(
        ghost_id=g.ghost_id, victim_id="bob",
        kind=HauntKind.NIGHTMARE, intensity=0,
    )
    assert h is None


def test_haunt_unknown_ghost():
    reg = PlayerGhostRegistry()
    assert reg.apply_haunt(
        ghost_id="ghost_404", victim_id="bob",
        kind=HauntKind.NIGHTMARE, intensity=10,
    ) is None


def test_whisper_returns_message():
    reg = PlayerGhostRegistry()
    g = reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
    )
    msg = reg.whisper(
        ghost_id=g.ghost_id, listener_id="cid",
    )
    assert msg is not None
    assert isinstance(msg, str)
    assert reg.get(g.ghost_id).state == GhostState.WHISPERING


def test_whisper_records_listener():
    reg = PlayerGhostRegistry()
    g = reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
    )
    reg.whisper(ghost_id=g.ghost_id, listener_id="cid")
    assert "cid" in reg.get(g.ghost_id).whispers_heard_by


def test_whisper_unknown_ghost():
    reg = PlayerGhostRegistry()
    assert reg.whisper(
        ghost_id="ghost_404", listener_id="x",
    ) is None


def test_whisper_deterministic_for_same_pair():
    reg = PlayerGhostRegistry()
    g = reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
    )
    msg_a = reg.whisper(
        ghost_id=g.ghost_id, listener_id="cid",
    )
    msg_b = reg.whisper(
        ghost_id=g.ghost_id, listener_id="cid",
    )
    assert msg_a == msg_b


def test_tick_expires_old_ghosts():
    reg = PlayerGhostRegistry()
    reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
        now_seconds=0.0,
    )
    expired = reg.tick(
        now_seconds=DEFAULT_HAUNT_WINDOW_SECONDS + 1,
    )
    assert len(expired) == 1
    assert expired[0].deceased_player_id == "alice"


def test_tick_keeps_active_ghosts():
    reg = PlayerGhostRegistry()
    reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
        now_seconds=0.0,
    )
    expired = reg.tick(now_seconds=100.0)
    assert expired == ()


def test_haunt_on_departed_ghost_rejected():
    reg = PlayerGhostRegistry()
    g = reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
        now_seconds=0.0,
    )
    reg.tick(now_seconds=DEFAULT_HAUNT_WINDOW_SECONDS + 1)
    assert reg.apply_haunt(
        ghost_id=g.ghost_id, victim_id="bob",
        kind=HauntKind.NIGHTMARE, intensity=10,
    ) is None


def test_whisper_on_departed_ghost_rejected():
    reg = PlayerGhostRegistry()
    g = reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
        now_seconds=0.0,
    )
    reg.tick(now_seconds=DEFAULT_HAUNT_WINDOW_SECONDS + 1)
    assert reg.whisper(
        ghost_id=g.ghost_id, listener_id="x",
    ) is None


def test_after_departure_can_summon_again():
    reg = PlayerGhostRegistry()
    reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="batallia",
        now_seconds=0.0,
    )
    reg.tick(now_seconds=DEFAULT_HAUNT_WINDOW_SECONDS + 1)
    # Player permadied a second time on a different
    # character — new ghost
    g2 = reg.summon_ghost(
        deceased_player_id="alice",
        death_zone_id="ronfaure",
        now_seconds=DEFAULT_HAUNT_WINDOW_SECONDS + 100,
    )
    assert g2 is not None


def test_total_active_count():
    reg = PlayerGhostRegistry()
    reg.summon_ghost(
        deceased_player_id="a", death_zone_id="z",
    )
    reg.summon_ghost(
        deceased_player_id="b", death_zone_id="z",
    )
    assert reg.total_active_ghosts() == 2


def test_total_ever_persists_after_departure():
    reg = PlayerGhostRegistry()
    reg.summon_ghost(
        deceased_player_id="a", death_zone_id="z",
        now_seconds=0.0,
    )
    reg.tick(now_seconds=DEFAULT_HAUNT_WINDOW_SECONDS + 1)
    assert reg.total_active_ghosts() == 0
    assert reg.total_ghosts_ever() == 1
