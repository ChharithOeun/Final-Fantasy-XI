"""Tests for whale song navigation."""
from __future__ import annotations

from server.whale_song_navigation import (
    LISTEN_DURATION_SECONDS,
    NoteValue,
    WhaleSongNavigation,
)


def test_register_motif_happy():
    w = WhaleSongNavigation()
    ok = w.register_motif(
        motif_id="m1",
        notes=(NoteValue.LOW, NoteValue.MID, NoteValue.HIGH),
        route_zones=("kelp_labyrinth", "abyss_trench"),
    )
    assert ok is True


def test_register_motif_blank_id():
    w = WhaleSongNavigation()
    ok = w.register_motif(
        motif_id="",
        notes=(NoteValue.LOW,),
        route_zones=("a", "b"),
    )
    assert ok is False


def test_register_motif_too_short_route():
    w = WhaleSongNavigation()
    ok = w.register_motif(
        motif_id="m",
        notes=(NoteValue.LOW,),
        route_zones=("a",),
    )
    assert ok is False


def test_register_motif_no_notes():
    w = WhaleSongNavigation()
    ok = w.register_motif(
        motif_id="m",
        notes=(),
        route_zones=("a", "b"),
    )
    assert ok is False


def test_register_motif_duplicate():
    w = WhaleSongNavigation()
    w.register_motif(
        motif_id="m", notes=(NoteValue.LOW,),
        route_zones=("a", "b"),
    )
    ok = w.register_motif(
        motif_id="m", notes=(NoteValue.HIGH,),
        route_zones=("a", "c"),
    )
    assert ok is False


def test_start_listen_blocks_non_decoder_job():
    w = WhaleSongNavigation()
    w.register_motif(
        motif_id="m", notes=(NoteValue.LOW,),
        route_zones=("a", "b"),
    )
    ok = w.start_listen(
        player_id="p", motif_id="m",
        job="WAR", now_seconds=0,
    )
    assert ok is False


def test_start_listen_brd_ok():
    w = WhaleSongNavigation()
    w.register_motif(
        motif_id="m", notes=(NoteValue.LOW,),
        route_zones=("a", "b"),
    )
    ok = w.start_listen(
        player_id="p", motif_id="m",
        job="BRD", now_seconds=0,
    )
    assert ok is True


def test_start_listen_unknown_motif():
    w = WhaleSongNavigation()
    ok = w.start_listen(
        player_id="p", motif_id="ghost",
        job="BRD", now_seconds=0,
    )
    assert ok is False


def test_decode_too_brief():
    w = WhaleSongNavigation()
    w.register_motif(
        motif_id="m",
        notes=(NoteValue.LOW, NoteValue.MID),
        route_zones=("a", "b"),
    )
    w.start_listen(
        player_id="p", motif_id="m",
        job="SCH", now_seconds=0,
    )
    r = w.submit_decode(
        player_id="p",
        notes=(NoteValue.LOW, NoteValue.MID),
        now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "listened too briefly"


def test_decode_correct_unlocks_route():
    w = WhaleSongNavigation()
    w.register_motif(
        motif_id="m",
        notes=(NoteValue.LOW, NoteValue.MID, NoteValue.HIGH),
        route_zones=("kelp_labyrinth", "abyss_trench"),
    )
    w.start_listen(
        player_id="p", motif_id="m",
        job="SCH", now_seconds=0,
    )
    r = w.submit_decode(
        player_id="p",
        notes=(NoteValue.LOW, NoteValue.MID, NoteValue.HIGH),
        now_seconds=LISTEN_DURATION_SECONDS,
    )
    assert r.accepted is True
    assert r.route_unlocked is True
    assert r.route_zones == ("kelp_labyrinth", "abyss_trench")
    assert w.has_route(
        player_id="p",
        route_zones=("kelp_labyrinth", "abyss_trench"),
    ) is True


def test_decode_wrong_sequence():
    w = WhaleSongNavigation()
    w.register_motif(
        motif_id="m",
        notes=(NoteValue.LOW, NoteValue.MID),
        route_zones=("a", "b"),
    )
    w.start_listen(
        player_id="p", motif_id="m",
        job="BRD", now_seconds=0,
    )
    r = w.submit_decode(
        player_id="p",
        notes=(NoteValue.HIGH, NoteValue.HIGH),
        now_seconds=LISTEN_DURATION_SECONDS,
    )
    assert r.accepted is False
    assert r.reason == "incorrect interpretation"


def test_decode_without_listen():
    w = WhaleSongNavigation()
    r = w.submit_decode(
        player_id="p",
        notes=(NoteValue.LOW,),
        now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "not listening"


def test_has_route_default_false():
    w = WhaleSongNavigation()
    assert w.has_route(
        player_id="p", route_zones=("a", "b"),
    ) is False
