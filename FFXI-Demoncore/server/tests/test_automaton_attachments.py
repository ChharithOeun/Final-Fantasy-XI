"""Tests for automaton_attachments — Tomb Raid drop chain."""
from __future__ import annotations

import pytest

from server.automaton_attachments import (
    ATTACHMENT_BY_ID,
    SOURCE_MOB_ID,
    TOMB_RAID_SET,
    WHM_AUTOMATON_DROP_CHANCE,
    AttachmentInventory,
    Maneuver,
    award_drop,
    next_tomb_raid_drop,
    roll_roaming_automaton_drop,
)
from server.rng_pool import RngPool


# -- TOMB_RAID_SET integrity -----------------------------------------

def test_set_has_exactly_five_tiers():
    assert len(TOMB_RAID_SET) == 5


def test_tiers_are_ordered_one_through_five():
    assert [a.tier for a in TOMB_RAID_SET] == [1, 2, 3, 4, 5]


def test_all_attachments_are_lightning_maneuver():
    for a in TOMB_RAID_SET:
        assert a.maneuver == Maneuver.LIGHTNING


def test_all_attachments_are_rare_ex():
    for a in TOMB_RAID_SET:
        assert a.is_rare_ex is True


def test_all_attachments_are_not_craftable():
    """User requirement: Tomb Raid is drop-only, can't be crafted."""
    for a in TOMB_RAID_SET:
        assert a.is_craftable is False


def test_all_attachments_share_the_same_source_mob():
    for a in TOMB_RAID_SET:
        assert a.source_mob == SOURCE_MOB_ID


def test_attachment_ids_are_unique():
    ids = [a.attachment_id for a in TOMB_RAID_SET]
    assert len(set(ids)) == len(ids)


def test_attachment_lookup_by_id():
    for a in TOMB_RAID_SET:
        assert ATTACHMENT_BY_ID[a.attachment_id] is a


def test_drop_chance_is_one_percent():
    """User requirement: 1% drop rate."""
    assert WHM_AUTOMATON_DROP_CHANCE == 0.01


def test_each_attachment_carries_a_description():
    """Players want flavor text — pin that authors filled it in."""
    for a in TOMB_RAID_SET:
        assert a.description != ""


# -- AttachmentInventory ---------------------------------------------

def test_new_inventory_is_empty():
    inv = AttachmentInventory(player_id="alice")
    assert inv.owned == set()
    assert inv.tomb_raid_progress() == 0


def test_add_records_ownership():
    inv = AttachmentInventory(player_id="alice")
    new = inv.add("tomb_raid_1")
    assert new is True
    assert inv.has("tomb_raid_1")


def test_add_duplicate_is_noop():
    """R/EX semantics: cannot own two of the same."""
    inv = AttachmentInventory(player_id="alice")
    inv.add("tomb_raid_1")
    again = inv.add("tomb_raid_1")
    assert again is False
    assert inv.tomb_raid_progress() == 1


def test_progress_counts_only_tomb_raid_attachments():
    inv = AttachmentInventory(player_id="alice")
    inv.add("tomb_raid_1")
    inv.add("tomb_raid_3")
    inv.add("some_other_attachment")
    assert inv.tomb_raid_progress() == 2


# -- next_tomb_raid_drop --------------------------------------------

def test_empty_inventory_needs_tier_one_first():
    inv = AttachmentInventory(player_id="alice")
    nxt = next_tomb_raid_drop(inv)
    assert nxt is not None
    assert nxt.tier == 1
    assert nxt.attachment_id == "tomb_raid_1"


def test_after_tier_one_owned_next_is_tier_two():
    inv = AttachmentInventory(player_id="alice")
    inv.add("tomb_raid_1")
    nxt = next_tomb_raid_drop(inv)
    assert nxt is not None
    assert nxt.tier == 2


def test_in_order_progression_through_all_five():
    inv = AttachmentInventory(player_id="alice")
    expected_tiers = [1, 2, 3, 4, 5]
    for expected_tier in expected_tiers:
        nxt = next_tomb_raid_drop(inv)
        assert nxt is not None
        assert nxt.tier == expected_tier
        inv.add(nxt.attachment_id)
    # After all five owned, returns None.
    assert next_tomb_raid_drop(inv) is None


def test_skipping_a_tier_in_inventory_returns_first_missing():
    """If somehow a player has II but not I (shouldn't happen via
    the drop engine, but defensive against admin tools), the next
    drop should be tier I — the FIRST missing tier."""
    inv = AttachmentInventory(player_id="alice")
    inv.add("tomb_raid_2")
    inv.add("tomb_raid_3")
    nxt = next_tomb_raid_drop(inv)
    assert nxt is not None
    assert nxt.tier == 1


# -- roll_roaming_automaton_drop ------------------------------------

def test_drop_with_zero_chance_never_fires():
    inv = AttachmentInventory(player_id="alice")
    pool = RngPool(world_seed=0)
    for _ in range(100):
        result = roll_roaming_automaton_drop(
            inventory=inv, rng_pool=pool, drop_chance=0.0,
        )
        assert result is None


def test_drop_with_full_chance_always_fires_when_player_needs_one():
    inv = AttachmentInventory(player_id="alice")
    pool = RngPool(world_seed=0)
    result = roll_roaming_automaton_drop(
        inventory=inv, rng_pool=pool, drop_chance=1.0,
    )
    assert result is not None
    assert result.tier == 1


def test_drop_returns_none_when_inventory_is_complete():
    """A player who owns all 5 never sees another drop, even at
    100% chance."""
    inv = AttachmentInventory(player_id="alice")
    for a in TOMB_RAID_SET:
        inv.add(a.attachment_id)
    pool = RngPool(world_seed=0)
    for _ in range(100):
        result = roll_roaming_automaton_drop(
            inventory=inv, rng_pool=pool, drop_chance=1.0,
        )
        assert result is None


def test_drop_invalid_chance_raises():
    inv = AttachmentInventory(player_id="alice")
    pool = RngPool(world_seed=0)
    with pytest.raises(ValueError):
        roll_roaming_automaton_drop(
            inventory=inv, rng_pool=pool, drop_chance=-0.01,
        )
    with pytest.raises(ValueError):
        roll_roaming_automaton_drop(
            inventory=inv, rng_pool=pool, drop_chance=1.5,
        )


def test_drop_is_deterministic_with_same_seed():
    """Replay must produce the same sequence of fires/misses."""
    pool_a = RngPool(world_seed=42)
    pool_b = RngPool(world_seed=42)
    inv_a = AttachmentInventory(player_id="alice")
    inv_b = AttachmentInventory(player_id="alice")
    drops_a = []
    drops_b = []
    for _ in range(200):
        a = roll_roaming_automaton_drop(
            inventory=inv_a, rng_pool=pool_a,
        )
        b = roll_roaming_automaton_drop(
            inventory=inv_b, rng_pool=pool_b,
        )
        drops_a.append(a)
        drops_b.append(b)
    assert drops_a == drops_b


def test_drop_caller_only_gets_one_attachment_per_call():
    """A single call to roll_roaming_automaton_drop returns AT
    MOST one attachment — never two. This is the per-kill cap."""
    inv = AttachmentInventory(player_id="alice")
    pool = RngPool(world_seed=0)
    result = roll_roaming_automaton_drop(
        inventory=inv, rng_pool=pool, drop_chance=1.0,
    )
    # API returns Optional[Attachment] — single instance, never a list.
    assert result is None or hasattr(result, "attachment_id")


def test_award_drop_adds_to_inventory():
    inv = AttachmentInventory(player_id="alice")
    att = TOMB_RAID_SET[0]
    awarded = award_drop(inventory=inv, attachment=att)
    assert awarded is True
    assert inv.has(att.attachment_id)


def test_award_drop_duplicate_is_noop():
    inv = AttachmentInventory(player_id="alice")
    att = TOMB_RAID_SET[0]
    award_drop(inventory=inv, attachment=att)
    again = award_drop(inventory=inv, attachment=att)
    assert again is False


# -- composition / lifecycle ----------------------------------------

def test_full_lifecycle_grind_through_all_five_tiers():
    """End-to-end: hunter grinds the roaming WHM automaton with
    100% drop chance for the test, expecting to receive tiers in
    order I, II, III, IV, V across 5 successive kills, and nothing
    on the 6th kill."""
    inv = AttachmentInventory(player_id="alice")
    pool = RngPool(world_seed=0xDEADBEEF)

    received = []
    for _ in range(6):
        drop = roll_roaming_automaton_drop(
            inventory=inv, rng_pool=pool, drop_chance=1.0,
        )
        if drop is not None:
            award_drop(inventory=inv, attachment=drop)
            received.append(drop.attachment_id)
        else:
            received.append(None)

    assert received == [
        "tomb_raid_1",
        "tomb_raid_2",
        "tomb_raid_3",
        "tomb_raid_4",
        "tomb_raid_5",
        None,                # already complete
    ]
    assert inv.tomb_raid_progress() == 5


def test_realistic_one_percent_drop_rate_over_many_kills():
    """Over a large number of kills at 1%, alice should land at
    least one drop. Use a fixed seed so the test is deterministic."""
    inv = AttachmentInventory(player_id="alice")
    pool = RngPool(world_seed=12345)

    drops_received = 0
    # 500 kills at 1% expected ~5 drops; pin a deterministic count.
    for _ in range(500):
        drop = roll_roaming_automaton_drop(
            inventory=inv, rng_pool=pool,
        )
        if drop is not None:
            award_drop(inventory=inv, attachment=drop)
            drops_received += 1

    # Sanity: at 1% over 500 kills we should land at least 1 drop
    # under most seeds. Pin against this specific seed.
    assert drops_received >= 1


def test_realistic_kill_with_fresh_inventory_uses_loot_drops_stream():
    """The stream defaults to STREAM_LOOT_DROPS so this drop is
    deterministic from the world seed alongside other loot."""
    pool = RngPool(world_seed=999)
    inv_a = AttachmentInventory(player_id="alice")
    drops_a = [
        roll_roaming_automaton_drop(
            inventory=inv_a, rng_pool=pool, drop_chance=0.5,
        )
        for _ in range(20)
    ]

    pool_b = RngPool(world_seed=999)
    inv_b = AttachmentInventory(player_id="alice")
    drops_b = []
    for _ in range(20):
        # Manual draw on loot_drops stream to verify the stream
        # being used is "loot_drops".
        d = roll_roaming_automaton_drop(
            inventory=inv_b, rng_pool=pool_b, drop_chance=0.5,
            stream_name="loot_drops",
        )
        drops_b.append(d)

    assert [None if x is None else x.attachment_id for x in drops_a] == \
           [None if x is None else x.attachment_id for x in drops_b]
