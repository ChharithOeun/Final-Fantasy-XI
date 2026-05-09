"""Tests for player_lawsuit."""
from __future__ import annotations

from server.player_lawsuit import (
    PlayerLawsuitSystem, LawsuitState, Verdict,
)


def _file(s: PlayerLawsuitSystem) -> str:
    return s.file_lawsuit(
        court_id="court_1", plaintiff_id="alice",
        defendant_id="bob", kind="theft",
        claim="bob took my mythril ore",
        filed_day=10,
    )


def _through_answered(s: PlayerLawsuitSystem) -> str:
    lid = _file(s)
    s.answer(lawsuit_id=lid, defendant_id="bob")
    return lid


def test_file_happy():
    s = PlayerLawsuitSystem()
    assert _file(s) is not None


def test_file_self_blocked():
    s = PlayerLawsuitSystem()
    assert s.file_lawsuit(
        court_id="court_1", plaintiff_id="alice",
        defendant_id="alice", kind="theft",
        claim="x", filed_day=10,
    ) is None


def test_file_empty_kind_blocked():
    s = PlayerLawsuitSystem()
    assert s.file_lawsuit(
        court_id="court_1", plaintiff_id="alice",
        defendant_id="bob", kind="",
        claim="x", filed_day=10,
    ) is None


def test_file_empty_claim_blocked():
    s = PlayerLawsuitSystem()
    assert s.file_lawsuit(
        court_id="court_1", plaintiff_id="alice",
        defendant_id="bob", kind="theft",
        claim="", filed_day=10,
    ) is None


def test_submit_evidence_plaintiff():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    assert s.submit_evidence(
        lawsuit_id=lid, party_id="alice",
        item="receipt for mythril",
    ) is True


def test_submit_evidence_defendant():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    assert s.submit_evidence(
        lawsuit_id=lid, party_id="bob",
        item="alibi from a witness",
    ) is True


def test_submit_evidence_third_party_blocked():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    assert s.submit_evidence(
        lawsuit_id=lid, party_id="stranger",
        item="x",
    ) is False


def test_submit_evidence_empty_blocked():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    assert s.submit_evidence(
        lawsuit_id=lid, party_id="alice", item="",
    ) is False


def test_answer_happy():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    assert s.answer(
        lawsuit_id=lid, defendant_id="bob",
    ) is True
    assert s.lawsuit(
        lawsuit_id=lid,
    ).state == LawsuitState.ANSWERED


def test_answer_wrong_defendant_blocked():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    assert s.answer(
        lawsuit_id=lid, defendant_id="cara",
    ) is False


def test_answer_twice_blocked():
    s = PlayerLawsuitSystem()
    lid = _through_answered(s)
    assert s.answer(
        lawsuit_id=lid, defendant_id="bob",
    ) is False


def test_rule_plaintiff_happy():
    s = PlayerLawsuitSystem()
    lid = _through_answered(s)
    assert s.rule(
        lawsuit_id=lid, justice_id="judge_1",
        verdict=Verdict.PLAINTIFF,
    ) is True
    spec = s.lawsuit(lawsuit_id=lid)
    assert spec.state == LawsuitState.JUDGED
    assert spec.verdict == Verdict.PLAINTIFF


def test_rule_defendant_happy():
    s = PlayerLawsuitSystem()
    lid = _through_answered(s)
    assert s.rule(
        lawsuit_id=lid, justice_id="judge_1",
        verdict=Verdict.DEFENDANT,
    ) is True


def test_rule_party_as_justice_blocked():
    s = PlayerLawsuitSystem()
    lid = _through_answered(s)
    assert s.rule(
        lawsuit_id=lid, justice_id="alice",
        verdict=Verdict.PLAINTIFF,
    ) is False


def test_rule_before_answer_blocked():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    assert s.rule(
        lawsuit_id=lid, justice_id="judge_1",
        verdict=Verdict.PLAINTIFF,
    ) is False


def test_dismiss_happy():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    assert s.dismiss(
        lawsuit_id=lid, plaintiff_id="alice",
    ) is True
    assert s.lawsuit(
        lawsuit_id=lid,
    ).state == LawsuitState.DISMISSED


def test_dismiss_wrong_plaintiff_blocked():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    assert s.dismiss(
        lawsuit_id=lid, plaintiff_id="bob",
    ) is False


def test_dismiss_after_judgment_blocked():
    s = PlayerLawsuitSystem()
    lid = _through_answered(s)
    s.rule(
        lawsuit_id=lid, justice_id="judge_1",
        verdict=Verdict.PLAINTIFF,
    )
    assert s.dismiss(
        lawsuit_id=lid, plaintiff_id="alice",
    ) is False


def test_evidence_after_judgment_blocked():
    s = PlayerLawsuitSystem()
    lid = _through_answered(s)
    s.rule(
        lawsuit_id=lid, justice_id="judge_1",
        verdict=Verdict.PLAINTIFF,
    )
    assert s.submit_evidence(
        lawsuit_id=lid, party_id="alice", item="late",
    ) is False


def test_evidence_listing():
    s = PlayerLawsuitSystem()
    lid = _file(s)
    s.submit_evidence(
        lawsuit_id=lid, party_id="alice", item="r1",
    )
    s.submit_evidence(
        lawsuit_id=lid, party_id="alice", item="r2",
    )
    assert s.evidence(
        lawsuit_id=lid, party_id="alice",
    ) == ["r1", "r2"]


def test_suits_against_lookup():
    s = PlayerLawsuitSystem()
    _file(s)
    s.file_lawsuit(
        court_id="court_1", plaintiff_id="cara",
        defendant_id="bob", kind="fraud",
        claim="x", filed_day=11,
    )
    assert len(s.suits_against(
        defendant_id="bob",
    )) == 2


def test_unknown_lawsuit():
    s = PlayerLawsuitSystem()
    assert s.lawsuit(lawsuit_id="ghost") is None


def test_state_count():
    assert len(list(LawsuitState)) == 4


def test_verdict_count():
    assert len(list(Verdict)) == 2
