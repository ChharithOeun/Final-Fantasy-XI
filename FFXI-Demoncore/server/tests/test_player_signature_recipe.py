"""Tests for player_signature_recipe."""
from __future__ import annotations

from server.player_signature_recipe import (
    PlayerSignatureRecipeSystem, LicenseState,
)


def _register(
    s: PlayerSignatureRecipeSystem,
    fee: int = 1000,
) -> str:
    return s.register_recipe(
        owner_id="naji", name="Naji's Mythril Stew",
        difficulty=80, license_fee_gil=fee,
    )


def test_register_happy():
    s = PlayerSignatureRecipeSystem()
    assert _register(s) is not None


def test_register_empty_name_blocked():
    s = PlayerSignatureRecipeSystem()
    assert s.register_recipe(
        owner_id="x", name="", difficulty=10,
        license_fee_gil=100,
    ) is None


def test_register_zero_fee_blocked():
    s = PlayerSignatureRecipeSystem()
    assert _register(s, fee=0) is None


def test_register_invalid_difficulty_blocked():
    s = PlayerSignatureRecipeSystem()
    assert s.register_recipe(
        owner_id="naji", name="x", difficulty=500,
        license_fee_gil=100,
    ) is None


def test_grant_license_happy():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    assert s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=10,
    ) is not None


def test_grant_license_owner_self_blocked():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    assert s.grant_license(
        recipe_id=rid, licensee_id="naji",
        granted_day=10,
    ) is None


def test_grant_license_dup_blocked():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=10,
    )
    assert s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=11,
    ) is None


def test_grant_license_unknown_recipe_blocked():
    s = PlayerSignatureRecipeSystem()
    assert s.grant_license(
        recipe_id="ghost", licensee_id="bob",
        granted_day=10,
    ) is None


def test_grant_license_pays_owner():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s, fee=500)
    s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=10,
    )
    s.grant_license(
        recipe_id=rid, licensee_id="cara",
        granted_day=11,
    )
    assert s.recipe(
        recipe_id=rid,
    ).total_royalties_paid_gil == 1000


def test_revoke_license_happy():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    lid = s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=10,
    )
    assert s.revoke_license(
        recipe_id=rid, license_id=lid,
        owner_id="naji",
    ) is True
    assert s.license_lookup(
        recipe_id=rid, license_id=lid,
    ).state == LicenseState.REVOKED


def test_revoke_license_wrong_owner_blocked():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    lid = s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=10,
    )
    assert s.revoke_license(
        recipe_id=rid, license_id=lid,
        owner_id="bob",
    ) is False


def test_revoke_clears_active_listing():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    lid = s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=10,
    )
    s.revoke_license(
        recipe_id=rid, license_id=lid,
        owner_id="naji",
    )
    assert "bob" not in s.licensees_for_recipe(
        recipe_id=rid,
    )


def test_re_license_after_revoke_ok():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    lid = s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=10,
    )
    s.revoke_license(
        recipe_id=rid, license_id=lid,
        owner_id="naji",
    )
    assert s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=20,
    ) is not None


def test_report_violation_happy():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    assert s.report_violation(
        recipe_id=rid, owner_id="naji",
        violator_id="bob", reported_day=10,
    ) is not None


def test_report_violation_wrong_owner_blocked():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    assert s.report_violation(
        recipe_id=rid, owner_id="bob",
        violator_id="cara", reported_day=10,
    ) is None


def test_report_violation_against_owner_self_blocked():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    assert s.report_violation(
        recipe_id=rid, owner_id="naji",
        violator_id="naji", reported_day=10,
    ) is None


def test_report_violation_against_licensee_blocked():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=5,
    )
    assert s.report_violation(
        recipe_id=rid, owner_id="naji",
        violator_id="bob", reported_day=10,
    ) is None


def test_report_violation_dup_blocked():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    s.report_violation(
        recipe_id=rid, owner_id="naji",
        violator_id="bob", reported_day=10,
    )
    assert s.report_violation(
        recipe_id=rid, owner_id="naji",
        violator_id="bob", reported_day=11,
    ) is None


def test_licensees_for_recipe_listing():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    s.grant_license(
        recipe_id=rid, licensee_id="bob",
        granted_day=10,
    )
    s.grant_license(
        recipe_id=rid, licensee_id="cara",
        granted_day=11,
    )
    assert s.licensees_for_recipe(
        recipe_id=rid,
    ) == ["bob", "cara"]


def test_violations_for_recipe_listing():
    s = PlayerSignatureRecipeSystem()
    rid = _register(s)
    s.report_violation(
        recipe_id=rid, owner_id="naji",
        violator_id="bob", reported_day=10,
    )
    assert len(s.violations_for_recipe(
        recipe_id=rid,
    )) == 1


def test_recipes_by_owner():
    s = PlayerSignatureRecipeSystem()
    _register(s)
    _register(s)
    assert len(s.recipes_by_owner(
        owner_id="naji",
    )) == 2


def test_unknown_recipe():
    s = PlayerSignatureRecipeSystem()
    assert s.recipe(recipe_id="ghost") is None


def test_enum_count():
    assert len(list(LicenseState)) == 3
