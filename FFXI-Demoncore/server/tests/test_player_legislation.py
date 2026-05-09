"""Tests for player_legislation."""
from __future__ import annotations

from server.player_legislation import (
    PlayerLegislationSystem, BillState,
)


def _found(s: PlayerLegislationSystem) -> str:
    return s.found_body(
        speaker_id="naji",
        name="Bastok Council",
    )


def _ready(s: PlayerLegislationSystem) -> tuple[str, str]:
    bid = _found(s)
    for leg in ("alice", "bob", "cara"):
        s.enroll_legislator(
            body_id=bid, speaker_id="naji",
            legislator_id=leg,
        )
    bill = s.propose_bill(
        body_id=bid, sponsor_id="alice",
        title="Repair the Aqueduct",
        body_text="Allocate 50000 gil from the treasury.",
    )
    s.begin_vote(
        body_id=bid, bill_id=bill, speaker_id="naji",
    )
    return bid, bill


def test_found_body_happy():
    s = PlayerLegislationSystem()
    assert _found(s) is not None


def test_found_body_speaker_is_legislator():
    s = PlayerLegislationSystem()
    bid = _found(s)
    assert "naji" in s.legislators(body_id=bid)


def test_enroll_legislator_happy():
    s = PlayerLegislationSystem()
    bid = _found(s)
    assert s.enroll_legislator(
        body_id=bid, speaker_id="naji",
        legislator_id="alice",
    ) is True


def test_enroll_legislator_wrong_speaker_blocked():
    s = PlayerLegislationSystem()
    bid = _found(s)
    assert s.enroll_legislator(
        body_id=bid, speaker_id="bob",
        legislator_id="alice",
    ) is False


def test_enroll_legislator_dup_blocked():
    s = PlayerLegislationSystem()
    bid = _found(s)
    s.enroll_legislator(
        body_id=bid, speaker_id="naji",
        legislator_id="alice",
    )
    assert s.enroll_legislator(
        body_id=bid, speaker_id="naji",
        legislator_id="alice",
    ) is False


def test_propose_bill_happy():
    s = PlayerLegislationSystem()
    bid = _found(s)
    s.enroll_legislator(
        body_id=bid, speaker_id="naji",
        legislator_id="alice",
    )
    assert s.propose_bill(
        body_id=bid, sponsor_id="alice",
        title="x", body_text="y",
    ) is not None


def test_propose_bill_non_legislator_blocked():
    s = PlayerLegislationSystem()
    bid = _found(s)
    assert s.propose_bill(
        body_id=bid, sponsor_id="stranger",
        title="x", body_text="y",
    ) is None


def test_propose_bill_empty_blocked():
    s = PlayerLegislationSystem()
    bid = _found(s)
    assert s.propose_bill(
        body_id=bid, sponsor_id="naji",
        title="", body_text="y",
    ) is None


def test_begin_vote_happy():
    s = PlayerLegislationSystem()
    bid = _found(s)
    bill = s.propose_bill(
        body_id=bid, sponsor_id="naji",
        title="x", body_text="y",
    )
    assert s.begin_vote(
        body_id=bid, bill_id=bill, speaker_id="naji",
    ) is True


def test_begin_vote_wrong_speaker_blocked():
    s = PlayerLegislationSystem()
    bid = _found(s)
    bill = s.propose_bill(
        body_id=bid, sponsor_id="naji",
        title="x", body_text="y",
    )
    assert s.begin_vote(
        body_id=bid, bill_id=bill, speaker_id="alice",
    ) is False


def test_begin_vote_twice_blocked():
    s = PlayerLegislationSystem()
    bid = _found(s)
    bill = s.propose_bill(
        body_id=bid, sponsor_id="naji",
        title="x", body_text="y",
    )
    s.begin_vote(
        body_id=bid, bill_id=bill, speaker_id="naji",
    )
    assert s.begin_vote(
        body_id=bid, bill_id=bill, speaker_id="naji",
    ) is False


def test_cast_vote_happy():
    s = PlayerLegislationSystem()
    bid, bill = _ready(s)
    assert s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="alice", yea=True,
    ) is True


def test_cast_vote_non_legislator_blocked():
    s = PlayerLegislationSystem()
    bid, bill = _ready(s)
    assert s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="stranger", yea=True,
    ) is False


def test_cast_vote_dup_blocked():
    s = PlayerLegislationSystem()
    bid, bill = _ready(s)
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="alice", yea=True,
    )
    assert s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="alice", yea=False,
    ) is False


def test_cast_vote_before_begin_blocked():
    s = PlayerLegislationSystem()
    bid = _found(s)
    bill = s.propose_bill(
        body_id=bid, sponsor_id="naji",
        title="x", body_text="y",
    )
    assert s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="naji", yea=True,
    ) is False


def test_close_vote_passes():
    s = PlayerLegislationSystem()
    bid, bill = _ready(s)
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="alice", yea=True,
    )
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="bob", yea=True,
    )
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="cara", yea=False,
    )
    outcome = s.close_vote(
        body_id=bid, bill_id=bill, speaker_id="naji",
    )
    assert outcome == BillState.PASSED


def test_close_vote_fails():
    s = PlayerLegislationSystem()
    bid, bill = _ready(s)
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="alice", yea=False,
    )
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="bob", yea=False,
    )
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="cara", yea=True,
    )
    outcome = s.close_vote(
        body_id=bid, bill_id=bill, speaker_id="naji",
    )
    assert outcome == BillState.FAILED


def test_close_vote_tie_fails():
    s = PlayerLegislationSystem()
    bid, bill = _ready(s)
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="alice", yea=True,
    )
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="bob", yea=False,
    )
    outcome = s.close_vote(
        body_id=bid, bill_id=bill, speaker_id="naji",
    )
    # 1 yea, 1 nay — strict majority not reached
    assert outcome == BillState.FAILED


def test_close_vote_wrong_speaker_blocked():
    s = PlayerLegislationSystem()
    bid, bill = _ready(s)
    assert s.close_vote(
        body_id=bid, bill_id=bill,
        speaker_id="alice",
    ) is None


def test_yea_nay_counts_recorded():
    s = PlayerLegislationSystem()
    bid, bill = _ready(s)
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="alice", yea=True,
    )
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="bob", yea=True,
    )
    s.cast_vote(
        body_id=bid, bill_id=bill,
        legislator_id="cara", yea=False,
    )
    s.close_vote(
        body_id=bid, bill_id=bill, speaker_id="naji",
    )
    bill_spec = s.bill(body_id=bid, bill_id=bill)
    assert bill_spec.yea_count == 2
    assert bill_spec.nay_count == 1


def test_unknown_body():
    s = PlayerLegislationSystem()
    assert s.body(body_id="ghost") is None


def test_unknown_bill():
    s = PlayerLegislationSystem()
    bid = _found(s)
    assert s.bill(
        body_id=bid, bill_id="ghost",
    ) is None


def test_enum_count():
    assert len(list(BillState)) == 4
