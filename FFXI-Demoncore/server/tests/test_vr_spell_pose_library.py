"""Tests for vr_spell_pose_library."""
from __future__ import annotations

from server.vr_spell_pose_library import (
    PoseElement, PoseSource, SpellPose, VrSpellPoseLibrary,
)


def _seal(code: str) -> PoseElement:
    return PoseElement(source=PoseSource.SEAL, code=code)


def _gesture(code: str) -> PoseElement:
    return PoseElement(source=PoseSource.GESTURE, code=code)


def _katon_ichi() -> SpellPose:
    return SpellPose(
        pose_id="katon_ichi",
        display_name="Katon: Ichi",
        sequence=(_seal("tiger"), _seal("boar"), _seal("dog")),
        spell_intent="ninjutsu.katon_ichi",
    )


def _suiton_ichi() -> SpellPose:
    return SpellPose(
        pose_id="suiton_ichi",
        display_name="Suiton: Ichi",
        sequence=(_seal("rat"), _seal("snake"), _seal("monkey")),
        spell_intent="ninjutsu.suiton_ichi",
    )


def _doton_ichi() -> SpellPose:
    return SpellPose(
        pose_id="doton_ichi",
        display_name="Doton: Ichi",
        sequence=(_seal("ox"), _seal("ram")),
        spell_intent="ninjutsu.doton_ichi",
    )


def _doton_ni() -> SpellPose:
    return SpellPose(
        pose_id="doton_ni",
        display_name="Doton: Ni",
        sequence=(_seal("ox"), _seal("ram"), _seal("dragon")),
        spell_intent="ninjutsu.doton_ni",
    )


def _blm_throw() -> SpellPose:
    return SpellPose(
        pose_id="blm_thrown_fire",
        display_name="Hurled Flare",
        sequence=(_gesture("point"), _gesture("throw")),
        spell_intent="blm.thrown_fire",
    )


def _geo_rune() -> SpellPose:
    return SpellPose(
        pose_id="geo_indi_frailty",
        display_name="Indi-Frailty",
        sequence=(_gesture("draw_rune"),),
        spell_intent="geo.indi_frailty",
    )


def test_register_happy():
    lib = VrSpellPoseLibrary()
    assert lib.register_pose(_katon_ichi()) is True


def test_register_blank_id_blocked():
    lib = VrSpellPoseLibrary()
    bad = SpellPose(
        pose_id="", display_name="x",
        sequence=(_seal("tiger"),),
        spell_intent="bad",
    )
    assert lib.register_pose(bad) is False


def test_register_empty_sequence_blocked():
    lib = VrSpellPoseLibrary()
    bad = SpellPose(
        pose_id="empty",
        display_name="empty",
        sequence=(),
        spell_intent="bad",
    )
    assert lib.register_pose(bad) is False


def test_register_dup_id_blocked():
    lib = VrSpellPoseLibrary()
    lib.register_pose(_katon_ichi())
    dup_id = SpellPose(
        pose_id="katon_ichi",
        display_name="not really katon",
        sequence=(_seal("dragon"),),
        spell_intent="x",
    )
    assert lib.register_pose(dup_id) is False


def test_register_dup_sequence_blocked():
    """Two distinct pose IDs cannot share a sequence."""
    lib = VrSpellPoseLibrary()
    lib.register_pose(_katon_ichi())
    same_seq = SpellPose(
        pose_id="another",
        display_name="another",
        sequence=(_seal("tiger"), _seal("boar"), _seal("dog")),
        spell_intent="x",
    )
    assert lib.register_pose(same_seq) is False


def test_lookup_exact_match():
    lib = VrSpellPoseLibrary()
    lib.register_pose(_katon_ichi())
    found = lib.lookup_by_sequence(
        sequence=[_seal("tiger"), _seal("boar"), _seal("dog")],
    )
    assert found is not None
    assert found.pose_id == "katon_ichi"


def test_lookup_partial_returns_none():
    """Partial sequence is not an exact match."""
    lib = VrSpellPoseLibrary()
    lib.register_pose(_katon_ichi())
    found = lib.lookup_by_sequence(
        sequence=[_seal("tiger"), _seal("boar")],
    )
    assert found is None


def test_lookup_unknown_returns_none():
    lib = VrSpellPoseLibrary()
    found = lib.lookup_by_sequence(sequence=[_seal("tiger")])
    assert found is None


def test_candidates_with_prefix_filters():
    lib = VrSpellPoseLibrary()
    lib.register_pose(_doton_ichi())  # ox, ram
    lib.register_pose(_doton_ni())    # ox, ram, dragon
    lib.register_pose(_katon_ichi())  # tiger, boar, dog
    cands = lib.candidates_with_prefix(
        prefix=[_seal("ox")],
    )
    ids = {p.pose_id for p in cands}
    assert "doton_ichi" in ids
    assert "doton_ni" in ids
    assert "katon_ichi" not in ids


def test_candidates_with_prefix_two_match():
    """ox+ram matches both Doton: Ichi (exact) and Ni (prefix)."""
    lib = VrSpellPoseLibrary()
    lib.register_pose(_doton_ichi())
    lib.register_pose(_doton_ni())
    cands = lib.candidates_with_prefix(
        prefix=[_seal("ox"), _seal("ram")],
    )
    ids = [p.pose_id for p in cands]
    # Sorted by length: doton_ichi (2) < doton_ni (3)
    assert ids == ["doton_ichi", "doton_ni"]


def test_candidates_empty_prefix_returns_all():
    lib = VrSpellPoseLibrary()
    lib.register_pose(_katon_ichi())
    lib.register_pose(_suiton_ichi())
    cands = lib.candidates_with_prefix(prefix=[])
    assert len(cands) == 2


def test_candidates_no_match_returns_empty():
    lib = VrSpellPoseLibrary()
    lib.register_pose(_katon_ichi())
    cands = lib.candidates_with_prefix(
        prefix=[_seal("rabbit")],
    )
    assert cands == []


def test_gesture_pose():
    """Sources can be GESTURE not just SEAL."""
    lib = VrSpellPoseLibrary()
    assert lib.register_pose(_blm_throw()) is True
    found = lib.lookup_by_sequence(
        sequence=[_gesture("point"), _gesture("throw")],
    )
    assert found is not None
    assert found.spell_intent == "blm.thrown_fire"


def test_mixed_source_lookup():
    """Same code in different sources doesn't collide."""
    lib = VrSpellPoseLibrary()
    seal_only = SpellPose(
        pose_id="seal_only",
        display_name="seal-only",
        sequence=(_seal("draw_rune"),),
        spell_intent="x",
    )
    gesture_only = SpellPose(
        pose_id="gesture_only",
        display_name="gesture-only",
        sequence=(_gesture("draw_rune"),),
        spell_intent="y",
    )
    assert lib.register_pose(seal_only) is True
    assert lib.register_pose(gesture_only) is True
    found_g = lib.lookup_by_sequence(
        sequence=[_gesture("draw_rune")],
    )
    assert found_g is not None
    assert found_g.pose_id == "gesture_only"


def test_all_poses_returns_all():
    lib = VrSpellPoseLibrary()
    lib.register_pose(_katon_ichi())
    lib.register_pose(_suiton_ichi())
    lib.register_pose(_geo_rune())
    poses = lib.all_poses()
    assert len(poses) == 3


def test_unregister_works():
    lib = VrSpellPoseLibrary()
    lib.register_pose(_katon_ichi())
    assert lib.unregister(pose_id="katon_ichi") is True
    # Lookup after unregister returns None
    assert lib.lookup_by_sequence(
        sequence=[_seal("tiger"), _seal("boar"), _seal("dog")],
    ) is None


def test_unregister_unknown():
    lib = VrSpellPoseLibrary()
    assert lib.unregister(pose_id="ghost") is False


def test_re_register_after_unregister():
    """After unregistering, the same id+sequence works."""
    lib = VrSpellPoseLibrary()
    lib.register_pose(_katon_ichi())
    lib.unregister(pose_id="katon_ichi")
    assert lib.register_pose(_katon_ichi()) is True
