"""Tests for storyboard_panels."""
from __future__ import annotations

import pytest

from server.storyboard_panels import (
    AspectRatio,
    CameraMove,
    Framing,
    Panel,
    StoryboardSystem,
)


def _panel(
    panel_id: str = "p1",
    scene_id: str = "s1",
    shot_index: int = 0,
    framing: Framing = Framing.MEDIUM,
    camera_move: CameraMove = CameraMove.STATIC,
    lens_mm_hint: float = 50.0,
    eye_trace: str = "center",
    axis_side: str = "A",
    has_dialogue: bool = False,
    dialogue_excerpt: str = "",
    aspect: AspectRatio = AspectRatio.THEATRICAL_FLAT,
) -> Panel:
    return Panel(
        panel_id=panel_id,
        scene_id=scene_id,
        shot_index=shot_index,
        aspect_ratio=aspect,
        framing=framing,
        camera_move=camera_move,
        action_description="action",
        lens_mm_hint=lens_mm_hint,
        focus_target="curilla",
        has_dialogue=has_dialogue,
        dialogue_excerpt=dialogue_excerpt,
        sound_cue="",
        eye_trace=eye_trace,
        axis_side=axis_side,
    )


# ---- Aspect ratios ----

def test_academy_ratio_numeric():
    assert AspectRatio.ACADEMY.numeric == pytest.approx(1.33)


def test_anamorphic_ratio_numeric():
    assert AspectRatio.ANAMORPHIC.numeric == pytest.approx(2.39)


def test_social_vertical_is_under_one():
    assert AspectRatio.SOCIAL_VERTICAL.numeric < 1


def test_aspect_ratio_round_trip():
    p = _panel(aspect=AspectRatio.UNIVISIUM)
    assert p.aspect_ratio == AspectRatio.UNIVISIUM


# ---- Registration ----

def test_register_panel_stores():
    sys = StoryboardSystem()
    sys.register_panel(_panel())
    assert sys.panel_count() == 1


def test_register_duplicate_rejected():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1"))
    with pytest.raises(ValueError):
        sys.register_panel(_panel("p1"))


def test_negative_shot_index_rejected():
    sys = StoryboardSystem()
    with pytest.raises(ValueError):
        sys.register_panel(_panel(shot_index=-1))


def test_negative_lens_rejected():
    sys = StoryboardSystem()
    with pytest.raises(ValueError):
        sys.register_panel(_panel(lens_mm_hint=-10))


def test_invalid_eye_trace_rejected():
    sys = StoryboardSystem()
    with pytest.raises(ValueError):
        sys.register_panel(_panel(eye_trace="diagonal"))


def test_invalid_axis_side_rejected():
    sys = StoryboardSystem()
    with pytest.raises(ValueError):
        sys.register_panel(_panel(axis_side="C"))


def test_dialogue_panel_requires_excerpt():
    sys = StoryboardSystem()
    with pytest.raises(ValueError):
        sys.register_panel(
            _panel(has_dialogue=True, dialogue_excerpt=""),
        )


def test_lookup_unknown_raises():
    sys = StoryboardSystem()
    with pytest.raises(KeyError):
        sys.lookup("nope")


# ---- Lookups / aggregation ----

def test_panels_for_scene_orders_by_shot_index():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p2", shot_index=2))
    sys.register_panel(_panel("p1", shot_index=0))
    sys.register_panel(_panel("p3", shot_index=1))
    panels = sys.panels_for_scene("s1")
    assert [p.panel_id for p in panels] == ["p1", "p3", "p2"]


def test_panels_for_shot_filters_by_index():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", shot_index=0))
    sys.register_panel(_panel("p2", shot_index=0))
    sys.register_panel(_panel("p3", shot_index=1))
    panels = sys.panels_for_shot("s1", 0)
    assert len(panels) == 2


def test_sheet_returns_panels_for_scene():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", shot_index=0))
    sys.register_panel(_panel("p2", shot_index=1))
    sheet = sys.sheet("s1", max_panels=10)
    assert len(sheet.panels) == 2
    assert sheet.scene_id == "s1"


def test_sheet_clamps_to_max_panels():
    sys = StoryboardSystem()
    for i in range(5):
        sys.register_panel(_panel(f"p{i}", shot_index=i))
    sheet = sys.sheet("s1", max_panels=3)
    assert len(sheet.panels) == 3


def test_sheet_zero_max_panels_rejected():
    sys = StoryboardSystem()
    with pytest.raises(ValueError):
        sys.sheet("s1", max_panels=0)


def test_sheet_zero_budget_rejected():
    sys = StoryboardSystem()
    with pytest.raises(ValueError):
        sys.sheet("s1", target_page_budget=0)


def test_panels_with_dialogue_filters():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1"))
    sys.register_panel(
        _panel("p2", has_dialogue=True, dialogue_excerpt="Hi."),
    )
    out = sys.panels_with_dialogue()
    assert len(out) == 1
    assert out[0].panel_id == "p2"


# ---- Continuity validation ----

def test_axis_jump_flagged_warning():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", axis_side="A"))
    p2 = _panel("p2", shot_index=1, axis_side="B")
    sys.register_panel(p2)
    issues = sys.validate_continuity_with("p1", p2)
    kinds = {i.kind for i in issues}
    assert "axis_jump" in kinds
    sev = {i.severity for i in issues if i.kind == "axis_jump"}
    assert "warning" in sev


def test_axis_jump_with_insert_bypass_no_issue():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", axis_side="A"))
    p2 = _panel(
        "p2", shot_index=1, axis_side="B", framing=Framing.INSERT,
    )
    sys.register_panel(p2)
    issues = sys.validate_continuity_with("p1", p2)
    kinds = {i.kind for i in issues}
    assert "axis_jump" not in kinds


def test_axis_jump_with_extreme_close_bypass_no_issue():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", axis_side="A"))
    p2 = _panel(
        "p2", shot_index=1, axis_side="B",
        framing=Framing.EXTREME_CLOSE,
    )
    sys.register_panel(p2)
    issues = sys.validate_continuity_with("p1", p2)
    assert all(i.kind != "axis_jump" for i in issues)


def test_eye_trace_left_to_right_break():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", eye_trace="left"))
    p2 = _panel("p2", shot_index=1, eye_trace="right")
    sys.register_panel(p2)
    issues = sys.validate_continuity_with("p1", p2)
    kinds = {i.kind for i in issues}
    assert "eye_trace_break" in kinds


def test_eye_trace_center_to_anywhere_no_break():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", eye_trace="center"))
    p2 = _panel("p2", shot_index=1, eye_trace="left")
    sys.register_panel(p2)
    issues = sys.validate_continuity_with("p1", p2)
    assert all(i.kind != "eye_trace_break" for i in issues)


def test_lens_jump_24_to_200_flagged():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", lens_mm_hint=24))
    p2 = _panel("p2", shot_index=1, lens_mm_hint=200)
    sys.register_panel(p2)
    issues = sys.validate_continuity_with("p1", p2)
    kinds = {i.kind for i in issues}
    assert "lens_jump" in kinds


def test_lens_jump_50_to_85_no_issue():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", lens_mm_hint=50))
    p2 = _panel("p2", shot_index=1, lens_mm_hint=85)
    sys.register_panel(p2)
    issues = sys.validate_continuity_with("p1", p2)
    assert all(i.kind != "lens_jump" for i in issues)


def test_continuity_clean_returns_empty():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1", axis_side="A", lens_mm_hint=50))
    p2 = _panel(
        "p2", shot_index=1, axis_side="A", lens_mm_hint=85,
    )
    sys.register_panel(p2)
    issues = sys.validate_continuity_with("p1", p2)
    assert issues == ()


def test_camera_move_enum_round_trip():
    p = _panel(camera_move=CameraMove.WHIP)
    assert p.camera_move == CameraMove.WHIP


def test_all_camera_moves_distinct():
    seen = {m.value for m in CameraMove}
    assert len(seen) == len(list(CameraMove))


def test_all_panels_lists_everything():
    sys = StoryboardSystem()
    sys.register_panel(_panel("p1"))
    sys.register_panel(_panel("p2", shot_index=1))
    assert len(sys.all_panels()) == 2
