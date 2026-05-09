"""Tests for bounty_contracts."""
from __future__ import annotations

from server.bounty_contracts import (
    BountyContractsSystem, BountyState, HostileKind,
)


def _provoke(
    s: BountyContractsSystem,
    aggressor: str = "volker", victim: str = "naji",
    day: int = 5,
) -> None:
    s.register_hostile_event(
        aggressor_id=aggressor, victim_id=victim,
        kind=HostileKind.KILL, occurred_day=day,
    )


def test_register_event_happy():
    s = BountyContractsSystem()
    eid = s.register_hostile_event(
        aggressor_id="a", victim_id="b",
        kind=HostileKind.KILL, occurred_day=10,
    )
    assert eid is not None


def test_register_event_self_blocked():
    s = BountyContractsSystem()
    assert s.register_hostile_event(
        aggressor_id="a", victim_id="a",
        kind=HostileKind.KILL, occurred_day=10,
    ) is None


def test_open_bounty_with_provocation():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    )
    assert bid is not None


def test_open_bounty_no_provocation_blocked():
    s = BountyContractsSystem()
    assert s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    ) is None


def test_open_bounty_provocation_too_old_blocked():
    s = BountyContractsSystem()
    # Provocation 30 days before posting; window is 14
    _provoke(s, day=5)
    assert s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=40,
    ) is None


def test_open_bounty_self_target_blocked():
    s = BountyContractsSystem()
    _provoke(s, aggressor="naji", victim="naji", day=5)
    # Even if we somehow got an event, posting against
    # self is rejected.
    assert s.open_bounty(
        poster_id="naji", target_id="naji",
        reward_gil=10000, posted_day=10,
    ) is None


def test_open_bounty_negative_reward_blocked():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    assert s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=0, posted_day=10,
    ) is None


def test_per_pair_cooldown_blocks_repeat():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    # Second attempt 3 days later (within 7-day cooldown)
    assert s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=5000, posted_day=13,
    ) is None


def test_cooldown_clears_after_window():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    _provoke(s, day=20)  # fresh provocation
    bid2 = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=5000, posted_day=25,
    )
    assert bid2 is not None


def test_claim_bounty_happy():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    )
    payout = s.claim_bounty(
        bounty_id=bid, claimant_id="bob",
        eliminated_day=12,
    )
    assert payout == 10000


def test_claim_self_blocked():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    )
    # Poster can't claim
    assert s.claim_bounty(
        bounty_id=bid, claimant_id="naji",
        eliminated_day=12,
    ) is None
    # Target can't claim
    assert s.claim_bounty(
        bounty_id=bid, claimant_id="volker",
        eliminated_day=12,
    ) is None


def test_claim_after_expiry_blocked():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    )
    # Expires day 10 + 21 = 31
    assert s.claim_bounty(
        bounty_id=bid, claimant_id="bob",
        eliminated_day=35,
    ) is None


def test_withdraw_bounty_50pct_refund():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    )
    refund = s.withdraw_bounty(
        bounty_id=bid, poster_id="naji",
    )
    assert refund == 5000
    assert s.bounty(
        bounty_id=bid,
    ).state == BountyState.REFUNDED


def test_withdraw_wrong_poster_blocked():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    )
    assert s.withdraw_bounty(
        bounty_id=bid, poster_id="bob",
    ) is None


def test_withdraw_after_claim_blocked():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    )
    s.claim_bounty(
        bounty_id=bid, claimant_id="bob",
        eliminated_day=12,
    )
    assert s.withdraw_bounty(
        bounty_id=bid, poster_id="naji",
    ) is None


def test_expire_bounty_50pct_refund():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    )
    refund = s.expire_bounty(
        bounty_id=bid, current_day=35,
    )
    assert refund == 5000


def test_expire_before_deadline_blocked():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=10000, posted_day=10,
    )
    assert s.expire_bounty(
        bounty_id=bid, current_day=15,
    ) is None


def test_mutual_bounty_locks_to_feud():
    """Bob bounties Cara, Cara bounties Bob — both
    flip to FEUD_LOCKED."""
    s = BountyContractsSystem()
    s.register_hostile_event(
        aggressor_id="cara", victim_id="bob",
        kind=HostileKind.KILL, occurred_day=5,
    )
    s.register_hostile_event(
        aggressor_id="bob", victim_id="cara",
        kind=HostileKind.KILL, occurred_day=6,
    )
    bid_a = s.open_bounty(
        poster_id="bob", target_id="cara",
        reward_gil=5000, posted_day=10,
    )
    bid_b = s.open_bounty(
        poster_id="cara", target_id="bob",
        reward_gil=8000, posted_day=11,
    )
    a = s.bounty(bounty_id=bid_a)
    b = s.bounty(bounty_id=bid_b)
    assert a.state == BountyState.FEUD_LOCKED
    assert b.state == BountyState.FEUD_LOCKED


def test_feud_pool_aggregates():
    s = BountyContractsSystem()
    s.register_hostile_event(
        aggressor_id="cara", victim_id="bob",
        kind=HostileKind.KILL, occurred_day=5,
    )
    s.register_hostile_event(
        aggressor_id="bob", victim_id="cara",
        kind=HostileKind.KILL, occurred_day=6,
    )
    s.open_bounty(
        poster_id="bob", target_id="cara",
        reward_gil=5000, posted_day=10,
    )
    s.open_bounty(
        poster_id="cara", target_id="bob",
        reward_gil=8000, posted_day=11,
    )
    # 5000 + 8000 = 13000 in arena pool
    assert s.feud_pool_total() == 13000


def test_feud_locked_cannot_be_claimed():
    s = BountyContractsSystem()
    s.register_hostile_event(
        aggressor_id="cara", victim_id="bob",
        kind=HostileKind.KILL, occurred_day=5,
    )
    s.register_hostile_event(
        aggressor_id="bob", victim_id="cara",
        kind=HostileKind.KILL, occurred_day=6,
    )
    bid_a = s.open_bounty(
        poster_id="bob", target_id="cara",
        reward_gil=5000, posted_day=10,
    )
    s.open_bounty(
        poster_id="cara", target_id="bob",
        reward_gil=8000, posted_day=11,
    )
    # bid_a is now FEUD_LOCKED, can't claim
    assert s.claim_bounty(
        bounty_id=bid_a, claimant_id="dave",
        eliminated_day=15,
    ) is None


def test_open_bounties_against_target():
    s = BountyContractsSystem()
    _provoke(s, aggressor="volker", victim="naji", day=5)
    _provoke(s, aggressor="volker", victim="bob", day=5)
    s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    s.open_bounty(
        poster_id="bob", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    against = s.open_bounties_against(
        target_id="volker",
    )
    assert len(against) == 2


def test_target_notification_set():
    s = BountyContractsSystem()
    _provoke(s, day=5)
    bid = s.open_bounty(
        poster_id="naji", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    assert s.bounty(
        bounty_id=bid,
    ).notification_sent is True


def test_unknown_bounty():
    s = BountyContractsSystem()
    assert s.bounty(bounty_id="ghost") is None


def test_enum_counts():
    assert len(list(HostileKind)) == 3
    assert len(list(BountyState)) == 5
