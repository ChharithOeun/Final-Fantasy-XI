"""Tests for crew disbandment."""
from __future__ import annotations

from server.crew_disbandment import (
    BUYOUT_PCT,
    COOLING_OFF_SECONDS,
    CAPTAIN_SHARE_BONUS,
    CrewDisbandment,
    DisbandStage,
)


def test_propose_happy():
    d = CrewDisbandment()
    r = d.propose(
        charter_id="c1", captain_id="cap", now_seconds=0,
    )
    assert r.accepted is True
    assert r.stage == DisbandStage.PROPOSED


def test_propose_blank_ids():
    d = CrewDisbandment()
    r = d.propose(charter_id="", captain_id="cap", now_seconds=0)
    assert r.accepted is False


def test_propose_double_blocked():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    r = d.propose(
        charter_id="c1", captain_id="cap", now_seconds=10,
    )
    assert r.accepted is False


def test_cancel_within_window():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    r = d.cancel(
        charter_id="c1", captain_id="cap", now_seconds=3_600,
    )
    assert r.accepted is True
    assert r.stage == DisbandStage.CANCELLED


def test_cancel_after_window_blocked():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    r = d.cancel(
        charter_id="c1", captain_id="cap",
        now_seconds=COOLING_OFF_SECONDS + 1,
    )
    assert r.accepted is False


def test_cancel_wrong_captain():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    r = d.cancel(
        charter_id="c1", captain_id="other", now_seconds=10,
    )
    assert r.accepted is False


def test_ratify_after_cooling_off():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    r = d.ratify(
        charter_id="c1",
        now_seconds=COOLING_OFF_SECONDS + 1,
    )
    assert r.accepted is True
    assert r.stage == DisbandStage.RATIFIED


def test_ratify_too_early():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    r = d.ratify(charter_id="c1", now_seconds=10)
    assert r.accepted is False


def test_ratify_no_proposal():
    d = CrewDisbandment()
    r = d.ratify(
        charter_id="c1",
        now_seconds=COOLING_OFF_SECONDS + 1,
    )
    assert r.accepted is False


def test_compute_shares_by_tenure():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    shares = d.compute_shares(
        charter_id="c1",
        members_with_tenure_weeks={
            "cap": 10, "m1": 5, "m2": 5,
        },
        captain_id="cap",
        total_holdings_value=10_000,
    )
    # cap shares = 10 + 5 = 15; m1 = 5; m2 = 5; total = 25
    # cap = 10000 * 15/25 = 6000; m1 = m2 = 2000
    assert shares["cap"] == 6_000
    assert shares["m1"] == 2_000
    assert shares["m2"] == 2_000


def test_compute_shares_zero_holdings():
    d = CrewDisbandment()
    shares = d.compute_shares(
        charter_id="c1",
        members_with_tenure_weeks={"cap": 5, "m1": 3},
        captain_id="cap",
        total_holdings_value=0,
    )
    assert shares["cap"] == 0
    assert shares["m1"] == 0


def test_buyout_happy():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    r = d.buyout(
        charter_id="c1", member_id="m1",
        total_value=10_000, now_seconds=10,
    )
    assert r.accepted is True
    assert r.payout_gil == 2_500   # 25% of 10000


def test_buyout_captain_blocked():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    r = d.buyout(
        charter_id="c1", member_id="cap",
        total_value=1_000, now_seconds=10,
    )
    assert r.accepted is False


def test_buyout_double_blocked():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    d.buyout(
        charter_id="c1", member_id="m1",
        total_value=1_000, now_seconds=10,
    )
    r = d.buyout(
        charter_id="c1", member_id="m1",
        total_value=1_000, now_seconds=20,
    )
    assert r.accepted is False


def test_buyout_excludes_from_distribution():
    d = CrewDisbandment()
    d.propose(charter_id="c1", captain_id="cap", now_seconds=0)
    d.buyout(
        charter_id="c1", member_id="m1",
        total_value=10_000, now_seconds=10,
    )
    shares = d.compute_shares(
        charter_id="c1",
        members_with_tenure_weeks={
            "cap": 5, "m1": 5, "m2": 5,
        },
        captain_id="cap",
        total_holdings_value=10_000,
    )
    # m1 bought out — gets nothing in distribution
    assert "m1" not in shares
    # cap and m2 split
    assert shares["cap"] > 0
    assert shares["m2"] > 0


def test_stage_of_default_none():
    d = CrewDisbandment()
    assert d.stage_of(charter_id="ghost") == DisbandStage.NONE
