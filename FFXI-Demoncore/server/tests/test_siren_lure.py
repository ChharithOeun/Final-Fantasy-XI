"""Tests for siren lure."""
from __future__ import annotations

from server.siren_lure import (
    LureKind,
    SirenLureSystem,
    SongPower,
)


def test_total_song_powers():
    s = SirenLureSystem()
    assert s.total_song_powers() == 4


def test_song_profile_lookup():
    s = SirenLureSystem()
    p = s.song_profile(power=SongPower.HYMN)
    assert p.duration_seconds == 600
    assert p.base_strength == 80


def test_cast_song_records_active():
    s = SirenLureSystem()
    ok = s.cast_song(
        siren_id="serel",
        power=SongPower.CHORD,
        lane_zone_id="tideplate_shallows",
        trap_zone_id="kelp_labyrinth",
        now_seconds=1_000,
    )
    assert ok is True
    active = s.active_songs(siren_id="serel", now_seconds=1_001)
    assert len(active) == 1
    assert active[0].power == SongPower.CHORD


def test_cast_song_rejects_same_zone():
    s = SirenLureSystem()
    ok = s.cast_song(
        siren_id="serel",
        power=SongPower.CHORD,
        lane_zone_id="kelp_labyrinth",
        trap_zone_id="kelp_labyrinth",
        now_seconds=1,
    )
    assert ok is False


def test_cast_song_rejects_blank_inputs():
    s = SirenLureSystem()
    assert s.cast_song(
        siren_id="",
        power=SongPower.WHISPER,
        lane_zone_id="a",
        trap_zone_id="b",
        now_seconds=1,
    ) is False
    assert s.cast_song(
        siren_id="x",
        power=SongPower.WHISPER,
        lane_zone_id="",
        trap_zone_id="b",
        now_seconds=1,
    ) is False


def test_cast_song_cooldown_blocks():
    s = SirenLureSystem()
    ok1 = s.cast_song(
        siren_id="serel",
        power=SongPower.CHORD,
        lane_zone_id="tideplate_shallows",
        trap_zone_id="kelp_labyrinth",
        now_seconds=0,
    )
    assert ok1 is True
    # second cast immediately should fail (active + cooldown)
    ok2 = s.cast_song(
        siren_id="serel",
        power=SongPower.CHORD,
        lane_zone_id="tideplate_shallows",
        trap_zone_id="kelp_labyrinth",
        now_seconds=10,
    )
    assert ok2 is False


def test_cast_song_after_cooldown_succeeds():
    s = SirenLureSystem()
    s.cast_song(
        siren_id="serel",
        power=SongPower.CHORD,
        lane_zone_id="a", trap_zone_id="b",
        now_seconds=0,
    )
    # CHORD: duration 300 + cooldown 180 = 480 elapsed needed
    ok = s.cast_song(
        siren_id="serel",
        power=SongPower.CHORD,
        lane_zone_id="a", trap_zone_id="b",
        now_seconds=600,
    )
    assert ok is True


def test_active_songs_expire():
    s = SirenLureSystem()
    s.cast_song(
        siren_id="serel",
        power=SongPower.WHISPER,  # 120s duration
        lane_zone_id="a", trap_zone_id="b",
        now_seconds=0,
    )
    assert len(s.active_songs(siren_id="serel", now_seconds=60)) == 1
    assert len(s.active_songs(siren_id="serel", now_seconds=200)) == 0


def test_resolve_passage_no_song():
    s = SirenLureSystem()
    r = s.resolve_ship_passage(
        siren_id="serel",
        ship_resist=10,
        lure_roll=10,
        now_seconds=0,
    )
    assert r.accepted is False
    assert r.reason == "no active song"


def test_resolve_passage_resists():
    s = SirenLureSystem()
    s.cast_song(
        siren_id="serel",
        power=SongPower.WHISPER,  # base_strength 20
        lane_zone_id="a", trap_zone_id="trap",
        now_seconds=0,
    )
    # 20 + 5 = 25 <= 30 → resists
    r = s.resolve_ship_passage(
        siren_id="serel",
        ship_resist=30,
        lure_roll=5,
        now_seconds=10,
    )
    assert r.accepted is True
    assert r.diverted is False


def test_resolve_passage_diverts():
    s = SirenLureSystem()
    s.cast_song(
        siren_id="serel",
        power=SongPower.HYMN,  # base 80, lure BECALM
        lane_zone_id="tideplate_shallows",
        trap_zone_id="wreckage_graveyard",
        now_seconds=0,
    )
    r = s.resolve_ship_passage(
        siren_id="serel",
        ship_resist=20,
        lure_roll=10,
        now_seconds=5,
    )
    assert r.accepted is True
    assert r.diverted is True
    assert r.trap_zone_id == "wreckage_graveyard"
    assert r.lure_kind == LureKind.BECALM


def test_resolve_passage_invalid_metrics():
    s = SirenLureSystem()
    r = s.resolve_ship_passage(
        siren_id="serel",
        ship_resist=-1,
        lure_roll=10,
        now_seconds=0,
    )
    assert r.accepted is False


def test_requiem_typical_lure_shipwreck():
    s = SirenLureSystem()
    s.cast_song(
        siren_id="serel",
        power=SongPower.REQUIEM,
        lane_zone_id="a", trap_zone_id="abyss_trench",
        now_seconds=0,
    )
    r = s.resolve_ship_passage(
        siren_id="serel",
        ship_resist=10,
        lure_roll=10,
        now_seconds=5,
    )
    assert r.diverted is True
    assert r.lure_kind == LureKind.SHIPWRECK
    assert r.trap_zone_id == "abyss_trench"


def test_strongest_active_song_used():
    s = SirenLureSystem()
    # cast a whisper, then later a stronger hymn (different siren so no cd)
    s.cast_song(
        siren_id="serel",
        power=SongPower.WHISPER,
        lane_zone_id="a", trap_zone_id="b",
        now_seconds=0,
    )
    # bypass cd via long delay
    s.cast_song(
        siren_id="serel",
        power=SongPower.HYMN,
        lane_zone_id="a", trap_zone_id="trap_strong",
        now_seconds=10_000,
    )
    r = s.resolve_ship_passage(
        siren_id="serel",
        ship_resist=30,
        lure_roll=10,
        now_seconds=10_005,
    )
    # only HYMN is active because WHISPER expired
    assert r.diverted is True
    assert r.trap_zone_id == "trap_strong"
