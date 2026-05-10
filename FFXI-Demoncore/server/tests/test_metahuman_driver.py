"""Tests for metahuman_driver."""
from __future__ import annotations

import pytest

from server.metahuman_driver import (
    ARKIT_BLENDSHAPES, AVATARS, AvatarBinding,
    Emotion, MetaHumanDriver, Race,
    list_avatars, lookup,
)


def test_arkit_has_52_blendshapes():
    assert len(ARKIT_BLENDSHAPES) == 52


def test_arkit_has_jaw_open():
    assert "jawOpen" in ARKIT_BLENDSHAPES


def test_avatars_has_at_least_18_entries():
    assert len(AVATARS) >= 18


def test_canon_heroes_present():
    expected_heroes = {
        "curilla", "volker", "ayame", "maat",
        "trion", "nanaa_mihgo", "aldo", "cid",
    }
    assert expected_heroes.issubset(set(AVATARS))


def test_pc_archetype_set_present():
    archetypes = {
        f"pc_{r}_{s}"
        for r in ("hume", "elvaan", "tarutaru",
                  "mithra", "galka")
        for s in ("m", "f")
    }
    assert archetypes.issubset(set(AVATARS))


def test_curilla_is_elvaan_f():
    a = AVATARS["curilla"]
    assert a.race == Race.ELVAAN
    assert a.body_skeleton_variant == "Elvaan_F"


def test_lookup_top_level_happy():
    a = lookup("maat")
    assert a.ffxi_npc_id == "maat"


def test_lookup_top_level_unknown_raises():
    with pytest.raises(KeyError):
        lookup("__nope__")


def test_driver_lookup_happy():
    d = MetaHumanDriver()
    a = d.lookup("volker")
    assert isinstance(a, AvatarBinding)
    assert a.ffxi_npc_id == "volker"


def test_driver_lookup_unknown_raises():
    d = MetaHumanDriver()
    with pytest.raises(KeyError):
        d.lookup("ghost_npc")


def test_apply_emotion_neutral_all_zero():
    d = MetaHumanDriver()
    w = d.apply_emotion("curilla", Emotion.NEUTRAL)
    assert len(w) == 52
    assert all(v == 0.0 for v in w.values())


def test_apply_emotion_happy_smiles():
    d = MetaHumanDriver()
    w = d.apply_emotion("ayame", Emotion.HAPPY)
    assert w["mouthSmileLeft"] > 0.5
    assert w["mouthSmileRight"] > 0.5


def test_apply_emotion_angry_brow_down():
    d = MetaHumanDriver()
    w = d.apply_emotion("volker", Emotion.ANGRY)
    assert w["browDownLeft"] > 0.5
    assert w["browDownRight"] > 0.5


def test_apply_emotion_afraid_eyes_wide():
    d = MetaHumanDriver()
    w = d.apply_emotion("nanaa_mihgo", Emotion.AFRAID)
    assert w["eyeWideLeft"] > 0.5
    assert w["eyeWideRight"] > 0.5


def test_apply_emotion_intensity_scales():
    d = MetaHumanDriver()
    full = d.apply_emotion("curilla", Emotion.HAPPY, 1.0)
    half = d.apply_emotion("curilla", Emotion.HAPPY, 0.5)
    assert (
        half["mouthSmileLeft"]
        == pytest.approx(full["mouthSmileLeft"] * 0.5)
    )


def test_apply_emotion_intensity_zero_zeros_out():
    d = MetaHumanDriver()
    w = d.apply_emotion("curilla", Emotion.HAPPY, 0.0)
    assert all(v == 0.0 for v in w.values())


def test_apply_emotion_unknown_npc_raises():
    d = MetaHumanDriver()
    with pytest.raises(KeyError):
        d.apply_emotion("ghost", Emotion.HAPPY)


def test_apply_emotion_intensity_out_of_range_raises():
    d = MetaHumanDriver()
    with pytest.raises(ValueError):
        d.apply_emotion("curilla", Emotion.HAPPY, 1.5)


def test_register_avatar_invalid_skeleton_raises():
    d = MetaHumanDriver()
    bad = AvatarBinding(
        ffxi_npc_id="weirdo",
        metahuman_template="X",
        face_blueprint_id="X",
        body_skeleton_variant="Galka_M",  # wrong race
        skin_tone_id="X",
        costume_rig_id="X",
        race=Race.MITHRA,
    )
    with pytest.raises(ValueError):
        d.register_avatar(bad)


def test_register_avatar_happy():
    d = MetaHumanDriver()
    ok = AvatarBinding(
        ffxi_npc_id="iroha",
        metahuman_template="Adult Female Athletic",
        face_blueprint_id="MH_F_Hume_Iroha",
        body_skeleton_variant="Hume_F",
        skin_tone_id="hume_warm_01",
        costume_rig_id="iroha_kimono",
        race=Race.HUME,
    )
    d.register_avatar(ok)
    assert d.lookup("iroha").ffxi_npc_id == "iroha"


def test_bind_costume_happy():
    d = MetaHumanDriver()
    new = d.bind_costume("maat", "maat_palace_robes")
    assert new.costume_rig_id == "maat_palace_robes"


def test_bind_costume_empty_raises():
    d = MetaHumanDriver()
    with pytest.raises(ValueError):
        d.bind_costume("maat", "")


def test_retarget_same_race():
    d = MetaHumanDriver()
    plan = d.retarget_animation("Hume_M", "Hume_F")
    assert plan["ik_rig"] == "MH_SameRace_IK"
    assert plan["needs_height_normalize"] is False


def test_retarget_cross_race():
    d = MetaHumanDriver()
    plan = d.retarget_animation("Hume_M", "Galka_M")
    assert plan["ik_rig"] == "MH_CrossRace_IK"
    assert plan["needs_height_normalize"] is True


def test_retarget_unknown_skeleton_raises():
    d = MetaHumanDriver()
    with pytest.raises(ValueError):
        d.retarget_animation("Hume_M", "Centaur_M")


def test_list_avatars_sorted():
    names = list_avatars()
    assert names == tuple(sorted(names))


def test_mithra_is_female_only():
    # Race rule: Mithra must use Mithra_F skeleton.
    a = AVATARS["nanaa_mihgo"]
    assert a.race == Race.MITHRA
    assert a.body_skeleton_variant == "Mithra_F"


def test_galka_is_male_only():
    # Race rule: Galka must use Galka_M skeleton.
    a = AVATARS["pc_galka_m"]
    assert a.race == Race.GALKA
    assert a.body_skeleton_variant == "Galka_M"
