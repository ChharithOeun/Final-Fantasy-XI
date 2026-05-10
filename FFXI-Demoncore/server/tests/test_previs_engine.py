"""Tests for previs_engine."""
from __future__ import annotations

import pytest

from server.previs_engine import (
    BlockingKey,
    CameraKey,
    ExportTarget,
    PrevisEngine,
    PrevisShot,
)


def _key(t: float = 0.0, pos: tuple = (0.0, 0.0, 0.0),
         look: tuple = (1.0, 0.0, 0.0), lens: float = 35.0) -> CameraKey:
    return CameraKey(t=t, position=pos, look_at=look, lens_mm=lens)


def _shot(
    shot_id: str = "sh001",
    duration_s: float = 5.0,
    keys: tuple[CameraKey, ...] = (),
    blocking: tuple[BlockingKey, ...] = (),
    sound: str = "",
    assets: tuple[str, ...] = (),
) -> PrevisShot:
    if not keys:
        keys = (_key(0.0), _key(duration_s))
    return PrevisShot(
        shot_id=shot_id,
        duration_s=duration_s,
        camera_path=keys,
        talent_blocking=blocking,
        sound_track_uri=sound,
        low_poly_assets=assets,
    )


# ---- Registration ----

def test_register_shot_stores():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot())
    assert eng.shot_count() == 1


def test_register_duplicate_rejected():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot("a"))


def test_zero_duration_rejected():
    eng = PrevisEngine()
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot(duration_s=0))


def test_negative_duration_rejected():
    eng = PrevisEngine()
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot(duration_s=-1))


def test_empty_camera_path_rejected():
    eng = PrevisEngine()
    bare = PrevisShot(
        shot_id="bare",
        duration_s=5.0,
        camera_path=(),
        talent_blocking=(),
    )
    with pytest.raises(ValueError):
        eng.register_previs_shot(bare)


def test_camera_key_past_duration_rejected():
    eng = PrevisEngine()
    keys = (_key(0.0), _key(10.0))
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot(duration_s=5.0, keys=keys))


def test_camera_key_negative_t_rejected():
    eng = PrevisEngine()
    keys = (_key(-0.1),)
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot(keys=keys))


def test_non_monotonic_keys_rejected():
    eng = PrevisEngine()
    keys = (_key(0.0), _key(2.0), _key(1.0))
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot(keys=keys))


def test_zero_lens_rejected():
    eng = PrevisEngine()
    keys = (_key(0.0, lens=0.0),)
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot(keys=keys))


def test_blocking_negative_t_rejected():
    eng = PrevisEngine()
    blocking = (
        BlockingKey(
            t=-1.0, npc_id="curilla",
            position=(0.0, 0.0, 0.0), action_tag="idle",
        ),
    )
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot(blocking=blocking))


def test_blocking_empty_npc_id_rejected():
    eng = PrevisEngine()
    blocking = (
        BlockingKey(
            t=0.0, npc_id="",
            position=(0.0, 0.0, 0.0), action_tag="idle",
        ),
    )
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot(blocking=blocking))


def test_blocking_non_monotonic_per_npc_rejected():
    eng = PrevisEngine()
    blocking = (
        BlockingKey(
            t=0.0, npc_id="x",
            position=(0.0, 0.0, 0.0), action_tag="a",
        ),
        BlockingKey(
            t=2.0, npc_id="x",
            position=(0.0, 0.0, 0.0), action_tag="b",
        ),
        BlockingKey(
            t=1.0, npc_id="x",
            position=(0.0, 0.0, 0.0), action_tag="c",
        ),
    )
    with pytest.raises(ValueError):
        eng.register_previs_shot(_shot(blocking=blocking))


def test_lookup_unknown_raises():
    eng = PrevisEngine()
    with pytest.raises(KeyError):
        eng.lookup("nope")


# ---- Sequencing ----

def test_sequence_sums_runtime():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a", 4.0))
    eng.register_previs_shot(_shot("b", 6.0))
    seq = eng.sequence("seq1", ["a", "b"])
    assert seq.total_runtime_s == 10.0
    assert eng.runtime_s(seq) == 10.0


def test_sequence_requires_shots():
    eng = PrevisEngine()
    with pytest.raises(ValueError):
        eng.sequence("seq", [])


def test_sequence_rejects_repeated_shot():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    with pytest.raises(ValueError):
        eng.sequence("seq", ["a", "a"])


def test_sequence_unknown_shot_raises():
    eng = PrevisEngine()
    with pytest.raises(KeyError):
        eng.sequence("seq", ["missing"])


def test_sequence_empty_id_rejected():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    with pytest.raises(ValueError):
        eng.sequence("", ["a"])


# ---- Transition validation ----

def test_validate_transitions_clean_sequence():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    eng.register_previs_shot(_shot("b"))
    seq = eng.sequence("s", ["a", "b"])
    assert eng.validate_transitions(seq) == ()


# ---- Export targets ----

def test_export_for_ue5():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    seq = eng.sequence("s", ["a"])
    m = eng.export_for(ExportTarget.UE5_SEQUENCER_USD, seq)
    assert m["target"] == "ue5_sequencer_usd"
    assert m["fps"] == 24
    assert "usd_version" in m


def test_export_for_maya():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    seq = eng.sequence("s", ["a"])
    m = eng.export_for(ExportTarget.MAYA_MA, seq)
    assert m["maya_version"] == "2024"


def test_export_for_blender():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    seq = eng.sequence("s", ["a"])
    m = eng.export_for(ExportTarget.BLENDER_BLEND, seq)
    assert m["blender_version"].startswith("4")


def test_export_for_shotgrid():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    seq = eng.sequence("s", ["a"])
    m = eng.export_for(ExportTarget.SHOTGRID_PLAYBLAST, seq)
    assert m["codec"] == "h264"


def test_export_for_kitsu():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    seq = eng.sequence("s", ["a"])
    m = eng.export_for(ExportTarget.KITSU_PLAYBLAST, seq)
    assert m["resolution"] == (1280, 720)


def test_export_includes_all_shots():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    eng.register_previs_shot(_shot("b"))
    seq = eng.sequence("s", ["a", "b"])
    m = eng.export_for(ExportTarget.UE5_SEQUENCER_USD, seq)
    assert len(m["shots"]) == 2


# ---- Camera interpolation ----

def test_simulate_camera_at_start():
    eng = PrevisEngine()
    keys = (
        CameraKey(t=0.0, position=(0.0, 0.0, 0.0),
                  look_at=(1.0, 0.0, 0.0), lens_mm=35.0),
        CameraKey(t=5.0, position=(10.0, 0.0, 0.0),
                  look_at=(1.0, 0.0, 0.0), lens_mm=85.0),
    )
    eng.register_previs_shot(_shot("a", 5.0, keys=keys))
    out = eng.simulate_camera_at("a", 0.0)
    assert out.position == (0.0, 0.0, 0.0)
    assert out.lens_mm == 35.0


def test_simulate_camera_at_end():
    eng = PrevisEngine()
    keys = (
        CameraKey(t=0.0, position=(0.0, 0.0, 0.0),
                  look_at=(1.0, 0.0, 0.0), lens_mm=35.0),
        CameraKey(t=5.0, position=(10.0, 0.0, 0.0),
                  look_at=(1.0, 0.0, 0.0), lens_mm=85.0),
    )
    eng.register_previs_shot(_shot("a", 5.0, keys=keys))
    out = eng.simulate_camera_at("a", 5.0)
    assert out.position == (10.0, 0.0, 0.0)


def test_simulate_camera_midpoint_lens_lerp():
    eng = PrevisEngine()
    keys = (
        CameraKey(t=0.0, position=(0.0, 0.0, 0.0),
                  look_at=(1.0, 0.0, 0.0), lens_mm=35.0),
        CameraKey(t=10.0, position=(10.0, 0.0, 0.0),
                  look_at=(1.0, 0.0, 0.0), lens_mm=135.0),
    )
    eng.register_previs_shot(_shot("a", 10.0, keys=keys))
    out = eng.simulate_camera_at("a", 5.0)
    assert out.lens_mm == pytest.approx(85.0, abs=0.01)
    assert out.position[0] == pytest.approx(5.0, abs=0.01)


def test_simulate_camera_out_of_range_raises():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a", 5.0))
    with pytest.raises(ValueError):
        eng.simulate_camera_at("a", 10.0)


def test_simulate_camera_unknown_shot_raises():
    eng = PrevisEngine()
    with pytest.raises(KeyError):
        eng.simulate_camera_at("nope", 0.0)


def test_all_shots_lists_everything():
    eng = PrevisEngine()
    eng.register_previs_shot(_shot("a"))
    eng.register_previs_shot(_shot("b"))
    assert len(eng.all_shots()) == 2
