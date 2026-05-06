"""Tests for recipe_discovery."""
from __future__ import annotations

from server.cookpot_recipes import DishKind
from server.recipe_discovery import RecipeDiscoveryRegistry


def test_first_cook_returns_event():
    r = RecipeDiscoveryRegistry()
    out = r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=10,
    )
    assert out is not None
    assert out.dish == DishKind.HUNTERS_STEW
    assert out.sequence_number == 1


def test_second_cook_returns_none():
    r = RecipeDiscoveryRegistry()
    r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=10,
    )
    out = r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=20,
    )
    assert out is None


def test_blank_player_blocked():
    r = RecipeDiscoveryRegistry()
    out = r.record_cook(
        player_id="", dish=DishKind.HUNTERS_STEW, cooked_at=10,
    )
    assert out is None


def test_sequence_number_increments():
    r = RecipeDiscoveryRegistry()
    e1 = r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=10,
    )
    e2 = r.record_cook(
        player_id="alice", dish=DishKind.WARMING_TEA,
        cooked_at=20,
    )
    assert e1.sequence_number == 1
    assert e2.sequence_number == 2


def test_two_players_independent_sequences():
    r = RecipeDiscoveryRegistry()
    a = r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=10,
    )
    b = r.record_cook(
        player_id="bob", dish=DishKind.HUNTERS_STEW,
        cooked_at=20,
    )
    # both get sequence 1 — first dish FOR THEM
    assert a.sequence_number == 1
    assert b.sequence_number == 1


def test_has_discovered():
    r = RecipeDiscoveryRegistry()
    r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=10,
    )
    assert r.has_discovered(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
    ) is True
    assert r.has_discovered(
        player_id="alice", dish=DishKind.WARMING_TEA,
    ) is False


def test_has_discovered_unknown_player():
    r = RecipeDiscoveryRegistry()
    assert r.has_discovered(
        player_id="ghost", dish=DishKind.HUNTERS_STEW,
    ) is False


def test_cookbook_of_orders_by_discovery():
    r = RecipeDiscoveryRegistry()
    r.record_cook(
        player_id="alice", dish=DishKind.WARMING_TEA,
        cooked_at=10,
    )
    r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=20,
    )
    r.record_cook(
        player_id="alice", dish=DishKind.BERRY_PORRIDGE,
        cooked_at=30,
    )
    book = r.cookbook_of(player_id="alice")
    assert book[0] == DishKind.WARMING_TEA
    assert book[2] == DishKind.BERRY_PORRIDGE


def test_cookbook_empty_for_unknown_player():
    r = RecipeDiscoveryRegistry()
    assert r.cookbook_of(player_id="ghost") == []


def test_total_discoveries():
    r = RecipeDiscoveryRegistry()
    r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=10,
    )
    r.record_cook(
        player_id="alice", dish=DishKind.WARMING_TEA,
        cooked_at=20,
    )
    assert r.total_discoveries(player_id="alice") == 2


def test_total_discoveries_zero_for_unknown():
    r = RecipeDiscoveryRegistry()
    assert r.total_discoveries(player_id="ghost") == 0


def test_get_discovery_returns_event():
    r = RecipeDiscoveryRegistry()
    r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=42,
    )
    e = r.get_discovery(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
    )
    assert e is not None
    assert e.discovered_at == 42


def test_get_discovery_unknown_returns_none():
    r = RecipeDiscoveryRegistry()
    e = r.get_discovery(
        player_id="ghost", dish=DishKind.HUNTERS_STEW,
    )
    assert e is None


def test_repeat_cook_does_not_change_total():
    r = RecipeDiscoveryRegistry()
    r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=10,
    )
    r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=20,
    )
    assert r.total_discoveries(player_id="alice") == 1


def test_carries_player_id():
    r = RecipeDiscoveryRegistry()
    e = r.record_cook(
        player_id="alice", dish=DishKind.HUNTERS_STEW,
        cooked_at=10,
    )
    assert e.player_id == "alice"
