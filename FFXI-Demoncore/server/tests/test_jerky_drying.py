"""Tests for jerky_drying."""
from __future__ import annotations

from server.jerky_drying import DryingStage, JerkyDryingRack


def test_place_slab_happy():
    r = JerkyDryingRack()
    ok = r.place_slab(
        slab_id="s1", rack_id="rack1",
        raw_meat_kind="raw_buffalo", salt_available=1,
        started_at=10,
    )
    assert ok is True
    assert r.stage_of(slab_id="s1") == DryingStage.FRESH


def test_blank_id_blocked():
    r = JerkyDryingRack()
    out = r.place_slab(
        slab_id="", rack_id="r", raw_meat_kind="raw_x",
        salt_available=1, started_at=10,
    )
    assert out is False


def test_non_raw_blocked():
    r = JerkyDryingRack()
    out = r.place_slab(
        slab_id="s", rack_id="r",
        raw_meat_kind="cooked_buffalo", salt_available=1,
        started_at=10,
    )
    assert out is False


def test_no_salt_blocked():
    r = JerkyDryingRack()
    out = r.place_slab(
        slab_id="s", rack_id="r",
        raw_meat_kind="raw_buffalo", salt_available=0,
        started_at=10,
    )
    assert out is False


def test_rack_capacity():
    r = JerkyDryingRack()
    for i in range(6):
        r.place_slab(
            slab_id=f"s{i}", rack_id="rack1",
            raw_meat_kind="raw_x", salt_available=1,
            started_at=10,
        )
    out = r.place_slab(
        slab_id="extra", rack_id="rack1",
        raw_meat_kind="raw_x", salt_available=1,
        started_at=10,
    )
    assert out is False


def test_duplicate_slab_blocked():
    r = JerkyDryingRack()
    r.place_slab(
        slab_id="s1", rack_id="r",
        raw_meat_kind="raw_x", salt_available=1,
        started_at=10,
    )
    again = r.place_slab(
        slab_id="s1", rack_id="r",
        raw_meat_kind="raw_y", salt_available=1,
        started_at=20,
    )
    assert again is False


def test_progress_advances_stage():
    r = JerkyDryingRack()
    r.place_slab(
        slab_id="s1", rack_id="r1",
        raw_meat_kind="raw_buffalo", salt_available=1,
        started_at=0,
    )
    # 30% of 3600 = 1080 sec
    r.tick(rack_id="r1", dt_seconds=1100)
    assert r.stage_of(slab_id="s1") == DryingStage.DRYING


def test_progress_to_nearly():
    r = JerkyDryingRack()
    r.place_slab(
        slab_id="s1", rack_id="r1",
        raw_meat_kind="raw_buffalo", salt_available=1,
        started_at=0,
    )
    # 70% = 2520
    r.tick(rack_id="r1", dt_seconds=2600)
    assert r.stage_of(slab_id="s1") == DryingStage.NEARLY


def test_progress_to_ready():
    r = JerkyDryingRack()
    r.place_slab(
        slab_id="s1", rack_id="r1",
        raw_meat_kind="raw_buffalo", salt_available=1,
        started_at=0,
    )
    r.tick(rack_id="r1", dt_seconds=3600)
    assert r.stage_of(slab_id="s1") == DryingStage.READY


def test_humid_regresses_to_fresh():
    r = JerkyDryingRack()
    r.place_slab(
        slab_id="s1", rack_id="r1",
        raw_meat_kind="raw_buffalo", salt_available=1,
        started_at=0,
    )
    r.tick(rack_id="r1", dt_seconds=2000)
    assert r.stage_of(slab_id="s1") == DryingStage.DRYING
    r.tick(rack_id="r1", dt_seconds=10, weather_humid=True)
    assert r.stage_of(slab_id="s1") == DryingStage.FRESH


def test_pull_when_ready():
    r = JerkyDryingRack()
    r.place_slab(
        slab_id="s1", rack_id="r1",
        raw_meat_kind="raw_buffalo", salt_available=1,
        started_at=0,
    )
    r.tick(rack_id="r1", dt_seconds=3600)
    out = r.pull_slab(slab_id="s1")
    assert out == "jerky_buffalo"


def test_pull_when_not_ready():
    r = JerkyDryingRack()
    r.place_slab(
        slab_id="s1", rack_id="r1",
        raw_meat_kind="raw_buffalo", salt_available=1,
        started_at=0,
    )
    out = r.pull_slab(slab_id="s1")
    assert out is None


def test_pull_unknown():
    r = JerkyDryingRack()
    out = r.pull_slab(slab_id="ghost")
    assert out is None


def test_pulled_slab_removed():
    r = JerkyDryingRack()
    r.place_slab(
        slab_id="s1", rack_id="r1",
        raw_meat_kind="raw_buffalo", salt_available=1,
        started_at=0,
    )
    r.tick(rack_id="r1", dt_seconds=3600)
    r.pull_slab(slab_id="s1")
    assert r.total_slabs() == 0


def test_tick_returns_ready_count():
    r = JerkyDryingRack()
    r.place_slab(
        slab_id="s1", rack_id="r1",
        raw_meat_kind="raw_x", salt_available=1, started_at=0,
    )
    r.place_slab(
        slab_id="s2", rack_id="r1",
        raw_meat_kind="raw_y", salt_available=1, started_at=0,
    )
    out = r.tick(rack_id="r1", dt_seconds=3600)
    assert out == 2


def test_tick_unknown_rack_zero():
    r = JerkyDryingRack()
    assert r.tick(rack_id="ghost", dt_seconds=10) == 0


def test_four_drying_stages():
    assert len(list(DryingStage)) == 4


def test_stage_unknown_returns_fresh():
    r = JerkyDryingRack()
    assert r.stage_of(slab_id="ghost") == DryingStage.FRESH
