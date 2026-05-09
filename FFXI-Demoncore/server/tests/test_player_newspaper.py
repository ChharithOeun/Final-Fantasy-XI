"""Tests for player_newspaper."""
from __future__ import annotations

from server.player_newspaper import (
    PlayerNewspaperSystem, PaperState, IssueState,
)


def _found(s: PlayerNewspaperSystem) -> str:
    return s.found_paper(
        editor_id="naji", name="Bastok Times",
        weekly_subscription_gil=100,
    )


def test_found_happy():
    s = PlayerNewspaperSystem()
    assert _found(s) is not None


def test_found_empty_editor_blocked():
    s = PlayerNewspaperSystem()
    assert s.found_paper(
        editor_id="", name="x",
        weekly_subscription_gil=100,
    ) is None


def test_found_zero_subscription_blocked():
    s = PlayerNewspaperSystem()
    assert s.found_paper(
        editor_id="naji", name="x",
        weekly_subscription_gil=0,
    ) is None


def test_subscribe_happy():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    assert s.subscribe(
        paper_id=pid, subscriber_id="bob",
    ) is True


def test_subscribe_editor_self_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    assert s.subscribe(
        paper_id=pid, subscriber_id="naji",
    ) is False


def test_subscribe_duplicate_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    s.subscribe(paper_id=pid, subscriber_id="bob")
    assert s.subscribe(
        paper_id=pid, subscriber_id="bob",
    ) is False


def test_unsubscribe_happy():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    s.subscribe(paper_id=pid, subscriber_id="bob")
    assert s.unsubscribe(
        paper_id=pid, subscriber_id="bob",
    ) is True


def test_begin_issue_happy():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    iid = s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=10,
    )
    assert iid is not None


def test_begin_issue_not_editor_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    assert s.begin_issue(
        paper_id=pid, editor_id="bob", issue_day=10,
    ) is None


def test_begin_issue_too_soon_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    iid = s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=10,
    )
    s.add_article(
        paper_id=pid, issue_id=iid,
        author_id="naji", headline="hi",
    )
    s.publish_issue(
        paper_id=pid, issue_id=iid, editor_id="naji",
    )
    # Less than 7 days later
    assert s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=12,
    ) is None


def test_add_article_happy():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    iid = s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=10,
    )
    aid = s.add_article(
        paper_id=pid, issue_id=iid,
        author_id="bob", headline="Cardian Sale!",
    )
    assert aid is not None


def test_add_article_cap_reached_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    iid = s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=10,
    )
    for i in range(6):
        s.add_article(
            paper_id=pid, issue_id=iid,
            author_id=f"a_{i}", headline=f"h_{i}",
        )
    assert s.add_article(
        paper_id=pid, issue_id=iid,
        author_id="overflow", headline="x",
    ) is None


def test_publish_issue_happy_revenue():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    s.subscribe(paper_id=pid, subscriber_id="bob")
    s.subscribe(paper_id=pid, subscriber_id="cara")
    s.subscribe(paper_id=pid, subscriber_id="dax")
    iid = s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=10,
    )
    s.add_article(
        paper_id=pid, issue_id=iid,
        author_id="naji", headline="news",
    )
    rev = s.publish_issue(
        paper_id=pid, issue_id=iid, editor_id="naji",
    )
    assert rev == 300


def test_publish_issue_empty_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    iid = s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=10,
    )
    assert s.publish_issue(
        paper_id=pid, issue_id=iid, editor_id="naji",
    ) is None


def test_publish_issue_not_editor_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    iid = s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=10,
    )
    s.add_article(
        paper_id=pid, issue_id=iid,
        author_id="x", headline="y",
    )
    assert s.publish_issue(
        paper_id=pid, issue_id=iid, editor_id="bob",
    ) is None


def test_close_paper_happy():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    assert s.close_paper(
        paper_id=pid, editor_id="naji",
    ) is True
    assert s.paper(
        paper_id=pid,
    ).state == PaperState.CLOSED


def test_close_paper_not_editor_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    assert s.close_paper(
        paper_id=pid, editor_id="bob",
    ) is False


def test_subscribe_to_closed_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    s.close_paper(paper_id=pid, editor_id="naji")
    assert s.subscribe(
        paper_id=pid, subscriber_id="bob",
    ) is False


def test_publish_after_close_blocked():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    iid = s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=10,
    )
    s.add_article(
        paper_id=pid, issue_id=iid,
        author_id="x", headline="y",
    )
    s.close_paper(paper_id=pid, editor_id="naji")
    assert s.publish_issue(
        paper_id=pid, issue_id=iid, editor_id="naji",
    ) is None


def test_prior_issue_archived_on_new_begin():
    s = PlayerNewspaperSystem()
    pid = _found(s)
    iid1 = s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=10,
    )
    s.add_article(
        paper_id=pid, issue_id=iid1,
        author_id="x", headline="y",
    )
    s.publish_issue(
        paper_id=pid, issue_id=iid1, editor_id="naji",
    )
    s.begin_issue(
        paper_id=pid, editor_id="naji", issue_day=20,
    )
    assert s.issue(
        paper_id=pid, issue_id=iid1,
    ).state == IssueState.ARCHIVED


def test_unknown_paper():
    s = PlayerNewspaperSystem()
    assert s.paper(paper_id="ghost") is None


def test_enum_counts():
    assert len(list(PaperState)) == 2
    assert len(list(IssueState)) == 3
