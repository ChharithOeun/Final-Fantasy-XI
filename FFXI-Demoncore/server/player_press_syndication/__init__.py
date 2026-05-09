"""Player press syndication — newspaper-to-newspaper licensing.

Two newspapers strike a syndication deal: the source paper
licenses articles to the destination paper for reprinting.
The deal is contracted with a royalty percentage; whenever
the destination paper records revenue from an issue that
contains syndicated articles, royalty is paid back to the
source proportional to the number of syndicated slots in
that issue.

Lifecycle (deal)
    PROPOSED      source proposed, awaiting dest
    ACTIVE        accepted; reprints flowing
    ENDED         either party terminated

Public surface
--------------
    DealState enum
    SyndicationDeal dataclass (frozen)
    SyndicatedArticle dataclass (frozen)
    PlayerPressSyndicationSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MAX_ROYALTY_PCT = 50
_MAX_ARTICLES_PER_ISSUE = 6


class DealState(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    ENDED = "ended"


@dataclasses.dataclass(frozen=True)
class SyndicationDeal:
    deal_id: str
    source_paper_id: str
    dest_paper_id: str
    source_editor_id: str
    dest_editor_id: str
    royalty_pct: int
    state: DealState
    total_royalty_paid_gil: int


@dataclasses.dataclass(frozen=True)
class SyndicatedArticle:
    article_id: str
    deal_id: str
    title: str


@dataclasses.dataclass
class _DState:
    spec: SyndicationDeal
    articles: dict[str, SyndicatedArticle] = (
        dataclasses.field(default_factory=dict)
    )


@dataclasses.dataclass
class PlayerPressSyndicationSystem:
    _deals: dict[str, _DState] = dataclasses.field(
        default_factory=dict,
    )
    _next_deal: int = 1
    _next_article: int = 1

    def propose_deal(
        self, *, source_paper_id: str,
        dest_paper_id: str,
        source_editor_id: str,
        dest_editor_id: str,
        royalty_pct: int,
    ) -> t.Optional[str]:
        if not source_paper_id or not dest_paper_id:
            return None
        if source_paper_id == dest_paper_id:
            return None
        if not source_editor_id or not dest_editor_id:
            return None
        if source_editor_id == dest_editor_id:
            return None
        if not 1 <= royalty_pct <= _MAX_ROYALTY_PCT:
            return None
        did = f"deal_{self._next_deal}"
        self._next_deal += 1
        self._deals[did] = _DState(
            spec=SyndicationDeal(
                deal_id=did,
                source_paper_id=source_paper_id,
                dest_paper_id=dest_paper_id,
                source_editor_id=source_editor_id,
                dest_editor_id=dest_editor_id,
                royalty_pct=royalty_pct,
                state=DealState.PROPOSED,
                total_royalty_paid_gil=0,
            ),
        )
        return did

    def accept_deal(
        self, *, deal_id: str, dest_editor_id: str,
    ) -> bool:
        if deal_id not in self._deals:
            return False
        st = self._deals[deal_id]
        if st.spec.state != DealState.PROPOSED:
            return False
        if st.spec.dest_editor_id != dest_editor_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=DealState.ACTIVE,
        )
        return True

    def syndicate_article(
        self, *, deal_id: str,
        source_editor_id: str, title: str,
    ) -> t.Optional[str]:
        if deal_id not in self._deals:
            return None
        st = self._deals[deal_id]
        if st.spec.state != DealState.ACTIVE:
            return None
        if st.spec.source_editor_id != source_editor_id:
            return None
        if not title:
            return None
        aid = f"synd_{self._next_article}"
        self._next_article += 1
        st.articles[aid] = SyndicatedArticle(
            article_id=aid, deal_id=deal_id,
            title=title,
        )
        return aid

    def record_issue_revenue(
        self, *, deal_id: str,
        dest_editor_id: str,
        issue_revenue_gil: int,
        articles_used: int,
        total_articles_in_issue: int,
    ) -> t.Optional[int]:
        """Records a destination-paper issue's revenue
        and returns the royalty payable to the source.
        Returns None on validation failure."""
        if deal_id not in self._deals:
            return None
        st = self._deals[deal_id]
        if st.spec.state != DealState.ACTIVE:
            return None
        if st.spec.dest_editor_id != dest_editor_id:
            return None
        if issue_revenue_gil < 0:
            return None
        if articles_used <= 0:
            return None
        if (
            total_articles_in_issue <= 0
            or total_articles_in_issue
            > _MAX_ARTICLES_PER_ISSUE
        ):
            return None
        if articles_used > total_articles_in_issue:
            return None
        royalty = (
            issue_revenue_gil
            * st.spec.royalty_pct
            * articles_used
            // (100 * total_articles_in_issue)
        )
        st.spec = dataclasses.replace(
            st.spec,
            total_royalty_paid_gil=(
                st.spec.total_royalty_paid_gil
                + royalty
            ),
        )
        return royalty

    def end_deal(
        self, *, deal_id: str, terminator_id: str,
    ) -> bool:
        if deal_id not in self._deals:
            return False
        st = self._deals[deal_id]
        if st.spec.state == DealState.ENDED:
            return False
        if terminator_id not in (
            st.spec.source_editor_id,
            st.spec.dest_editor_id,
        ):
            return False
        st.spec = dataclasses.replace(
            st.spec, state=DealState.ENDED,
        )
        return True

    def deal(
        self, *, deal_id: str,
    ) -> t.Optional[SyndicationDeal]:
        st = self._deals.get(deal_id)
        return st.spec if st else None

    def articles(
        self, *, deal_id: str,
    ) -> list[SyndicatedArticle]:
        st = self._deals.get(deal_id)
        if st is None:
            return []
        return list(st.articles.values())


__all__ = [
    "DealState", "SyndicationDeal",
    "SyndicatedArticle",
    "PlayerPressSyndicationSystem",
]
