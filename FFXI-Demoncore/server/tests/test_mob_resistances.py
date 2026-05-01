"""Tests for elemental affinity + mob resistance engine.

Run:  python -m pytest server/tests/test_mob_resistances.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from mob_resistances import (
    BossAffinityPhase,
    BossPhaseShifter,
    ELEMENT_OPPOSITES,
    Element,
    MOB_CLASS_AFFINITIES,
    MobAffinity,
    VISUAL_CUE_TABLE,
    affinity_for,
    apply_ailment_x_affinity,
    apply_chain_x_affinity,
    damage_multiplier,
    visual_cue_for,
)
from mob_resistances.elements import opposite_of


# ----------------------------------------------------------------------
# Element wheel
# ----------------------------------------------------------------------

def test_fire_ice_opposites():
    assert ELEMENT_OPPOSITES[Element.FIRE] == Element.ICE
    assert ELEMENT_OPPOSITES[Element.ICE] == Element.FIRE


def test_water_lightning_opposites():
    assert ELEMENT_OPPOSITES[Element.WATER] == Element.LIGHTNING
    assert ELEMENT_OPPOSITES[Element.LIGHTNING] == Element.WATER


def test_earth_wind_opposites():
    assert ELEMENT_OPPOSITES[Element.EARTH] == Element.WIND
    assert ELEMENT_OPPOSITES[Element.WIND] == Element.EARTH


def test_light_dark_opposites():
    assert ELEMENT_OPPOSITES[Element.LIGHT] == Element.DARK
    assert ELEMENT_OPPOSITES[Element.DARK] == Element.LIGHT


def test_none_has_no_opposite():
    assert opposite_of(Element.NONE) == Element.NONE


def test_eight_elements_total():
    """Every element except NONE has an opposite registered."""
    elemental = [e for e in Element if e != Element.NONE]
    assert len(elemental) == 8
    for e in elemental:
        assert e in ELEMENT_OPPOSITES


# ----------------------------------------------------------------------
# Damage multiplier resolution
# ----------------------------------------------------------------------

def test_matching_element_half_damage():
    """Doc example: fire chain on fire-aligned Orc = 0.50x."""
    orc = MOB_CLASS_AFFINITIES["orc"]
    mult = damage_multiplier(attacker_element=Element.FIRE,
                              defender=orc)
    assert mult == 0.50


def test_weak_to_element_125():
    """Doc example: water chain on Quadav = 1.25x."""
    quadav = MOB_CLASS_AFFINITIES["quadav"]
    mult = damage_multiplier(attacker_element=Element.WATER,
                              defender=quadav)
    assert mult == 1.25


def test_strong_vs_element_075():
    """Orc strong-vs-wind: wind on Orc = 0.75x."""
    orc = MOB_CLASS_AFFINITIES["orc"]
    mult = damage_multiplier(attacker_element=Element.WIND,
                              defender=orc)
    assert mult == 0.75


def test_neutral_element_100():
    """Earth on Quadav (lightning aligned, weak water, strong wind):
    earth is none of those → neutral 1.00."""
    quadav = MOB_CLASS_AFFINITIES["quadav"]
    mult = damage_multiplier(attacker_element=Element.EARTH,
                              defender=quadav)
    assert mult == 1.00


def test_non_elemental_attack_unaffected():
    """NONE-element damage (physical, fixed) doesn't read affinity."""
    quadav = MOB_CLASS_AFFINITIES["quadav"]
    mult = damage_multiplier(attacker_element=Element.NONE,
                              defender=quadav)
    assert mult == 1.00


def test_demon_resists_all_except_weak_to():
    """Demon NM (resists_all=True): everything except light is 0.75x."""
    demon = MOB_CLASS_AFFINITIES["demon_nm"]
    # Light is the weak_to → 1.25x
    assert damage_multiplier(attacker_element=Element.LIGHT,
                              defender=demon) == 1.25
    # Dark (matching) → 0.50
    assert damage_multiplier(attacker_element=Element.DARK,
                              defender=demon) == 0.50
    # Fire (random other) → 0.75 (resists_all)
    assert damage_multiplier(attacker_element=Element.FIRE,
                              defender=demon) == 0.75


def test_doc_orc_table_example():
    """Doc: 'fire chain on Orc = 50% damage; water chain on same Orc
    = 125%'. Verify both."""
    orc = MOB_CLASS_AFFINITIES["orc"]
    fire_dmg = damage_multiplier(attacker_element=Element.FIRE, defender=orc)
    # Orc weak_to is ICE per the table; water is neutral
    water_dmg = damage_multiplier(attacker_element=Element.WATER, defender=orc)
    ice_dmg = damage_multiplier(attacker_element=Element.ICE, defender=orc)
    assert fire_dmg == 0.50
    # Note: doc text says "water chain on the same Orc does 125%" but
    # the per-class table says Orc weak_to = ICE. We honor the TABLE,
    # which is canonical. Water on Orc is neutral.
    assert water_dmg == 1.00
    assert ice_dmg == 1.25
    # The 2.5x ratio the doc highlights between picking the right
    # chain element vs the wrong one: ice (1.25) / fire (0.50) = 2.5x
    assert ice_dmg / fire_dmg == 2.5


# ----------------------------------------------------------------------
# Per-mob-class table
# ----------------------------------------------------------------------

def test_quadav_lightning_water_wind():
    q = MOB_CLASS_AFFINITIES["quadav"]
    assert q.aligned_element == Element.LIGHTNING
    assert q.weak_to == Element.WATER
    assert q.strong_vs == Element.WIND


def test_yagudo_water_lightning_fire():
    y = MOB_CLASS_AFFINITIES["yagudo"]
    assert y.aligned_element == Element.WATER
    assert y.weak_to == Element.LIGHTNING
    assert y.strong_vs == Element.FIRE


def test_skeleton_dark_light_no_strong_vs():
    """Skeletons have a weak_to but no strong_vs (per the table)."""
    s = MOB_CLASS_AFFINITIES["skeleton"]
    assert s.aligned_element == Element.DARK
    assert s.weak_to == Element.LIGHT
    assert s.strong_vs is None


def test_affinity_for_lookup():
    a = affinity_for("Quadav")     # case-insensitive
    assert a is not None
    assert a.aligned_element == Element.LIGHTNING


def test_affinity_for_variable_returns_none():
    """Slimes vary per zone; dragons vary per individual. The lookup
    returns None and the caller supplies the affinity at spawn time."""
    assert affinity_for("slime") is None
    assert affinity_for("dragon") is None


# ----------------------------------------------------------------------
# Composition: chain × affinity × stationary
# ----------------------------------------------------------------------

def test_chain_x_affinity_compose():
    base = 1000.0
    result = apply_chain_x_affinity(
        chain_dmg_base=base, affinity_multiplier=1.25,
        stationary_bonus=1.10,
    )
    assert result == pytest.approx(1375.0)


def test_chain_with_matching_element_halves():
    """Even with stationary bonus, matching element reduces damage."""
    base = 1000.0
    result = apply_chain_x_affinity(
        chain_dmg_base=base, affinity_multiplier=0.50,
        stationary_bonus=1.0,
    )
    assert result == 500.0


def test_ailment_x_affinity_compose():
    """3x Slow on a wind-weak target during Earth chain = 3.75x.
    base 1.0 × 3 × 1.25 = 3.75."""
    result = apply_ailment_x_affinity(
        base_ailment_strength=1.0,
        affinity_multiplier=1.25,
        ailment_amp=3.0,
    )
    assert result == pytest.approx(3.75)


def test_ailment_doc_example():
    """Doc: 'apex CC pressure — boss is locked at ~14% normal speed
    for 30s.' Slow base reduces speed to 0.50, 3x amp = 1.5 effective
    multiplier on slow magnitude, × 1.25 affinity = 1.875 effective.
    1 - 0.50 × 1.875 = -0.0625 (clamped to floor) => speed multiplier
    of about 0.14. We check the ailment-strength math here, not the
    speed clamp; the speed-system layer applies the floor."""
    # Verifying: the multiplied ailment value is 1.875
    result = apply_ailment_x_affinity(
        base_ailment_strength=0.50, ailment_amp=3.0,
        affinity_multiplier=1.25,
    )
    assert result == pytest.approx(1.875)


# ----------------------------------------------------------------------
# Visual cues
# ----------------------------------------------------------------------

def test_visual_cue_lookup():
    fire = visual_cue_for(Element.FIRE)
    assert "reddish" in fire.description.lower()
    assert fire.niagara_emitter == "NS_AffinityGlow_Fire"


def test_each_element_has_visual_cue():
    for element in Element:
        if element == Element.NONE:
            cue = visual_cue_for(Element.NONE)
            assert cue.niagara_emitter == ""
            continue
        cue = visual_cue_for(element)
        assert cue.element == element
        assert cue.description != ""
        assert cue.niagara_emitter.startswith("NS_AffinityGlow_")


def test_visual_cue_table_eight_entries():
    assert len(VISUAL_CUE_TABLE) == 8


def test_dark_cue_is_purple():
    cue = visual_cue_for(Element.DARK)
    assert "purple" in cue.description.lower()


def test_light_cue_is_white_gold():
    cue = visual_cue_for(Element.LIGHT)
    assert "white" in cue.description.lower() or "gold" in cue.description.lower()


# ----------------------------------------------------------------------
# Boss phase shifter
# ----------------------------------------------------------------------

def _maat_phases() -> list[BossAffinityPhase]:
    """Maat: opens dark, shifts to light at wounded, flips NONE under
    Hundred Fists."""
    return [
        BossAffinityPhase(
            name="pristine",
            affinity=MobAffinity(Element.DARK, Element.LIGHT, None),
            is_hidden=True,             # affinity hidden in pristine
            hp_threshold=100.0,
        ),
        BossAffinityPhase(
            name="wounded",
            affinity=MobAffinity(Element.LIGHT, Element.DARK, None),
            is_hidden=False,
            hp_threshold=50.0,
        ),
        BossAffinityPhase(
            name="hundred_fists",
            affinity=MobAffinity(Element.NONE, None, None),
            is_hidden=False,
            state_flag="hundred_fists",
        ),
    ]


def test_phase_shifter_pristine():
    s = BossPhaseShifter(_maat_phases())
    phase = s.current_phase(hp_pct=100.0)
    assert phase.name == "pristine"
    assert phase.affinity.aligned_element == Element.DARK


def test_phase_shifter_wounded_at_50_pct():
    s = BossPhaseShifter(_maat_phases())
    phase = s.current_phase(hp_pct=50.0)
    assert phase.name == "wounded"
    assert phase.affinity.aligned_element == Element.LIGHT


def test_phase_shifter_wounded_at_30_pct():
    s = BossPhaseShifter(_maat_phases())
    phase = s.current_phase(hp_pct=30.0)
    assert phase.name == "wounded"


def test_phase_shifter_state_flag_overrides_hp():
    """Hundred Fists active: affinity becomes NONE regardless of HP."""
    s = BossPhaseShifter(_maat_phases())
    phase = s.current_phase(hp_pct=80.0, flags={"hundred_fists"})
    assert phase.name == "hundred_fists"
    assert phase.affinity.aligned_element == Element.NONE


def test_phase_shifter_visible_affinity_hides_pristine():
    """Pristine phase has is_hidden=True → players don't see it."""
    s = BossPhaseShifter(_maat_phases())
    visible = s.visible_affinity(hp_pct=100.0)
    assert visible is None


def test_phase_shifter_effective_affinity_unhidden():
    """Even when hidden, the math still reads the real affinity."""
    s = BossPhaseShifter(_maat_phases())
    effective = s.effective_affinity(hp_pct=100.0)
    assert effective.aligned_element == Element.DARK


def test_phase_shifter_visible_affinity_at_wounded():
    """Wounded phase is unhidden → visible to players."""
    s = BossPhaseShifter(_maat_phases())
    visible = s.visible_affinity(hp_pct=40.0)
    assert visible is not None
    assert visible.aligned_element == Element.LIGHT


def test_phase_shifter_empty_phases_raises():
    with pytest.raises(ValueError):
        BossPhaseShifter([])


def test_hundred_fists_denies_3x_bonus():
    """When boss is in NONE-element phase, no element matches → 1.0x.
    No elemental advantage; 3x ailment amp is denied affinity bonus."""
    s = BossPhaseShifter(_maat_phases())
    aff = s.effective_affinity(hp_pct=80.0, flags={"hundred_fists"})
    # Casting any element on a NONE-aligned defender:
    for elem in (Element.FIRE, Element.ICE, Element.LIGHT, Element.DARK):
        mult = damage_multiplier(attacker_element=elem, defender=aff)
        # NONE-aligned mobs have no aligned/weak/strong; everything is neutral
        # Except: Element.NONE matches itself (via aligned_element==NONE → 0.5)
        if elem == Element.NONE:
            assert mult == 0.50
        else:
            assert mult == 1.00


# ----------------------------------------------------------------------
# Integration: realistic chain damage scenarios
# ----------------------------------------------------------------------

def test_water_chain_on_quadav_full_pipeline():
    """End-to-end: water chain on Quadav with stationary attackers.
    base=2000, water vs Quadav = 1.25x, stationary = 1.10x → 2750."""
    quadav = MOB_CLASS_AFFINITIES["quadav"]
    mult = damage_multiplier(attacker_element=Element.WATER,
                              defender=quadav)
    final = apply_chain_x_affinity(
        chain_dmg_base=2000, affinity_multiplier=mult,
        stationary_bonus=1.10,
    )
    assert final == pytest.approx(2750)


def test_lightning_chain_on_quadav_matching_halved():
    """Lightning on Quadav = matching = 0.50x."""
    quadav = MOB_CLASS_AFFINITIES["quadav"]
    mult = damage_multiplier(attacker_element=Element.LIGHTNING,
                              defender=quadav)
    final = apply_chain_x_affinity(chain_dmg_base=2000, affinity_multiplier=mult)
    assert final == 1000


def test_2_5x_ratio_right_vs_wrong_chain():
    """Doc claim: 'party that reads affinity does 2.5x the damage of
    a party that doesn't.' Verify with Quadav: water (1.25x) vs
    lightning (0.50x) = 2.5x ratio."""
    quadav = MOB_CLASS_AFFINITIES["quadav"]
    right = damage_multiplier(attacker_element=Element.WATER, defender=quadav)
    wrong = damage_multiplier(attacker_element=Element.LIGHTNING, defender=quadav)
    assert right / wrong == 2.5
