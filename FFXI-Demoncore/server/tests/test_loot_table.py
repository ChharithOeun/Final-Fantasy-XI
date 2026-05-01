"""Tests for loot_table — drop tables, TH modifier, roll engine."""
from __future__ import annotations

import pytest

from server.loot_table import (
    MAX_TH_LEVEL,
    DropEntry,
    DropTable,
    Rarity,
    drops_count_by_rarity,
    roll_drops,
    treasure_hunter_modifier,
)
from server.rng_pool import RngPool


# -- DropEntry validation ---------------------------------------------

def test_drop_entry_rejects_out_of_range_rate():
    with pytest.raises(ValueError):
        DropEntry(item_id="gil", base_rate=1.5, rarity=Rarity.COMMON)
    with pytest.raises(ValueError):
        DropEntry(item_id="gil", base_rate=-0.1, rarity=Rarity.COMMON)


def test_drop_entry_accepts_boundary_rates():
    DropEntry(item_id="gil", base_rate=0.0, rarity=Rarity.COMMON)
    DropEntry(item_id="gil", base_rate=1.0, rarity=Rarity.COMMON)


# -- DropTable lookups -----------------------------------------------

def _sample_table() -> DropTable:
    return DropTable(
        mob_class_id="goblin_smithy",
        label="Goblin Smithy",
        entries=(
            DropEntry("gil_drop",       0.95, Rarity.COMMON),
            DropEntry("goblin_mask",    0.30, Rarity.UNCOMMON),
            DropEntry("goblin_armor",   0.05, Rarity.RARE),
            DropEntry("ridill",         0.001, Rarity.SUPER_RARE),
            DropEntry("smithy_signet",  0.20, Rarity.EX),
        ),
    )


def test_by_rarity_filters_correctly():
    table = _sample_table()
    assert {e.item_id for e in table.by_rarity(Rarity.COMMON)} == \
           {"gil_drop"}
    assert {e.item_id for e in table.by_rarity(Rarity.UNCOMMON)} == \
           {"goblin_mask"}
    assert {e.item_id for e in table.by_rarity(Rarity.RARE)} == \
           {"goblin_armor"}
    assert {e.item_id for e in table.by_rarity(Rarity.SUPER_RARE)} == \
           {"ridill"}
    assert {e.item_id for e in table.by_rarity(Rarity.EX)} == \
           {"smithy_signet"}


# -- Treasure Hunter modifier -----------------------------------------

def test_th_zero_is_identity():
    for r in Rarity:
        assert treasure_hunter_modifier(r, 0) == 1.0


def test_th_modifier_monotonically_increases():
    """Higher TH level must never lower the modifier (caller sees
    a >=1.0 multiplier and bumps up at each step)."""
    for r in Rarity:
        prev = 0.0
        for lvl in range(0, MAX_TH_LEVEL + 1):
            cur = treasure_hunter_modifier(r, lvl)
            assert cur >= prev
            prev = cur


def test_th_rare_bumps_more_than_common():
    """The whole point of TH is that rares benefit more than commons."""
    common_bump = (
        treasure_hunter_modifier(Rarity.COMMON, 4) - 1.0
    )
    rare_bump = (
        treasure_hunter_modifier(Rarity.RARE, 4) - 1.0
    )
    assert rare_bump > common_bump


def test_th_ex_is_always_identity():
    """EX items are gated by other rules; TH cannot help."""
    for lvl in range(0, MAX_TH_LEVEL + 1):
        assert treasure_hunter_modifier(Rarity.EX, lvl) == 1.0


def test_th_negative_raises():
    with pytest.raises(ValueError):
        treasure_hunter_modifier(Rarity.COMMON, -1)


def test_th_above_max_saturates():
    """TH 99 doesn't crash; it caps at MAX_TH_LEVEL."""
    cap = treasure_hunter_modifier(Rarity.RARE, MAX_TH_LEVEL)
    assert treasure_hunter_modifier(Rarity.RARE, 99) == cap


# -- roll engine ------------------------------------------------------

def test_roll_drops_deterministic_with_same_seed():
    table = _sample_table()
    a = roll_drops(table=table, rng_pool=RngPool(world_seed=42))
    b = roll_drops(table=table, rng_pool=RngPool(world_seed=42))
    assert a == b


def test_roll_drops_different_seeds_likely_diverge():
    table = _sample_table()
    a = roll_drops(table=table, rng_pool=RngPool(world_seed=1))
    b = roll_drops(table=table, rng_pool=RngPool(world_seed=2))
    # Across a 5-entry table, the probability they happen to match
    # exactly is astronomically small — but assert on a long sequence
    # instead of one roll to be safe.
    a_long = []
    b_long = []
    pa = RngPool(world_seed=1)
    pb = RngPool(world_seed=2)
    for _ in range(20):
        a_long.append(roll_drops(table=table, rng_pool=pa))
        b_long.append(roll_drops(table=table, rng_pool=pb))
    assert a_long != b_long


def test_roll_drops_threshold_zero_never_drops():
    """An entry with base_rate=0 must never appear in the output."""
    table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("never_drops", 0.0, Rarity.RARE),
        ),
    )
    pool = RngPool(world_seed=0)
    for _ in range(100):
        drops = roll_drops(table=table, rng_pool=pool)
        assert all(d.item_id != "never_drops" for d in drops)


def test_roll_drops_threshold_one_always_drops():
    """An entry with base_rate=1.0 must always appear."""
    table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("always_drops", 1.0, Rarity.COMMON),
        ),
    )
    pool = RngPool(world_seed=0)
    for _ in range(100):
        drops = roll_drops(table=table, rng_pool=pool)
        assert any(d.item_id == "always_drops" for d in drops)


def test_roll_drops_each_drop_carries_rarity_and_threshold():
    table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("known_rare", 1.0, Rarity.RARE),
        ),
    )
    pool = RngPool(world_seed=0)
    drops = roll_drops(table=table, rng_pool=pool)
    assert len(drops) == 1
    assert drops[0].rarity == Rarity.RARE
    assert drops[0].rolled_against == 1.0


def test_th_clamps_post_modifier_rate_to_one():
    """A 95% common with TH IV would mathematically be 109% — clamp
    to 1.0 so nothing crashes."""
    table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("high_rate_common", 0.95, Rarity.COMMON),
        ),
    )
    pool = RngPool(world_seed=0)
    drops = roll_drops(table=table, rng_pool=pool, th_level=4)
    assert len(drops) == 1
    assert drops[0].rolled_against == 1.0   # capped


def test_th_increases_average_drop_rate_for_rare_tier():
    """Statistical sanity — over many kills, TH IV produces more
    rare drops than no TH. Use a fixed seed so the test is
    deterministic."""
    table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("rare_target", 0.05, Rarity.RARE),
        ),
    )
    no_th = sum(
        1 for _ in range(1000)
        for d in roll_drops(
            table=table,
            rng_pool=RngPool(world_seed=_ * 31),
            th_level=0,
        )
        if d.item_id == "rare_target"
    )
    with_th = sum(
        1 for _ in range(1000)
        for d in roll_drops(
            table=table,
            rng_pool=RngPool(world_seed=_ * 31),
            th_level=4,
        )
        if d.item_id == "rare_target"
    )
    assert with_th > no_th


def test_drops_count_by_rarity_histogram():
    table = _sample_table()
    pool = RngPool(world_seed=0)
    # Roll a bunch and accumulate.
    total = {r: 0 for r in Rarity}
    for _ in range(50):
        drops = roll_drops(table=table, rng_pool=pool)
        for r, n in drops_count_by_rarity(drops).items():
            total[r] += n
    # Common at 95% should dwarf super-rare at 0.1%.
    assert total[Rarity.COMMON] > total[Rarity.SUPER_RARE]


def test_roll_drops_uses_loot_drops_stream_by_default():
    """Default stream is STREAM_LOOT_DROPS — confirm by drawing
    from that stream the expected count and matching."""
    table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("a", 0.5, Rarity.COMMON),
            DropEntry("b", 0.5, Rarity.COMMON),
        ),
    )
    pool_a = RngPool(world_seed=99)
    pool_b = RngPool(world_seed=99)

    drops_a = roll_drops(table=table, rng_pool=pool_a)
    # Manually consume the same stream from a fresh pool.
    rng_b = pool_b.stream("loot_drops")
    expected_drops = []
    for entry in table.entries:
        if rng_b.random() < entry.base_rate:
            expected_drops.append(entry.item_id)
    assert [d.item_id for d in drops_a] == expected_drops


def test_custom_stream_name_yields_independent_results():
    """Loot rolls on a custom stream don't share entropy with the
    default loot_drops stream."""
    table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("a", 0.5, Rarity.COMMON),
        ),
    )
    pool = RngPool(world_seed=999)

    d_default = []
    d_custom = []
    pool_default = RngPool(world_seed=999)
    pool_custom = RngPool(world_seed=999)
    for _ in range(20):
        d_default.append(
            roll_drops(table=table, rng_pool=pool_default)
        )
        d_custom.append(
            roll_drops(table=table, rng_pool=pool_custom,
                       stream_name="weather"),
        )
    # Different streams from same world seed -> different sequences.
    assert d_default != d_custom


# -- composition ------------------------------------------------------

def test_full_lifecycle_kill_a_goblin_smithy():
    """Composition smoke: roll the goblin smithy table 100 times
    with TH II, verify shape of histogram."""
    table = _sample_table()
    pool = RngPool(world_seed=0xC0FFEE)
    common_count = 0
    rare_count = 0
    for _ in range(100):
        drops = roll_drops(table=table, rng_pool=pool, th_level=2)
        for d in drops:
            if d.rarity == Rarity.COMMON:
                common_count += 1
            elif d.rarity == Rarity.RARE:
                rare_count += 1
    # 95% common * 1.10 -> expect ~95+ commons across 100 rolls.
    assert common_count > 80
    # 5% rare * 1.40 = 7% -> expect a handful, not zero.
    assert rare_count >= 1
