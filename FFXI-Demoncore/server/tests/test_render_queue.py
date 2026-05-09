"""Tests for render_queue."""
from __future__ import annotations

import pytest

from server.render_queue import (
    PRESETS, RenderJob, RenderPreset, RenderQueueSystem,
    list_presets, preset,
)


def test_five_presets():
    assert len(PRESETS) == 5


def test_preset_names():
    expected = {
        "gameplay_realtime", "cutscene_cinematic",
        "trailer_master", "social_clip",
        "led_virtual_production",
    }
    assert set(PRESETS) == expected


def test_select_preset_happy():
    s = RenderQueueSystem()
    p = s.select_preset("trailer_master")
    assert isinstance(p, RenderPreset)
    assert s.selected is p


def test_select_preset_unknown_raises():
    s = RenderQueueSystem()
    with pytest.raises(ValueError):
        s.select_preset("ghost_preset")


def test_gameplay_is_60fps():
    assert PRESETS["gameplay_realtime"].fps == 60


def test_cutscene_is_24fps():
    assert PRESETS["cutscene_cinematic"].fps == 24


def test_trailer_master_is_uncompressed_exr():
    p = PRESETS["trailer_master"]
    assert p.output_format == "exr_seq"
    assert "EXR" in p.codec
    assert p.bit_depth == 16


def test_trailer_master_is_aces_ap0():
    assert PRESETS["trailer_master"].color_space == "ACES_AP0"


def test_gameplay_motion_blur_off():
    assert PRESETS["gameplay_realtime"].motion_blur_enabled is False


def test_cinematic_motion_blur_on():
    assert PRESETS["cutscene_cinematic"].motion_blur_enabled is True


def test_output_path_mp4():
    s = RenderQueueSystem()
    p = s.output_path_for("gameplay_realtime", "boss_01")
    assert p.endswith(".mp4")


def test_output_path_exr_sequence():
    s = RenderQueueSystem()
    p = s.output_path_for("trailer_master", "trailer_v3")
    assert ".####.exr" in p


def test_output_path_unknown_preset_raises():
    s = RenderQueueSystem()
    with pytest.raises(ValueError):
        s.output_path_for("ghost", "x")


def test_output_path_empty_sequence_raises():
    s = RenderQueueSystem()
    with pytest.raises(ValueError):
        s.output_path_for("trailer_master", "")


def test_queue_render_happy():
    s = RenderQueueSystem()
    jid = s.queue_render(
        preset="cutscene_cinematic", sequence="boss_intro",
    )
    assert jid is not None


def test_queue_render_unknown_preset_returns_none():
    s = RenderQueueSystem()
    assert s.queue_render(
        preset="ghost", sequence="x",
    ) is None


def test_queue_render_empty_sequence_returns_none():
    s = RenderQueueSystem()
    assert s.queue_render(
        preset="cutscene_cinematic", sequence="",
    ) is None


def test_queue_render_appends_job():
    s = RenderQueueSystem()
    s.queue_render(preset="gameplay_realtime", sequence="a")
    s.queue_render(preset="gameplay_realtime", sequence="b")
    assert len(s.jobs()) == 2


def test_get_estimated_time_gameplay_1x():
    s = RenderQueueSystem()
    s.select_preset("gameplay_realtime")
    assert s.get_estimated_time(
        seconds_of_footage=60,
    ) == pytest.approx(60.0)


def test_get_estimated_time_trailer_120x():
    s = RenderQueueSystem()
    s.select_preset("trailer_master")
    # 60s of footage * 120x = 7200s = 2h
    assert s.get_estimated_time(
        seconds_of_footage=60,
    ) == pytest.approx(7200.0)


def test_get_estimated_time_explicit_preset():
    s = RenderQueueSystem()
    t_ = s.get_estimated_time(
        seconds_of_footage=10,
        preset="cutscene_cinematic",
    )
    assert t_ == pytest.approx(300.0)  # 10 * 30


def test_get_estimated_time_no_preset_raises():
    s = RenderQueueSystem()
    with pytest.raises(RuntimeError):
        s.get_estimated_time(seconds_of_footage=10)


def test_get_estimated_time_unknown_preset_raises():
    s = RenderQueueSystem()
    with pytest.raises(ValueError):
        s.get_estimated_time(
            seconds_of_footage=10, preset="ghost",
        )


def test_get_estimated_time_zero_footage_raises():
    s = RenderQueueSystem()
    s.select_preset("gameplay_realtime")
    with pytest.raises(ValueError):
        s.get_estimated_time(seconds_of_footage=0)


def test_cancel_existing_job():
    s = RenderQueueSystem()
    jid = s.queue_render(
        preset="gameplay_realtime", sequence="a",
    )
    assert s.cancel(jid) is True
    assert len(s.jobs()) == 0


def test_cancel_unknown_job_returns_false():
    s = RenderQueueSystem()
    assert s.cancel("ghost_job") is False


def test_list_presets_sorted():
    names = list_presets()
    assert names == tuple(sorted(names))


def test_preset_helper_unknown_raises():
    with pytest.raises(ValueError):
        preset("ghost")


def test_led_vp_at_24fps():
    # Match film cadence so the LED wall sync stays clean.
    assert PRESETS["led_virtual_production"].fps == 24


def test_social_clip_codec_av1():
    assert PRESETS["social_clip"].codec == "AV1"
