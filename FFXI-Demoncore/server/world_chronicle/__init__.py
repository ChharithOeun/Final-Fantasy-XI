"""World chronicle — in-game searchable archive of server history.

A read-only library every player can wander into. Entries
are written from the server history log (and other systems)
and surfaced as searchable chronicle articles. Players can
read, save excerpts to their own journals, and (if they
care) trace what's been happening on the server.

Article kinds
-------------
    BIOGRAPHY        a player profile woven from their
                     history entries + ballads
    BATTLE_REPORT    a single notable battle summary
    NATION_HISTORY   long-form region/nation entries
    BESTIARY_ENTRY   notable monster + recorded encounters
    OBITUARY         permadeath player remembrance
    CALENDAR_NOTE    festivals, seasonal events recorded

Search axes
-----------
    by kind          (article kind)
    by tag           (free-form tags: 'sea', 'aht_urhgan',
                      'world_first', 'mythic')
    by author        (system entries are 'system';
                      bardic entries are composer_id)

Public surface
--------------
    ArticleKind enum
    ChronicleArticle dataclass (frozen)
    ChronicleQuery dataclass (frozen)
    WorldChronicle
        .publish_article(kind, title, body, author_id,
                         tags, published_at,
                         linked_entry_id) -> article_id
        .get(article_id) -> Optional[ChronicleArticle]
        .search(query) -> tuple[ChronicleArticle, ...]
        .articles_by_author(author_id) -> tuple[...]
        .articles_with_tag(tag) -> tuple[...]
        .total_articles() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ArticleKind(str, enum.Enum):
    BIOGRAPHY = "biography"
    BATTLE_REPORT = "battle_report"
    NATION_HISTORY = "nation_history"
    BESTIARY_ENTRY = "bestiary_entry"
    OBITUARY = "obituary"
    CALENDAR_NOTE = "calendar_note"


@dataclasses.dataclass(frozen=True)
class ChronicleArticle:
    article_id: str
    kind: ArticleKind
    title: str
    body: str
    author_id: str
    tags: tuple[str, ...]
    published_at: int
    linked_entry_id: t.Optional[str] = None
    revision: int = 1


@dataclasses.dataclass(frozen=True)
class ChronicleQuery:
    kinds: tuple[ArticleKind, ...] = ()
    tags: tuple[str, ...] = ()
    author_id: t.Optional[str] = None
    title_substring: t.Optional[str] = None
    since_seconds: t.Optional[int] = None


@dataclasses.dataclass
class WorldChronicle:
    _articles: list[ChronicleArticle] = dataclasses.field(
        default_factory=list,
    )
    _next_id: int = 0
    _by_author: dict[str, list[int]] = dataclasses.field(
        default_factory=dict,
    )
    _by_tag: dict[str, list[int]] = dataclasses.field(
        default_factory=dict,
    )

    def publish_article(
        self, *, kind: ArticleKind, title: str, body: str,
        author_id: str, tags: t.Iterable[str],
        published_at: int,
        linked_entry_id: t.Optional[str] = None,
    ) -> str:
        if not title or not body or not author_id:
            return ""
        clean_tags = tuple(
            sorted({t.strip().lower() for t in tags if t and t.strip()})
        )
        self._next_id += 1
        aid = f"art_{self._next_id}"
        art = ChronicleArticle(
            article_id=aid, kind=kind, title=title, body=body,
            author_id=author_id, tags=clean_tags,
            published_at=published_at,
            linked_entry_id=linked_entry_id,
        )
        idx = len(self._articles)
        self._articles.append(art)
        self._by_author.setdefault(author_id, []).append(idx)
        for tag in clean_tags:
            self._by_tag.setdefault(tag, []).append(idx)
        return aid

    def get(
        self, *, article_id: str,
    ) -> t.Optional[ChronicleArticle]:
        for a in self._articles:
            if a.article_id == article_id:
                return a
        return None

    def search(
        self, *, query: ChronicleQuery,
    ) -> tuple[ChronicleArticle, ...]:
        out: list[ChronicleArticle] = []
        title_needle = (
            query.title_substring.lower()
            if query.title_substring else None
        )
        wanted_tags = (
            {t.lower() for t in query.tags}
            if query.tags else set()
        )
        for a in self._articles:
            if query.kinds and a.kind not in query.kinds:
                continue
            if query.author_id is not None and (
                a.author_id != query.author_id
            ):
                continue
            if wanted_tags and not wanted_tags.issubset(set(a.tags)):
                continue
            if title_needle and title_needle not in a.title.lower():
                continue
            if query.since_seconds is not None and (
                a.published_at < query.since_seconds
            ):
                continue
            out.append(a)
        return tuple(out)

    def articles_by_author(
        self, *, author_id: str,
    ) -> tuple[ChronicleArticle, ...]:
        idxs = self._by_author.get(author_id, [])
        return tuple(self._articles[i] for i in idxs)

    def articles_with_tag(
        self, *, tag: str,
    ) -> tuple[ChronicleArticle, ...]:
        idxs = self._by_tag.get(tag.strip().lower(), [])
        return tuple(self._articles[i] for i in idxs)

    def total_articles(self) -> int:
        return len(self._articles)


__all__ = [
    "ArticleKind", "ChronicleArticle", "ChronicleQuery",
    "WorldChronicle",
]
