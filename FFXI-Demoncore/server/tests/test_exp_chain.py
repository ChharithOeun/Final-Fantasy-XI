"""Tests for exp_chain — chain bonus, level sync, party share."""
from __future__ import annotations

import pytest

from server.exp_chain import (
    BuffSource,
    LevelSync,
    XpBuff,
    buffs_total_multiplier,
    chain_bonus_multiplier,
    chain_window_seconds,
    compute_xp_award,
    is_chain_alive,
    next_chain_count,
)


# -- chain bonus table -----------------------------------------------

def test_chain_zero_and_one_baseline():
    assert chain_bonus_multiplier(0) == 1.00
    assert chain_bonus_multiplier(1) == 1.00


def test_chain_two_three_four_progression():
    assert chain_bonus_multiplier(2) > 1.00
    assert chain_bonus_multiplier(3) > chain_bonus_multiplier(2)
    assert chain_bonus_multiplier(4) > chain_bonus_multiplier(3)


def test_chain_caps_at_five():
    """Chain 5+ should plateau at the same cap value."""
    cap = chain_bonus_multiplier(5)
    assert chain_bonus_multiplier(6) == cap
    assert chain_bonus_multiplier(99) == cap


def test_chain_negative_raises():
    with pytest.raises(ValueError):
        chain_bonus_multiplier(-1)


# -- chain window scaling --------------------------------------------

def test_chain_window_solo_largest():
    assert chain_window_seconds(party_size=1) > \
           chain_window_seconds(party_size=6)


def test_chain_window_alliance_smallest():
    assert chain_window_seconds(party_size=18) < \
           chain_window_seconds(party_size=6)


def test_chain_window_clamps_to_solo_for_zero_or_negative():
    assert chain_window_seconds(party_size=0) == \
           chain_window_seconds(party_size=1)


# -- chain alive check -----------------------------------------------

def test_chain_alive_within_window():
    assert is_chain_alive(
        last_kill_tick=1000, now_tick=1010, party_size=1,
    )


def test_chain_dead_after_window():
    win = chain_window_seconds(party_size=1)
    assert not is_chain_alive(
        last_kill_tick=1000, now_tick=1000 + win, party_size=1,
    )
    assert not is_chain_alive(
        last_kill_tick=1000, now_tick=1000 + win + 1, party_size=1,
    )


def test_chain_dead_with_no_prior_kill():
    assert not is_chain_alive(
        last_kill_tick=None, now_tick=1000, party_size=1,
    )


# -- next_chain_count -----------------------------------------------

def test_next_chain_first_kill_starts_at_one():
    assert next_chain_count(
        prev_chain=0, last_kill_tick=None,
        now_tick=1000, party_size=1,
    ) == 1


def test_next_chain_increments_when_alive():
    assert next_chain_count(
        prev_chain=2, last_kill_tick=1000,
        now_tick=1010, party_size=1,
    ) == 3


def test_next_chain_resets_when_window_lapses():
    win = chain_window_seconds(party_size=1)
    assert next_chain_count(
        prev_chain=4, last_kill_tick=1000,
        now_tick=1000 + win + 5, party_size=1,
    ) == 1


# -- buff stacking ---------------------------------------------------

def test_buffs_empty_yields_one():
    assert buffs_total_multiplier(()) == 1.0


def test_buffs_single_50_pct_buff():
    b = XpBuff(source=BuffSource.EMPRESS_BAND, bonus_pct=0.5)
    assert buffs_total_multiplier((b,)) == 1.5


def test_buffs_two_50_pct_buffs_stack_additively():
    """Two +50% buffs -> +100% = 2.0x, NOT 2.25x (multiplicative)."""
    b1 = XpBuff(source=BuffSource.EMPRESS_BAND, bonus_pct=0.5)
    b2 = XpBuff(source=BuffSource.DEDICATION_RING, bonus_pct=0.5)
    assert buffs_total_multiplier((b1, b2)) == 2.0


def test_xp_buff_negative_pct_raises():
    with pytest.raises(ValueError):
        XpBuff(source=BuffSource.EMPRESS_BAND, bonus_pct=-0.1)


# -- LevelSync -------------------------------------------------------

def test_level_sync_active_when_capped_below_natural():
    sync = LevelSync(cap_level=30, natural_level=75)
    assert sync.is_active()


def test_level_sync_inactive_when_at_natural():
    sync = LevelSync(cap_level=75, natural_level=75)
    assert not sync.is_active()


def test_level_sync_inactive_when_above_natural():
    sync = LevelSync(cap_level=99, natural_level=75)
    assert not sync.is_active()


# -- compute_xp_award --------------------------------------------------

def test_solo_no_chain_no_buff_just_returns_base():
    award = compute_xp_award(
        base_xp=100, prev_chain=0,
        last_kill_tick=None, now_tick=1000, party_size=1,
    )
    assert award.final_xp == 100
    assert award.chain_count == 1
    assert award.chain_multiplier == 1.00


def test_chain_two_solo_applies_chain_bonus():
    award = compute_xp_award(
        base_xp=100, prev_chain=1,
        last_kill_tick=1000, now_tick=1010, party_size=1,
    )
    # 100 * 1.20 = 120
    assert award.chain_count == 2
    assert award.final_xp == 120


def test_chain_five_caps():
    award = compute_xp_award(
        base_xp=100, prev_chain=4,
        last_kill_tick=1000, now_tick=1010, party_size=1,
    )
    assert award.chain_count == 5
    assert award.chain_multiplier == 1.75


def test_party_of_six_divides_xp():
    award = compute_xp_award(
        base_xp=600, prev_chain=0,
        last_kill_tick=None, now_tick=1000, party_size=6,
    )
    # 600 / 6 = 100, no chain bonus -> 100
    assert award.final_xp == 100
    assert award.party_share_divisor == 6


def test_buffs_apply_after_chain_and_share():
    award = compute_xp_award(
        base_xp=600, prev_chain=1,
        last_kill_tick=1000, now_tick=1010, party_size=6,
        buffs=(XpBuff(BuffSource.EMPRESS_BAND, 0.5),),
    )
    # 600 / 6 = 100; chain 2 = 1.2 -> 120; buffs +50% -> 180
    assert award.final_xp == 180
    assert award.buffs_total == 1.5


def test_level_sync_caps_xp_when_active():
    sync = LevelSync(cap_level=30, natural_level=75)
    award = compute_xp_award(
        base_xp=400, prev_chain=0,
        last_kill_tick=None, now_tick=1000, party_size=1,
        sync=sync, sync_cap_xp=120,
    )
    # base 400 capped to 120; chain 1 -> 120
    assert award.sync_capped is True
    assert award.final_xp == 120


def test_level_sync_doesnt_apply_when_inactive():
    sync = LevelSync(cap_level=75, natural_level=75)
    award = compute_xp_award(
        base_xp=400, prev_chain=0,
        last_kill_tick=None, now_tick=1000, party_size=1,
        sync=sync, sync_cap_xp=120,
    )
    assert award.sync_capped is False
    assert award.final_xp == 400


def test_level_sync_doesnt_cap_below_base_when_base_already_lower():
    sync = LevelSync(cap_level=30, natural_level=75)
    award = compute_xp_award(
        base_xp=100, prev_chain=0,
        last_kill_tick=None, now_tick=1000, party_size=1,
        sync=sync, sync_cap_xp=120,
    )
    # Base 100 is below the 120 cap; no capping needed.
    assert award.sync_capped is False
    assert award.final_xp == 100


def test_negative_base_xp_raises():
    with pytest.raises(ValueError):
        compute_xp_award(
            base_xp=-10, prev_chain=0,
            last_kill_tick=None, now_tick=0, party_size=1,
        )


def test_zero_party_size_raises():
    with pytest.raises(ValueError):
        compute_xp_award(
            base_xp=100, prev_chain=0,
            last_kill_tick=None, now_tick=0, party_size=0,
        )


def test_chain_was_extended_property():
    award_solo = compute_xp_award(
        base_xp=100, prev_chain=0,
        last_kill_tick=None, now_tick=1000, party_size=1,
    )
    assert award_solo.chain_was_extended is False
    award_chain = compute_xp_award(
        base_xp=100, prev_chain=1,
        last_kill_tick=1000, now_tick=1010, party_size=1,
    )
    assert award_chain.chain_was_extended is True


# -- composition smoke ----------------------------------------------

def test_full_lifecycle_chain_5_party_4_with_empress():
    """Realistic combat scenario:
    party of 4, base XP 800, on a chain 5 with Empress Band."""
    award = compute_xp_award(
        base_xp=800, prev_chain=4,
        last_kill_tick=1000, now_tick=1010, party_size=4,
        buffs=(XpBuff(BuffSource.EMPRESS_BAND, 0.5),),
    )
    # 800 / 4 = 200; chain 5 = 1.75 -> 350; buffs 1.5 -> 525
    assert award.final_xp == 525
    assert award.chain_count == 5
    assert award.chain_was_extended is True


def test_chain_resets_when_window_expires_during_pull():
    """Took too long between kills — chain resets to 1, no bonus."""
    win = chain_window_seconds(party_size=6)
    award = compute_xp_award(
        base_xp=600, prev_chain=4,
        last_kill_tick=1000, now_tick=1000 + win + 5,
        party_size=6,
    )
    assert award.chain_count == 1
    assert award.chain_multiplier == 1.00
    # 600 / 6 = 100, no chain, no buffs -> 100
    assert award.final_xp == 100
