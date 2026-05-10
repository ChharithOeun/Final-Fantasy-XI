"""Tests for shot_list."""
from __future__ import annotations

import datetime as dt

import pytest

from server.shot_list import (
    ShotListSystem,
    ShotRow,
    ShotStatus,
    TimeOfDay,
)


def _row(
    shot_id: str = "s001",
    scene_id: str = "sc1",
    slate: str = "1A",
    lens_mm: float = 50.0,
    location: str = "bastok_markets",
    time_of_day: TimeOfDay = TimeOfDay.DAY,
    talent: tuple[str, ...] = ("curilla",),
    setup: int = 30,
    audio: bool = True,
    vfx: bool = False,
    mocap: bool = False,
    depends_on: tuple[str, ...] = (),
) -> ShotRow:
    return ShotRow(
        shot_id=shot_id,
        scene_id=scene_id,
        slate=slate,
        description="d",
        lens_mm=lens_mm,
        location=location,
        time_of_day=time_of_day,
        talent_ids=talent,
        props_required=(),
        vfx_required=vfx,
        audio_required=audio,
        mocap_required=mocap,
        expected_setup_minutes=setup,
        depends_on=depends_on,
    )


# ---- Registration ----

def test_register_shot_stores():
    sys = ShotListSystem()
    sys.register_shot(_row())
    assert len(sys.all_shots()) == 1


def test_register_duplicate_rejected():
    sys = ShotListSystem()
    sys.register_shot(_row("s001"))
    with pytest.raises(ValueError):
        sys.register_shot(_row("s001"))


def test_zero_lens_rejected():
    sys = ShotListSystem()
    with pytest.raises(ValueError):
        sys.register_shot(_row(lens_mm=0))


def test_negative_setup_rejected():
    sys = ShotListSystem()
    with pytest.raises(ValueError):
        sys.register_shot(_row(setup=-5))


def test_empty_slate_rejected():
    sys = ShotListSystem()
    with pytest.raises(ValueError):
        sys.register_shot(_row(slate=""))


def test_self_dependency_rejected():
    sys = ShotListSystem()
    with pytest.raises(ValueError):
        sys.register_shot(_row("s001", depends_on=("s001",)))


def test_lookup_unknown_raises():
    sys = ShotListSystem()
    with pytest.raises(KeyError):
        sys.lookup("nope")


# ---- Scene / talent / status filtering ----

def test_shots_for_scene():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", scene_id="A"))
    sys.register_shot(_row("s2", scene_id="A"))
    sys.register_shot(_row("s3", scene_id="B"))
    assert len(sys.shots_for_scene("A")) == 2
    assert len(sys.shots_for_scene("B")) == 1


def test_shots_for_talent():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", talent=("curilla",)))
    sys.register_shot(_row("s2", talent=("trion", "curilla")))
    sys.register_shot(_row("s3", talent=("trion",)))
    assert len(sys.shots_for_talent("curilla")) == 2
    assert len(sys.shots_for_talent("trion")) == 2


def test_mark_status_updates():
    sys = ShotListSystem()
    sys.register_shot(_row("s1"))
    out = sys.mark_status("s1", ShotStatus.SHOT)
    assert out.status == ShotStatus.SHOT
    assert sys.lookup("s1").status == ShotStatus.SHOT


def test_mark_status_unknown_raises():
    sys = ShotListSystem()
    with pytest.raises(KeyError):
        sys.mark_status("nope", ShotStatus.SHOT)


def test_shots_by_status():
    sys = ShotListSystem()
    sys.register_shot(_row("s1"))
    sys.register_shot(_row("s2"))
    sys.mark_status("s1", ShotStatus.SHOT)
    assert len(sys.shots_by_status(ShotStatus.SHOT)) == 1
    assert len(sys.shots_by_status(ShotStatus.PLANNED)) == 1


def test_completion_percent_zero_for_empty():
    sys = ShotListSystem()
    assert sys.completion_percent() == 0.0


def test_completion_percent_full_when_all_shot():
    sys = ShotListSystem()
    sys.register_shot(_row("s1"))
    sys.register_shot(_row("s2"))
    sys.mark_status("s1", ShotStatus.SHOT)
    sys.mark_status("s2", ShotStatus.OMITTED)
    assert sys.completion_percent() == 100.0


# ---- Grouping ----

def test_group_by_location():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", location="bastok"))
    sys.register_shot(_row("s2", location="bastok"))
    sys.register_shot(_row("s3", location="jeuno"))
    g = sys.group_by_location()
    assert len(g["bastok"]) == 2
    assert len(g["jeuno"]) == 1


def test_group_by_time_of_day():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", time_of_day=TimeOfDay.DAY))
    sys.register_shot(_row("s2", time_of_day=TimeOfDay.DAY))
    sys.register_shot(_row("s3", time_of_day=TimeOfDay.NIGHT))
    g = sys.group_by_time_of_day()
    assert len(g[TimeOfDay.DAY]) == 2
    assert len(g[TimeOfDay.NIGHT]) == 1


# ---- Scheduling / call sheets ----

def test_assign_date_marks_scheduled():
    sys = ShotListSystem()
    sys.register_shot(_row("s1"))
    out = sys.assign_date("s1", dt.date(2026, 5, 10))
    assert out.shoot_date == dt.date(2026, 5, 10)
    assert out.status == ShotStatus.SCHEDULED


def test_call_sheet_aggregates_talent():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", talent=("curilla", "trion")))
    sys.register_shot(_row("s2", talent=("trion",)))
    sys.assign_date("s1", dt.date(2026, 5, 10))
    sys.assign_date("s2", dt.date(2026, 5, 10))
    sheet = sys.call_sheet_for(dt.date(2026, 5, 10))
    assert "curilla" in sheet.talent_required
    assert "trion" in sheet.talent_required


def test_call_sheet_groups_by_location():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", location="A"))
    sys.register_shot(_row("s2", location="A"))
    sys.register_shot(_row("s3", location="B"))
    for s in ("s1", "s2", "s3"):
        sys.assign_date(s, dt.date(2026, 5, 10))
    sheet = sys.call_sheet_for(dt.date(2026, 5, 10))
    locs = dict(sheet.location_groups)
    assert len(locs["A"]) == 2
    assert len(locs["B"]) == 1


def test_call_sheet_sums_setup_minutes():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", setup=30))
    sys.register_shot(_row("s2", setup=45))
    for s in ("s1", "s2"):
        sys.assign_date(s, dt.date(2026, 5, 10))
    sheet = sys.call_sheet_for(dt.date(2026, 5, 10))
    assert sheet.total_setup_minutes == 75


def test_call_sheet_empty_when_no_shots():
    sys = ShotListSystem()
    sheet = sys.call_sheet_for(dt.date(2026, 5, 10))
    assert sheet.location_groups == ()
    assert sheet.talent_required == ()


# ---- Equipment pull ----

def test_equipment_pull_collects_lenses():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", lens_mm=24))
    sys.register_shot(_row("s2", lens_mm=85))
    sys.register_shot(_row("s3", lens_mm=24))
    pull = sys.equipment_pull_list()
    assert pull.lenses_mm == (24.0, 85.0)


def test_equipment_pull_flags_audio_vfx_mocap():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", audio=True))
    sys.register_shot(_row("s2", vfx=True, audio=False))
    sys.register_shot(_row("s3", mocap=True, audio=False))
    pull = sys.equipment_pull_list()
    assert pull.needs_audio is True
    assert pull.needs_vfx is True
    assert pull.needs_mocap is True


def test_equipment_pull_filtered_by_scene():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", scene_id="A", lens_mm=24))
    sys.register_shot(_row("s2", scene_id="B", lens_mm=200))
    pull = sys.equipment_pull_list(scene_ids=["A"])
    assert pull.lenses_mm == (24.0,)


def test_equipment_pull_counts_locations():
    sys = ShotListSystem()
    sys.register_shot(_row("s1", location="A"))
    sys.register_shot(_row("s2", location="B"))
    sys.register_shot(_row("s3", location="A"))
    pull = sys.equipment_pull_list()
    assert pull.location_count == 2


# ---- Critical path ----

def test_critical_path_orders_by_block_count():
    sys = ShotListSystem()
    sys.register_shot(_row("s1"))
    sys.register_shot(_row("s2", depends_on=("s1",)))
    sys.register_shot(_row("s3", depends_on=("s1",)))
    sys.register_shot(_row("s4", depends_on=("s2",)))
    cp = sys.critical_path()
    # s1 blocks s2, s3, s4 (transitively) — most blocking.
    assert cp[0] == "s1"


def test_critical_path_excludes_terminal_shots():
    sys = ShotListSystem()
    sys.register_shot(_row("s1"))
    sys.register_shot(_row("s2", depends_on=("s1",)))
    cp = sys.critical_path()
    assert "s1" in cp
    assert "s2" not in cp


def test_critical_path_empty_for_no_dependencies():
    sys = ShotListSystem()
    sys.register_shot(_row("s1"))
    sys.register_shot(_row("s2"))
    assert sys.critical_path() == ()
