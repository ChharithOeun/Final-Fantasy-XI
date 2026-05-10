"""Tests for animation_retargeting."""
from __future__ import annotations

import pytest

from server.animation_retargeting import (
    BoneMapping,
    PropKind,
    RetargetMap,
    RetargetingSystem,
    SkeletonKind,
    SourceSkeleton,
    TargetSkeleton,
    standard_body_mappings,
)


# ---- enum coverage ----

def test_six_source_skeletons():
    assert len(list(SourceSkeleton)) == 6


def test_eight_target_skeletons():
    assert len(list(TargetSkeleton)) == 8


def test_face_and_body_kinds():
    assert {k for k in SkeletonKind} == {
        SkeletonKind.BODY, SkeletonKind.FACE,
    }


def test_live_link_face_is_face_kind():
    s = RetargetingSystem()
    assert (
        s.kind_of(SourceSkeleton.LIVE_LINK_FACE_52)
        == SkeletonKind.FACE
    )


def test_rokoko_is_body_kind():
    s = RetargetingSystem()
    assert (
        s.kind_of(SourceSkeleton.ROKOKO_BODY_82)
        == SkeletonKind.BODY
    )


def test_metahuman_is_body_kind():
    s = RetargetingSystem()
    assert (
        s.kind_of(SourceSkeleton.METAHUMAN_DEFAULT)
        == SkeletonKind.BODY
    )


# ---- registration ----

def test_register_skeleton_marks_known():
    s = RetargetingSystem()
    s.register_skeleton(
        source=SourceSkeleton.MIXAMO_STANDARD,
        target=TargetSkeleton.FFXI_HUME_M,
    )
    assert s.known_source(SourceSkeleton.MIXAMO_STANDARD)
    assert s.known_target(TargetSkeleton.FFXI_HUME_M)


def test_register_only_source():
    s = RetargetingSystem()
    s.register_skeleton(
        source=SourceSkeleton.OPTITRACK_PRIME,
    )
    assert s.known_source(SourceSkeleton.OPTITRACK_PRIME)


def test_register_only_target():
    s = RetargetingSystem()
    s.register_skeleton(target=TargetSkeleton.FFXI_GALKA)
    assert s.known_target(TargetSkeleton.FFXI_GALKA)


# ---- retarget map ----

def test_register_retarget_map_stores():
    s = RetargetingSystem()
    s.register_retarget_map(
        SourceSkeleton.MIXAMO_STANDARD,
        TargetSkeleton.FFXI_HUME_M,
        standard_body_mappings(TargetSkeleton.FFXI_HUME_M),
    )
    assert s.has_map(
        SourceSkeleton.MIXAMO_STANDARD,
        TargetSkeleton.FFXI_HUME_M,
    )


def test_register_face_to_body_raises():
    s = RetargetingSystem()
    with pytest.raises(ValueError):
        s.register_retarget_map(
            SourceSkeleton.LIVE_LINK_FACE_52,
            TargetSkeleton.FFXI_HUME_M,
            (),
        )


def test_get_map_unknown_raises():
    s = RetargetingSystem()
    with pytest.raises(KeyError):
        s.get_map(
            SourceSkeleton.ROKOKO_BODY_82,
            TargetSkeleton.FFXI_GALKA,
        )


def test_retarget_map_lists_target_bones():
    s = RetargetingSystem()
    rm = s.register_retarget_map(
        SourceSkeleton.MIXAMO_STANDARD,
        TargetSkeleton.FFXI_GALKA,
        standard_body_mappings(TargetSkeleton.FFXI_GALKA),
    )
    bones = rm.target_bones()
    assert "spine" in bones
    assert "head" in bones
    assert "foot_l" in bones


# ---- standard_body_mappings ----

def test_standard_mappings_cover_mandatory():
    rm = standard_body_mappings(TargetSkeleton.FFXI_HUME_M)
    target_bones = {m.target_bone for m in rm}
    for bone in (
        "root", "spine", "neck", "head",
        "shoulder_l", "shoulder_r",
        "arm_l", "arm_r",
        "hand_l", "hand_r",
        "hip", "leg_l", "leg_r", "foot_l", "foot_r",
    ):
        assert bone in target_bones


def test_standard_mappings_galka_shoulder_30pct_wider():
    rm = standard_body_mappings(TargetSkeleton.FFXI_GALKA)
    by_bone = {m.target_bone: m.scale_factor for m in rm}
    assert by_bone["shoulder_l"] == 1.30
    assert by_bone["shoulder_r"] == 1.30


def test_standard_mappings_taru_head_oversized():
    rm = standard_body_mappings(
        TargetSkeleton.FFXI_TARUTARU_M,
    )
    by_bone = {m.target_bone: m.scale_factor for m in rm}
    assert by_bone["head"] == 1.6
    assert by_bone["arm_l"] == 0.7
    assert by_bone["arm_r"] == 0.7


def test_standard_mappings_mithra_includes_tail():
    rm = standard_body_mappings(TargetSkeleton.FFXI_MITHRA)
    target_bones = {m.target_bone for m in rm}
    assert "tail_root" in target_bones
    assert "tail_mid" in target_bones
    assert "tail_tip" in target_bones


def test_standard_mappings_elvaan_15pct_taller_spine():
    rm = standard_body_mappings(TargetSkeleton.FFXI_ELVAAN_M)
    by_bone = {m.target_bone: m.scale_factor for m in rm}
    assert by_bone["spine"] == 1.15


def test_standard_mappings_mithra_hip_sway():
    rm = standard_body_mappings(TargetSkeleton.FFXI_MITHRA)
    by_bone = {m.target_bone: m.scale_factor for m in rm}
    assert by_bone["hip"] == 1.20


# ---- validate_retarget ----

def test_validate_retarget_good():
    s = RetargetingSystem()
    s.register_retarget_map(
        SourceSkeleton.METAHUMAN_DEFAULT,
        TargetSkeleton.FFXI_HUME_M,
        standard_body_mappings(TargetSkeleton.FFXI_HUME_M),
    )
    assert s.validate_retarget(
        SourceSkeleton.METAHUMAN_DEFAULT,
        TargetSkeleton.FFXI_HUME_M,
    )


def test_validate_retarget_face_source_raises():
    s = RetargetingSystem()
    with pytest.raises(ValueError):
        s.validate_retarget(
            SourceSkeleton.LIVE_LINK_FACE_52,
            TargetSkeleton.FFXI_HUME_M,
        )


def test_validate_retarget_no_map_raises():
    s = RetargetingSystem()
    with pytest.raises(ValueError):
        s.validate_retarget(
            SourceSkeleton.MIXAMO_STANDARD,
            TargetSkeleton.FFXI_GALKA,
        )


def test_validate_retarget_missing_bone_raises():
    s = RetargetingSystem()
    # Provide a map that's missing 'foot_l'.
    bad = tuple(
        m for m in standard_body_mappings(
            TargetSkeleton.FFXI_HUME_M,
        )
        if m.target_bone != "foot_l"
    )
    s.register_retarget_map(
        SourceSkeleton.MIXAMO_STANDARD,
        TargetSkeleton.FFXI_HUME_M,
        bad,
    )
    with pytest.raises(ValueError):
        s.validate_retarget(
            SourceSkeleton.MIXAMO_STANDARD,
            TargetSkeleton.FFXI_HUME_M,
        )


def test_validate_retarget_mithra_missing_tail_raises():
    s = RetargetingSystem()
    no_tail = tuple(
        m for m in standard_body_mappings(
            TargetSkeleton.FFXI_MITHRA,
        )
        if not m.target_bone.startswith("tail_")
    )
    s.register_retarget_map(
        SourceSkeleton.MIXAMO_STANDARD,
        TargetSkeleton.FFXI_MITHRA,
        no_tail,
    )
    with pytest.raises(ValueError):
        s.validate_retarget(
            SourceSkeleton.MIXAMO_STANDARD,
            TargetSkeleton.FFXI_MITHRA,
        )


# ---- retarget_clip ----

def test_retarget_clip_returns_uri():
    s = RetargetingSystem()
    s.register_retarget_map(
        SourceSkeleton.MIXAMO_STANDARD,
        TargetSkeleton.FFXI_HUME_M,
        standard_body_mappings(TargetSkeleton.FFXI_HUME_M),
    )
    out = s.retarget_clip(
        "anim://walk",
        SourceSkeleton.MIXAMO_STANDARD,
        TargetSkeleton.FFXI_HUME_M,
    )
    assert "retarget://" in out
    assert "mixamo_standard" in out
    assert "ffxi_hume_m" in out


def test_retarget_clip_no_map_raises():
    s = RetargetingSystem()
    with pytest.raises(ValueError):
        s.retarget_clip(
            "anim://walk",
            SourceSkeleton.ROKOKO_BODY_82,
            TargetSkeleton.FFXI_GALKA,
        )


def test_retarget_clip_face_source_raises():
    s = RetargetingSystem()
    with pytest.raises(ValueError):
        s.retarget_clip(
            "anim://x",
            SourceSkeleton.LIVE_LINK_FACE_52,
            TargetSkeleton.FFXI_GALKA,
        )


def test_retarget_clip_empty_uri_raises():
    s = RetargetingSystem()
    with pytest.raises(ValueError):
        s.retarget_clip(
            "",
            SourceSkeleton.MIXAMO_STANDARD,
            TargetSkeleton.FFXI_HUME_M,
        )


# ---- IK + foot lock ----

def test_foot_lock_default_on():
    s = RetargetingSystem()
    s.register_skeleton(target=TargetSkeleton.FFXI_GALKA)
    assert s.foot_lock_for(TargetSkeleton.FFXI_GALKA)


def test_foot_lock_can_be_disabled():
    s = RetargetingSystem()
    s.register_skeleton(target=TargetSkeleton.FFXI_HUME_M)
    s.set_foot_lock(TargetSkeleton.FFXI_HUME_M, False)
    assert not s.foot_lock_for(TargetSkeleton.FFXI_HUME_M)


def test_foot_lock_unregistered_target_default_on():
    s = RetargetingSystem()
    # Even unregistered targets default to foot-lock on.
    assert s.foot_lock_for(TargetSkeleton.FFXI_TARUTARU_F)


# ---- prop attachment ----

def test_prop_socket_hammer_right_hand():
    s = RetargetingSystem()
    socket = s.prop_attachment_socket(
        TargetSkeleton.FFXI_GALKA, PropKind.HAMMER,
    )
    assert socket == "HAND_R_PROP"


def test_prop_socket_scroll_left_hand():
    s = RetargetingSystem()
    socket = s.prop_attachment_socket(
        TargetSkeleton.FFXI_HUME_F, PropKind.SCROLL,
    )
    assert socket == "HAND_L_PROP"


def test_prop_socket_lantern_left_hand():
    s = RetargetingSystem()
    socket = s.prop_attachment_socket(
        TargetSkeleton.FFXI_ELVAAN_M, PropKind.LANTERN,
    )
    assert socket == "HAND_L_PROP"


def test_prop_socket_auto_registers_target():
    s = RetargetingSystem()
    s.prop_attachment_socket(
        TargetSkeleton.FFXI_MITHRA, PropKind.SWORD,
    )
    assert s.known_target(TargetSkeleton.FFXI_MITHRA)


# ---- mandatory bones helper ----

def test_mandatory_bones_for_hume_m():
    s = RetargetingSystem()
    bones = s.mandatory_bones_for(
        TargetSkeleton.FFXI_HUME_M,
    )
    assert "spine" in bones
    assert "tail_root" not in bones


def test_mandatory_bones_for_mithra_includes_tail():
    s = RetargetingSystem()
    bones = s.mandatory_bones_for(
        TargetSkeleton.FFXI_MITHRA,
    )
    assert "tail_root" in bones
    assert "tail_mid" in bones
    assert "tail_tip" in bones


# ---- diagnostics ----

def test_all_targets_sorted():
    s = RetargetingSystem()
    s.register_skeleton(target=TargetSkeleton.FFXI_GALKA)
    s.register_skeleton(target=TargetSkeleton.FFXI_HUME_M)
    out = s.all_targets()
    assert list(out) == sorted(out, key=lambda t: t.value)


def test_all_sources_sorted():
    s = RetargetingSystem()
    s.register_skeleton(
        source=SourceSkeleton.ROKOKO_BODY_82,
    )
    s.register_skeleton(
        source=SourceSkeleton.MIXAMO_STANDARD,
    )
    out = s.all_sources()
    assert list(out) == sorted(out, key=lambda s: s.value)


def test_race_scale_table_returns_copy():
    s = RetargetingSystem()
    a = s.race_scale_table(TargetSkeleton.FFXI_GALKA)
    a["shoulder_l"] = 99.0
    b = s.race_scale_table(TargetSkeleton.FFXI_GALKA)
    assert b["shoulder_l"] == 1.30


def test_race_scale_table_for_each_target():
    s = RetargetingSystem()
    for target in TargetSkeleton:
        out = s.race_scale_table(target)
        assert isinstance(out, dict)
        assert len(out) > 0
