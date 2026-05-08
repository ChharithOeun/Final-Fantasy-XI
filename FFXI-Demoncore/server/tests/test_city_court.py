"""Tests for city_court."""
from __future__ import annotations

from server.city_court import (
    CityCourtSystem, Verdict, PleaKind, CaseState,
)


def _file(s, **overrides):
    args = dict(
        court_id="bastok_court", defendant_id="bob",
        charges=["theft", "assault"],
        filed_day=10, witnesses=["cara"],
        bounty_value=1000,
    )
    args.update(overrides)
    return s.file_case(**args)


def test_file_happy():
    s = CityCourtSystem()
    assert _file(s) is not None


def test_file_blank_court():
    s = CityCourtSystem()
    assert _file(s, court_id="") is None


def test_file_blank_defendant():
    s = CityCourtSystem()
    assert _file(s, defendant_id="") is None


def test_file_no_charges():
    s = CityCourtSystem()
    assert _file(s, charges=[]) is None


def test_file_negative_day():
    s = CityCourtSystem()
    assert _file(s, filed_day=-1) is None


def test_file_negative_bounty():
    s = CityCourtSystem()
    assert _file(s, bounty_value=-1) is None


def test_plea_happy():
    s = CityCourtSystem()
    cid = _file(s, filed_day=10)
    assert s.enter_plea(
        case_id=cid, plea=PleaKind.GUILTY, now_day=11,
    ) is True


def test_plea_unknown():
    s = CityCourtSystem()
    assert s.enter_plea(
        case_id="ghost", plea=PleaKind.GUILTY,
        now_day=11,
    ) is False


def test_double_plea_blocked():
    s = CityCourtSystem()
    cid = _file(s)
    s.enter_plea(
        case_id=cid, plea=PleaKind.GUILTY, now_day=11,
    )
    assert s.enter_plea(
        case_id=cid, plea=PleaKind.NOT_GUILTY,
        now_day=12,
    ) is False


def test_plea_before_file_blocked():
    s = CityCourtSystem()
    cid = _file(s, filed_day=10)
    assert s.enter_plea(
        case_id=cid, plea=PleaKind.GUILTY, now_day=5,
    ) is False


def test_verdict_happy():
    s = CityCourtSystem()
    cid = _file(s)
    s.enter_plea(
        case_id=cid, plea=PleaKind.GUILTY, now_day=11,
    )
    assert s.render_verdict(
        case_id=cid, verdict=Verdict.GUILTY_FINE,
        judge_id="judge_smith", now_day=12,
        sentence_value=5_000,
    ) is True


def test_verdict_before_plea_blocked():
    s = CityCourtSystem()
    cid = _file(s)
    assert s.render_verdict(
        case_id=cid, verdict=Verdict.GUILTY_FINE,
        judge_id="j", now_day=12,
    ) is False


def test_verdict_blank_judge():
    s = CityCourtSystem()
    cid = _file(s)
    s.enter_plea(
        case_id=cid, plea=PleaKind.GUILTY, now_day=11,
    )
    assert s.render_verdict(
        case_id=cid, verdict=Verdict.ACQUITTED,
        judge_id="", now_day=12,
    ) is False


def test_verdict_negative_sentence():
    s = CityCourtSystem()
    cid = _file(s)
    s.enter_plea(
        case_id=cid, plea=PleaKind.GUILTY, now_day=11,
    )
    assert s.render_verdict(
        case_id=cid, verdict=Verdict.GUILTY_FINE,
        judge_id="j", now_day=12, sentence_value=-1,
    ) is False


def test_execute_sentence_happy():
    s = CityCourtSystem()
    cid = _file(s)
    s.enter_plea(
        case_id=cid, plea=PleaKind.GUILTY, now_day=11,
    )
    s.render_verdict(
        case_id=cid, verdict=Verdict.GUILTY_PRISON,
        judge_id="j", now_day=12, sentence_value=30,
    )
    assert s.execute_sentence(
        case_id=cid, now_day=12,
    ) is True


def test_execute_before_verdict_blocked():
    s = CityCourtSystem()
    cid = _file(s)
    s.enter_plea(
        case_id=cid, plea=PleaKind.GUILTY, now_day=11,
    )
    assert s.execute_sentence(
        case_id=cid, now_day=12,
    ) is False


def test_double_execute_blocked():
    s = CityCourtSystem()
    cid = _file(s)
    s.enter_plea(
        case_id=cid, plea=PleaKind.GUILTY, now_day=11,
    )
    s.render_verdict(
        case_id=cid, verdict=Verdict.ACQUITTED,
        judge_id="j", now_day=12,
    )
    s.execute_sentence(case_id=cid, now_day=12)
    assert s.execute_sentence(
        case_id=cid, now_day=13,
    ) is False


def test_acquittal_full_flow():
    s = CityCourtSystem()
    cid = _file(s)
    s.enter_plea(
        case_id=cid, plea=PleaKind.NOT_GUILTY,
        now_day=11,
    )
    s.render_verdict(
        case_id=cid, verdict=Verdict.ACQUITTED,
        judge_id="j", now_day=12,
    )
    s.execute_sentence(case_id=cid, now_day=12)
    c = s.case(case_id=cid)
    assert c.state == CaseState.EXECUTED
    assert c.verdict == Verdict.ACQUITTED


def test_cases_for_defendant():
    s = CityCourtSystem()
    _file(s, defendant_id="bob")
    _file(s, defendant_id="bob")
    _file(s, defendant_id="cara")
    assert len(s.cases_for(defendant_id="bob")) == 2


def test_open_cases_excludes_executed():
    s = CityCourtSystem()
    cid_open = _file(s)
    cid_done = _file(s)
    s.enter_plea(
        case_id=cid_done, plea=PleaKind.GUILTY,
        now_day=11,
    )
    s.render_verdict(
        case_id=cid_done, verdict=Verdict.ACQUITTED,
        judge_id="j", now_day=12,
    )
    s.execute_sentence(case_id=cid_done, now_day=12)
    out = s.open_cases()
    ids = [c.case_id for c in out]
    assert cid_open in ids
    assert cid_done not in ids


def test_case_unknown():
    s = CityCourtSystem()
    assert s.case(case_id="ghost") is None


def test_enum_counts():
    assert len(list(Verdict)) == 5
    assert len(list(PleaKind)) == 2
    assert len(list(CaseState)) == 4
