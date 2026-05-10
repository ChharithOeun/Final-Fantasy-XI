"""Tests for player_body_rig."""
from __future__ import annotations

import pytest

from server.player_body_rig import (
    PlayerBodyRigSystem,
    Race,
    VisibilityKind,
    WeaponDrawState,
)


# ---- enum coverage ----

def test_visibility_kind_count_six():
    assert len(list(VisibilityKind)) == 6


def test_weapon_draw_state_count_six():
    assert len(list(WeaponDrawState)) == 6


def test_race_count_five():
    assert len(list(Race)) == 5


def test_visibility_kind_includes_first_person_hands():
    assert (
        VisibilityKind.FIRST_PERSON_HANDS_ONLY
        in list(VisibilityKind)
    )


def test_weapon_dual_drawn_present():
    assert WeaponDrawState.DUAL_DRAWN in list(WeaponDrawState)


# ---- register ----

def test_register_body_default_visibility():
    s = PlayerBodyRigSystem()
    state = s.register_body("p1", Race.HUME, "male")
    assert state.player_id == "p1"
    assert state.race == Race.HUME
    assert state.visibility_kind == VisibilityKind.THIRD_PERSON_FULL


def test_register_empty_id_raises():
    s = PlayerBodyRigSystem()
    with pytest.raises(ValueError):
        s.register_body("", Race.HUME, "male")


def test_register_duplicate_raises():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    with pytest.raises(ValueError):
        s.register_body("p1", Race.ELVAAN, "female")


def test_register_invalid_gender_raises():
    s = PlayerBodyRigSystem()
    with pytest.raises(ValueError):
        s.register_body("p1", Race.HUME, "other")


def test_state_of_unknown_raises():
    s = PlayerBodyRigSystem()
    with pytest.raises(KeyError):
        s.state_of("nope")


def test_body_count_starts_zero():
    s = PlayerBodyRigSystem()
    assert s.body_count() == 0


def test_body_count_after_register():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.register_body("p2", Race.GALKA, "male")
    assert s.body_count() == 2


# ---- visibility ----

def test_set_visibility_changes_kind():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.MITHRA, "female")
    state = s.set_visibility(
        "p1", VisibilityKind.FIRST_PERSON_HANDS_ONLY,
    )
    assert (
        state.visibility_kind
        == VisibilityKind.FIRST_PERSON_HANDS_ONLY
    )


def test_helmet_toggle_flips_visibility():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    state1 = s.helmet_toggle("p1")
    assert state1.helmet_visible is False
    state2 = s.helmet_toggle("p1")
    assert state2.helmet_visible is True


def test_set_gloves_visible():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    state = s.set_gloves_visible("p1", False)
    assert state.gloves_visible is False


def test_set_capes_visible():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.ELVAAN, "male")
    state = s.set_capes_visible("p1", False)
    assert state.shoulder_capes_visible is False


def test_set_decals_blood():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    state = s.set_decals("p1", blood=True)
    assert state.has_blood_decal is True


def test_set_decals_wet_intensity():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    state = s.set_decals("p1", wet_intensity=0.7)
    assert state.wet_decal_intensity == pytest.approx(0.7)


def test_set_decals_invalid_wet_raises():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    with pytest.raises(ValueError):
        s.set_decals("p1", wet_intensity=1.5)


# ---- weapon equip ----

def test_equip_main_hand_persists():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    state = s.equip_main_hand("p1", "sword_iron")
    assert state.main_hand_weapon_id == "sword_iron"


def test_equip_off_hand_persists():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    state = s.equip_off_hand("p1", "shield_round")
    assert state.off_hand_weapon_or_shield_id == "shield_round"


def test_equip_sub_weapon_persists():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    state = s.equip_sub_weapon("p1", "bow_long")
    assert state.sub_weapon_id == "bow_long"


# ---- draw ----

def test_draw_main_hand_returns_anim_id():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.GALKA, "male")
    s.equip_main_hand("p1", "axe_great")
    anim = s.draw_weapon("p1", "main")
    assert anim == "anim_draw_main_galka"
    assert s.state_of("p1").main_hand_state == WeaponDrawState.DRAWING


def test_draw_without_weapon_raises():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    with pytest.raises(ValueError):
        s.draw_weapon("p1", "main")


def test_draw_already_drawn_returns_empty():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.equip_main_hand("p1", "sword_iron")
    s.draw_weapon("p1", "main")
    s.complete_draw("p1", "main")
    assert s.draw_weapon("p1", "main") == ""


def test_draw_invalid_slot_raises():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    with pytest.raises(ValueError):
        s.draw_weapon("p1", "tail")


def test_complete_draw_promotes_to_drawn():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.equip_main_hand("p1", "sword_iron")
    s.draw_weapon("p1", "main")
    state = s.complete_draw("p1", "main")
    assert state.main_hand_state == WeaponDrawState.DRAWN


def test_dual_draw_promotes_to_dual_drawn():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.MITHRA, "female")
    s.equip_main_hand("p1", "katana_main")
    s.equip_off_hand("p1", "katana_off")
    s.draw_weapon("p1", "main")
    s.complete_draw("p1", "main")
    s.draw_weapon("p1", "off")
    state = s.complete_draw("p1", "off")
    assert state.main_hand_state == WeaponDrawState.DUAL_DRAWN
    assert state.off_hand_state == WeaponDrawState.DUAL_DRAWN


def test_off_hand_shield_does_not_promote_dual():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.ELVAAN, "male")
    s.equip_main_hand("p1", "sword_iron")
    s.equip_off_hand("p1", "shield_round")
    s.draw_weapon("p1", "main")
    s.complete_draw("p1", "main")
    s.draw_weapon("p1", "off")
    state = s.complete_draw("p1", "off")
    assert state.main_hand_state == WeaponDrawState.DRAWN
    assert state.off_hand_state == WeaponDrawState.DRAWN


# ---- sheathe ----

def test_sheathe_returns_anim_id():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.equip_main_hand("p1", "sword_iron")
    s.draw_weapon("p1", "main")
    s.complete_draw("p1", "main")
    anim = s.sheathe_weapon("p1", "main")
    assert anim == "anim_sheathe_main_hume"
    assert (
        s.state_of("p1").main_hand_state
        == WeaponDrawState.SHEATHING
    )


def test_sheathe_already_sheathed_returns_empty():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.equip_main_hand("p1", "sword_iron")
    assert s.sheathe_weapon("p1", "main") == ""


def test_complete_sheathe_returns_to_sheathed():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.equip_main_hand("p1", "sword_iron")
    s.draw_weapon("p1", "main")
    s.complete_draw("p1", "main")
    s.sheathe_weapon("p1", "main")
    state = s.complete_sheathe("p1", "main")
    assert state.main_hand_state == WeaponDrawState.SHEATHED


def test_sheathe_main_drops_dual_flag():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.equip_main_hand("p1", "katana_main")
    s.equip_off_hand("p1", "katana_off")
    s.draw_weapon("p1", "main")
    s.complete_draw("p1", "main")
    s.draw_weapon("p1", "off")
    s.complete_draw("p1", "off")
    s.sheathe_weapon("p1", "main")
    state = s.state_of("p1")
    assert state.main_hand_state == WeaponDrawState.SHEATHING
    assert state.off_hand_state == WeaponDrawState.DRAWN


# ---- casting ----

def test_begin_casting_sets_main_state():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.TARUTARU, "male")
    s.equip_main_hand("p1", "staff_oak")
    state = s.begin_casting("p1")
    assert state.main_hand_state == WeaponDrawState.CASTING


# ---- is_weapon_drawn ----

def test_is_weapon_drawn_main_drawn():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.equip_main_hand("p1", "sword_iron")
    s.draw_weapon("p1", "main")
    s.complete_draw("p1", "main")
    assert s.is_weapon_drawn("p1", "main")


def test_is_weapon_drawn_main_sheathed():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.equip_main_hand("p1", "sword_iron")
    assert not s.is_weapon_drawn("p1", "main")


def test_is_weapon_drawn_dual():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    s.equip_main_hand("p1", "katana_main")
    s.equip_off_hand("p1", "katana_off")
    s.draw_weapon("p1", "main")
    s.complete_draw("p1", "main")
    s.draw_weapon("p1", "off")
    s.complete_draw("p1", "off")
    assert s.is_weapon_drawn("p1", "main")
    assert s.is_weapon_drawn("p1", "off")


def test_is_weapon_drawn_invalid_slot_raises():
    s = PlayerBodyRigSystem()
    s.register_body("p1", Race.HUME, "male")
    with pytest.raises(ValueError):
        s.is_weapon_drawn("p1", "tail")


# ---- per-race ----

def test_galka_shoulder_scale_one_three():
    s = PlayerBodyRigSystem()
    assert s.shoulder_scale(Race.GALKA) == pytest.approx(1.3)


def test_taru_shoulder_scale_lower():
    s = PlayerBodyRigSystem()
    assert s.shoulder_scale(Race.TARUTARU) < 1.0


def test_taru_hand_height_negative():
    s = PlayerBodyRigSystem()
    assert s.hand_height_offset(Race.TARUTARU) < 0


def test_mithra_visible_tail():
    s = PlayerBodyRigSystem()
    assert s.has_visible_tail(Race.MITHRA)


def test_hume_no_tail():
    s = PlayerBodyRigSystem()
    assert not s.has_visible_tail(Race.HUME)


def test_galka_hume_shoulder_diff():
    s = PlayerBodyRigSystem()
    assert s.shoulder_scale(Race.GALKA) > s.shoulder_scale(
        Race.HUME,
    )


def test_draw_duration_constant():
    s = PlayerBodyRigSystem()
    assert s.draw_duration_s() == pytest.approx(0.35)


def test_sheathe_duration_constant():
    s = PlayerBodyRigSystem()
    assert s.sheathe_duration_s() == pytest.approx(0.5)
