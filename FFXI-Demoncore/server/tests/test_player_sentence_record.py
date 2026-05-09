"""Tests for player_sentence_record."""
from __future__ import annotations

from server.player_sentence_record import (
    PlayerSentenceRecordSystem, SentenceState, Penalty,
)


def _impose_fine(
    s: PlayerSentenceRecordSystem, amount: int = 5000,
) -> str:
    return s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.FINE,
        imposed_day=10, amount_gil=amount,
    )


def test_impose_fine_happy():
    s = PlayerSentenceRecordSystem()
    assert _impose_fine(s) is not None


def test_impose_fine_zero_amount_blocked():
    s = PlayerSentenceRecordSystem()
    assert _impose_fine(s, amount=0) is None


def test_impose_restitution_happy():
    s = PlayerSentenceRecordSystem()
    assert s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.RESTITUTION,
        imposed_day=10, amount_gil=3000,
        payable_to_id="alice",
    ) is not None


def test_impose_restitution_no_payee_blocked():
    s = PlayerSentenceRecordSystem()
    assert s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.RESTITUTION,
        imposed_day=10, amount_gil=3000,
    ) is None


def test_impose_restitution_self_payee_blocked():
    s = PlayerSentenceRecordSystem()
    assert s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.RESTITUTION,
        imposed_day=10, amount_gil=3000,
        payable_to_id="bob",
    ) is None


def test_impose_banishment_happy():
    s = PlayerSentenceRecordSystem()
    assert s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.BANISHMENT,
        imposed_day=10, expiry_day=100,
    ) is not None


def test_impose_banishment_zero_expiry_blocked():
    s = PlayerSentenceRecordSystem()
    assert s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.BANISHMENT,
        imposed_day=10, expiry_day=10,
    ) is None


def test_impose_self_blocked():
    s = PlayerSentenceRecordSystem()
    assert s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="bob",
        penalty=Penalty.FINE,
        imposed_day=10, amount_gil=1000,
    ) is None


def test_pay_fine_happy():
    s = PlayerSentenceRecordSystem()
    sid = _impose_fine(s)
    assert s.pay(
        sentence_id=sid, defendant_id="bob",
    ) is True
    assert s.sentence(
        sentence_id=sid,
    ).state == SentenceState.PAID


def test_pay_wrong_defendant_blocked():
    s = PlayerSentenceRecordSystem()
    sid = _impose_fine(s)
    assert s.pay(
        sentence_id=sid, defendant_id="alice",
    ) is False


def test_pay_banishment_blocked():
    s = PlayerSentenceRecordSystem()
    sid = s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.BANISHMENT,
        imposed_day=10, expiry_day=100,
    )
    # Can't "pay" banishment — must serve it
    assert s.pay(
        sentence_id=sid, defendant_id="bob",
    ) is False


def test_pay_twice_blocked():
    s = PlayerSentenceRecordSystem()
    sid = _impose_fine(s)
    s.pay(sentence_id=sid, defendant_id="bob")
    assert s.pay(
        sentence_id=sid, defendant_id="bob",
    ) is False


def test_check_expiry_lifts_banishment():
    s = PlayerSentenceRecordSystem()
    sid = s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.BANISHMENT,
        imposed_day=10, expiry_day=100,
    )
    assert s.check_expiry(
        sentence_id=sid, current_day=150,
    ) is True
    assert s.sentence(
        sentence_id=sid,
    ).state == SentenceState.LIFTED


def test_check_expiry_too_early_blocked():
    s = PlayerSentenceRecordSystem()
    sid = s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.BANISHMENT,
        imposed_day=10, expiry_day=100,
    )
    assert s.check_expiry(
        sentence_id=sid, current_day=50,
    ) is False


def test_check_expiry_fine_blocked():
    s = PlayerSentenceRecordSystem()
    sid = _impose_fine(s)
    # Fines don't expire
    assert s.check_expiry(
        sentence_id=sid, current_day=1000,
    ) is False


def test_pardon_happy():
    s = PlayerSentenceRecordSystem()
    sid = _impose_fine(s)
    assert s.pardon(
        sentence_id=sid, pardoner_id="king_naji",
    ) is True
    assert s.sentence(
        sentence_id=sid,
    ).state == SentenceState.PARDONED


def test_pardon_self_blocked():
    s = PlayerSentenceRecordSystem()
    sid = _impose_fine(s)
    assert s.pardon(
        sentence_id=sid, pardoner_id="bob",
    ) is False


def test_pardon_already_paid_blocked():
    s = PlayerSentenceRecordSystem()
    sid = _impose_fine(s)
    s.pay(sentence_id=sid, defendant_id="bob")
    assert s.pardon(
        sentence_id=sid, pardoner_id="king_naji",
    ) is False


def test_sentences_against_listing():
    s = PlayerSentenceRecordSystem()
    _impose_fine(s)
    _impose_fine(s)
    assert len(s.sentences_against(
        defendant_id="bob",
    )) == 2


def test_outstanding_against_filters():
    s = PlayerSentenceRecordSystem()
    sid1 = _impose_fine(s)
    _impose_fine(s)
    s.pay(sentence_id=sid1, defendant_id="bob")
    assert len(s.outstanding_against(
        defendant_id="bob",
    )) == 1


def test_is_currently_banished_true():
    s = PlayerSentenceRecordSystem()
    s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.BANISHMENT,
        imposed_day=10, expiry_day=100,
    )
    assert s.is_currently_banished(
        defendant_id="bob", current_day=50,
    ) is True


def test_is_currently_banished_after_expiry_false():
    s = PlayerSentenceRecordSystem()
    s.impose(
        lawsuit_id="suit_1", defendant_id="bob",
        presiding_justice_id="judge_1",
        penalty=Penalty.BANISHMENT,
        imposed_day=10, expiry_day=100,
    )
    assert s.is_currently_banished(
        defendant_id="bob", current_day=150,
    ) is False


def test_unknown_sentence():
    s = PlayerSentenceRecordSystem()
    assert s.sentence(
        sentence_id="ghost",
    ) is None


def test_state_count():
    assert len(list(SentenceState)) == 4


def test_penalty_count():
    assert len(list(Penalty)) == 4
