"""Tests for the recipe book UI."""
from __future__ import annotations

from server.recipe_book_ui import (
    CraftKind,
    Recipe,
    RecipeBookUI,
)


def _seed(b: RecipeBookUI):
    b.register_recipe(
        recipe=Recipe(
            recipe_id="iron_sword",
            label="Iron Sword",
            craft=CraftKind.SMITHING,
            skill_required=15,
            inputs={"iron_ingot": 1, "wooden_grip": 1},
            output_item_id="iron_sword",
        ),
    )
    b.register_recipe(
        recipe=Recipe(
            recipe_id="ether",
            label="Ether",
            craft=CraftKind.ALCHEMY,
            skill_required=20,
            inputs={"distilled_water": 1, "yagudo_drink": 1},
            output_item_id="ether",
        ),
    )


def test_register_recipe():
    b = RecipeBookUI()
    _seed(b)
    assert b.total_recipes() == 2


def test_register_double_rejected():
    b = RecipeBookUI()
    _seed(b)
    second = b.register_recipe(
        recipe=Recipe(
            recipe_id="iron_sword", label="x",
            craft=CraftKind.SMITHING,
            skill_required=1,
            inputs={"x": 1},
            output_item_id="x",
        ),
    )
    assert not second


def test_register_no_inputs_rejected():
    b = RecipeBookUI()
    res = b.register_recipe(
        recipe=Recipe(
            recipe_id="x", label="x",
            craft=CraftKind.SMITHING,
            skill_required=1, inputs={},
            output_item_id="x",
        ),
    )
    assert not res


def test_register_zero_output_rejected():
    b = RecipeBookUI()
    res = b.register_recipe(
        recipe=Recipe(
            recipe_id="x", label="x",
            craft=CraftKind.SMITHING,
            skill_required=1,
            inputs={"i": 1},
            output_item_id="x",
            output_qty=0,
        ),
    )
    assert not res


def test_discover_recipe():
    b = RecipeBookUI()
    _seed(b)
    assert b.discover(
        player_id="alice", recipe_id="iron_sword",
    )
    entries = b.discovered_for(player_id="alice")
    assert len(entries) == 1


def test_discover_unknown():
    b = RecipeBookUI()
    assert not b.discover(
        player_id="alice", recipe_id="ghost",
    )


def test_discover_increments_times():
    b = RecipeBookUI()
    _seed(b)
    b.discover(
        player_id="alice", recipe_id="iron_sword",
    )
    b.discover(
        player_id="alice", recipe_id="iron_sword",
    )
    entries = b.discovered_for(player_id="alice")
    assert entries[0].times_synthesized == 2


def test_update_inventory():
    b = RecipeBookUI()
    _seed(b)
    b.update_inventory(
        player_id="alice",
        item_qty={"iron_ingot": 5, "wooden_grip": 3},
    )
    book = b._books["alice"]
    assert book.inventory["iron_ingot"] == 5


def test_zero_qty_removes_inventory_entry():
    b = RecipeBookUI()
    _seed(b)
    b.update_inventory(
        player_id="alice",
        item_qty={"iron_ingot": 5},
    )
    b.update_inventory(
        player_id="alice",
        item_qty={"iron_ingot": 0},
    )
    book = b._books["alice"]
    assert "iron_ingot" not in book.inventory


def test_missing_for_recipe():
    b = RecipeBookUI()
    _seed(b)
    b.update_inventory(
        player_id="alice",
        item_qty={"iron_ingot": 1},
    )
    missing = b.missing_for(
        player_id="alice", recipe_id="iron_sword",
    )
    assert missing == {"wooden_grip": 1}


def test_missing_unknown_recipe():
    b = RecipeBookUI()
    assert b.missing_for(
        player_id="alice", recipe_id="ghost",
    ) is None


def test_missing_no_inventory_full_list():
    b = RecipeBookUI()
    _seed(b)
    missing = b.missing_for(
        player_id="alice", recipe_id="iron_sword",
    )
    assert missing == {"iron_ingot": 1, "wooden_grip": 1}


def test_search_substring():
    b = RecipeBookUI()
    _seed(b)
    b.discover(player_id="alice", recipe_id="iron_sword")
    b.discover(player_id="alice", recipe_id="ether")
    hits = b.search(player_id="alice", query="sword")
    assert {h.recipe_id for h in hits} == {"iron_sword"}


def test_search_filter_craft():
    b = RecipeBookUI()
    _seed(b)
    b.discover(player_id="alice", recipe_id="iron_sword")
    b.discover(player_id="alice", recipe_id="ether")
    hits = b.search(
        player_id="alice", craft=CraftKind.ALCHEMY,
    )
    assert {h.recipe_id for h in hits} == {"ether"}


def test_search_max_skill_filter():
    b = RecipeBookUI()
    _seed(b)
    b.discover(player_id="alice", recipe_id="iron_sword")
    b.discover(player_id="alice", recipe_id="ether")
    hits = b.search(player_id="alice", max_skill=15)
    assert {h.recipe_id for h in hits} == {"iron_sword"}


def test_search_craftable_now_filter():
    b = RecipeBookUI()
    _seed(b)
    b.discover(player_id="alice", recipe_id="iron_sword")
    b.update_inventory(
        player_id="alice",
        item_qty={"iron_ingot": 1, "wooden_grip": 1},
    )
    hits = b.search(
        player_id="alice", craftable_now=True,
    )
    assert {h.recipe_id for h in hits} == {"iron_sword"}


def test_search_craftable_now_excludes_missing():
    b = RecipeBookUI()
    _seed(b)
    b.discover(player_id="alice", recipe_id="iron_sword")
    hits = b.search(
        player_id="alice", craftable_now=True,
    )
    assert hits == ()


def test_search_no_book_empty():
    b = RecipeBookUI()
    _seed(b)
    hits = b.search(player_id="ghost")
    assert hits == ()


def test_search_have_materials_flag():
    b = RecipeBookUI()
    _seed(b)
    b.discover(player_id="alice", recipe_id="iron_sword")
    hits = b.search(player_id="alice")
    assert not hits[0].have_materials


def test_search_missing_dict_in_hit():
    b = RecipeBookUI()
    _seed(b)
    b.discover(player_id="alice", recipe_id="iron_sword")
    b.update_inventory(
        player_id="alice",
        item_qty={"iron_ingot": 1},
    )
    hits = b.search(player_id="alice")
    assert hits[0].missing == {"wooden_grip": 1}


def test_search_max_results_cap():
    b = RecipeBookUI()
    for i in range(10):
        b.register_recipe(
            recipe=Recipe(
                recipe_id=f"r_{i}", label=f"r_{i}",
                craft=CraftKind.COOKING,
                skill_required=1,
                inputs={"x": 1},
                output_item_id="x",
            ),
        )
        b.discover(
            player_id="alice", recipe_id=f"r_{i}",
        )
    hits = b.search(player_id="alice", max_results=3)
    assert len(hits) == 3
