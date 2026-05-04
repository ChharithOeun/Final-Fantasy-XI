"""Tests for the surround audio mixer."""
from __future__ import annotations

import math

from server.surround_audio_mixer import (
    INAUDIBLE_DB_FLOOR,
    NEAR_FIELD_RADIUS,
    SoundLayer,
    SurroundAudioMixer,
)


def test_add_source():
    m = SurroundAudioMixer()
    s = m.add_source(
        source_id="orc_roar",
        layer=SoundLayer.SFX,
        zone_id="ronfaure",
        x=10, y=10, z=0, base_db=0,
    )
    assert s is not None
    assert m.total_sources() == 1


def test_double_add_rejected():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=0, y=0, z=0,
    )
    second = m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=0, y=0, z=0,
    )
    assert second is None


def test_remove_source():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=0, y=0, z=0,
    )
    assert m.remove_source(source_id="x")
    assert m.total_sources() == 0


def test_remove_unknown_returns_false():
    m = SurroundAudioMixer()
    assert not m.remove_source(source_id="ghost")


def test_listener_at_creates_record():
    m = SurroundAudioMixer()
    L = m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0,
    )
    assert L.listener_id == "alice"


def test_mix_unknown_listener_empty():
    m = SurroundAudioMixer()
    assert m.mix_for(listener_id="ghost") == ()


def test_source_in_zone_appears():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=10, y=10, z=0, base_db=0,
    )
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0,
    )
    samples = m.mix_for(listener_id="alice")
    assert len(samples) == 1


def test_source_other_zone_excluded():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="other", x=0, y=0, z=0,
    )
    m.listener_at(
        listener_id="alice", zone_id="here",
        x=0, y=0, z=0,
    )
    assert m.mix_for(listener_id="alice") == ()


def test_near_field_full_strength():
    m = SurroundAudioMixer(rolloff_db_per_yalm=1.0)
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=0, y=NEAR_FIELD_RADIUS, z=0,
        base_db=0,
    )
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0,
    )
    sample = m.mix_for(listener_id="alice")[0]
    assert sample.attenuated_db == 0.0


def test_distance_attenuation():
    m = SurroundAudioMixer(rolloff_db_per_yalm=1.0)
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=0, y=15, z=0,
        base_db=0,
    )
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0,
    )
    sample = m.mix_for(listener_id="alice")[0]
    # 15 - 5 = 10 yalms beyond near field, * 1.0 = -10 dB
    assert sample.attenuated_db == -10.0


def test_inaudible_below_floor():
    m = SurroundAudioMixer(rolloff_db_per_yalm=10.0)
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=0, y=100, z=0,
        base_db=0,
    )
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0,
    )
    sample = m.mix_for(listener_id="alice")[0]
    assert not sample.audible


def test_azimuth_north_facing_north():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=0, y=10, z=0,
    )
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0, facing_radians=0.0,
    )
    sample = m.mix_for(listener_id="alice")[0]
    # Source directly ahead → azimuth ~0
    assert abs(sample.azimuth_radians) < 1e-6


def test_azimuth_east_facing_north():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=10, y=0, z=0,
    )
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0, facing_radians=0.0,
    )
    sample = m.mix_for(listener_id="alice")[0]
    # Source east → azimuth ~+pi/2
    assert (
        abs(sample.azimuth_radians - math.pi / 2)
        < 1e-6
    )


def test_facing_rotation_changes_azimuth():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=10, y=0, z=0,
    )
    # Face east — source now appears straight ahead
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0,
        facing_radians=math.pi / 2,
    )
    sample = m.mix_for(listener_id="alice")[0]
    assert abs(sample.azimuth_radians) < 1e-6


def test_elevation_above():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=0, y=10, z=10,
    )
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0,
    )
    sample = m.mix_for(listener_id="alice")[0]
    # Source at 45° above horizontal → elevation ~+pi/4
    assert (
        abs(sample.elevation_radians - math.pi / 4)
        < 1e-6
    )


def test_distance_field_in_sample():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="x", layer=SoundLayer.SFX,
        zone_id="z", x=0, y=10, z=0,
    )
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0,
    )
    sample = m.mix_for(listener_id="alice")[0]
    assert sample.distance == 10.0


def test_layer_propagated():
    m = SurroundAudioMixer()
    m.add_source(
        source_id="voice_a",
        layer=SoundLayer.VOICE,
        zone_id="z", x=0, y=5, z=0,
    )
    m.listener_at(
        listener_id="alice", zone_id="z",
        x=0, y=0, z=0,
    )
    sample = m.mix_for(listener_id="alice")[0]
    assert sample.layer == SoundLayer.VOICE


def test_inaudible_floor_constant():
    assert INAUDIBLE_DB_FLOOR < 0
