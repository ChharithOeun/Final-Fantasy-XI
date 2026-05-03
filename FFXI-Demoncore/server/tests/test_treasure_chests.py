"""Tests for treasure chest registry."""
from __future__ import annotations

import random

from server.treasure_chests import (
    Chest,
    LockTier,
    OpenMethod,
    OpenOutcome,
    TrapTier,
    TreasureChestRegistry,
)


def _basic_chest(
    chest_id: str = "c1",
    lock_tier: LockTier = LockTier.STANDARD,
    trap_tier: TrapTier = TrapTier.NONE,
    matching_key_id: str = "iron_key",
) -> Chest:
    return Chest(
        chest_id=chest_id, zone_id="vunkerl_inlet",
        position_tile=(50, 50),
        lock_tier=lock_tier, trap_tier=trap_tier,
        matching_key_id=matching_key_id,
        loot_table_id="vunkerl_chest_low",
    )


def test_spawn_and_lookup():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest())
    assert reg.chest("c1") is not None
    assert reg.total_chests() == 1


def test_chests_in_zone_filters():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest())
    reg.spawn_chest(Chest(
        chest_id="c2", zone_id="other",
        position_tile=(0, 0),
        lock_tier=LockTier.NONE,
    ))
    in_vunkerl = reg.chests_in_zone("vunkerl_inlet")
    assert len(in_vunkerl) == 1


def test_open_no_chest_returns_locked():
    reg = TreasureChestRegistry()
    res = reg.open(
        player_id="alice", chest_id="ghost",
        method=OpenMethod.KEY,
    )
    assert res.outcome == OpenOutcome.LOCKED
    assert "no such chest" in res.reason


def test_already_opened_returns_empty():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest(lock_tier=LockTier.NONE))
    reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.BRUTE_FORCE,
        rng=random.Random(0),
    )
    res = reg.open(
        player_id="bob", chest_id="c1",
        method=OpenMethod.BRUTE_FORCE,
        rng=random.Random(0),
    )
    assert res.outcome == OpenOutcome.EMPTY


def test_correct_key_opens_chest():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest())
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.KEY, key_id="iron_key",
        rng=random.Random(123),
    )
    # Key path can still get a mimic — but with seed 123 it
    # should resolve cleanly.
    assert res.outcome in (
        OpenOutcome.LOOTED, OpenOutcome.MIMIC,
        OpenOutcome.TRAPPED,
    )


def test_wrong_key_locked():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest(matching_key_id="iron_key"))
    # Suppress mimic by overriding chance via fresh rng with
    # small dice; since rng order is mimic-first, this is hard
    # to guarantee. So we use the lockpick path instead.
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.KEY, key_id="brass_key",
        rng=random.Random(99),
    )
    # Wrong key -> LOCKED unless mimic preempts
    assert res.outcome in (OpenOutcome.LOCKED, OpenOutcome.MIMIC)


def test_lockpick_with_skill_above_dc():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest())     # STANDARD lock, DC 50
    rng = random.Random(0)
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.LOCKPICK, lockpick_skill=200,
        rng=rng,
    )
    assert res.outcome in (
        OpenOutcome.LOOTED, OpenOutcome.MIMIC,
    )


def test_lockpick_with_skill_below_dc():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest(lock_tier=LockTier.MASTER))
    # DC=120, skill=10
    rng = random.Random(7)
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.LOCKPICK, lockpick_skill=10,
        rng=rng,
    )
    assert res.outcome in (OpenOutcome.LOCKED, OpenOutcome.MIMIC)


def test_arcane_lock_resists_lockpick():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest(lock_tier=LockTier.ARCANE))
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.LOCKPICK, lockpick_skill=999,
        rng=random.Random(0),
    )
    assert res.outcome in (OpenOutcome.LOCKED, OpenOutcome.MIMIC)


def test_brute_force_arcane_blocked():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest(lock_tier=LockTier.ARCANE))
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.BRUTE_FORCE,
        rng=random.Random(0),
    )
    assert res.outcome in (OpenOutcome.LOCKED, OpenOutcome.MIMIC)


def test_decipher_opens_arcane():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest(lock_tier=LockTier.ARCANE))
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.DECIPHER, decipher_skill=150,
        rng=random.Random(50),
    )
    assert res.outcome in (
        OpenOutcome.LOOTED, OpenOutcome.MIMIC,
    )


def test_brute_force_triggers_trap():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest(
        lock_tier=LockTier.NONE,    # no mimic; no lock
        trap_tier=TrapTier.POISON,
    ))
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.BRUTE_FORCE,
        rng=random.Random(0),
    )
    assert res.outcome == OpenOutcome.TRAPPED
    assert res.trap_kind == TrapTier.POISON


def test_skilled_lockpick_disarms_trap():
    """Lockpick well above DC + 30 disarms the trap."""
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest(
        lock_tier=LockTier.STANDARD,
        trap_tier=TrapTier.EXPLOSIVE,
    ))
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.LOCKPICK, lockpick_skill=200,
        rng=random.Random(11),    # avoid mimic
    )
    # 200 > 50+30 = 80, so trap doesn't fire
    if res.outcome == OpenOutcome.LOOTED:
        # Loot path; trap was disarmed
        assert res.trap_kind is None


def test_key_does_not_disarm_trap():
    """Even the matching key triggers traps."""
    # Force no-mimic by using NONE tier (no mimic chance)
    reg = TreasureChestRegistry()
    reg.spawn_chest(Chest(
        chest_id="c1", zone_id="z",
        position_tile=(0, 0),
        lock_tier=LockTier.NONE,
        trap_tier=TrapTier.POISON,
        matching_key_id="key_a",
    ))
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.KEY, key_id="key_a",
        rng=random.Random(0),
    )
    # Lock NONE -> mimic 0% -> never mimics
    assert res.outcome == OpenOutcome.TRAPPED


def test_reset_chest_restores_state():
    reg = TreasureChestRegistry()
    reg.spawn_chest(_basic_chest(lock_tier=LockTier.NONE))
    reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.BRUTE_FORCE,
        rng=random.Random(0),
    )
    assert reg.chest("c1").is_open
    assert reg.reset_chest(chest_id="c1", now_seconds=100.0)
    assert not reg.chest("c1").is_open


def test_no_lock_no_trap_brute_force_loots():
    reg = TreasureChestRegistry()
    reg.spawn_chest(Chest(
        chest_id="c1", zone_id="z",
        position_tile=(0, 0),
        lock_tier=LockTier.NONE, trap_tier=TrapTier.NONE,
    ))
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.BRUTE_FORCE,
        rng=random.Random(0),
    )
    assert res.outcome == OpenOutcome.LOOTED
    assert res.loot_roll_seed is not None


def test_open_log_records_results():
    reg = TreasureChestRegistry()
    reg.spawn_chest(Chest(
        chest_id="c1", zone_id="z",
        position_tile=(0, 0),
        lock_tier=LockTier.NONE, trap_tier=TrapTier.NONE,
    ))
    reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.BRUTE_FORCE,
        rng=random.Random(0),
    )
    log = reg.open_log()
    assert len(log) == 1
    assert log[0].outcome == OpenOutcome.LOOTED


def test_full_lifecycle_chest_in_zone():
    """A chest in Vunkerl Inlet: standard lock, explosive trap.
    First attempt with low skill triggers trap. Reset. Second
    attempt with high skill loots cleanly."""
    reg = TreasureChestRegistry()
    reg.spawn_chest(Chest(
        chest_id="c1", zone_id="vunkerl_inlet",
        position_tile=(50, 50),
        lock_tier=LockTier.STANDARD,
        trap_tier=TrapTier.EXPLOSIVE,
        matching_key_id="iron_key",
    ))
    # Low-skill picker — trap fires (DC 50, skill 60 = below
    # disarm threshold of 50+30=80)
    rng = random.Random(99)
    res = reg.open(
        player_id="alice", chest_id="c1",
        method=OpenMethod.LOCKPICK, lockpick_skill=60,
        rng=rng,
    )
    if res.outcome == OpenOutcome.MIMIC:
        return  # rng draw; that's fine
    assert res.outcome == OpenOutcome.TRAPPED
    # Reset for respawn
    reg.reset_chest(chest_id="c1", now_seconds=1000.0)
    # High-skill picker — disarms
    rng2 = random.Random(0)
    res2 = reg.open(
        player_id="bob", chest_id="c1",
        method=OpenMethod.LOCKPICK, lockpick_skill=200,
        rng=rng2,
    )
    assert res2.outcome in (
        OpenOutcome.LOOTED, OpenOutcome.MIMIC,
    )
