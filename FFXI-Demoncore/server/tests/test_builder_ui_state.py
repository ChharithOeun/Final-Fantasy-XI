"""Tests for builder_ui_state."""
from __future__ import annotations

from server.addon_intent_spec import (
    AddonIntentSpec, GearSetEntry, OffenseMode,
)
from server.builder_ui_state import BuilderMode, BuilderUIState
from server.gear_slot_filter import Slot


def test_open_fresh_happy():
    b = BuilderUIState()
    out = b.open_fresh(
        player_id="alice", addon_id="rdm_chharith", job="RDM",
    )
    assert out is True
    assert b.mode(player_id="alice") == BuilderMode.FRESH


def test_open_fresh_blank_player():
    b = BuilderUIState()
    out = b.open_fresh(
        player_id="", addon_id="x", job="RDM",
    )
    assert out is False


def test_open_fresh_blank_addon():
    b = BuilderUIState()
    out = b.open_fresh(
        player_id="alice", addon_id="", job="RDM",
    )
    assert out is False


def test_open_fresh_validation_runs():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    v = b.current_validation(player_id="alice")
    assert v is not None
    # No weapon sets yet → warnings only, but valid? No, weapon set
    # validation is per-set; an empty weapon_sets dict passes.
    # The required validators don't include "must have weapons."


def test_open_existing_uses_provided_spec():
    b = BuilderUIState()
    spec = AddonIntentSpec(
        addon_id="rdm", job="RDM",
        weapon_sets={
            "DT": GearSetEntry(
                set_name="DT",
                slot_to_item={"main": "Murgleis"},
            ),
        },
    )
    out = b.open_existing(player_id="alice", spec=spec)
    assert out is True
    cur = b.current_spec(player_id="alice")
    assert "DT" in cur.weapon_sets


def test_open_existing_blank_addon_blocked():
    b = BuilderUIState()
    spec = AddonIntentSpec(addon_id="", job="x")
    assert b.open_existing(player_id="alice", spec=spec) is False


def test_set_active_set():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    out = b.set_active_set(
        player_id="alice", set_name="Death Blossom",
    )
    assert out is True


def test_set_active_set_blank_blocked():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    out = b.set_active_set(player_id="alice", set_name="")
    assert out is False


def test_set_active_set_unknown_player():
    b = BuilderUIState()
    out = b.set_active_set(player_id="ghost", set_name="x")
    assert out is False


def test_assign_slot_creates_set():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    out = b.assign_slot(
        player_id="alice", set_name="Death Blossom",
        slot=Slot.MAIN, item_id="murgleis",
    )
    assert out is True
    cur = b.current_spec(player_id="alice")
    assert cur.weapon_sets["Death Blossom"].slot_to_item["main"] == "murgleis"


def test_assign_slot_extends_existing_set():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    b.assign_slot(
        player_id="alice", set_name="DT",
        slot=Slot.MAIN, item_id="murgleis",
    )
    b.assign_slot(
        player_id="alice", set_name="DT",
        slot=Slot.SUB, item_id="sakpata_sword",
    )
    cur = b.current_spec(player_id="alice")
    set_dt = cur.weapon_sets["DT"]
    assert set_dt.slot_to_item["main"] == "murgleis"
    assert set_dt.slot_to_item["sub"] == "sakpata_sword"


def test_assign_slot_blank_set_blocked():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    out = b.assign_slot(
        player_id="alice", set_name="",
        slot=Slot.MAIN, item_id="murgleis",
    )
    assert out is False


def test_assign_slot_unknown_player_blocked():
    b = BuilderUIState()
    out = b.assign_slot(
        player_id="ghost", set_name="DT",
        slot=Slot.MAIN, item_id="x",
    )
    assert out is False


def test_assign_slot_flips_to_editing_mode():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    assert b.mode(player_id="alice") == BuilderMode.FRESH
    b.assign_slot(
        player_id="alice", set_name="DT",
        slot=Slot.MAIN, item_id="murgleis",
    )
    assert b.mode(player_id="alice") == BuilderMode.EDITING


def test_assign_slot_revalidates():
    """Each assignment re-runs validation so the UI is live."""
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    v_before = b.current_validation(player_id="alice")
    b.assign_slot(
        player_id="alice", set_name="DT",
        slot=Slot.MAIN, item_id="murgleis",
    )
    v_after = b.current_validation(player_id="alice")
    # both are valid, but objects are different (re-evaluated)
    assert v_before is not v_after


def test_save_draft_marks_baseline():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    b.assign_slot(
        player_id="alice", set_name="DT",
        slot=Slot.MAIN, item_id="murgleis",
    )
    assert b.has_unsaved_changes(player_id="alice") is True
    b.save_draft(player_id="alice")
    assert b.has_unsaved_changes(player_id="alice") is False


def test_unsaved_after_save_then_modify():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    b.save_draft(player_id="alice")
    b.assign_slot(
        player_id="alice", set_name="DT",
        slot=Slot.MAIN, item_id="murgleis",
    )
    assert b.has_unsaved_changes(player_id="alice") is True


def test_save_draft_unknown_player():
    b = BuilderUIState()
    assert b.save_draft(player_id="ghost") is False


def test_default_offense_mode_revalidates():
    b = BuilderUIState()
    spec = AddonIntentSpec(
        addon_id="rdm", job="RDM",
        weapon_sets={
            "DT": GearSetEntry(
                set_name="DT",
                slot_to_item={"main": "Murgleis"},
            ),
        },
        offense_modes=[
            OffenseMode(mode_name="DT", weaponskill_target="x"),
        ],
    )
    b.open_existing(player_id="alice", spec=spec)
    # set valid mode
    b.set_default_offense_mode(player_id="alice", mode_name="DT")
    v = b.current_validation(player_id="alice")
    assert v.valid is True
    # set bogus mode → validation flips to invalid
    b.set_default_offense_mode(player_id="alice", mode_name="GHOST")
    v2 = b.current_validation(player_id="alice")
    assert v2.valid is False


def test_set_default_offense_unknown_player():
    b = BuilderUIState()
    assert b.set_default_offense_mode(
        player_id="ghost", mode_name="DT",
    ) is False


def test_current_spec_unknown_none():
    b = BuilderUIState()
    assert b.current_spec(player_id="ghost") is None


def test_current_validation_unknown_none():
    b = BuilderUIState()
    assert b.current_validation(player_id="ghost") is None


def test_mode_unknown_none():
    b = BuilderUIState()
    assert b.mode(player_id="ghost") is None


def test_three_builder_modes():
    assert len(list(BuilderMode)) == 3


def test_total_drafts():
    b = BuilderUIState()
    b.open_fresh(player_id="alice", addon_id="x", job="RDM")
    b.open_fresh(player_id="bob", addon_id="y", job="WHM")
    assert b.total_drafts() == 2


def test_no_unsaved_for_unknown_player():
    b = BuilderUIState()
    assert b.has_unsaved_changes(player_id="ghost") is False
