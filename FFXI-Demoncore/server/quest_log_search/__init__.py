"""Quest log search — full-text search + filter across the log.

Spans both the MSQ tracker (quest_log_msq_tracker) and the
side-quest clue system (side_quest_clue_system). The player can
type a query, optionally narrowing by:

  expansion        Expansion enum filter
  status           IN_PROGRESS / COMPLETE / NOT_STARTED
  level_min/max   level band on MSQ steps
  side_only / msq_only   limit which track is searched
  fragment_min    minimum visible legibility for side quests

The search is INDEXED — each registered quest's title +
description is split into tokens. Queries match on token
substrings (case-insensitive). Returns ranked results sorted
by score desc, deterministic by quest_id tiebreak.

This is INTERNAL bookkeeping; it does not modify quest state.

Public surface
--------------
    QuestSource enum
    SearchHit dataclass
    QuestLogSearch
        .index_quest(quest_id, source, expansion, title,
                     description, level_min, level_max)
        .update_status(quest_id, status_str, side_legibility_str)
        .search(query, ...) -> tuple[SearchHit]
        .clear_index()
"""
from __future__ import annotations

import dataclasses
import enum
import re
import typing as t


class QuestSource(str, enum.Enum):
    MSQ = "msq"
    SIDE = "side"


@dataclasses.dataclass
class _IndexedQuest:
    quest_id: str
    source: QuestSource
    expansion: str
    title: str
    description: str
    level_min: int
    level_max: int
    status: str = "in_progress"
    side_legibility: str = "hidden"     # only for side quests
    tokens: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class SearchHit:
    quest_id: str
    source: QuestSource
    title: str
    snippet: str
    score: int
    expansion: str
    status: str


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(
        m.group(0).lower()
        for m in _TOKEN_RE.finditer(text)
    )


@dataclasses.dataclass
class QuestLogSearch:
    _quests: dict[str, _IndexedQuest] = dataclasses.field(
        default_factory=dict,
    )

    def index_quest(
        self, *, quest_id: str, source: QuestSource,
        expansion: str, title: str,
        description: str = "",
        level_min: int = 1,
        level_max: int = 99,
        status: str = "in_progress",
        side_legibility: str = "hidden",
    ) -> bool:
        q = _IndexedQuest(
            quest_id=quest_id, source=source,
            expansion=expansion, title=title,
            description=description,
            level_min=level_min, level_max=level_max,
            status=status,
            side_legibility=side_legibility,
            tokens=_tokenize(title + " " + description),
        )
        self._quests[quest_id] = q
        return True

    def update_status(
        self, *, quest_id: str,
        status: t.Optional[str] = None,
        side_legibility: t.Optional[str] = None,
    ) -> bool:
        q = self._quests.get(quest_id)
        if q is None:
            return False
        if status is not None:
            q.status = status
        if side_legibility is not None:
            q.side_legibility = side_legibility
        return True

    def search(
        self, *, query: str = "",
        expansion: t.Optional[str] = None,
        status: t.Optional[str] = None,
        level_min: t.Optional[int] = None,
        level_max: t.Optional[int] = None,
        side_only: bool = False,
        msq_only: bool = False,
        min_legibility: t.Optional[str] = None,
        max_results: int = 50,
    ) -> tuple[SearchHit, ...]:
        if side_only and msq_only:
            return ()
        terms = _tokenize(query) if query else ()
        hits: list[SearchHit] = []
        for q in self._quests.values():
            if side_only and q.source != QuestSource.SIDE:
                continue
            if msq_only and q.source != QuestSource.MSQ:
                continue
            if expansion is not None and q.expansion != expansion:
                continue
            if status is not None and q.status != status:
                continue
            if (
                level_min is not None
                and q.level_max < level_min
            ):
                continue
            if (
                level_max is not None
                and q.level_min > level_max
            ):
                continue
            if (
                q.source == QuestSource.SIDE
                and min_legibility is not None
                and not _legibility_at_least(
                    q.side_legibility, min_legibility,
                )
            ):
                continue
            if terms:
                score = _score_terms(terms, q.tokens)
                if score == 0:
                    continue
            else:
                score = 1   # empty query — every match worth 1
            snippet = (
                q.description[:80]
                if q.description
                else q.title
            )
            hits.append(SearchHit(
                quest_id=q.quest_id, source=q.source,
                title=q.title, snippet=snippet,
                score=score, expansion=q.expansion,
                status=q.status,
            ))
        hits.sort(
            key=lambda h: (-h.score, h.quest_id),
        )
        return tuple(hits[:max_results])

    def clear_index(self) -> None:
        self._quests.clear()

    def total_indexed(self) -> int:
        return len(self._quests)


_LEGIBILITY_ORDER = (
    "hidden", "smell", "partial_title", "full",
)


def _legibility_at_least(
    actual: str, minimum: str,
) -> bool:
    if actual not in _LEGIBILITY_ORDER:
        return False
    if minimum not in _LEGIBILITY_ORDER:
        return False
    return (
        _LEGIBILITY_ORDER.index(actual)
        >= _LEGIBILITY_ORDER.index(minimum)
    )


def _score_terms(
    terms: tuple[str, ...],
    tokens: tuple[str, ...],
) -> int:
    """Each query term scores 1 per exact token match in the
    quest, plus bonus 2 if it matches as a SUBSTRING of any
    token (longer-prefix-friendlier)."""
    score = 0
    token_set = set(tokens)
    for term in terms:
        if term in token_set:
            score += 3
        elif any(term in tok for tok in tokens):
            score += 2
    return score


__all__ = [
    "QuestSource",
    "SearchHit",
    "QuestLogSearch",
]
