"""Tests for the combat resolver + skillchain detector.

Run:  python -m pytest server/tests/test_combat.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from combat import (
    DamageContext,
    DamageResolver,
    Element,
    SkillchainDetector,
    SkillchainElement,
    SkillchainEvent,
    SkillchainLevel,
    SpellType,
    WeaponSkillEvent,
    WSProperty,
)


# ----------------------------------------------------------------------
# SkillchainDetector — Level 1 chains
# ----------------------------------------------------------------------

def test_compression_then_induration_yields_induration():
    """Crescent Moon (compression) + Hexa Strike (induration variant)."""
    det = SkillchainDetector()

    # First WS: compression opener
    e1 = WeaponSkillEvent(
        actor_id="war_alice", target_id="quadav_001",
        ws_id="crescent_moon", property=WSProperty.COMPRESSION,
        damage=400, landed_at=10.0,
    )
    result = det.observe_weapon_skill(e1)
    assert result is None   # no chain yet

    # Second WS: induration (within 8s) → Induration chain
    e2 = WeaponSkillEvent(
        actor_id="whm_bob", target_id="quadav_001",
        ws_id="hexa_strike", property=WSProperty.INDURATION,
        damage=300, landed_at=12.0,
    )
    result = det.observe_weapon_skill(e2)
    assert result is not None
    assert result.element == SkillchainElement.INDURATION
    assert result.level == SkillchainLevel.LEVEL_1
    assert result.contributors == ["war_alice", "whm_bob"]
    assert result.base_damage_sum == 700


def test_compression_then_detonation_yields_detonation():
    det = SkillchainDetector()
    det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="a", target_id="t", ws_id="ws1",
        property=WSProperty.COMPRESSION, damage=100, landed_at=0,
    ))
    result = det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="b", target_id="t", ws_id="ws2",
        property=WSProperty.DETONATION, damage=100, landed_at=2,
    ))
    assert result.element == SkillchainElement.DETONATION


def test_chain_window_expires_after_8_seconds():
    det = SkillchainDetector()
    det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="a", target_id="t", ws_id="ws1",
        property=WSProperty.COMPRESSION, damage=100, landed_at=0,
    ))
    # 9 seconds later — past the close window
    result = det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="b", target_id="t", ws_id="ws2",
        property=WSProperty.INDURATION, damage=100, landed_at=9.5,
    ))
    assert result is None


def test_incompatible_property_combo_no_chain():
    """Liquefaction + Liquefaction has no canonical mapping (same element)."""
    det = SkillchainDetector()
    det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="a", target_id="t", ws_id="ws1",
        property=WSProperty.LIQUEFACTION, damage=100, landed_at=0,
    ))
    result = det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="b", target_id="t", ws_id="ws2",
        property=WSProperty.LIQUEFACTION, damage=100, landed_at=2,
    ))
    assert result is None


# ----------------------------------------------------------------------
# Level 2 — extension within 3s of detonation
# ----------------------------------------------------------------------

def test_l1_compression_then_l2_distortion():
    """Compression L1 -> reverberation (water) extension extends to Distortion."""
    det = SkillchainDetector()
    # L1 chain: Reverberation x Induration → Distortion (no — L1 table)
    # Let's use: Reverb + Compression = Compression L1, then induration => Induration extension is wrong.
    # Use the canonical: Compression -> Induration (L1 Induration), then Reverberation
    det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="a", target_id="t", ws_id="ws1",
        property=WSProperty.COMPRESSION, damage=100, landed_at=0,
    ))
    l1 = det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="b", target_id="t", ws_id="ws2",
        property=WSProperty.INDURATION, damage=100, landed_at=2,
    ))
    assert l1.level == SkillchainLevel.LEVEL_1
    assert l1.element == SkillchainElement.INDURATION

    # Within 3s of detonation, add Reverberation → Distortion (L2)
    l2 = det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="c", target_id="t", ws_id="ws3",
        property=WSProperty.REVERBERATION, damage=150, landed_at=3.5,
    ))
    assert l2 is not None
    assert l2.level == SkillchainLevel.LEVEL_2
    assert l2.element == SkillchainElement.DISTORTION
    assert l2.contributors == ["a", "b", "c"]
    assert l2.base_damage_sum == 350


# ----------------------------------------------------------------------
# Active window queries
# ----------------------------------------------------------------------

def test_get_active_window_after_detonation():
    det = SkillchainDetector()
    det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="a", target_id="t", ws_id="ws1",
        property=WSProperty.COMPRESSION, damage=100, landed_at=0,
    ))
    det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="b", target_id="t", ws_id="ws2",
        property=WSProperty.INDURATION, damage=100, landed_at=2,
    ))
    # Active window = the L1 chain that just detonated
    assert det.get_active_window("t") == SkillchainElement.INDURATION
    assert det.is_in_mb_window("t", now=3.5) is True
    assert det.is_in_mb_window("t", now=6.0) is False


def test_reset_target_clears_state():
    det = SkillchainDetector()
    det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="a", target_id="t", ws_id="ws1",
        property=WSProperty.COMPRESSION, damage=100, landed_at=0,
    ))
    det.reset_target("t")
    # Next WS opens a new chain (no detonation yet)
    result = det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="b", target_id="t", ws_id="ws2",
        property=WSProperty.INDURATION, damage=100, landed_at=2,
    ))
    assert result is None


# ----------------------------------------------------------------------
# DamageResolver — basic spell + chain bonuses
# ----------------------------------------------------------------------

@pytest.fixture
def resolver():
    return DamageResolver()


def test_resolve_basic_direct_damage(resolver):
    result = resolver.resolve(DamageContext(
        base_spell_damage=850,
        spell_type=SpellType.DIRECT_DAMAGE,
        spell_element=Element.ICE,
    ))
    assert result.final_damage == 850
    assert result.cancelled_by_intervention is False


def test_resolve_chain_level_1_with_weight(resolver):
    """L1 chain × weight bonus × stationary."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=600,        # raw WS damage
        skillchain_landed=SkillchainElement.INDURATION,
        chain_level=SkillchainLevel.LEVEL_1,
        caster_stationary=True,
        caster_gear_weight=14,        # Curtana
    ))
    # Expected: 600 * 1.25 (L1) * (1 + 0.005*9) (weight bonus) * 1.15 (stationary)
    expected = int(600 * 1.25 * 1.045 * 1.15)
    assert result.final_damage == expected
    assert result.breakdown["chain_level_multiplier"] == 1.25
    assert result.breakdown["stationary_bonus"] == 1.15


def test_resolve_magic_burst_exact_match(resolver):
    """Blizzard III on Distortion (water+ice) chain — element overlap."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=850,
        spell_type=SpellType.DIRECT_DAMAGE,
        spell_element=Element.ICE,
        skillchain_landed=SkillchainElement.DISTORTION,
        chain_level=SkillchainLevel.LEVEL_2,
        in_mb_window=True,
        caster_stationary=True,
    ))
    # Direct match: ice on Distortion (water+ice) = 1.0 element_match
    # Final = 850 * 1.65 (L2) * 1.045 (weight default 30 → 0% bonus) * 1.15 stationary
    #         then × 1.80 (L2 MB) × 1.0 (element_match) × 1.15 stationary × 1.0 nin
    # The chain damage goes through then is multiplied by mb_dmg_factor
    # So minimum should be substantially above 850
    assert result.final_damage > 850
    assert result.breakdown["mb_multiplier"] == 1.80


def test_resolve_magic_burst_opposition_penalty(resolver):
    """BLM nukes Blizzard III on a Liquefaction chain — opposition."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=850,
        spell_type=SpellType.DIRECT_DAMAGE,
        spell_element=Element.ICE,
        skillchain_landed=SkillchainElement.LIQUEFACTION,
        chain_level=SkillchainLevel.LEVEL_1,
        in_mb_window=True,
    ))
    # element_match should be 0.5 (opposition)
    assert result.breakdown["element_match"] == 0.5


def test_resolve_ailment_3x_amplification(resolver):
    """Slow II MB on a chain — 3x amplification."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=100,        # 100 = effect strength encoded as "damage"
        spell_type=SpellType.AILMENT,
        skillchain_landed=SkillchainElement.DISTORTION,
        chain_level=SkillchainLevel.LEVEL_2,
        in_mb_window=True,
    ))
    assert result.ailment_amplification == 3.0
    assert result.breakdown["ailment_amplification"] == 3.0
    # Final damage should be at least 3x the base for ailments
    assert result.final_damage >= 300


def test_resolve_ailment_no_window_no_amp(resolver):
    """Slow II cast outside MB window — no amplification."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=100,
        spell_type=SpellType.AILMENT,
        in_mb_window=False,
    ))
    assert result.ailment_amplification == 1.0


# ----------------------------------------------------------------------
# Affinity (MOB_RESISTANCES.md)
# ----------------------------------------------------------------------

def test_affinity_weak_to_amplifies(resolver):
    """Water spell on lightning-aligned mob (water IS its weak_to)."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=500,
        spell_type=SpellType.DIRECT_DAMAGE,
        spell_element=Element.WATER,
        target_aligned_element=Element.LIGHTNING,
        target_weak_to=Element.WATER,
    ))
    # 500 × 1.25 = 625
    assert result.final_damage == 625
    assert result.breakdown["affinity_multiplier"] == 1.25


def test_affinity_matching_element_halves(resolver):
    """Fire spell on fire-aligned Orc — half damage."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=500,
        spell_type=SpellType.DIRECT_DAMAGE,
        spell_element=Element.FIRE,
        target_aligned_element=Element.FIRE,
    ))
    assert result.final_damage == 250
    assert result.breakdown["affinity_multiplier"] == 0.5


def test_affinity_strong_against_reduces(resolver):
    """Fire on a wind-strong mob (Goblin)."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=500,
        spell_type=SpellType.DIRECT_DAMAGE,
        spell_element=Element.FIRE,
        target_strong_against=Element.FIRE,
    ))
    assert result.final_damage == 375
    assert result.breakdown["affinity_multiplier"] == 0.75


def test_affinity_neutral_no_change(resolver):
    """No relevant affinity — base damage."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=500,
        spell_type=SpellType.DIRECT_DAMAGE,
        spell_element=Element.LIGHTNING,
        target_aligned_element=Element.FIRE,
        target_weak_to=Element.WATER,
    ))
    assert result.final_damage == 500


# ----------------------------------------------------------------------
# Intervention path (defensive twin)
# ----------------------------------------------------------------------

def test_intervention_cancels_damage(resolver):
    """WHM Cure-V intervention on enemy chain → enemy damage = 0."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=8000,    # would-be enemy MB damage
        spell_type=SpellType.HEALING,
        is_intervention=True,
        intervention_chain_element=SkillchainElement.DISTORTION,
        in_mb_window=True,
    ))
    assert result.cancelled_by_intervention is True
    assert result.final_damage == 0
    assert result.intervention_amplification == 3.0


def test_intervention_light_bonus_5x(resolver):
    """Intervention on Light skillchain → 5x amplification."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=8000,
        spell_type=SpellType.HEALING,
        is_intervention=True,
        intervention_chain_element=SkillchainElement.LIGHT,
        in_mb_window=True,
    ))
    assert result.cancelled_by_intervention is True
    assert result.intervention_amplification == 5.0
    assert result.breakdown["light_bonus"] is True


def test_intervention_outside_window_doesnt_apply(resolver):
    """If MB window has passed, no intervention path; standard damage applies."""
    result = resolver.resolve(DamageContext(
        base_spell_damage=8000,
        spell_type=SpellType.HEALING,
        is_intervention=True,
        intervention_chain_element=SkillchainElement.DISTORTION,
        in_mb_window=False,         # window closed
    ))
    assert result.cancelled_by_intervention is False


# ----------------------------------------------------------------------
# Integrated end-to-end scenario
# ----------------------------------------------------------------------

def test_e2e_distortion_chain_then_ailment_burst():
    """Full scenario: WAR opens, NIN closes Distortion, RDM lands ailment MB."""
    det = SkillchainDetector()
    resolver = DamageResolver()

    # T+0.5: WAR opens with Crescent Moon (compression)
    det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="war", target_id="maat", ws_id="crescent_moon",
        property=WSProperty.COMPRESSION, damage=400, landed_at=0.5,
    ))

    # T+1.6: NIN signs Hyoton: Ichi (induration)
    chain_event = det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="nin", target_id="maat", ws_id="hyoton_ichi",
        property=WSProperty.INDURATION, damage=300, landed_at=1.6,
    ))
    assert chain_event is not None
    assert chain_event.element == SkillchainElement.INDURATION
    assert chain_event.level == SkillchainLevel.LEVEL_1

    # T+2.0: another WS lands extending to L2 Distortion via Reverberation
    l2 = det.observe_weapon_skill(WeaponSkillEvent(
        actor_id="rdm", target_id="maat", ws_id="hexa_strike",
        property=WSProperty.REVERBERATION, damage=350, landed_at=2.0,
    ))
    assert l2 is not None
    assert l2.element == SkillchainElement.DISTORTION
    assert l2.level == SkillchainLevel.LEVEL_2

    # T+3.0: RDM Bio II during MB window — ailment 3x
    assert det.is_in_mb_window("maat", now=3.0)
    bio_result = resolver.resolve(DamageContext(
        base_spell_damage=80,         # Bio II base effect strength
        spell_type=SpellType.AILMENT,
        skillchain_landed=SkillchainElement.DISTORTION,
        chain_level=SkillchainLevel.LEVEL_2,
        in_mb_window=True,
    ))
    assert bio_result.ailment_amplification == 3.0
    assert bio_result.final_damage >= 240   # 3x base 80
