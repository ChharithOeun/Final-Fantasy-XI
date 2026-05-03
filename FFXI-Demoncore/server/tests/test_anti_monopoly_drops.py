"""Tests for the anti-monopoly drop policy + recipe validator."""
from __future__ import annotations

from server.anti_monopoly_drops import (
    DIRECT_DROP_KINDS,
    DropSource,
    DropSourceKind,
    all_registered,
    audit_su_slip_catalog,
    has_direct_drop,
    is_registered,
    register_material,
    sources_for,
    validate_recipe,
)


def test_all_su_core_mats_registered():
    """Every core tier material referenced by Su slips must be
    in the registry — otherwise the Su pipeline would have a
    monopoly hook."""
    expected = {
        "shadow_dust", "shadow_resin", "ebon_filament",
        "voidstone_shard", "voidstone_core", "godsblood_essence",
        "weapon_grade_alloy", "weapon_grade_oil",
    }
    registered = all_registered()
    missing = expected - registered
    assert not missing, f"unregistered Su mats: {missing}"


def test_archetype_essence_mats_registered():
    for archetype in ("caster", "melee", "ranger", "ninja",
                       "blue_mage", "puppet", "beast", "dancer", "rune"):
        assert is_registered(f"essence_{archetype}")


def test_every_registered_material_has_direct_drop():
    """The registry itself must obey the policy."""
    for mid in all_registered():
        assert has_direct_drop(mid), (
            f"{mid} has no direct-drop source — registry is broken"
        )


def test_direct_drop_kinds_excludes_synth():
    """Synth output is not a direct drop. Every drop kind in the
    enum should be in DIRECT_DROP_KINDS, since we don't have a
    SYNTH kind in the enum (synthesis output is implicit via
    `can_also_be_crafted` on the registry entry)."""
    for kind in DropSourceKind:
        assert kind in DIRECT_DROP_KINDS


def test_validate_recipe_passes_for_clean_inputs():
    report = validate_recipe(
        ["shadow_dust", "essence_caster", "essence_melee"],
    )
    assert report.ok
    assert report.missing_direct_drop == ()
    assert report.unregistered == ()


def test_validate_recipe_flags_unregistered():
    report = validate_recipe(["nonexistent_phantom_mat"])
    assert not report.ok
    assert "nonexistent_phantom_mat" in report.unregistered


def test_validate_recipe_flags_no_direct_drop():
    """Register a material with ONLY a synth fallback (no direct
    drop sources) and the validator must catch it."""
    register_material(
        material_id="craft_only_test_mat",
        sources=(),                    # zero direct sources
        can_also_be_crafted=True,
    )
    report = validate_recipe(["craft_only_test_mat"])
    assert not report.ok
    assert "craft_only_test_mat" in report.missing_direct_drop


def test_audit_su_slip_catalog_passes():
    """The crown jewel: walk the entire Su slip catalog and
    verify every material referenced is anti-monopoly compliant."""
    report = audit_su_slip_catalog()
    assert report.ok, report.summary()


def test_sources_for_returns_full_list():
    sources = sources_for("shadow_dust")
    assert len(sources) >= 2
    # Multiple source kinds — that's the anti-monopoly safety net
    kinds = {s.kind for s in sources}
    assert DropSourceKind.VENDOR in kinds


def test_vendor_only_material_is_compliant():
    """A vendor-only material is OK — vendor counts as direct
    drop because it gives newbies a guaranteed access path."""
    register_material(
        material_id="vendor_only_test_mat",
        sources=(
            DropSource("test_npc",
                       DropSourceKind.VENDOR,
                       notes="100 gil"),
        ),
        can_also_be_crafted=False,
    )
    report = validate_recipe(["vendor_only_test_mat"])
    assert report.ok


def test_godsblood_is_capstone_only():
    """Verify the world-first capstone has only world-first sources."""
    sources = sources_for("godsblood_essence")
    assert len(sources) >= 1
    # No vendor fallback for the capstone — it's TOP-of-content
    kinds = {s.kind for s in sources}
    assert DropSourceKind.VENDOR not in kinds


def test_validation_summary_renders():
    report = validate_recipe(["shadow_dust"])
    s = report.summary()
    assert "OK" in s

    bad = validate_recipe(["fake_mat"])
    s2 = bad.summary()
    assert "FAIL" in s2


def test_register_overwrites_existing_entry():
    register_material(
        material_id="rotation_test_mat",
        sources=(
            DropSource("first_source", DropSourceKind.MOB),
        ),
    )
    assert len(sources_for("rotation_test_mat")) == 1
    register_material(
        material_id="rotation_test_mat",
        sources=(
            DropSource("first_source", DropSourceKind.MOB),
            DropSource("second_source", DropSourceKind.BOSS),
        ),
    )
    assert len(sources_for("rotation_test_mat")) == 2
