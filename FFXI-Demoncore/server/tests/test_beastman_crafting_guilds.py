"""Tests for the beastman crafting guilds."""
from __future__ import annotations

from server.beastman_crafting_guilds import (
    BeastmanCraftingGuilds,
    GuildKind,
    GuildRank,
    RecipeTier,
)
from server.beastman_playable_races import BeastmanRace


def _seed(g):
    g.register_recipe(
        recipe_id="beak_dagger",
        guild=GuildKind.YAGUDO_FORGE,
        tier=RecipeTier.NOVICE,
        inputs=(("beak_shard", 2), ("rope", 1)),
        output_id="beak_dagger_item",
        output_qty=1,
        skill_required=0,
    )
    g.join_guild(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
        race=BeastmanRace.YAGUDO,
    )


def test_register_recipe():
    g = BeastmanCraftingGuilds()
    _seed(g)
    assert g.total_recipes() == 1


def test_register_recipe_duplicate():
    g = BeastmanCraftingGuilds()
    _seed(g)
    res = g.register_recipe(
        recipe_id="beak_dagger",
        guild=GuildKind.YAGUDO_FORGE,
        tier=RecipeTier.NOVICE,
        inputs=(("a", 1),),
        output_id="x", output_qty=1,
        skill_required=0,
    )
    assert res is None


def test_register_recipe_zero_output():
    g = BeastmanCraftingGuilds()
    res = g.register_recipe(
        recipe_id="bad",
        guild=GuildKind.YAGUDO_FORGE,
        tier=RecipeTier.NOVICE,
        inputs=(("a", 1),),
        output_id="x", output_qty=0,
        skill_required=0,
    )
    assert res is None


def test_register_recipe_skill_below_tier_floor():
    g = BeastmanCraftingGuilds()
    res = g.register_recipe(
        recipe_id="bad",
        guild=GuildKind.YAGUDO_FORGE,
        tier=RecipeTier.MASTER,
        inputs=(("a", 1),),
        output_id="x", output_qty=1,
        skill_required=10,
    )
    assert res is None


def test_register_recipe_zero_qty_input():
    g = BeastmanCraftingGuilds()
    res = g.register_recipe(
        recipe_id="bad",
        guild=GuildKind.YAGUDO_FORGE,
        tier=RecipeTier.NOVICE,
        inputs=(("a", 0),),
        output_id="x", output_qty=1,
        skill_required=0,
    )
    assert res is None


def test_join_guild_basic():
    g = BeastmanCraftingGuilds()
    _seed(g)
    assert g.skill_in(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    ) == 0


def test_join_guild_double_rejected():
    g = BeastmanCraftingGuilds()
    _seed(g)
    res = g.join_guild(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
        race=BeastmanRace.YAGUDO,
    )
    assert not res


def test_join_multiple_guilds_same_race():
    g = BeastmanCraftingGuilds()
    _seed(g)
    # Yagudo player joins Quadav guild — allowed at the join level,
    # but cross-race exclusive recipes will be blocked.
    res = g.join_guild(
        player_id="kraw",
        guild=GuildKind.QUADAV_STONEWORK,
        race=BeastmanRace.YAGUDO,
    )
    assert res


def test_join_race_mismatch_after_first_join():
    g = BeastmanCraftingGuilds()
    _seed(g)
    res = g.join_guild(
        player_id="kraw",
        guild=GuildKind.QUADAV_STONEWORK,
        race=BeastmanRace.QUADAV,
    )
    assert not res


def test_craft_basic():
    g = BeastmanCraftingGuilds()
    _seed(g)
    res = g.craft(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
        recipe_id="beak_dagger",
        available={"beak_shard": 5, "rope": 2},
    )
    assert res.accepted
    assert res.output_id == "beak_dagger_item"
    assert res.new_skill == 3


def test_craft_missing_material():
    g = BeastmanCraftingGuilds()
    _seed(g)
    res = g.craft(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
        recipe_id="beak_dagger",
        available={"beak_shard": 1},
    )
    assert not res.accepted


def test_craft_unknown_recipe():
    g = BeastmanCraftingGuilds()
    _seed(g)
    res = g.craft(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
        recipe_id="nope",
        available={},
    )
    assert not res.accepted


def test_craft_not_in_guild():
    g = BeastmanCraftingGuilds()
    _seed(g)
    res = g.craft(
        player_id="bob",
        guild=GuildKind.YAGUDO_FORGE,
        recipe_id="beak_dagger",
        available={"beak_shard": 5, "rope": 2},
    )
    assert not res.accepted


def test_craft_race_locked_blocks_other_race():
    g = BeastmanCraftingGuilds()
    g.register_recipe(
        recipe_id="quadav_plinth",
        guild=GuildKind.QUADAV_STONEWORK,
        tier=RecipeTier.NOVICE,
        inputs=(("slate", 3),),
        output_id="plinth",
        output_qty=1,
        skill_required=0,
        exclusive_to_race=True,
    )
    g.join_guild(
        player_id="kraw",
        guild=GuildKind.QUADAV_STONEWORK,
        race=BeastmanRace.YAGUDO,
    )
    res = g.craft(
        player_id="kraw",
        guild=GuildKind.QUADAV_STONEWORK,
        recipe_id="quadav_plinth",
        available={"slate": 5},
    )
    assert not res.accepted


def test_craft_non_exclusive_cross_race_works():
    g = BeastmanCraftingGuilds()
    g.register_recipe(
        recipe_id="generic_torch",
        guild=GuildKind.QUADAV_STONEWORK,
        tier=RecipeTier.NOVICE,
        inputs=(("oil", 1),),
        output_id="torch",
        output_qty=1,
        skill_required=0,
        exclusive_to_race=False,
    )
    g.join_guild(
        player_id="kraw",
        guild=GuildKind.QUADAV_STONEWORK,
        race=BeastmanRace.YAGUDO,
    )
    res = g.craft(
        player_id="kraw",
        guild=GuildKind.QUADAV_STONEWORK,
        recipe_id="generic_torch",
        available={"oil": 1},
    )
    assert res.accepted


def test_craft_insufficient_skill():
    g = BeastmanCraftingGuilds()
    g.register_recipe(
        recipe_id="hard_thing",
        guild=GuildKind.YAGUDO_FORGE,
        tier=RecipeTier.JOURNEYMAN,
        inputs=(("a", 1),),
        output_id="x",
        output_qty=1,
        skill_required=70,
    )
    g.join_guild(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
        race=BeastmanRace.YAGUDO,
    )
    res = g.craft(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
        recipe_id="hard_thing",
        available={"a": 1},
    )
    assert not res.accepted


def test_skill_caps_at_100():
    g = BeastmanCraftingGuilds()
    _seed(g)
    for _ in range(50):
        g.craft(
            player_id="kraw",
            guild=GuildKind.YAGUDO_FORGE,
            recipe_id="beak_dagger",
            available={"beak_shard": 10, "rope": 2},
        )
    assert g.skill_in(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    ) == 100


def test_promote_journeyman():
    g = BeastmanCraftingGuilds()
    _seed(g)
    for _ in range(20):
        g.craft(
            player_id="kraw",
            guild=GuildKind.YAGUDO_FORGE,
            recipe_id="beak_dagger",
            available={"beak_shard": 10, "rope": 2},
        )
    res = g.promote(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    )
    assert res.accepted
    assert res.new_rank == GuildRank.JOURNEYMAN


def test_promote_insufficient_skill():
    g = BeastmanCraftingGuilds()
    _seed(g)
    res = g.promote(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    )
    assert not res.accepted


def test_promote_not_in_guild():
    g = BeastmanCraftingGuilds()
    res = g.promote(
        player_id="ghost",
        guild=GuildKind.YAGUDO_FORGE,
    )
    assert not res.accepted


def test_rank_in():
    g = BeastmanCraftingGuilds()
    _seed(g)
    assert g.rank_in(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    ) == GuildRank.APPRENTICE


def test_rank_in_not_member():
    g = BeastmanCraftingGuilds()
    assert g.rank_in(
        player_id="ghost",
        guild=GuildKind.YAGUDO_FORGE,
    ) is None


def test_promote_to_master():
    g = BeastmanCraftingGuilds()
    _seed(g)
    for _ in range(50):
        g.craft(
            player_id="kraw",
            guild=GuildKind.YAGUDO_FORGE,
            recipe_id="beak_dagger",
            available={"beak_shard": 10, "rope": 2},
        )
    g.promote(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    )
    res = g.promote(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    )
    assert res.accepted
    assert res.new_rank == GuildRank.MASTER


def test_promote_already_master():
    g = BeastmanCraftingGuilds()
    _seed(g)
    for _ in range(50):
        g.craft(
            player_id="kraw",
            guild=GuildKind.YAGUDO_FORGE,
            recipe_id="beak_dagger",
            available={"beak_shard": 10, "rope": 2},
        )
    g.promote(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    )
    g.promote(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    )
    res = g.promote(
        player_id="kraw",
        guild=GuildKind.YAGUDO_FORGE,
    )
    assert not res.accepted
