"""Tests for automaton_attachments — Tomb Raid drop chain."""
from __future__ import annotations

import pytest

from server.automaton_attachments import (
    ATTACHMENT_BY_ID,
    SOURCE_MOB_ID,
    TH_PROC_CHANCE_PER_LIGHTNING_PER_PIECE,
    TOMB_RAID_SET,
    WHM_AUTOMATON_DROP_CHANCE,
    AttachmentInventory,
    Maneuver,
    award_drop,
    equipment_level_with_attachments,
    lightning_proc_chance_bonus,
    next_tomb_raid_drop,
    proc_with_attachments,
    roll_roaming_automaton_drop,
    tomb_raid_th_bonus,
)
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
    roll_drops_for,
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


# -- Tomb Raid TH bonus -------------------------------------------

def test_tomb_raid_th_bonus_empty_is_zero():
    assert tomb_raid_th_bonus(()) == 0


def test_tomb_raid_th_bonus_tier_one_only():
    """Tomb Raid I = +1 TH."""
    assert tomb_raid_th_bonus((TOMB_RAID_SET[0],)) == 1


def test_tomb_raid_th_bonus_tier_five_only():
    """Tomb Raid V = +5 TH."""
    assert tomb_raid_th_bonus((TOMB_RAID_SET[4],)) == 5


def test_tomb_raid_th_bonus_full_set():
    """All 5 equipped: 1 + 2 + 3 + 4 + 5 = 15."""
    assert tomb_raid_th_bonus(TOMB_RAID_SET) == 15


def test_tomb_raid_th_bonus_partial_set():
    """Tomb Raid IV + V = 4 + 5 = 9 (the equipped cap)."""
    pieces = (TOMB_RAID_SET[3], TOMB_RAID_SET[4])
    assert tomb_raid_th_bonus(pieces) == 9


def test_tomb_raid_th_bonus_ignores_non_tomb_raid():
    """Other attachments contribute zero."""
    from server.automaton_attachments import Attachment
    decoy = Attachment(
        attachment_id="other_attachment",
        label="Random Other Attachment",
        maneuver=Maneuver.FIRE,
        tier=99,        # huge tier — but not a Tomb Raid piece
        is_rare_ex=False,
        is_craftable=True,
        source_mob="some_mob",
    )
    assert tomb_raid_th_bonus((decoy,)) == 0
    # Mixed set: only the Tomb Raid contributes.
    assert tomb_raid_th_bonus((decoy, TOMB_RAID_SET[2])) == 3


# -- equipment_level_with_attachments --------------------------------

def test_equipment_level_with_attachments_no_pieces():
    assert equipment_level_with_attachments(3, ()) == 3


def test_equipment_level_with_attachments_full_set():
    """Base gear 4 + Tomb Raid full set 15 = 19 raw (clamped at 9
    by effective_th_level downstream)."""
    raw = equipment_level_with_attachments(4, TOMB_RAID_SET)
    assert raw == 19


def test_equipment_level_negative_base_raises():
    with pytest.raises(ValueError):
        equipment_level_with_attachments(-1, TOMB_RAID_SET)


def test_th_state_with_full_tomb_raid_clamps_at_nine():
    """A player with 0 base, 0 skill, but full Tomb Raid set
    equipped (raw +15) should resolve to TH 9 effective when no
    procs have fired."""
    state = TreasureHunterState(
        equipment_level=equipment_level_with_attachments(
            0, TOMB_RAID_SET,
        ),
    )
    assert effective_th_level(state) == MAX_TH_EQUIPPED


# -- lightning_proc_chance_bonus -------------------------------------

def test_proc_chance_bonus_no_pieces():
    assert lightning_proc_chance_bonus(
        (), lightning_maneuvers_active=3,
    ) == 0.0


def test_proc_chance_bonus_no_maneuvers():
    assert lightning_proc_chance_bonus(
        TOMB_RAID_SET, lightning_maneuvers_active=0,
    ) == 0.0


def test_proc_chance_bonus_one_piece_one_maneuver():
    """1 piece × 1 maneuver × 0.01 = 0.01."""
    assert lightning_proc_chance_bonus(
        (TOMB_RAID_SET[0],), lightning_maneuvers_active=1,
    ) == 0.01


def test_proc_chance_bonus_full_set_three_maneuvers():
    """5 pieces × 3 maneuvers × 0.01 = 0.15 (15%)."""
    assert lightning_proc_chance_bonus(
        TOMB_RAID_SET, lightning_maneuvers_active=3,
    ) == 0.15


def test_proc_chance_bonus_constant_is_one_percent():
    assert TH_PROC_CHANCE_PER_LIGHTNING_PER_PIECE == 0.01


def test_proc_chance_bonus_negative_maneuvers_raises():
    with pytest.raises(ValueError):
        lightning_proc_chance_bonus(
            TOMB_RAID_SET, lightning_maneuvers_active=-1,
        )


def test_proc_chance_bonus_ignores_non_tomb_raid_attachments():
    from server.automaton_attachments import Attachment
    decoy = Attachment(
        attachment_id="other",
        label="Other",
        maneuver=Maneuver.LIGHTNING,
        tier=10,
        is_rare_ex=False,
        is_craftable=True,
        source_mob="mob",
    )
    # Even with a "lightning" decoy attachment, only Tomb Raid
    # pieces count toward the proc chance bonus.
    bonus = lightning_proc_chance_bonus(
        (decoy,), lightning_maneuvers_active=3,
    )
    assert bonus == 0.0


# -- proc_with_attachments -------------------------------------------

def test_proc_with_attachments_zero_bonus_matches_default():
    """No pieces, no maneuvers: same as proc_treasure_hunter at
    default chance."""
    pool_a = RngPool(world_seed=0)
    pool_b = RngPool(world_seed=0)
    s = TreasureHunterState(equipment_level=5)

    fires_a = []
    fires_b = []
    state_a = state_b = s
    for _ in range(50):
        from server.loot_table import proc_treasure_hunter
        a, state_a = proc_treasure_hunter(state_a, pool_a)
        b, state_b = proc_with_attachments(
            state_b, pool_b,
            equipped=(),
            lightning_maneuvers_active=0,
        )
        fires_a.append(a)
        fires_b.append(b)
    assert fires_a == fires_b


def test_proc_with_attachments_high_bonus_clamps_at_one():
    """Wild values (8 maneuvers, full Tomb Raid + base chance) would
    sum past 1.0; the wrapper clamps so internal proc never breaks."""
    pool = RngPool(world_seed=0)
    s = TreasureHunterState(equipment_level=9)
    # 5 pieces × 8 maneuvers × 0.01 = 0.40, plus base 0.10 = 0.50
    # That's not above 1.0 yet — push it harder.
    procced, _ = proc_with_attachments(
        s, pool,
        equipped=TOMB_RAID_SET,
        lightning_maneuvers_active=200,
        base_proc_chance=0.5,
    )
    # With effectively 100% proc, it must land.
    assert procced is True


def test_proc_with_attachments_lightning_bonus_increases_proc_rate():
    """Statistical sanity: with full Tomb Raid + 3 lightning
    maneuvers, total chance = 0.10 + 0.15 = 0.25; without bonuses
    it's 0.10. Compare deterministic seeded counts."""
    pool_no_bonus = RngPool(world_seed=12345)
    pool_with_bonus = RngPool(world_seed=12345)
    s_no = TreasureHunterState()
    s_yes = TreasureHunterState()

    fires_no = 0
    fires_yes = 0
    for _ in range(100):
        a, s_no = proc_with_attachments(
            s_no, pool_no_bonus,
            equipped=(),
            lightning_maneuvers_active=0,
        )
        b, s_yes = proc_with_attachments(
            s_yes, pool_with_bonus,
            equipped=TOMB_RAID_SET,
            lightning_maneuvers_active=3,
        )
        if a:
            fires_no += 1
        if b:
            fires_yes += 1
        # Reset proc level so we can keep firing past 16.
        from server.loot_table import reset_proc
        s_no = reset_proc(s_no)
        s_yes = reset_proc(s_yes)
    assert fires_yes > fires_no


# -- composition with loot_table -------------------------------------

def test_full_lifecycle_pup_with_full_tomb_raid_drops_a_super_rare():
    """End-to-end: PUP master with full Tomb Raid set, automaton
    has 3 lightning maneuvers up. Master is the killer; the pet
    inherits master's TH state. Procs accumulate during a long
    fight; final drop roll on a SUPER_RARE benefits."""
    # Master starts with 0 equipped (gear), but the attachments
    # contribute +15 raw -> capped at 9 effective.
    master_equip = equipment_level_with_attachments(0, TOMB_RAID_SET)
    master = TreasureHunterState(
        base_level=1,                  # subjob THF
        equipment_level=master_equip,  # 15 raw, clamps at 9
        skill_level=0,
    )
    assert effective_th_level(master) == MAX_TH_EQUIPPED

    pet = master_th_for_pet(master)
    pool = RngPool(world_seed=0xCAFEBABE)

    # 50 hit fight; pet's hits proc TH with the lightning bonus.
    for _ in range(50):
        procced, pet = proc_with_attachments(
            pet, pool,
            equipped=TOMB_RAID_SET,
            lightning_maneuvers_active=3,
        )

    # Sync proc back to master (canonical fight-engine flow).
    import dataclasses as dc
    master = dc.replace(master, proc_level=pet.proc_level)
    final_th = effective_th_level(master)
    assert final_th >= MAX_TH_EQUIPPED   # baseline at minimum

    # Drop roll on a SUPER_RARE table.
    table = DropTable(
        mob_class_id="boss", entries=(
            DropEntry("kraken_club", 0.02, Rarity.SUPER_RARE),
        ),
    )
    drops = roll_drops_for(
        table=table, rng_pool=pool, th_state=master,
    )
    if drops:
        # Threshold should reflect at least the TH 9 modifier
        # (2.30x for super_rare). 0.02 * 2.30 = 0.046 minimum.
        assert drops[0].rolled_against >= 0.045


def test_full_lifecycle_partial_tomb_raid_lightning_proc_chain():
    """A player with Tomb Raid I, II, III equipped + 2 lightning
    maneuvers active should see meaningful proc chance:
    base 0.10 + (3 pieces × 2 maneuvers × 0.01) = 0.16."""
    equipped = (TOMB_RAID_SET[0], TOMB_RAID_SET[1], TOMB_RAID_SET[2])
    bonus = lightning_proc_chance_bonus(
        equipped, lightning_maneuvers_active=2,
    )
    assert bonus == 0.06     # 3 * 2 * 0.01
    total = DEFAULT_TH_PROC_CHANCE + bonus
    assert abs(total - 0.16) < 1e-9
