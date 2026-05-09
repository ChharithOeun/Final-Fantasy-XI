"""Tests for player_press_syndication."""
from __future__ import annotations

from server.player_press_syndication import (
    PlayerPressSyndicationSystem, DealState,
)


def _propose(
    s: PlayerPressSyndicationSystem,
    royalty: int = 10,
) -> str:
    return s.propose_deal(
        source_paper_id="paper_a",
        dest_paper_id="paper_b",
        source_editor_id="naji",
        dest_editor_id="cara",
        royalty_pct=royalty,
    )


def _through_active(
    s: PlayerPressSyndicationSystem,
) -> str:
    did = _propose(s)
    s.accept_deal(deal_id=did, dest_editor_id="cara")
    return did


def test_propose_happy():
    s = PlayerPressSyndicationSystem()
    assert _propose(s) is not None


def test_propose_self_deal_blocked():
    s = PlayerPressSyndicationSystem()
    assert s.propose_deal(
        source_paper_id="paper_a",
        dest_paper_id="paper_a",
        source_editor_id="x", dest_editor_id="y",
        royalty_pct=10,
    ) is None


def test_propose_same_editor_blocked():
    s = PlayerPressSyndicationSystem()
    assert s.propose_deal(
        source_paper_id="a", dest_paper_id="b",
        source_editor_id="naji",
        dest_editor_id="naji", royalty_pct=10,
    ) is None


def test_propose_zero_royalty_blocked():
    s = PlayerPressSyndicationSystem()
    assert _propose(s, royalty=0) is None


def test_propose_excessive_royalty_blocked():
    s = PlayerPressSyndicationSystem()
    assert _propose(s, royalty=80) is None


def test_accept_deal_happy():
    s = PlayerPressSyndicationSystem()
    did = _propose(s)
    assert s.accept_deal(
        deal_id=did, dest_editor_id="cara",
    ) is True
    assert s.deal(
        deal_id=did,
    ).state == DealState.ACTIVE


def test_accept_deal_by_source_blocked():
    s = PlayerPressSyndicationSystem()
    did = _propose(s)
    assert s.accept_deal(
        deal_id=did, dest_editor_id="naji",
    ) is False


def test_accept_deal_twice_blocked():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    assert s.accept_deal(
        deal_id=did, dest_editor_id="cara",
    ) is False


def test_syndicate_article_happy():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    aid = s.syndicate_article(
        deal_id=did, source_editor_id="naji",
        title="Beastmen Sighted in Tahrongi",
    )
    assert aid is not None


def test_syndicate_before_accept_blocked():
    s = PlayerPressSyndicationSystem()
    did = _propose(s)
    assert s.syndicate_article(
        deal_id=did, source_editor_id="naji",
        title="x",
    ) is None


def test_syndicate_by_dest_blocked():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    assert s.syndicate_article(
        deal_id=did, source_editor_id="cara",
        title="x",
    ) is None


def test_syndicate_after_end_blocked():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    s.end_deal(deal_id=did, terminator_id="naji")
    assert s.syndicate_article(
        deal_id=did, source_editor_id="naji",
        title="x",
    ) is None


def test_record_revenue_happy():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    # 10% royalty * 1000 gil * 2/4 ratio = 50 gil
    royalty = s.record_issue_revenue(
        deal_id=did, dest_editor_id="cara",
        issue_revenue_gil=1000, articles_used=2,
        total_articles_in_issue=4,
    )
    assert royalty == 50


def test_record_revenue_zero_articles_blocked():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    assert s.record_issue_revenue(
        deal_id=did, dest_editor_id="cara",
        issue_revenue_gil=1000, articles_used=0,
        total_articles_in_issue=4,
    ) is None


def test_record_revenue_too_many_articles_blocked():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    assert s.record_issue_revenue(
        deal_id=did, dest_editor_id="cara",
        issue_revenue_gil=1000, articles_used=5,
        total_articles_in_issue=4,
    ) is None


def test_record_revenue_by_source_blocked():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    assert s.record_issue_revenue(
        deal_id=did, dest_editor_id="naji",
        issue_revenue_gil=1000, articles_used=2,
        total_articles_in_issue=4,
    ) is None


def test_record_revenue_accumulates():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    s.record_issue_revenue(
        deal_id=did, dest_editor_id="cara",
        issue_revenue_gil=1000, articles_used=2,
        total_articles_in_issue=4,
    )
    s.record_issue_revenue(
        deal_id=did, dest_editor_id="cara",
        issue_revenue_gil=2000, articles_used=1,
        total_articles_in_issue=4,
    )
    # 50 + 50 = 100
    assert s.deal(
        deal_id=did,
    ).total_royalty_paid_gil == 100


def test_end_deal_by_source_happy():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    assert s.end_deal(
        deal_id=did, terminator_id="naji",
    ) is True


def test_end_deal_by_dest_happy():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    assert s.end_deal(
        deal_id=did, terminator_id="cara",
    ) is True


def test_end_deal_by_stranger_blocked():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    assert s.end_deal(
        deal_id=did, terminator_id="bob",
    ) is False


def test_end_deal_already_ended_blocked():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    s.end_deal(deal_id=did, terminator_id="naji")
    assert s.end_deal(
        deal_id=did, terminator_id="cara",
    ) is False


def test_articles_listing():
    s = PlayerPressSyndicationSystem()
    did = _through_active(s)
    s.syndicate_article(
        deal_id=did, source_editor_id="naji",
        title="t1",
    )
    s.syndicate_article(
        deal_id=did, source_editor_id="naji",
        title="t2",
    )
    assert len(s.articles(deal_id=did)) == 2


def test_unknown_deal():
    s = PlayerPressSyndicationSystem()
    assert s.deal(deal_id="ghost") is None


def test_enum_count():
    assert len(list(DealState)) == 3
