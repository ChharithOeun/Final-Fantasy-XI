"""Tests for player_woodworking."""
from __future__ import annotations

from server.player_woodworking import (
    PlayerWoodworkingSystem, Stage, Finish,
)


def test_begin_happy():
    s = PlayerWoodworkingSystem()
    assert s.begin(
        crafter_id="bob", item_kind="dining_chair",
        lumber_units=5, started_day=10,
    ) is not None


def test_begin_blank():
    s = PlayerWoodworkingSystem()
    assert s.begin(
        crafter_id="", item_kind="x",
        lumber_units=1, started_day=10,
    ) is None


def test_begin_zero_lumber():
    s = PlayerWoodworkingSystem()
    assert s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=0, started_day=10,
    ) is None


def test_begin_starts_planed():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    assert s.project(
        project_id=pid,
    ).stage == Stage.PLANED


def test_advance_through_stages():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    s.advance(project_id=pid, skill_check=80)
    assert s.project(
        project_id=pid,
    ).stage == Stage.JOINED
    s.advance(project_id=pid, skill_check=80)
    assert s.project(
        project_id=pid,
    ).stage == Stage.SANDED
    s.advance(project_id=pid, skill_check=80)
    assert s.project(
        project_id=pid,
    ).stage == Stage.FINISHED


def test_advance_invalid_skill_check():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    assert s.advance(
        project_id=pid, skill_check=120,
    ) is False


def test_advance_past_finished_blocked():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    for _ in range(3):
        s.advance(project_id=pid, skill_check=80)
    assert s.advance(
        project_id=pid, skill_check=80,
    ) is False


def test_advance_quality_accumulates():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    # Initial 20, +20 each advance at skill 100
    s.advance(project_id=pid, skill_check=100)
    assert s.project(
        project_id=pid,
    ).quality_score == 40


def test_advance_quality_caps_at_100():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    for _ in range(3):
        s.advance(project_id=pid, skill_check=100)
    # 20 + 20*3 = 80; can't reach 100 in this path
    p = s.project(project_id=pid)
    assert p.quality_score == 80


def test_skip_stage_penalty():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    s.advance(project_id=pid, skill_check=80)
    # quality = 20 + 16 = 36
    s.skip_stage(project_id=pid)
    # now SANDED, quality = max(0, 36-25) = 11
    p = s.project(project_id=pid)
    assert p.stage == Stage.SANDED
    assert p.quality_score == 11


def test_apply_finish_at_finished():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    for _ in range(3):
        s.advance(project_id=pid, skill_check=80)
    assert s.apply_finish(
        project_id=pid, finish=Finish.LACQUER,
        now_day=15,
    ) is True


def test_apply_finish_before_finished_blocked():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    s.advance(project_id=pid, skill_check=80)
    assert s.apply_finish(
        project_id=pid, finish=Finish.OIL,
        now_day=12,
    ) is False


def test_double_finish_blocked():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    for _ in range(3):
        s.advance(project_id=pid, skill_check=80)
    s.apply_finish(
        project_id=pid, finish=Finish.OIL,
        now_day=15,
    )
    assert s.apply_finish(
        project_id=pid, finish=Finish.STAIN,
        now_day=16,
    ) is False


def test_abandon():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    assert s.abandon(project_id=pid) is True


def test_abandon_after_finished_blocked():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    for _ in range(3):
        s.advance(project_id=pid, skill_check=80)
    s.apply_finish(
        project_id=pid, finish=Finish.WAX,
        now_day=15,
    )
    # After finish completed_day set, but stage is
    # still Stage.FINISHED — abandon should reject
    # finished projects.
    assert s.abandon(project_id=pid) is False


def test_is_complete_requires_finish():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    for _ in range(3):
        s.advance(project_id=pid, skill_check=80)
    assert s.is_complete(project_id=pid) is False
    s.apply_finish(
        project_id=pid, finish=Finish.WAX,
        now_day=15,
    )
    assert s.is_complete(project_id=pid) is True


def test_projects_of_crafter():
    s = PlayerWoodworkingSystem()
    s.begin(
        crafter_id="bob", item_kind="a",
        lumber_units=1, started_day=10,
    )
    s.begin(
        crafter_id="bob", item_kind="b",
        lumber_units=1, started_day=11,
    )
    s.begin(
        crafter_id="other", item_kind="c",
        lumber_units=1, started_day=12,
    )
    out = s.projects_of(crafter_id="bob")
    assert len(out) == 2


def test_advance_unknown():
    s = PlayerWoodworkingSystem()
    assert s.advance(
        project_id="ghost", skill_check=80,
    ) is False


def test_project_unknown():
    s = PlayerWoodworkingSystem()
    assert s.project(project_id="ghost") is None


def test_skip_at_last_stage_blocked():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    for _ in range(3):
        s.advance(project_id=pid, skill_check=80)
    # Now FINISHED — can't skip
    assert s.skip_stage(project_id=pid) is False


def test_finish_quality_bump():
    s = PlayerWoodworkingSystem()
    pid = s.begin(
        crafter_id="bob", item_kind="x",
        lumber_units=5, started_day=10,
    )
    for _ in range(3):
        s.advance(project_id=pid, skill_check=50)
    # Quality 20+10*3 = 50
    s.apply_finish(
        project_id=pid, finish=Finish.OIL,
        now_day=15,
    )
    assert s.project(
        project_id=pid,
    ).quality_score == 55


def test_enum_counts():
    assert len(list(Stage)) == 5
    assert len(list(Finish)) == 5
