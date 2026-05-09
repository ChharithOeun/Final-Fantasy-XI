"""Player newspaper — weekly subscription publication.

An editor founds a newspaper, subscribers pay a weekly fee,
and each issue collects revenue from the active subscriber
base. Editors compose issues from articles submitted by
correspondents and stamp them PUBLISHED to bill subscribers
and lock the issue into the historical record.

Lifecycle (paper)
    ACTIVE       open for subscriptions and issues
    CLOSED       editor wound the paper down

Lifecycle (issue)
    DRAFT        editor still composing
    PUBLISHED    delivered, subscribers billed
    ARCHIVED     historical (auto on next issue)

Public surface
--------------
    PaperState enum
    IssueState enum
    Newspaper dataclass (frozen)
    Issue dataclass (frozen)
    Article dataclass (frozen)
    PlayerNewspaperSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MAX_ARTICLES_PER_ISSUE = 6
_MIN_DAYS_BETWEEN_ISSUES = 7


class PaperState(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class IssueState(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclasses.dataclass(frozen=True)
class Newspaper:
    paper_id: str
    editor_id: str
    name: str
    weekly_subscription_gil: int
    state: PaperState
    last_issue_day: int


@dataclasses.dataclass(frozen=True)
class Article:
    article_id: str
    author_id: str
    headline: str


@dataclasses.dataclass(frozen=True)
class Issue:
    issue_id: str
    paper_id: str
    issue_day: int
    state: IssueState
    revenue_gil: int


@dataclasses.dataclass
class _IState:
    spec: Issue
    articles: list[Article] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class _PState:
    spec: Newspaper
    subscribers: set[str] = dataclasses.field(
        default_factory=set,
    )
    issues: dict[str, _IState] = dataclasses.field(
        default_factory=dict,
    )
    issue_order: list[str] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class PlayerNewspaperSystem:
    _papers: dict[str, _PState] = dataclasses.field(
        default_factory=dict,
    )
    _next_paper: int = 1
    _next_issue: int = 1
    _next_article: int = 1

    def found_paper(
        self, *, editor_id: str, name: str,
        weekly_subscription_gil: int,
    ) -> t.Optional[str]:
        if not editor_id or not name:
            return None
        if weekly_subscription_gil <= 0:
            return None
        pid = f"paper_{self._next_paper}"
        self._next_paper += 1
        self._papers[pid] = _PState(
            spec=Newspaper(
                paper_id=pid, editor_id=editor_id,
                name=name,
                weekly_subscription_gil=(
                    weekly_subscription_gil
                ),
                state=PaperState.ACTIVE,
                last_issue_day=-_MIN_DAYS_BETWEEN_ISSUES,
            ),
        )
        return pid

    def subscribe(
        self, *, paper_id: str, subscriber_id: str,
    ) -> bool:
        if paper_id not in self._papers:
            return False
        st = self._papers[paper_id]
        if st.spec.state != PaperState.ACTIVE:
            return False
        if not subscriber_id:
            return False
        if subscriber_id == st.spec.editor_id:
            return False
        if subscriber_id in st.subscribers:
            return False
        st.subscribers.add(subscriber_id)
        return True

    def unsubscribe(
        self, *, paper_id: str, subscriber_id: str,
    ) -> bool:
        if paper_id not in self._papers:
            return False
        st = self._papers[paper_id]
        if subscriber_id not in st.subscribers:
            return False
        st.subscribers.remove(subscriber_id)
        return True

    def begin_issue(
        self, *, paper_id: str, editor_id: str,
        issue_day: int,
    ) -> t.Optional[str]:
        if paper_id not in self._papers:
            return None
        st = self._papers[paper_id]
        if st.spec.state != PaperState.ACTIVE:
            return None
        if st.spec.editor_id != editor_id:
            return None
        elapsed = issue_day - st.spec.last_issue_day
        if elapsed < _MIN_DAYS_BETWEEN_ISSUES:
            return None
        # Any prior PUBLISHED issue becomes ARCHIVED
        for prior_id in st.issue_order:
            ist = st.issues[prior_id]
            if ist.spec.state == IssueState.PUBLISHED:
                ist.spec = dataclasses.replace(
                    ist.spec, state=IssueState.ARCHIVED,
                )
        iid = f"issue_{self._next_issue}"
        self._next_issue += 1
        st.issues[iid] = _IState(
            spec=Issue(
                issue_id=iid, paper_id=paper_id,
                issue_day=issue_day,
                state=IssueState.DRAFT,
                revenue_gil=0,
            ),
        )
        st.issue_order.append(iid)
        return iid

    def add_article(
        self, *, paper_id: str, issue_id: str,
        author_id: str, headline: str,
    ) -> t.Optional[str]:
        if paper_id not in self._papers:
            return None
        st = self._papers[paper_id]
        if st.spec.state != PaperState.ACTIVE:
            return None
        if issue_id not in st.issues:
            return None
        ist = st.issues[issue_id]
        if ist.spec.state != IssueState.DRAFT:
            return None
        if not author_id or not headline:
            return None
        if len(ist.articles) >= _MAX_ARTICLES_PER_ISSUE:
            return None
        aid = f"art_{self._next_article}"
        self._next_article += 1
        ist.articles.append(Article(
            article_id=aid, author_id=author_id,
            headline=headline,
        ))
        return aid

    def publish_issue(
        self, *, paper_id: str, issue_id: str,
        editor_id: str,
    ) -> t.Optional[int]:
        """Returns the gil revenue collected from
        subscribers, or None on failure."""
        if paper_id not in self._papers:
            return None
        st = self._papers[paper_id]
        if st.spec.state != PaperState.ACTIVE:
            return None
        if st.spec.editor_id != editor_id:
            return None
        if issue_id not in st.issues:
            return None
        ist = st.issues[issue_id]
        if ist.spec.state != IssueState.DRAFT:
            return None
        if not ist.articles:
            return None
        revenue = (
            len(st.subscribers)
            * st.spec.weekly_subscription_gil
        )
        ist.spec = dataclasses.replace(
            ist.spec, state=IssueState.PUBLISHED,
            revenue_gil=revenue,
        )
        st.spec = dataclasses.replace(
            st.spec, last_issue_day=ist.spec.issue_day,
        )
        return revenue

    def close_paper(
        self, *, paper_id: str, editor_id: str,
    ) -> bool:
        if paper_id not in self._papers:
            return False
        st = self._papers[paper_id]
        if st.spec.state != PaperState.ACTIVE:
            return False
        if st.spec.editor_id != editor_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=PaperState.CLOSED,
        )
        return True

    def paper(
        self, *, paper_id: str,
    ) -> t.Optional[Newspaper]:
        st = self._papers.get(paper_id)
        return st.spec if st else None

    def issue(
        self, *, paper_id: str, issue_id: str,
    ) -> t.Optional[Issue]:
        st = self._papers.get(paper_id)
        if st is None:
            return None
        ist = st.issues.get(issue_id)
        return ist.spec if ist else None

    def subscribers(
        self, *, paper_id: str,
    ) -> list[str]:
        st = self._papers.get(paper_id)
        if st is None:
            return []
        return sorted(st.subscribers)

    def issues(
        self, *, paper_id: str,
    ) -> list[Issue]:
        st = self._papers.get(paper_id)
        if st is None:
            return []
        return [
            st.issues[iid].spec
            for iid in st.issue_order
        ]

    def articles(
        self, *, paper_id: str, issue_id: str,
    ) -> list[Article]:
        st = self._papers.get(paper_id)
        if st is None:
            return []
        ist = st.issues.get(issue_id)
        if ist is None:
            return []
        return list(ist.articles)


__all__ = [
    "PaperState", "IssueState", "Newspaper",
    "Issue", "Article", "PlayerNewspaperSystem",
]
