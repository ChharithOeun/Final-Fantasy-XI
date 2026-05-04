"""Tests for the audio listener config."""
from __future__ import annotations

from server.audio_listener_config import (
    AudioListenerConfigs,
    BusKind,
    DEFAULT_MASTER,
    MAX_VOL,
    MIN_VOL,
    SurroundLayout,
)


def test_default_config():
    a = AudioListenerConfigs()
    c = a.config_for(player_id="alice")
    assert c.master_vol == DEFAULT_MASTER
    assert c.layout == SurroundLayout.SURROUND_7_1


def test_set_master_clamps():
    a = AudioListenerConfigs()
    assert a.set_master(
        player_id="alice", vol_pct=200,
    ) == MAX_VOL
    assert a.set_master(
        player_id="alice", vol_pct=-5,
    ) == MIN_VOL


def test_set_bus_volumes():
    a = AudioListenerConfigs()
    a.set_bus(
        player_id="alice", bus=BusKind.SFX, vol_pct=50,
    )
    a.set_bus(
        player_id="alice", bus=BusKind.MUSIC, vol_pct=30,
    )
    c = a.config_for(player_id="alice")
    assert c.sfx_vol == 50
    assert c.music_vol == 30


def test_set_layout():
    a = AudioListenerConfigs()
    a.set_layout(
        player_id="alice",
        layout=SurroundLayout.HEADPHONE_VIRTUAL,
    )
    c = a.config_for(player_id="alice")
    assert c.layout == SurroundLayout.HEADPHONE_VIRTUAL


def test_voice_ducking_toggle():
    a = AudioListenerConfigs()
    a.set_voice_ducking(
        player_id="alice", enabled=False,
    )
    c = a.config_for(player_id="alice")
    assert not c.voice_ducking_enabled


def test_voice_ducking_db_override():
    a = AudioListenerConfigs()
    a.set_voice_ducking(
        player_id="alice", enabled=True, duck_db=-20.0,
    )
    assert a.config_for(
        player_id="alice",
    ).duck_db == -20.0


def test_mute_silences_all_buses():
    a = AudioListenerConfigs()
    a.set_muted(player_id="alice", muted=True)
    db = a.effective_gain_db(
        player_id="alice", bus=BusKind.SFX,
    )
    assert db == -120.0


def test_master_at_zero_silences():
    a = AudioListenerConfigs()
    a.set_master(player_id="alice", vol_pct=0)
    db = a.effective_gain_db(
        player_id="alice", bus=BusKind.SFX,
    )
    assert db <= -100.0


def test_full_master_full_bus_gives_zero_db():
    a = AudioListenerConfigs()
    a.set_master(player_id="alice", vol_pct=100)
    a.set_bus(
        player_id="alice", bus=BusKind.SFX, vol_pct=100,
    )
    db = a.effective_gain_db(
        player_id="alice", bus=BusKind.SFX,
    )
    assert abs(db) < 0.01


def test_voice_ducks_music_when_active():
    a = AudioListenerConfigs()
    a.set_master(player_id="alice", vol_pct=100)
    a.set_bus(
        player_id="alice", bus=BusKind.MUSIC, vol_pct=100,
    )
    a.set_voice_ducking(
        player_id="alice", enabled=True, duck_db=-8.0,
    )
    db_normal = a.effective_gain_db(
        player_id="alice", bus=BusKind.MUSIC,
    )
    db_ducked = a.effective_gain_db(
        player_id="alice",
        bus=BusKind.MUSIC,
        voice_active=True,
    )
    assert abs((db_normal - db_ducked) - 8.0) < 0.01


def test_voice_ducking_does_not_attenuate_voice():
    a = AudioListenerConfigs()
    a.set_master(player_id="alice", vol_pct=100)
    a.set_bus(
        player_id="alice", bus=BusKind.VOICE, vol_pct=100,
    )
    db = a.effective_gain_db(
        player_id="alice",
        bus=BusKind.VOICE,
        voice_active=True,
    )
    assert abs(db) < 0.01


def test_voice_ducking_does_not_attenuate_ui():
    a = AudioListenerConfigs()
    a.set_master(player_id="alice", vol_pct=100)
    a.set_bus(
        player_id="alice", bus=BusKind.UI, vol_pct=100,
    )
    db = a.effective_gain_db(
        player_id="alice",
        bus=BusKind.UI,
        voice_active=True,
    )
    assert abs(db) < 0.01


def test_voice_ducking_off_no_effect():
    a = AudioListenerConfigs()
    a.set_master(player_id="alice", vol_pct=100)
    a.set_bus(
        player_id="alice", bus=BusKind.MUSIC, vol_pct=100,
    )
    a.set_voice_ducking(
        player_id="alice", enabled=False,
    )
    db = a.effective_gain_db(
        player_id="alice",
        bus=BusKind.MUSIC,
        voice_active=True,
    )
    assert abs(db) < 0.01


def test_per_player_isolation():
    a = AudioListenerConfigs()
    a.set_master(player_id="alice", vol_pct=20)
    a.set_master(player_id="bob", vol_pct=80)
    assert (
        a.config_for(player_id="alice").master_vol
        != a.config_for(player_id="bob").master_vol
    )


def test_total_configs():
    a = AudioListenerConfigs()
    a.config_for(player_id="a")
    a.config_for(player_id="b")
    a.config_for(player_id="c")
    assert a.total_configs() == 3


def test_bus_clamps_to_bounds():
    a = AudioListenerConfigs()
    assert a.set_bus(
        player_id="alice", bus=BusKind.AMBIENT,
        vol_pct=999,
    ) == MAX_VOL
    assert a.set_bus(
        player_id="alice", bus=BusKind.AMBIENT,
        vol_pct=-5,
    ) == MIN_VOL


def test_unmute_restores_audio():
    a = AudioListenerConfigs()
    a.set_master(player_id="alice", vol_pct=100)
    a.set_bus(
        player_id="alice", bus=BusKind.SFX, vol_pct=100,
    )
    a.set_muted(player_id="alice", muted=True)
    a.set_muted(player_id="alice", muted=False)
    db = a.effective_gain_db(
        player_id="alice", bus=BusKind.SFX,
    )
    assert abs(db) < 0.01
