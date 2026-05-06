"""Tests for bard_foresight_etude."""
from __future__ import annotations

from server.bard_foresight_etude import (
    BardForesightEtude,
    EtudeKind,
    MAX_SONG_SLOTS,
    SONG_RECAST_SECONDS,
    SUBJOB_DURATION_PCT,
)
from server.telegraph_visibility_gate import (
    TelegraphVisibilityGate, VisibilitySource,
)


def test_sing_scherzo_happy():
    e = BardForesightEtude()
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    assert out.accepted is True
    assert out.kind == EtudeKind.SCHERZO_OF_FORESIGHT


def test_blank_bard_blocked():
    e = BardForesightEtude()
    out = e.sing(
        bard_id="", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    assert out.accepted is False


def test_recast_cooldown_blocks():
    e = BardForesightEtude()
    e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    # within cooldown — blocked
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=4,
    )
    assert out.accepted is False
    assert out.reason == "recast"
    # past cooldown — refreshes existing scherzo
    later = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=SONG_RECAST_SECONDS + 1,
    )
    assert later.accepted is True


def test_max_slots_blocks_third():
    e = BardForesightEtude()
    # Scherzo (1 slot) + Ballad (2 slots) = 3 > MAX_SONG_SLOTS=2
    e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.BALLAD_OF_FORESIGHT,
        now_seconds=SONG_RECAST_SECONDS + 1,
    )
    assert out.accepted is False


def test_resing_same_song_refreshes_no_extra_slot():
    e = BardForesightEtude()
    out1 = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    out2 = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=SONG_RECAST_SECONDS + 1,
    )
    assert out2.accepted is True
    assert out2.song_id == out1.song_id


def test_subjob_half_duration():
    e = BardForesightEtude()
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0, has_subjob_only=True,
    )
    # full would be 60s; subjob = 30s
    assert out.expires_at == 30


def test_tick_grants_visibility():
    e = BardForesightEtude()
    gate = TelegraphVisibilityGate()
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    n = e.tick(
        song_id=out.song_id, now_seconds=2,
        listeners_in_radius=["bob", "carol", "dave"],
        gate=gate,
    )
    assert n == 3
    assert gate.is_visible(player_id="bob", now_seconds=3) is True


def test_visibility_source_is_bard():
    e = BardForesightEtude()
    gate = TelegraphVisibilityGate()
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    e.tick(
        song_id=out.song_id, now_seconds=2,
        listeners_in_radius=["bob"], gate=gate,
    )
    sources = gate.active_sources(player_id="bob", now_seconds=3)
    assert VisibilitySource.BARD_FORESIGHT in sources


def test_tick_after_song_expires_dispels():
    e = BardForesightEtude()
    gate = TelegraphVisibilityGate()
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    # past 60s
    n = e.tick(
        song_id=out.song_id, now_seconds=70,
        listeners_in_radius=["bob"], gate=gate,
    )
    assert n == 0
    songs = e.active_songs(bard_id="brd_alice", now_seconds=70)
    assert songs == ()


def test_dispel_explicitly():
    e = BardForesightEtude()
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    assert e.dispel(song_id=out.song_id) is True
    assert e.active_songs(
        bard_id="brd_alice", now_seconds=10,
    ) == ()


def test_listener_count_tracks():
    e = BardForesightEtude()
    gate = TelegraphVisibilityGate()
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    e.tick(
        song_id=out.song_id, now_seconds=2,
        listeners_in_radius=["bob", "carol"], gate=gate,
    )
    assert e.listener_count(song_id=out.song_id) == 2


def test_two_scherzos_use_two_slots():
    """Single bard cannot fit Scherzo (1) + Ballad (2)."""
    e = BardForesightEtude()
    out1 = e.sing(
        bard_id="brd_alice", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    assert out1.accepted is True
    # ballad would push us over the slot cap
    out2 = e.sing(
        bard_id="brd_alice", kind=EtudeKind.BALLAD_OF_FORESIGHT,
        now_seconds=SONG_RECAST_SECONDS + 1,
    )
    assert out2.accepted is False


def test_ballad_alone_fits():
    e = BardForesightEtude()
    out = e.sing(
        bard_id="brd_alice", kind=EtudeKind.BALLAD_OF_FORESIGHT,
        now_seconds=0,
    )
    assert out.accepted is True


def test_tick_unknown_song_no_effect():
    e = BardForesightEtude()
    gate = TelegraphVisibilityGate()
    n = e.tick(
        song_id="ghost", now_seconds=10,
        listeners_in_radius=["bob"], gate=gate,
    )
    assert n == 0


def test_ballad_longer_than_scherzo():
    e = BardForesightEtude()
    sch = e.sing(
        bard_id="brd_a", kind=EtudeKind.SCHERZO_OF_FORESIGHT,
        now_seconds=0,
    )
    bal = e.sing(
        bard_id="brd_b", kind=EtudeKind.BALLAD_OF_FORESIGHT,
        now_seconds=0,
    )
    assert bal.expires_at > sch.expires_at


def test_max_slots_constant():
    assert MAX_SONG_SLOTS == 2
