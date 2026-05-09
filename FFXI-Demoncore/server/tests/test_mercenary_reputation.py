"""Tests for mercenary_reputation."""
from __future__ import annotations

from server.mercenary_reputation import (
    MercenaryReputationSystem, JobKind, Outcome, Rank,
)


def test_record_success_increments():
    s = MercenaryReputationSystem()
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=10,
    )
    assert s.reputation(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
    ) == 10


def test_record_dispute_loss_decrements():
    s = MercenaryReputationSystem()
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=10,
    )
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.DISPUTE_LOSS,
        recorded_day=11,
    )
    # 10 - 5 = 5
    assert s.reputation(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
    ) == 5


def test_score_floor_at_zero():
    s = MercenaryReputationSystem()
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.DISPUTE_LOSS,
        recorded_day=10,
    )
    assert s.reputation(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
    ) == 0


def test_kinds_are_isolated():
    s = MercenaryReputationSystem()
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=10,
    )
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=11,
    )
    assert s.reputation(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
    ) == 20
    assert s.reputation(
        completer_id="naji",
        kind=JobKind.CONTENT_CARRY,
    ) == 0


def test_rank_progression():
    s = MercenaryReputationSystem()
    # Starting rank
    assert s.rank(
        completer_id="x", kind=JobKind.CRAFT_ORDER,
    ) == Rank.NOVICE
    # 5 successes = 50 → JOURNEYMAN
    for d in range(5):
        s.record_completion(
            completer_id="x", kind=JobKind.CRAFT_ORDER,
            outcome=Outcome.SUCCESS, recorded_day=d,
        )
    assert s.rank(
        completer_id="x", kind=JobKind.CRAFT_ORDER,
    ) == Rank.JOURNEYMAN


def test_rank_expert_threshold():
    s = MercenaryReputationSystem()
    for d in range(10):
        s.record_completion(
            completer_id="x", kind=JobKind.CRAFT_ORDER,
            outcome=Outcome.SUCCESS, recorded_day=d,
        )
    # 100 → EXPERT
    assert s.rank(
        completer_id="x", kind=JobKind.CRAFT_ORDER,
    ) == Rank.EXPERT


def test_rank_master_threshold():
    s = MercenaryReputationSystem()
    for d in range(25):
        s.record_completion(
            completer_id="x", kind=JobKind.CRAFT_ORDER,
            outcome=Outcome.SUCCESS, recorded_day=d,
        )
    # 250 → MASTER
    assert s.rank(
        completer_id="x", kind=JobKind.CRAFT_ORDER,
    ) == Rank.MASTER


def test_overall_reputation_aggregates():
    s = MercenaryReputationSystem()
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=10,
    )
    s.record_completion(
        completer_id="naji",
        kind=JobKind.CONTENT_CARRY,
        outcome=Outcome.SUCCESS, recorded_day=11,
    )
    s.record_completion(
        completer_id="naji",
        kind=JobKind.DELIVERY,
        outcome=Outcome.SUCCESS, recorded_day=12,
    )
    assert s.overall_reputation(
        completer_id="naji",
    ) == 30


def test_expiry_outcome_minor_penalty():
    s = MercenaryReputationSystem()
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=10,
    )
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.EXPIRY, recorded_day=11,
    )
    assert s.reputation(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
    ) == 8


def test_record_empty_completer():
    s = MercenaryReputationSystem()
    assert s.record_completion(
        completer_id="", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=10,
    ) is None


def test_record_negative_day():
    s = MercenaryReputationSystem()
    assert s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=-1,
    ) is None


def test_completions_by_completer():
    s = MercenaryReputationSystem()
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=10,
    )
    s.record_completion(
        completer_id="naji",
        kind=JobKind.CONTENT_CARRY,
        outcome=Outcome.SUCCESS, recorded_day=11,
    )
    s.record_completion(
        completer_id="bob", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=12,
    )
    naji = s.completions_by_completer(
        completer_id="naji",
    )
    bob = s.completions_by_completer(
        completer_id="bob",
    )
    assert len(naji) == 2
    assert len(bob) == 1


def test_unknown_completer_zero_rep():
    s = MercenaryReputationSystem()
    assert s.reputation(
        completer_id="ghost",
        kind=JobKind.CRAFT_ORDER,
    ) == 0


def test_unknown_completer_novice_rank():
    s = MercenaryReputationSystem()
    assert s.rank(
        completer_id="ghost",
        kind=JobKind.CRAFT_ORDER,
    ) == Rank.NOVICE


def test_unknown_completer_zero_overall():
    s = MercenaryReputationSystem()
    assert s.overall_reputation(
        completer_id="ghost",
    ) == 0


def test_completion_lookup():
    s = MercenaryReputationSystem()
    cid = s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.SUCCESS, recorded_day=10,
    )
    c = s.completion(completion_id=cid)
    assert c.delta == 10


def test_unknown_completion():
    s = MercenaryReputationSystem()
    assert s.completion(completion_id="ghost") is None


def test_dispute_below_floor_clamps():
    """Two dispute losses on a fresh completer
    floor at 0, not -10."""
    s = MercenaryReputationSystem()
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.DISPUTE_LOSS,
        recorded_day=10,
    )
    s.record_completion(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
        outcome=Outcome.DISPUTE_LOSS,
        recorded_day=11,
    )
    assert s.reputation(
        completer_id="naji", kind=JobKind.CRAFT_ORDER,
    ) == 0


def test_per_kind_rank_independence():
    s = MercenaryReputationSystem()
    for d in range(5):
        s.record_completion(
            completer_id="x", kind=JobKind.CRAFT_ORDER,
            outcome=Outcome.SUCCESS, recorded_day=d,
        )
    # Crafter is JOURNEYMAN, but novice at carry
    assert s.rank(
        completer_id="x", kind=JobKind.CRAFT_ORDER,
    ) == Rank.JOURNEYMAN
    assert s.rank(
        completer_id="x",
        kind=JobKind.CONTENT_CARRY,
    ) == Rank.NOVICE


def test_enum_counts():
    assert len(list(JobKind)) == 6
    assert len(list(Outcome)) == 3
    assert len(list(Rank)) == 4
