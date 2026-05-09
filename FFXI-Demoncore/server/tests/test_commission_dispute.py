"""Tests for commission_dispute."""
from __future__ import annotations

from server.commission_dispute import (
    CommissionDisputeSystem, DisputeState,
    DisputeOutcome,
)


def _file(
    s: CommissionDisputeSystem,
    filer_id: str = "naji",
) -> str:
    return s.file_dispute(
        job_id="job_42", poster_id="naji",
        completer_id="bob", filer_id=filer_id,
        reason="Crafted item failed spec",
        escrow_gil=10000, completed_day=10,
        filed_day=11,
    )


def test_file_happy():
    s = CommissionDisputeSystem()
    did = _file(s)
    assert did is not None


def test_file_outside_window_blocked():
    s = CommissionDisputeSystem()
    assert s.file_dispute(
        job_id="job_42", poster_id="naji",
        completer_id="bob", filer_id="naji",
        reason="r", escrow_gil=10000,
        completed_day=10, filed_day=20,
    ) is None


def test_file_before_completion_blocked():
    s = CommissionDisputeSystem()
    assert s.file_dispute(
        job_id="job_42", poster_id="naji",
        completer_id="bob", filer_id="naji",
        reason="r", escrow_gil=10000,
        completed_day=10, filed_day=5,
    ) is None


def test_file_third_party_filer_blocked():
    s = CommissionDisputeSystem()
    assert s.file_dispute(
        job_id="job_42", poster_id="naji",
        completer_id="bob", filer_id="cara",
        reason="r", escrow_gil=10000,
        completed_day=10, filed_day=11,
    ) is None


def test_file_empty_reason_blocked():
    s = CommissionDisputeSystem()
    assert s.file_dispute(
        job_id="job_42", poster_id="naji",
        completer_id="bob", filer_id="naji",
        reason="", escrow_gil=10000,
        completed_day=10, filed_day=11,
    ) is None


def test_file_zero_escrow_blocked():
    s = CommissionDisputeSystem()
    assert s.file_dispute(
        job_id="job_42", poster_id="naji",
        completer_id="bob", filer_id="naji",
        reason="r", escrow_gil=0,
        completed_day=10, filed_day=11,
    ) is None


def test_file_duplicate_active_blocked():
    s = CommissionDisputeSystem()
    _file(s)
    assert s.file_dispute(
        job_id="job_42", poster_id="naji",
        completer_id="bob", filer_id="bob",
        reason="counter", escrow_gil=10000,
        completed_day=10, filed_day=12,
    ) is None


def test_open_evidence_happy():
    s = CommissionDisputeSystem()
    did = _file(s)
    assert s.open_evidence(dispute_id=did) is True


def test_open_evidence_double_blocked():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    assert s.open_evidence(dispute_id=did) is False


def test_submit_evidence_happy():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    eid = s.submit_evidence(
        dispute_id=did, submitter_id="naji",
        description="Item arrived broken",
        submitted_day=12,
    )
    assert eid is not None


def test_submit_evidence_third_party_blocked():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    assert s.submit_evidence(
        dispute_id=did, submitter_id="cara",
        description="I saw it", submitted_day=12,
    ) is None


def test_submit_evidence_before_open_blocked():
    s = CommissionDisputeSystem()
    did = _file(s)
    assert s.submit_evidence(
        dispute_id=did, submitter_id="naji",
        description="d", submitted_day=12,
    ) is None


def test_resolve_poster_wins_full_refund():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    poster_pay, completer_pay = s.resolve(
        dispute_id=did,
        outcome=DisputeOutcome.POSTER_WINS,
    )
    assert poster_pay == 10000
    assert completer_pay == 0


def test_resolve_completer_wins_full_payout():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    poster_pay, completer_pay = s.resolve(
        dispute_id=did,
        outcome=DisputeOutcome.COMPLETER_WINS,
    )
    assert poster_pay == 0
    assert completer_pay == 10000


def test_resolve_split_50_50():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    poster_pay, completer_pay = s.resolve(
        dispute_id=did, outcome=DisputeOutcome.SPLIT,
    )
    assert poster_pay == 5000
    assert completer_pay == 5000


def test_resolve_split_odd_escrow():
    s = CommissionDisputeSystem()
    did = s.file_dispute(
        job_id="j", poster_id="naji",
        completer_id="bob", filer_id="naji",
        reason="r", escrow_gil=10001,
        completed_day=10, filed_day=11,
    )
    s.open_evidence(dispute_id=did)
    poster_pay, completer_pay = s.resolve(
        dispute_id=did, outcome=DisputeOutcome.SPLIT,
    )
    # 10001 // 2 = 5000, completer gets the extra
    assert poster_pay == 5000
    assert completer_pay == 5001


def test_resolve_dismissed_filer_pays_fine():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    poster_pay, completer_pay = s.resolve(
        dispute_id=did,
        outcome=DisputeOutcome.DISMISSED,
    )
    # Filer is naji (poster); fine is 5%, naji loses
    # 500 to bob.
    assert poster_pay == 9500
    assert completer_pay == 500


def test_resolve_dismissed_completer_filer():
    s = CommissionDisputeSystem()
    did = s.file_dispute(
        job_id="j", poster_id="naji",
        completer_id="bob", filer_id="bob",
        reason="r", escrow_gil=10000,
        completed_day=10, filed_day=11,
    )
    s.open_evidence(dispute_id=did)
    poster_pay, completer_pay = s.resolve(
        dispute_id=did,
        outcome=DisputeOutcome.DISMISSED,
    )
    # Filer is bob (completer); fine 5% goes to naji
    assert poster_pay == 500
    assert completer_pay == 9500


def test_resolve_before_evidence_blocked():
    s = CommissionDisputeSystem()
    did = _file(s)
    assert s.resolve(
        dispute_id=did,
        outcome=DisputeOutcome.POSTER_WINS,
    ) is None


def test_resolve_double_blocked():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    s.resolve(
        dispute_id=did,
        outcome=DisputeOutcome.POSTER_WINS,
    )
    assert s.resolve(
        dispute_id=did,
        outcome=DisputeOutcome.SPLIT,
    ) is None


def test_evidence_listed():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    s.submit_evidence(
        dispute_id=did, submitter_id="naji",
        description="A", submitted_day=12,
    )
    s.submit_evidence(
        dispute_id=did, submitter_id="bob",
        description="B", submitted_day=12,
    )
    assert len(s.evidence(dispute_id=did)) == 2


def test_after_resolution_can_re_dispute():
    s = CommissionDisputeSystem()
    did = _file(s)
    s.open_evidence(dispute_id=did)
    s.resolve(
        dispute_id=did,
        outcome=DisputeOutcome.SPLIT,
    )
    # Same job — could dispute again? Not really
    # useful, but the duplicate-blocker only stops
    # active disputes. Resolved leaves it open.
    second = s.file_dispute(
        job_id="job_42", poster_id="naji",
        completer_id="bob", filer_id="naji",
        reason="appeal", escrow_gil=5000,
        completed_day=10, filed_day=12,
    )
    assert second is not None


def test_unknown_dispute():
    s = CommissionDisputeSystem()
    assert s.dispute(dispute_id="ghost") is None
    assert s.evidence(dispute_id="ghost") == []


def test_enum_counts():
    assert len(list(DisputeState)) == 3
    assert len(list(DisputeOutcome)) == 4
