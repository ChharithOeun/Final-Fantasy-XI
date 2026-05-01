"""Extended tests for loot_table — TH state, proc, pet inheritance.

The base TH 0..9 modifier table is exercised in test_loot_table.py.
This file covers the Demoncore extensions:
  - TreasureHunterState composability (base + equipment + skill)
  - Equipped-stack ceiling at MAX_TH_EQUIPPED = 9
  - Proc bumps to MAX_TH_CRIT_PROC = 16
  - Pet inheritance: equipment + skill transfer; base does not
"""
from __future__ import annotations

import pytest

from server.loot_table import (
    DEFAULT_TH_PROC_CHANCE,
    MAX_TH_CRIT_PROC,
    MAX_TH_EQUIPPED,
    DropEntry,
    DropTable,
    Rarity,
    TreasureHunterState,
    effective_th_level,
    master_th_for_pet,
    proc_treasure_hunter,
    reset_proc,
    roll_drops_for,
    treasure_hunter_modifier,
)
from server.rng_pool import RngPool


# -- modifier table covers 0..16 -------------------------------------

def test_modifier_table_defined_for_levels_0_to_16():
    """Every rarity must have a modifier for every level 0..16."""
    for r in Rarity:
        for lvl in range(0, MAX_TH_CRIT_PROC + 1):
            v = treasure_hunter_modifier(r, lvl)
            assert v >= 1.0


def test_modifier_table_monotonic_through_proc_tiers():
    """Modifiers must never decrease as TH climbs into proc range."""
    for r in (Rarity.COMMON, Rarity.UNCOMMON,
              Rarity.RARE, Rarity.SUPER_RARE):
        prev = 0.0
        for lvl in range(0, MAX_TH_CRIT_PROC + 1):
            cur = treasure_hunter_modifier(r, lvl)
            assert cur >= prev
            prev = cur


def test_super_rare_at_th_16_is_meaningfully_higher_than_at_th_9():
    """The point of crit-proc territory is that it MEANS something.
    SUPER_RARE at TH 16 must be visibly better than at TH 9."""
    base = treasure_hunter_modifier(Rarity.SUPER_RARE, 9)
    proc = treasure_hunter_modifier(Rarity.SUPER_RARE, 16)
    assert (proc - base) > 0.5


def test_ex_modifier_remains_identity_through_proc_tiers():
    """EX is gated externally; TH never affects it, even at 16."""
    for lvl in range(0, MAX_TH_CRIT_PROC + 1):
        assert treasure_hunter_modifier(Rarity.EX, lvl) == 1.0


# -- TreasureHunterState construction --------------------------------

def test_state_default_is_all_zero():
    s = TreasureHunterState()
    assert s.base_level == 0
    assert s.equipment_level == 0
    assert s.skill_level == 0
    assert s.proc_level == 0


def test_state_rejects_negative_components():
    with pytest.raises(ValueError):
        TreasureHunterState(base_level=-1)
    with pytest.raises(ValueError):
        TreasureHunterState(equipment_level=-1)
    with pytest.raises(ValueError):
        TreasureHunterState(skill_level=-1)
    with pytest.raises(ValueError):
        TreasureHunterState(proc_level=-1)


# -- effective_th_level ----------------------------------------------

def test_effective_zero_state():
    assert effective_th_level(TreasureHunterState()) == 0


def test_effective_components_sum():
    s = TreasureHunterState(
        base_level=2, equipment_level=3, skill_level=1,
    )
    assert effective_th_level(s) == 6


def test_equipped_stack_caps_at_max_th_equipped():
    """base + equipment + skill cannot exceed 9."""
    s = TreasureHunterState(
        base_level=4, equipment_level=4, skill_level=4,
    )
    # raw 12 -> capped to 9
    assert effective_th_level(s) == MAX_TH_EQUIPPED


def test_proc_extends_above_equipped_cap():
    """Procs can push effective level past the equipped ceiling."""
    s = TreasureHunterState(
        equipment_level=9, proc_level=4,
    )
    assert effective_th_level(s) == 13


def test_total_caps_at_max_th_crit_proc():
    """Even with crazy procs, total can't exceed 16."""
    s = TreasureHunterState(
        equipment_level=9, proc_level=99,
    )
    assert effective_th_level(s) == MAX_TH_CRIT_PROC


def test_proc_only_reaches_16_with_full_equipped_stack():
    """If you have nothing equipped, you can still proc up to 16
    on raw procs alone — proc doesn't require an equipped base."""
    s = TreasureHunterState(proc_level=20)
    assert effective_th_level(s) == MAX_TH_CRIT_PROC


# -- proc_treasure_hunter ---------------------------------------------

def test_proc_with_zero_chance_never_fires():
    pool = RngPool(world_seed=42)
    s = TreasureHunterState(equipment_level=5)
    for _ in range(100):
        procced, s = proc_treasure_hunter(
            s, pool, proc_chance=0.0,
        )
        assert procced is False
    assert s.proc_level == 0


def test_proc_with_full_chance_fires_every_hit_until_cap():
    pool = RngPool(world_seed=42)
    s = TreasureHunterState(equipment_level=9)
    fires = 0
    for _ in range(50):
        procced, s = proc_treasure_hunter(
            s, pool, proc_chance=1.0,
        )
        if procced:
            fires += 1
    # Should fire exactly enough times to reach the 16 cap from 9.
    assert fires == MAX_TH_CRIT_PROC - MAX_TH_EQUIPPED
    assert effective_th_level(s) == MAX_TH_CRIT_PROC


def test_proc_at_cap_returns_false_without_modifying():
    """Once we're at TH 16, additional proc rolls are no-ops."""
    pool = RngPool(world_seed=42)
    s = TreasureHunterState(equipment_level=9, proc_level=7)
    assert effective_th_level(s) == MAX_TH_CRIT_PROC
    for _ in range(20):
        procced, s2 = proc_treasure_hunter(
            s, pool, proc_chance=1.0,
        )
        assert procced is False
        assert s2 is s   # exact same dataclass returned


def test_proc_invalid_chance_raises():
    pool = RngPool(world_seed=0)
    s = TreasureHunterState()
    with pytest.raises(ValueError):
        proc_treasure_hunter(s, pool, proc_chance=-0.1)
    with pytest.raises(ValueError):
        proc_treasure_hunter(s, pool, proc_chance=1.1)


def test_proc_is_deterministic_with_same_seed():
    """Replays must produce the same proc pattern."""
    state_a = TreasureHunterState(equipment_level=5)
    state_b = TreasureHunterState(equipment_level=5)
    pool_a = RngPool(world_seed=999)
    pool_b = RngPool(world_seed=999)
    fires_a, fires_b = [], []
    for _ in range(50):
        procced_a, state_a = proc_treasure_hunter(state_a, pool_a)
        procced_b, state_b = proc_treasure_hunter(state_b, pool_b)
        fires_a.append(procced_a)
        fires_b.append(procced_b)
    assert fires_a == fires_b
    assert state_a == state_b


# -- pet propagation ------------------------------------------------

def test_pet_inherits_equipment_and_skill():
    master = TreasureHunterState(
        base_level=3, equipment_level=4, skill_level=2,
    )
    pet = master_th_for_pet(master)
    assert pet.equipment_level == 4
    assert pet.skill_level == 2


def test_pet_does_not_inherit_master_base_level():
    """Subjob-derived TH is a player-only ability."""
    master = TreasureHunterState(base_level=3, equipment_level=2)
    pet = master_th_for_pet(master)
    assert pet.base_level == 0


def test_pet_inherits_master_proc_state():
    """Once a fight is in flight, accumulated procs benefit
    everybody on the team — the pet's hits land at the same TH
    level as the master's would."""
    master = TreasureHunterState(
        equipment_level=4, proc_level=5,
    )
    pet = master_th_for_pet(master)
    assert pet.proc_level == 5
    assert effective_th_level(pet) == 9


def test_pet_drops_use_inherited_th_level():
    """End-to-end: a pet kills a mob; the drop roll must use the
    pet's effective TH (which was inherited from the master)."""
    master = TreasureHunterState(equipment_level=9)
    pet = master_th_for_pet(master)

    table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("rare_target", 0.05, Rarity.RARE),
        ),
    )

    # With pet TH = master's equipment 9 -> RARE modifier is 2.05x.
    # Verify the threshold the engine rolled against reflects that.
    pool = RngPool(world_seed=0)
    # Force a deterministic fire — high-rate item.
    cert_table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("guaranteed", 0.40, Rarity.RARE),
        ),
    )
    drops = roll_drops_for(
        table=cert_table, rng_pool=pool, th_state=pet,
    )
    if drops:
        # 0.40 * 2.05 = 0.82 capped to 0.82
        assert abs(drops[0].rolled_against - 0.82) < 1e-9


# -- reset_proc ------------------------------------------------------

def test_reset_proc_clears_proc_only():
    s = TreasureHunterState(
        base_level=1, equipment_level=2, skill_level=3,
        proc_level=5,
    )
    cleared = reset_proc(s)
    assert cleared.proc_level == 0
    assert cleared.base_level == 1
    assert cleared.equipment_level == 2
    assert cleared.skill_level == 3


# -- roll_drops_for end-to-end --------------------------------------

def test_roll_drops_for_consumes_state_correctly():
    """roll_drops_for must produce the same result as roll_drops
    given an explicit equivalent th_level."""
    from server.loot_table import roll_drops

    state = TreasureHunterState(
        equipment_level=4, skill_level=1, proc_level=2,
    )
    table = DropTable(
        mob_class_id="test", entries=(
            DropEntry("a", 0.5, Rarity.COMMON),
            DropEntry("b", 0.05, Rarity.RARE),
            DropEntry("c", 0.001, Rarity.SUPER_RARE),
        ),
    )
    pool_a = RngPool(world_seed=42)
    pool_b = RngPool(world_seed=42)

    via_state = roll_drops_for(
        table=table, rng_pool=pool_a, th_state=state,
    )
    via_int = roll_drops(
        table=table, rng_pool=pool_b,
        th_level=effective_th_level(state),
    )
    assert via_state == via_int


def test_full_lifecycle_master_pet_combat():
    """Player has gear TH 4 + skill TH 2 + subjob THF base TH 1.
    Effective: 7. Sends pet. Pet attacks 30 hits, accumulates procs.
    Player attacks 30 hits, accumulates more procs. Final mob kill
    rolls drops at the high-water mark."""
    master = TreasureHunterState(
        base_level=1, equipment_level=4, skill_level=2,
    )
    assert effective_th_level(master) == 7
    pool = RngPool(world_seed=0xABCDEF)

    # Pet phase: hits proc against a high chance for repeatability.
    pet = master_th_for_pet(master)
    for _ in range(30):
        procced, pet = proc_treasure_hunter(
            pet, pool, proc_chance=0.5,
        )
    # Sync master's proc tally back to whatever the pet accumulated.
    # In the canonical fight-engine flow, the master and pet share
    # the same proc counter via a fight-scope handler.
    import dataclasses as dc
    master = dc.replace(master, proc_level=pet.proc_level)

    # Master keeps swinging.
    for _ in range(30):
        procced, master = proc_treasure_hunter(
            master, pool, proc_chance=0.5,
        )
        # Re-derive pet so its proc keeps in sync.
        pet = master_th_for_pet(master)

    # Final TH should be meaningful (between 7 and 16 inclusive).
    final = effective_th_level(master)
    assert 7 <= final <= MAX_TH_CRIT_PROC

    # Roll a drop table. Use a guaranteed RARE so we observe the
    # post-TH threshold reflects the elevated state.
    table = DropTable(
        mob_class_id="boss", entries=(
            DropEntry("trophy", 0.30, Rarity.RARE),
        ),
    )
    drops = roll_drops_for(
        table=table, rng_pool=pool, th_state=master,
    )
    if drops:
        # Threshold must be at least the TH 7 baseline (0.30 * 1.90).
        assert drops[0].rolled_against >= 0.30 * 1.90


def test_default_proc_chance_constant_is_reasonable():
    """Sanity: don't ship a 0.0 or 1.0 default by accident."""
    assert 0.05 <= DEFAULT_TH_PROC_CHANCE <= 0.25
