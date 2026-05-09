"""Tests for bounty_hunter_ranks."""
from __future__ import annotations

from server.bounty_hunter_ranks import (
    BountyHunterRanksSystem, HunterRank,
)


def test_register_happy():
    s = BountyHunterRanksSystem()
    assert s.register_hunter(
        hunter_id="naji", registered_day=10,
    ) is True


def test_register_duplicate_blocked():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    assert s.register_hunter(
        hunter_id="naji", registered_day=20,
    ) is False


def test_register_empty_blocked():
    s = BountyHunterRanksSystem()
    assert s.register_hunter(
        hunter_id="", registered_day=10,
    ) is False


def test_starting_rank_bronze():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    assert s.rank(hunter_id="naji") == HunterRank.BRONZE


def test_silver_at_5_claims():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    for d in range(11, 16):
        s.record_claim(
            hunter_id="naji", claimed_day=d,
        )
    assert s.rank(hunter_id="naji") == HunterRank.SILVER


def test_gold_at_15_claims():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    for d in range(11, 26):
        s.record_claim(
            hunter_id="naji", claimed_day=d,
        )
    assert s.rank(hunter_id="naji") == HunterRank.GOLD


def test_platinum_at_40_claims():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    for d in range(11, 51):
        s.record_claim(
            hunter_id="naji", claimed_day=d,
        )
    assert s.rank(
        hunter_id="naji",
    ) == HunterRank.PLATINUM


def test_legendary_at_100_claims():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    for d in range(11, 111):
        s.record_claim(
            hunter_id="naji", claimed_day=d,
        )
    assert s.rank(
        hunter_id="naji",
    ) == HunterRank.LEGENDARY


def test_can_claim_within_cap():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    # Bronze cap is 5,000
    assert s.can_claim_bounty(
        hunter_id="naji", reward_gil=4000,
    ) is True


def test_cannot_claim_above_cap():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    # Bronze cap is 5,000
    assert s.can_claim_bounty(
        hunter_id="naji", reward_gil=10000,
    ) is False


def test_silver_cap_higher():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    for d in range(11, 16):
        s.record_claim(
            hunter_id="naji", claimed_day=d,
        )
    assert s.can_claim_bounty(
        hunter_id="naji", reward_gil=15000,
    ) is True


def test_legendary_uncapped():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    for d in range(11, 111):
        s.record_claim(
            hunter_id="naji", claimed_day=d,
        )
    assert s.can_claim_bounty(
        hunter_id="naji", reward_gil=999_999_999,
    ) is True


def test_unregistered_cannot_claim():
    s = BountyHunterRanksSystem()
    assert s.can_claim_bounty(
        hunter_id="ghost", reward_gil=100,
    ) is False


def test_record_unregistered_blocked():
    s = BountyHunterRanksSystem()
    assert s.record_claim(
        hunter_id="ghost", claimed_day=10,
    ) is False


def test_record_backwards_day_blocked():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    s.record_claim(hunter_id="naji", claimed_day=15)
    assert s.record_claim(
        hunter_id="naji", claimed_day=10,
    ) is False


def test_inactivity_decay_no_op_within_window():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    for d in range(11, 16):
        s.record_claim(
            hunter_id="naji", claimed_day=d,
        )
    # 20 days after last claim — within 30-day window
    decay = s.apply_inactivity_decay(
        hunter_id="naji", current_day=35,
    )
    assert decay == 0


def test_inactivity_decay_after_window():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    for d in range(11, 21):
        s.record_claim(
            hunter_id="naji", claimed_day=d,
        )
    # Last claim day=20. 95 days later = 75 days inactive
    # = 2 full 30-day periods past the first → 2 decay
    decay = s.apply_inactivity_decay(
        hunter_id="naji", current_day=115,
    )
    assert decay == 2
    # 10 - 2 = 8 claims left
    assert s.claim_count(hunter_id="naji") == 8


def test_decay_floors_at_zero():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    s.record_claim(hunter_id="naji", claimed_day=11)
    # Massive inactivity
    decay = s.apply_inactivity_decay(
        hunter_id="naji", current_day=10000,
    )
    assert s.claim_count(hunter_id="naji") == 0


def test_max_bounty_query():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    # Bronze
    assert s.max_bounty(hunter_id="naji") == 5_000


def test_max_bounty_unknown_zero():
    s = BountyHunterRanksSystem()
    assert s.max_bounty(hunter_id="ghost") == 0


def test_rank_unknown_returns_none():
    s = BountyHunterRanksSystem()
    assert s.rank(hunter_id="ghost") is None


def test_claim_count_unknown_zero():
    s = BountyHunterRanksSystem()
    assert s.claim_count(hunter_id="ghost") == 0


def test_hunter_lookup():
    s = BountyHunterRanksSystem()
    s.register_hunter(
        hunter_id="naji", registered_day=10,
    )
    s.record_claim(hunter_id="naji", claimed_day=11)
    h = s.hunter(hunter_id="naji")
    assert h.successful_claims == 1


def test_enum_count():
    assert len(list(HunterRank)) == 5
