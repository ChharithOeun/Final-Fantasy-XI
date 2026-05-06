"""Tests for hotbar_layout."""
from __future__ import annotations

from server.hotbar_layout import HotbarLayoutRegistry


def test_ensure_layout_happy():
    r = HotbarLayoutRegistry()
    assert r.ensure_layout(player_id="alice", job="WHM") is True


def test_ensure_layout_blank_player_blocked():
    r = HotbarLayoutRegistry()
    out = r.ensure_layout(player_id="", job="WHM")
    assert out is False


def test_ensure_layout_blank_job_blocked():
    r = HotbarLayoutRegistry()
    out = r.ensure_layout(player_id="alice", job="")
    assert out is False


def test_ensure_layout_duplicate_blocked():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    out = r.ensure_layout(player_id="alice", job="WHM")
    assert out is False


def test_set_slot_happy():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    out = r.set_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=3,
        command_id="cure_iv", label="Cure IV",
        icon_hint="cure_icon",
    )
    assert out is True
    s = r.get_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=3,
    )
    assert s.command_id == "cure_iv"


def test_set_slot_blank_command_blocked():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    out = r.set_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=0, command_id="",
    )
    assert out is False


def test_set_slot_no_layout():
    r = HotbarLayoutRegistry()
    out = r.set_slot(
        player_id="ghost", job="WHM",
        bar_index=0, slot_index=0, command_id="x",
    )
    assert out is False


def test_set_slot_bar_out_of_range():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    out = r.set_slot(
        player_id="alice", job="WHM",
        bar_index=99, slot_index=0, command_id="x",
    )
    assert out is False


def test_set_slot_slot_out_of_range():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    out = r.set_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=99, command_id="x",
    )
    assert out is False


def test_set_slot_negative_index_blocked():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    out = r.set_slot(
        player_id="alice", job="WHM",
        bar_index=-1, slot_index=0, command_id="x",
    )
    assert out is False


def test_clear_slot_resets():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    r.set_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=0, command_id="cure",
    )
    out = r.clear_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=0,
    )
    assert out is True
    s = r.get_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=0,
    )
    assert s.command_id == ""


def test_clear_slot_unknown_layout():
    r = HotbarLayoutRegistry()
    out = r.clear_slot(
        player_id="ghost", job="WHM",
        bar_index=0, slot_index=0,
    )
    assert out is False


def test_get_slot_unknown_layout():
    r = HotbarLayoutRegistry()
    s = r.get_slot(
        player_id="ghost", job="WHM",
        bar_index=0, slot_index=0,
    )
    assert s is None


def test_get_slot_out_of_range_none():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    s = r.get_slot(
        player_id="alice", job="WHM",
        bar_index=99, slot_index=0,
    )
    assert s is None


def test_per_job_layouts_independent():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    r.ensure_layout(player_id="alice", job="BLM")
    r.set_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=0, command_id="cure",
    )
    s = r.get_slot(
        player_id="alice", job="BLM",
        bar_index=0, slot_index=0,
    )
    assert s.command_id == ""   # BLM bar untouched


def test_copy_layout_clones():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    r.set_slot(
        player_id="alice", job="WHM",
        bar_index=1, slot_index=4, command_id="cure",
    )
    out = r.copy_layout(
        player_id="alice", from_job="WHM", to_job="SCH",
    )
    assert out is True
    s = r.get_slot(
        player_id="alice", job="SCH",
        bar_index=1, slot_index=4,
    )
    assert s.command_id == "cure"


def test_copy_layout_doesnt_share_state():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    r.set_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=0, command_id="cure",
    )
    r.copy_layout(
        player_id="alice", from_job="WHM", to_job="SCH",
    )
    # mutating WHM should not change SCH
    r.set_slot(
        player_id="alice", job="WHM",
        bar_index=0, slot_index=0, command_id="cura",
    )
    s = r.get_slot(
        player_id="alice", job="SCH",
        bar_index=0, slot_index=0,
    )
    assert s.command_id == "cure"


def test_copy_layout_unknown_source():
    r = HotbarLayoutRegistry()
    out = r.copy_layout(
        player_id="alice", from_job="WHM", to_job="BLM",
    )
    assert out is False


def test_copy_layout_same_job_blocked():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    out = r.copy_layout(
        player_id="alice", from_job="WHM", to_job="WHM",
    )
    assert out is False


def test_eight_bars_twelve_slots():
    r = HotbarLayoutRegistry()
    assert r.num_bars() == 8
    assert r.slots_per_bar() == 12


def test_total_layouts():
    r = HotbarLayoutRegistry()
    r.ensure_layout(player_id="alice", job="WHM")
    r.ensure_layout(player_id="bob", job="BLM")
    assert r.total_layouts() == 2
