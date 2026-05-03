"""Tests for cooking spoilage."""
from __future__ import annotations

from server.cooking_spoilage import (
    Freshness,
    GAME_DAY_SECONDS,
    InventoryEntry,
    PRESERVATION_SKILL_THRESHOLD,
    SpoilProfile,
    SpoilageRegistry,
    preservation_bonus,
    seed_default_profiles,
)


def _registry() -> SpoilageRegistry:
    return seed_default_profiles(SpoilageRegistry())


def _entry(
    entry_id: str = "e1", item_id: str = "fish_fresh",
    qty: int = 1, created_at: float = 0.0,
) -> InventoryEntry:
    return InventoryEntry(
        entry_id=entry_id, item_id=item_id,
        quantity=qty, created_at_seconds=created_at,
    )


def test_seed_canonical_profiles():
    reg = _registry()
    assert reg.profile("fish_fresh") is not None
    assert reg.profile("cooked_dish") is not None
    assert reg.profile("crystal_fire") is not None


def test_immortal_item_never_spoils():
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            item_id="crystal_fire", created_at=0.0,
        ),
    )
    far_future = GAME_DAY_SECONDS * 365 * 100
    assert reg.freshness_of(
        player_id="alice", entry_id="e1",
        now_seconds=far_future,
    ) == Freshness.FRESH


def test_fresh_aging_stale_spoiled_progression():
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            item_id="fish_fresh", created_at=0.0,
        ),
    )
    # fish shelf=1 day. fresh<=12h, aging<=19.2h, stale<=24h
    twelve = GAME_DAY_SECONDS * 0.4
    eighteen = GAME_DAY_SECONDS * 0.7
    twenty_three = GAME_DAY_SECONDS * 0.95
    twenty_five = GAME_DAY_SECONDS * 1.1
    assert reg.freshness_of(
        player_id="alice", entry_id="e1",
        now_seconds=twelve,
    ) == Freshness.FRESH
    assert reg.freshness_of(
        player_id="alice", entry_id="e1",
        now_seconds=eighteen,
    ) == Freshness.AGING
    assert reg.freshness_of(
        player_id="alice", entry_id="e1",
        now_seconds=twenty_three,
    ) == Freshness.STALE
    assert reg.freshness_of(
        player_id="alice", entry_id="e1",
        now_seconds=twenty_five,
    ) == Freshness.SPOILED


def test_preservation_bonus_below_threshold():
    assert preservation_bonus(50) == 1.0


def test_preservation_bonus_at_threshold():
    assert preservation_bonus(
        PRESERVATION_SKILL_THRESHOLD,
    ) == 1.0


def test_preservation_bonus_full():
    assert preservation_bonus(
        PRESERVATION_SKILL_THRESHOLD + 100,
    ) == 2.0


def test_preservation_bonus_capped():
    assert preservation_bonus(999) == 2.0


def test_preservation_extends_shelf_life():
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            item_id="fish_fresh", created_at=0.0,
        ),
        cooking_skill=PRESERVATION_SKILL_THRESHOLD + 100,
    )
    # 25 hours = past base shelf but bonus 2x makes it 48h
    twenty_five = GAME_DAY_SECONDS * 1.1
    assert reg.freshness_of(
        player_id="alice", entry_id="e1",
        now_seconds=twenty_five,
    ) != Freshness.SPOILED


def test_non_preservable_ignores_bonus():
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            item_id="dried_jerky", created_at=0.0,
        ),
        cooking_skill=200,
    )
    # Jerky shelf=30 days. Without preservation bonus:
    #   FRESH 0..15d, AGING 15..24d, STALE 24..30d.
    # 20 days lands in AGING; if a bonus had applied, it'd
    # still be FRESH.
    twenty_days = GAME_DAY_SECONDS * 20
    assert reg.freshness_of(
        player_id="alice", entry_id="e1",
        now_seconds=twenty_days,
    ) == Freshness.AGING


def test_unknown_item_add_rejected():
    reg = _registry()
    res = reg.add_item(
        player_id="alice", entry=_entry(item_id="phantom"),
    )
    assert not res


def test_freshness_unknown_entry_returns_none():
    reg = _registry()
    assert reg.freshness_of(
        player_id="alice", entry_id="ghost",
        now_seconds=0.0,
    ) is None


def test_auto_remove_spoiled():
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            entry_id="old_fish", item_id="fish_fresh",
            created_at=0.0,
        ),
    )
    reg.add_item(
        player_id="alice", entry=_entry(
            entry_id="fresh_potion", item_id="cure_potion",
            created_at=GAME_DAY_SECONDS * 5,
        ),
    )
    removed = reg.auto_remove_spoiled(
        player_id="alice",
        now_seconds=GAME_DAY_SECONDS * 5 + 100,
    )
    # Old fish well past 1-day shelf, removed
    assert "old_fish" in removed
    # Fresh potion not spoiled yet, not removed
    assert "fresh_potion" not in removed


def test_consume_fresh_no_debuff():
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            item_id="fish_fresh", created_at=0.0,
        ),
    )
    fresh, debuff = reg.consume(
        player_id="alice", entry_id="e1",
        now_seconds=100.0,
    )
    assert fresh == Freshness.FRESH
    assert debuff is None


def test_consume_spoiled_returns_debuff():
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            item_id="fish_fresh", created_at=0.0,
        ),
    )
    fresh, debuff = reg.consume(
        player_id="alice", entry_id="e1",
        now_seconds=GAME_DAY_SECONDS * 2,
    )
    assert fresh == Freshness.SPOILED
    assert debuff == "food_poisoning"


def test_consume_decrements_quantity():
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            item_id="cure_potion", qty=3,
            created_at=0.0,
        ),
    )
    reg.consume(
        player_id="alice", entry_id="e1",
        now_seconds=100.0,
    )
    assert reg.total_in_inventory("alice") == 1


def test_consume_last_quantity_removes_entry():
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            item_id="cure_potion", qty=1,
            created_at=0.0,
        ),
    )
    reg.consume(
        player_id="alice", entry_id="e1",
        now_seconds=100.0,
    )
    assert reg.total_in_inventory("alice") == 0


def test_full_lifecycle_meal_pipeline():
    """Player crafts a fresh meal, holds it, eats it before
    spoilage, then leaves a second meal too long and gets food
    poisoning."""
    reg = _registry()
    reg.add_item(
        player_id="alice", entry=_entry(
            entry_id="meal_a", item_id="cooked_dish",
            created_at=0.0,
        ),
    )
    reg.add_item(
        player_id="alice", entry=_entry(
            entry_id="meal_b", item_id="cooked_dish",
            created_at=0.0,
        ),
    )
    # Eat meal_a fresh
    f1, d1 = reg.consume(
        player_id="alice", entry_id="meal_a",
        now_seconds=GAME_DAY_SECONDS,
    )
    assert f1 == Freshness.FRESH
    assert d1 is None
    # meal_b sits 5 days — well past 3-day shelf
    f2, d2 = reg.consume(
        player_id="alice", entry_id="meal_b",
        now_seconds=GAME_DAY_SECONDS * 5,
    )
    assert f2 == Freshness.SPOILED
    assert d2 == "food_poisoning"
