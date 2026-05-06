"""Tests for addon_intent_spec."""
from __future__ import annotations

from server.addon_intent_spec import (
    AddonIntentSpec, GearSetEntry, OffenseMode, SpellRule,
    validate,
)


def _minimal():
    return AddonIntentSpec(
        addon_id="rdm_chharith", job="RDM",
        weapon_sets={
            "Death Blossom": GearSetEntry(
                set_name="Death Blossom",
                slot_to_item={"main": "Murgleis", "sub": "Sakpata's Sword"},
            ),
        },
        offense_modes=[
            OffenseMode(mode_name="TP", weaponskill_target="Death Blossom"),
        ],
        idle_set=GearSetEntry(
            set_name="idle",
            slot_to_item={"head": "Viti. Chapeau +4"},
        ),
        food_item="Tropical Crepe",
        lockstyle_pallet="20",
        macro_book="3",
        macro_set="1",
        default_offense_mode="TP",
    )


def test_validate_minimal_happy():
    out = validate(_minimal())
    assert out.valid is True
    assert out.errors == ()


def test_blank_addon_id_invalid():
    s = _minimal()
    s.addon_id = ""
    out = validate(s)
    assert out.valid is False
    assert any("addon_id" in e for e in out.errors)


def test_blank_job_invalid():
    s = _minimal()
    s.job = ""
    out = validate(s)
    assert out.valid is False
    assert any("job" in e for e in out.errors)


def test_weapon_set_without_main_invalid():
    s = _minimal()
    s.weapon_sets["No Main"] = GearSetEntry(
        set_name="No Main",
        slot_to_item={"sub": "Daybreak"},
    )
    out = validate(s)
    assert out.valid is False
    assert any("main slot" in e for e in out.errors)


def test_default_mode_must_match_declared():
    s = _minimal()
    s.default_offense_mode = "PHANTOM_MODE"
    out = validate(s)
    assert out.valid is False
    assert any("PHANTOM_MODE" in e for e in out.errors)


def test_no_idle_set_warning():
    s = _minimal()
    s.idle_set = None
    out = validate(s)
    assert out.valid is True
    assert any("idle" in w for w in out.warnings)


def test_no_food_warning():
    s = _minimal()
    s.food_item = ""
    out = validate(s)
    assert out.valid is True
    assert any("food" in w for w in out.warnings)


def test_no_macro_book_warning():
    s = _minimal()
    s.macro_book = ""
    out = validate(s)
    assert out.valid is True
    assert any("macro_book" in w for w in out.warnings)


def test_blank_spell_id_invalid():
    s = _minimal()
    s.spell_rules.append(
        SpellRule(spell_id="", auto_cast_when="hp_low", target="self"),
    )
    out = validate(s)
    assert out.valid is False


def test_blank_spell_target_invalid():
    s = _minimal()
    s.spell_rules.append(
        SpellRule(spell_id="cure_iv", auto_cast_when="hp_low", target=""),
    )
    out = validate(s)
    assert out.valid is False


def test_valid_spell_rule_passes():
    s = _minimal()
    s.spell_rules.append(
        SpellRule(
            spell_id="cure_iv", auto_cast_when="hp_low",
            target="lowest_hp_party",
        ),
    )
    out = validate(s)
    assert out.valid is True


def test_blank_weapon_set_name_invalid():
    s = _minimal()
    s.weapon_sets[""] = GearSetEntry(
        set_name="", slot_to_item={"main": "x"},
    )
    out = validate(s)
    assert out.valid is False


def test_multiple_weapon_sets():
    s = _minimal()
    s.weapon_sets["Savage Blade"] = GearSetEntry(
        set_name="Savage Blade",
        slot_to_item={"main": "Naegling", "sub": "Machaera +2"},
    )
    out = validate(s)
    assert out.valid is True
    assert len(s.weapon_sets) == 2


def test_multiple_offense_modes():
    s = _minimal()
    s.offense_modes.append(
        OffenseMode(mode_name="DT", weaponskill_target="Death Blossom"),
    )
    s.offense_modes.append(
        OffenseMode(mode_name="ACC", weaponskill_target="Death Blossom"),
    )
    out = validate(s)
    assert out.valid is True


def test_default_mode_can_be_unset_blank():
    s = _minimal()
    s.default_offense_mode = ""
    out = validate(s)
    # blank default mode is allowed (forge picks first declared)
    assert out.valid is True


def test_warnings_do_not_invalidate():
    s = AddonIntentSpec(
        addon_id="x", job="WHM",
        weapon_sets={
            "Default": GearSetEntry(
                set_name="Default",
                slot_to_item={"main": "Yagrush"},
            ),
        },
    )
    out = validate(s)
    # multiple warnings (no idle, no food, no macro book) but valid
    assert out.valid is True
    assert len(out.warnings) >= 3


def test_errors_listed_all_at_once():
    """Validator surfaces all errors, not just the first."""
    s = AddonIntentSpec(
        addon_id="", job="",
        weapon_sets={
            "BadSet": GearSetEntry(
                set_name="BadSet",
                slot_to_item={"sub": "x"},   # no main
            ),
        },
    )
    out = validate(s)
    assert out.valid is False
    assert len(out.errors) >= 3   # 3 distinct issues


def test_canonical_rdm_shape_passes():
    """Mirrors the RDM.lua shape Tart shared as reference."""
    s = AddonIntentSpec(
        addon_id="rdm_chharith", job="RDM",
        weapon_sets={
            "Death Blossom": GearSetEntry(
                set_name="Death Blossom",
                slot_to_item={
                    "main": "Murgleis", "sub": "Sakpata's Sword",
                },
            ),
            "Savage Blade": GearSetEntry(
                set_name="Savage Blade",
                slot_to_item={
                    "main": "Naegling", "sub": "Machaera +2",
                },
            ),
            "Sanguine Blade": GearSetEntry(
                set_name="Sanguine Blade",
                slot_to_item={
                    "main": "Crocea Mors", "sub": "Sakpata's Sword",
                },
            ),
        },
        offense_modes=[
            OffenseMode(mode_name="TP", weaponskill_target="Death Blossom"),
            OffenseMode(mode_name="ACC", weaponskill_target="Death Blossom"),
            OffenseMode(mode_name="DT", weaponskill_target="Death Blossom"),
        ],
        idle_set=GearSetEntry(
            set_name="idle",
            slot_to_item={
                "ammo": "Staunch Tathlum +1",
                "body": "Lethargy Sayon +2",
            },
        ),
        food_item="Tropical Crepe",
        lockstyle_pallet="20",
        macro_book="3",
        macro_set="1",
        default_offense_mode="DT",
    )
    out = validate(s)
    assert out.valid is True


def test_empty_spec_invalid_no_crash():
    s = AddonIntentSpec(addon_id="", job="")
    out = validate(s)
    # Should report errors but not raise
    assert out.valid is False
