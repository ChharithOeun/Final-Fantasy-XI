"""Tests for nation_officer_recruitment."""
from __future__ import annotations

from server.nation_officer_recruitment import (
    NationOfficerRecruitmentSystem,
    RecruitmentState,
)


def _open(s, **overrides):
    args = dict(
        free_officer_id="off_zhuge",
        min_bid_gil=10_000, opened_day=10,
        closes_day=20,
    )
    args.update(overrides)
    return s.open(**args)


def test_open_happy():
    s = NationOfficerRecruitmentSystem()
    assert _open(s) is not None


def test_open_blank_officer():
    s = NationOfficerRecruitmentSystem()
    assert _open(s, free_officer_id="") is None


def test_open_inverted_dates():
    s = NationOfficerRecruitmentSystem()
    assert _open(
        s, opened_day=20, closes_day=10,
    ) is None


def test_open_dup_officer_blocked():
    s = NationOfficerRecruitmentSystem()
    _open(s)
    assert _open(s) is None


def test_place_bid_happy():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s)
    assert s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=80,
        gil=15_000, now_day=12,
    ) is True


def test_bid_below_min_blocked():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s, min_bid_gil=10_000)
    assert s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=80,
        gil=5_000, now_day=12,
    ) is False


def test_bid_after_close_blocked():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s, closes_day=20)
    assert s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=80,
        gil=15_000, now_day=25,
    ) is False


def test_bid_invalid_charisma():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s)
    assert s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=120,
        gil=15_000, now_day=12,
    ) is False


def test_same_nation_higher_overrides():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s)
    s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=80,
        gil=12_000, now_day=12,
    )
    assert s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=80,
        gil=15_000, now_day=13,
    ) is True
    bids = s.bids_for(recruitment_id=rid)
    assert len(bids) == 1
    assert bids[0].gil == 15_000


def test_same_nation_same_or_lower_blocked():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s)
    s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=80,
        gil=15_000, now_day=12,
    )
    assert s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=80,
        gil=15_000, now_day=13,
    ) is False


def test_close_happy_returns_winner():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s, closes_day=20)
    s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=80,
        gil=15_000, now_day=12,
    )
    s.place_bid(
        recruitment_id=rid, nation_id="windy",
        envoy_id="kerutoto", envoy_charisma=85,
        gil=20_000, now_day=14,
    )
    winner = s.close(
        recruitment_id=rid, now_day=20,
    )
    assert winner == "windy"


def test_close_tie_charisma_breaks():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s, closes_day=20)
    s.place_bid(
        recruitment_id=rid, nation_id="bastok",
        envoy_id="naji", envoy_charisma=70,
        gil=15_000, now_day=12,
    )
    s.place_bid(
        recruitment_id=rid, nation_id="windy",
        envoy_id="kerutoto", envoy_charisma=85,
        gil=15_000, now_day=14,
    )
    winner = s.close(
        recruitment_id=rid, now_day=20,
    )
    assert winner == "windy"


def test_close_no_bids_returns_none():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s, closes_day=20)
    assert s.close(
        recruitment_id=rid, now_day=20,
    ) is None
    r = s.recruitment(recruitment_id=rid)
    assert r.state == RecruitmentState.CLOSED


def test_close_too_early():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s, closes_day=20)
    assert s.close(
        recruitment_id=rid, now_day=15,
    ) is None
    r = s.recruitment(recruitment_id=rid)
    assert r.state == RecruitmentState.OPEN


def test_close_double_blocked():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s)
    s.close(recruitment_id=rid, now_day=20)
    assert s.close(
        recruitment_id=rid, now_day=21,
    ) is None


def test_cancel():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s)
    assert s.cancel(
        recruitment_id=rid, now_day=12,
    ) is True


def test_cancel_after_close_blocked():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s)
    s.close(recruitment_id=rid, now_day=20)
    assert s.cancel(
        recruitment_id=rid, now_day=21,
    ) is False


def test_open_recruitments():
    s = NationOfficerRecruitmentSystem()
    rid_a = _open(s, free_officer_id="a")
    rid_b = _open(s, free_officer_id="b")
    s.cancel(recruitment_id=rid_a, now_day=12)
    out = s.open_recruitments()
    ids = [r.recruitment_id for r in out]
    assert rid_a not in ids
    assert rid_b in ids


def test_bids_for_unknown():
    s = NationOfficerRecruitmentSystem()
    assert s.bids_for(
        recruitment_id="ghost",
    ) == []


def test_recruitment_unknown():
    s = NationOfficerRecruitmentSystem()
    assert s.recruitment(
        recruitment_id="ghost",
    ) is None


def test_winner_winning_gil_recorded():
    s = NationOfficerRecruitmentSystem()
    rid = _open(s, closes_day=20)
    s.place_bid(
        recruitment_id=rid, nation_id="windy",
        envoy_id="kerutoto", envoy_charisma=85,
        gil=20_000, now_day=14,
    )
    s.close(recruitment_id=rid, now_day=20)
    r = s.recruitment(recruitment_id=rid)
    assert r.winning_nation == "windy"
    assert r.winning_gil == 20_000


def test_enum_count():
    assert len(list(RecruitmentState)) == 3
