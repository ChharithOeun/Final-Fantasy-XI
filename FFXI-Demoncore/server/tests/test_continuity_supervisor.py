"""Tests for continuity_supervisor."""
from __future__ import annotations

import pytest

from server.continuity_supervisor import (
    ContinuitySupervisor,
    Severity,
    Snapshot,
)


def _snap(
    shot_id: str = "sh1",
    scene_id: str = "sc1",
    character_id: str = "curilla",
    wardrobe: tuple[str, ...] = ("plate_armor",),
    props: tuple[str, ...] = (),
    blood: tuple[str, ...] = (),
    weather: str = "clear",
    tod: str = "day",
    hair: str = "clean",
    wounds: tuple[str, ...] = (),
    accessories: tuple[str, ...] = (),
) -> Snapshot:
    return Snapshot(
        shot_id=shot_id,
        scene_id=scene_id,
        character_id=character_id,
        wardrobe=wardrobe,
        props_in_hand=props,
        blood_on_face_locations=blood,
        weather=weather,
        time_of_day=tod,
        hair_state=hair,
        wounds=wounds,
        accessories=accessories,
    )


# ---- Registration ----

def test_register_snapshot_stores():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap())
    assert len(sup.all_snapshots()) == 1


def test_register_duplicate_rejected():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1"))
    with pytest.raises(ValueError):
        sup.register_snapshot(_snap("sh1"))


def test_empty_shot_id_rejected():
    sup = ContinuitySupervisor()
    with pytest.raises(ValueError):
        sup.register_snapshot(_snap(shot_id=""))


def test_empty_character_rejected():
    sup = ContinuitySupervisor()
    with pytest.raises(ValueError):
        sup.register_snapshot(_snap(character_id=""))


def test_invalid_hair_state_rejected():
    sup = ContinuitySupervisor()
    with pytest.raises(ValueError):
        sup.register_snapshot(_snap(hair="green"))


def test_lookup_unknown_raises():
    sup = ContinuitySupervisor()
    with pytest.raises(KeyError):
        sup.lookup("nope", "curilla")


# ---- Wardrobe ----

def test_wardrobe_added_item_warning():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1"))
    sup.register_snapshot(
        _snap("sh2", wardrobe=("plate_armor", "cape")),
    )
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    fields = [i.field for i in issues]
    assert "wardrobe" in fields
    sevs = [
        i.severity for i in issues if i.field == "wardrobe"
    ]
    assert Severity.WARNING in sevs


def test_wardrobe_removed_item_warning():
    sup = ContinuitySupervisor()
    sup.register_snapshot(
        _snap("sh1", wardrobe=("plate_armor", "cape")),
    )
    sup.register_snapshot(_snap("sh2"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    assert any(i.field == "wardrobe" for i in issues)


def test_wardrobe_unchanged_no_issue():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1"))
    sup.register_snapshot(_snap("sh2"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    assert all(i.field != "wardrobe" for i in issues)


def test_wardrobe_reorder_flagged():
    sup = ContinuitySupervisor()
    sup.register_snapshot(
        _snap("sh1", wardrobe=("a", "b", "c")),
    )
    sup.register_snapshot(
        _snap("sh2", wardrobe=("c", "b", "a")),
    )
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    assert any(i.field == "wardrobe" for i in issues)


# ---- Props (errors) ----

def test_prop_appearing_is_error():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1"))
    sup.register_snapshot(_snap("sh2", props=("excalibur",)))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sevs = [
        i.severity for i in issues if i.field == "props_in_hand"
    ]
    assert Severity.ERROR in sevs


def test_prop_vanishing_is_error():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", props=("excalibur",)))
    sup.register_snapshot(_snap("sh2"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sevs = [
        i.severity for i in issues if i.field == "props_in_hand"
    ]
    assert Severity.ERROR in sevs


# ---- Blood ----

def test_blood_appearing_warning():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1"))
    sup.register_snapshot(_snap("sh2", blood=("left_cheek",)))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    assert any(i.field == "blood_on_face" for i in issues)


def test_blood_disappearing_warning():
    sup = ContinuitySupervisor()
    sup.register_snapshot(
        _snap("sh1", blood=("forehead", "left_cheek")),
    )
    sup.register_snapshot(_snap("sh2", blood=("forehead",)))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    blood_issues = [i for i in issues if i.field == "blood_on_face"]
    assert blood_issues
    assert "left_cheek" in blood_issues[0].detail


# ---- Hair ----

def test_clean_to_bloodied_warning():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", hair="clean"))
    sup.register_snapshot(_snap("sh2", hair="bloodied"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sevs = [i.severity for i in issues if i.field == "hair_state"]
    assert Severity.WARNING in sevs


def test_messy_to_clean_only_note():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", hair="messy"))
    sup.register_snapshot(_snap("sh2", hair="clean"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sevs = [i.severity for i in issues if i.field == "hair_state"]
    assert sevs == [Severity.NOTE]


# ---- Wounds ----

def test_wound_appearing_warning():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1"))
    sup.register_snapshot(_snap("sh2", wounds=("left_arm_gash",)))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sevs = [i.severity for i in issues if i.field == "wounds"]
    assert Severity.WARNING in sevs


def test_wound_healing_is_error():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", wounds=("left_arm_gash",)))
    sup.register_snapshot(_snap("sh2"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sevs = [i.severity for i in issues if i.field == "wounds"]
    assert Severity.ERROR in sevs


# ---- Accessories ----

def test_accessory_change_only_note():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", accessories=("ring",)))
    sup.register_snapshot(
        _snap("sh2", accessories=("ring", "necklace")),
    )
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sevs = [i.severity for i in issues if i.field == "accessories"]
    assert sevs == [Severity.NOTE]


# ---- Weather / time-of-day ----

def test_weather_change_warning():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", weather="clear"))
    sup.register_snapshot(_snap("sh2", weather="storm"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    assert any(i.field == "weather" for i in issues)


def test_time_of_day_change_warning():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", tod="day"))
    sup.register_snapshot(_snap("sh2", tod="night"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    assert any(i.field == "time_of_day" for i in issues)


def test_identical_snapshots_no_issues():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1"))
    sup.register_snapshot(_snap("sh2"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    assert issues == ()


# ---- Reset hook ----

def test_reset_for_drops_snapshots():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1"))
    sup.register_snapshot(_snap("sh2"))
    n = sup.reset_for("sc1", "curilla")
    assert n == 2
    assert sup.all_snapshots() == ()


def test_reset_for_isolated_to_character():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", character_id="curilla"))
    sup.register_snapshot(_snap("sh2", character_id="trion"))
    n = sup.reset_for("sc1", "curilla")
    assert n == 1
    assert len(sup.all_snapshots()) == 1


def test_reset_for_isolated_to_scene():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", scene_id="sc1"))
    sup.register_snapshot(_snap("sh2", scene_id="sc2"))
    n = sup.reset_for("sc1", "curilla")
    assert n == 1


# ---- Logs / reports / severity ----

def test_log_and_report_round_trip():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1"))
    sup.register_snapshot(_snap("sh2", weather="storm"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sup.log_for("seq1", issues)
    rep = sup.report_for("seq1")
    assert len(rep.issues) >= 1


def test_worst_severity_picks_error_over_warning():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", props=("sword",)))
    sup.register_snapshot(_snap("sh2", weather="storm"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sup.log_for("seq1", issues)
    assert sup.worst_severity_in("seq1") == Severity.ERROR


def test_worst_severity_none_for_empty():
    sup = ContinuitySupervisor()
    assert sup.worst_severity_in("nonexistent") is None


def test_export_pdf_stub_counts_severities():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", props=("sword",)))
    sup.register_snapshot(_snap("sh2", weather="storm"))
    issues = sup.check_continuity("sh1", "sh2", "curilla")
    sup.log_for("seq1", issues)
    stub = sup.export_pdf_stub("seq1")
    assert stub["format"] == "pdf"
    assert stub["by_severity"]["error"] >= 1


def test_snapshots_for_character_filters():
    sup = ContinuitySupervisor()
    sup.register_snapshot(_snap("sh1", character_id="curilla"))
    sup.register_snapshot(_snap("sh2", character_id="trion"))
    out = sup.snapshots_for_character("curilla")
    assert len(out) == 1
