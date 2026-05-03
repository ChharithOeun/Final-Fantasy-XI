"""Tests for the mat essentiality registry."""
from __future__ import annotations

from server.mat_essentiality_registry import (
    EssentialityTier,
    MatEssentialityRegistry,
    priority_for_tier,
    seed_default_essentials,
)


def test_priority_descending_with_tier():
    """Higher-essentiality tiers carry larger priority weights."""
    assert priority_for_tier(EssentialityTier.CORE_BASIC) > (
        priority_for_tier(EssentialityTier.CRAFT_INPUT)
    )
    assert priority_for_tier(EssentialityTier.CRAFT_INPUT) > (
        priority_for_tier(EssentialityTier.CONSUMABLE)
    )
    assert priority_for_tier(EssentialityTier.LUXURY) == 0


def test_register_and_lookup():
    reg = MatEssentialityRegistry()
    e = reg.register(
        item_id="iron_ore", tier=EssentialityTier.CRAFT_INPUT,
        tags=("metal", "smithing"),
    )
    assert reg.tier_for("iron_ore") == EssentialityTier.CRAFT_INPUT
    assert reg.priority_for("iron_ore") == 75
    assert e.priority == 75


def test_priority_for_unknown_is_zero():
    """Unregistered items default to LUXURY priority."""
    reg = MatEssentialityRegistry()
    assert reg.priority_for("ghost_item") == 0
    assert not reg.is_essential("ghost_item")


def test_is_essential_includes_three_tiers():
    reg = MatEssentialityRegistry()
    reg.register(
        item_id="potion", tier=EssentialityTier.CORE_BASIC,
    )
    reg.register(
        item_id="iron_ore", tier=EssentialityTier.CRAFT_INPUT,
    )
    reg.register(
        item_id="apple_mint", tier=EssentialityTier.CONSUMABLE,
    )
    reg.register(
        item_id="rosewood", tier=EssentialityTier.SPECIALTY,
    )
    reg.register(
        item_id="painting", tier=EssentialityTier.LUXURY,
    )
    assert reg.is_essential("potion")
    assert reg.is_essential("iron_ore")
    assert reg.is_essential("apple_mint")
    assert not reg.is_essential("rosewood")
    assert not reg.is_essential("painting")


def test_by_tier_filters():
    reg = MatEssentialityRegistry()
    reg.register(
        item_id="iron_ore", tier=EssentialityTier.CRAFT_INPUT,
    )
    reg.register(
        item_id="cotton_thread",
        tier=EssentialityTier.CRAFT_INPUT,
    )
    reg.register(
        item_id="potion", tier=EssentialityTier.CORE_BASIC,
    )
    inputs = reg.by_tier(EssentialityTier.CRAFT_INPUT)
    assert len(inputs) == 2
    ids = {e.item_id for e in inputs}
    assert ids == {"iron_ore", "cotton_thread"}


def test_by_tag_filters():
    reg = MatEssentialityRegistry()
    reg.register(
        item_id="iron_ore", tier=EssentialityTier.CRAFT_INPUT,
        tags=("metal", "smithing"),
    )
    reg.register(
        item_id="oak_lumber", tier=EssentialityTier.CRAFT_INPUT,
        tags=("wood", "woodworking"),
    )
    reg.register(
        item_id="mythril_ore", tier=EssentialityTier.CRAFT_INPUT,
        tags=("metal", "smithing"),
    )
    metals = reg.by_tag("metal")
    ids = {e.item_id for e in metals}
    assert ids == {"iron_ore", "mythril_ore"}


def test_priority_rank_orders_descending():
    reg = MatEssentialityRegistry()
    reg.register(
        item_id="painting", tier=EssentialityTier.LUXURY,
    )
    reg.register(
        item_id="iron_ore", tier=EssentialityTier.CRAFT_INPUT,
    )
    reg.register(
        item_id="potion", tier=EssentialityTier.CORE_BASIC,
    )
    ranked = reg.priority_rank()
    ordered_ids = [e.item_id for e in ranked]
    assert ordered_ids == ["potion", "iron_ore", "painting"]


def test_seed_default_populates_canonical_essentials():
    reg = seed_default_essentials(MatEssentialityRegistry())
    # Spot check core consumables
    assert reg.tier_for(
        "cure_potion",
    ) == EssentialityTier.CORE_BASIC
    # Crystals are CORE_BASIC
    for elem in ("fire", "ice", "wind", "earth",
                  "lightning", "water", "light", "dark"):
        assert reg.tier_for(
            f"crystal_{elem}",
        ) == EssentialityTier.CORE_BASIC
    # Craft inputs
    assert reg.tier_for(
        "iron_ore",
    ) == EssentialityTier.CRAFT_INPUT
    assert reg.tier_for(
        "cotton_thread",
    ) == EssentialityTier.CRAFT_INPUT
    # Specialty / luxury
    assert reg.tier_for(
        "rosewood_lumber",
    ) == EssentialityTier.SPECIALTY
    assert reg.tier_for(
        "decorative_egg",
    ) == EssentialityTier.LUXURY


def test_seed_default_tags_searchable():
    reg = seed_default_essentials(MatEssentialityRegistry())
    metals = reg.by_tag("metal")
    metal_ids = {e.item_id for e in metals}
    assert "iron_ore" in metal_ids
    assert "mythril_ore" in metal_ids


def test_tags_default_to_empty():
    reg = MatEssentialityRegistry()
    e = reg.register(
        item_id="lonely", tier=EssentialityTier.CONSUMABLE,
    )
    assert e.tags == frozenset()


def test_total_counts_registered():
    reg = MatEssentialityRegistry()
    reg.register(
        item_id="a", tier=EssentialityTier.CONSUMABLE,
    )
    reg.register(
        item_id="b", tier=EssentialityTier.CRAFT_INPUT,
    )
    assert reg.total() == 2


def test_register_overwrites_existing():
    reg = MatEssentialityRegistry()
    reg.register(
        item_id="iron_ore", tier=EssentialityTier.SPECIALTY,
    )
    reg.register(
        item_id="iron_ore", tier=EssentialityTier.CRAFT_INPUT,
    )
    assert reg.tier_for(
        "iron_ore",
    ) == EssentialityTier.CRAFT_INPUT


def test_full_lifecycle_priority_ranking():
    """Check that the seeded default catalog priorities sort the
    way the regulator expects: core first, luxuries last."""
    reg = seed_default_essentials(MatEssentialityRegistry())
    ranked = reg.priority_rank()
    assert ranked[0].tier == EssentialityTier.CORE_BASIC
    assert ranked[-1].tier == EssentialityTier.LUXURY
