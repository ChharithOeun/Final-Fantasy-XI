"""Tests for recipe_substitution_rules."""
from __future__ import annotations

from server.recipe_substitution_rules import (
    RecipeSubstitutionRules, SubKind,
)


def test_add_exact_ok_rule():
    s = RecipeSubstitutionRules()
    out = s.add_rule(
        recipe_id="rec_1", original_mat="fire_crystal",
        kind=SubKind.EXACT_OK,
        alternates=["fire_cluster"],
        posted_at=1000,
    )
    assert out is True


def test_add_tier_ok_rule():
    s = RecipeSubstitutionRules()
    out = s.add_rule(
        recipe_id="rec_1", original_mat="dough",
        kind=SubKind.TIER_OK, tier_tag="tier1_grain",
        posted_at=1000,
    )
    assert out is True


def test_add_hq_ok_rule():
    s = RecipeSubstitutionRules()
    out = s.add_rule(
        recipe_id="rec_1", original_mat="flour",
        kind=SubKind.HQ_OK, posted_at=1000,
    )
    assert out is True


def test_add_blank_recipe_blocked():
    s = RecipeSubstitutionRules()
    assert s.add_rule(
        recipe_id="", original_mat="x",
        kind=SubKind.HQ_OK, posted_at=1000,
    ) is False


def test_add_blank_original_blocked():
    s = RecipeSubstitutionRules()
    assert s.add_rule(
        recipe_id="rec_1", original_mat="  ",
        kind=SubKind.HQ_OK, posted_at=1000,
    ) is False


def test_exact_ok_empty_alternates_blocked():
    s = RecipeSubstitutionRules()
    assert s.add_rule(
        recipe_id="rec_1", original_mat="x",
        kind=SubKind.EXACT_OK,
        alternates=[], posted_at=1000,
    ) is False


def test_exact_ok_too_many_alternates_blocked():
    s = RecipeSubstitutionRules()
    assert s.add_rule(
        recipe_id="rec_1", original_mat="x",
        kind=SubKind.EXACT_OK,
        alternates=[f"alt_{i}" for i in range(7)],
        posted_at=1000,
    ) is False


def test_exact_ok_blank_alternate_blocked():
    s = RecipeSubstitutionRules()
    assert s.add_rule(
        recipe_id="rec_1", original_mat="x",
        kind=SubKind.EXACT_OK,
        alternates=["a", "  "], posted_at=1000,
    ) is False


def test_exact_ok_self_in_alternates_blocked():
    s = RecipeSubstitutionRules()
    assert s.add_rule(
        recipe_id="rec_1", original_mat="x",
        kind=SubKind.EXACT_OK,
        alternates=["x", "y"], posted_at=1000,
    ) is False


def test_tier_ok_blank_tag_blocked():
    s = RecipeSubstitutionRules()
    assert s.add_rule(
        recipe_id="rec_1", original_mat="dough",
        kind=SubKind.TIER_OK, tier_tag="  ",
        posted_at=1000,
    ) is False


def test_tier_ok_with_alternates_blocked():
    s = RecipeSubstitutionRules()
    assert s.add_rule(
        recipe_id="rec_1", original_mat="dough",
        kind=SubKind.TIER_OK, tier_tag="grain",
        alternates=["x"], posted_at=1000,
    ) is False


def test_hq_ok_with_extras_blocked():
    s = RecipeSubstitutionRules()
    assert s.add_rule(
        recipe_id="rec_1", original_mat="flour",
        kind=SubKind.HQ_OK, alternates=["x"],
        posted_at=1000,
    ) is False


def test_max_rules_per_recipe():
    s = RecipeSubstitutionRules()
    for i in range(5):
        s.add_rule(
            recipe_id="rec_1", original_mat=f"mat_{i}",
            kind=SubKind.HQ_OK, posted_at=1000,
        )
    out = s.add_rule(
        recipe_id="rec_1", original_mat="overflow",
        kind=SubKind.HQ_OK, posted_at=1000,
    )
    assert out is False


def test_dup_rule_blocked():
    s = RecipeSubstitutionRules()
    s.add_rule(
        recipe_id="rec_1", original_mat="flour",
        kind=SubKind.HQ_OK, posted_at=1000,
    )
    out = s.add_rule(
        recipe_id="rec_1", original_mat="flour",
        kind=SubKind.HQ_OK, posted_at=2000,
    )
    assert out is False


def test_different_kinds_same_mat_allowed():
    """The author can mark a single mat with multiple
    rule kinds (e.g., HQ_OK and TIER_OK both apply)."""
    s = RecipeSubstitutionRules()
    s.add_rule(
        recipe_id="rec_1", original_mat="flour",
        kind=SubKind.HQ_OK, posted_at=1000,
    )
    out = s.add_rule(
        recipe_id="rec_1", original_mat="flour",
        kind=SubKind.TIER_OK, tier_tag="grain",
        posted_at=2000,
    )
    assert out is True


def test_rules_for_returns_list():
    s = RecipeSubstitutionRules()
    s.add_rule(
        recipe_id="rec_1", original_mat="flour",
        kind=SubKind.HQ_OK, posted_at=1000,
    )
    out = s.rules_for(recipe_id="rec_1")
    assert len(out) == 1


def test_rules_for_unknown_empty():
    s = RecipeSubstitutionRules()
    assert s.rules_for(recipe_id="ghost") == []


def test_accepts_identity_true():
    s = RecipeSubstitutionRules()
    assert s.accepts(
        recipe_id="rec_1", slot_mat="x", candidate_mat="x",
    ) is True


def test_accepts_exact_ok_match():
    s = RecipeSubstitutionRules()
    s.add_rule(
        recipe_id="rec_1", original_mat="fire_crystal",
        kind=SubKind.EXACT_OK,
        alternates=["fire_cluster"], posted_at=1000,
    )
    assert s.accepts(
        recipe_id="rec_1", slot_mat="fire_crystal",
        candidate_mat="fire_cluster",
    ) is True


def test_accepts_exact_ok_non_match():
    s = RecipeSubstitutionRules()
    s.add_rule(
        recipe_id="rec_1", original_mat="fire_crystal",
        kind=SubKind.EXACT_OK,
        alternates=["fire_cluster"], posted_at=1000,
    )
    assert s.accepts(
        recipe_id="rec_1", slot_mat="fire_crystal",
        candidate_mat="ice_crystal",
    ) is False


def test_accepts_tier_ok_match():
    s = RecipeSubstitutionRules()
    s.add_rule(
        recipe_id="rec_1", original_mat="dough",
        kind=SubKind.TIER_OK, tier_tag="tier1_grain",
        posted_at=1000,
    )
    assert s.accepts(
        recipe_id="rec_1", slot_mat="dough",
        candidate_mat="rice_flour",
        tier_tags=["tier1_grain"],
    ) is True


def test_accepts_tier_ok_no_tags_false():
    s = RecipeSubstitutionRules()
    s.add_rule(
        recipe_id="rec_1", original_mat="dough",
        kind=SubKind.TIER_OK, tier_tag="tier1_grain",
        posted_at=1000,
    )
    assert s.accepts(
        recipe_id="rec_1", slot_mat="dough",
        candidate_mat="rice_flour",
    ) is False


def test_accepts_hq_ok_match():
    s = RecipeSubstitutionRules()
    s.add_rule(
        recipe_id="rec_1", original_mat="flour",
        kind=SubKind.HQ_OK, posted_at=1000,
    )
    assert s.accepts(
        recipe_id="rec_1", slot_mat="flour",
        candidate_mat="flour_hq",
    ) is True


def test_accepts_no_rule_returns_false():
    s = RecipeSubstitutionRules()
    assert s.accepts(
        recipe_id="rec_1", slot_mat="dough",
        candidate_mat="rice_flour",
    ) is False


def test_total_rules():
    s = RecipeSubstitutionRules()
    s.add_rule(
        recipe_id="rec_1", original_mat="a",
        kind=SubKind.HQ_OK, posted_at=1000,
    )
    s.add_rule(
        recipe_id="rec_2", original_mat="b",
        kind=SubKind.HQ_OK, posted_at=1000,
    )
    assert s.total_rules() == 2


def test_three_sub_kinds():
    assert len(list(SubKind)) == 3
