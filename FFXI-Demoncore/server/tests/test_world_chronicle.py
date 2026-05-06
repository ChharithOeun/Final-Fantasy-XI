"""Tests for world_chronicle."""
from __future__ import annotations

from server.world_chronicle import (
    ArticleKind,
    ChronicleQuery,
    WorldChronicle,
)


def test_publish_happy():
    c = WorldChronicle()
    aid = c.publish_article(
        kind=ArticleKind.BATTLE_REPORT,
        title="The Fall of Vorrak",
        body="On the dusk of Iceday, Iron Wing brought down...",
        author_id="system",
        tags=["sea", "world_first", "vorrak"],
        published_at=100,
        linked_entry_id="hist_1",
    )
    assert aid == "art_1"
    assert c.total_articles() == 1


def test_blank_title_blocked():
    c = WorldChronicle()
    aid = c.publish_article(
        kind=ArticleKind.BIOGRAPHY, title="", body="x",
        author_id="ulmia", tags=[], published_at=10,
    )
    assert aid == ""


def test_blank_body_blocked():
    c = WorldChronicle()
    aid = c.publish_article(
        kind=ArticleKind.BIOGRAPHY, title="X", body="",
        author_id="ulmia", tags=[], published_at=10,
    )
    assert aid == ""


def test_blank_author_blocked():
    c = WorldChronicle()
    aid = c.publish_article(
        kind=ArticleKind.BIOGRAPHY, title="X", body="x",
        author_id="", tags=[], published_at=10,
    )
    assert aid == ""


def test_get_returns_article():
    c = WorldChronicle()
    aid = c.publish_article(
        kind=ArticleKind.OBITUARY, title="Alice the Bold",
        body="Lvl 87 PLD lost on Iceday...",
        author_id="system", tags=["obit"], published_at=10,
    )
    art = c.get(article_id=aid)
    assert art is not None
    assert art.title == "Alice the Bold"


def test_get_missing_returns_none():
    c = WorldChronicle()
    assert c.get(article_id="art_999") is None


def test_tags_normalized_lowercase_and_dedup():
    c = WorldChronicle()
    aid = c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="X", body="x",
        author_id="system",
        tags=["Sea", "sea", "WORLD_FIRST", " vorrak "],
        published_at=10,
    )
    art = c.get(article_id=aid)
    assert art is not None
    assert "sea" in art.tags
    assert "world_first" in art.tags
    assert "vorrak" in art.tags
    # should not have both 'sea' and 'Sea'
    assert len(art.tags) == 3


def test_blank_tags_skipped():
    c = WorldChronicle()
    aid = c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="X", body="x",
        author_id="system", tags=["", "  ", "real"],
        published_at=10,
    )
    art = c.get(article_id=aid)
    assert art is not None
    assert art.tags == ("real",)


def test_search_by_kind():
    c = WorldChronicle()
    c.publish_article(
        kind=ArticleKind.BIOGRAPHY, title="A", body="x",
        author_id="u", tags=[], published_at=1,
    )
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="B", body="x",
        author_id="u", tags=[], published_at=2,
    )
    out = c.search(query=ChronicleQuery(
        kinds=(ArticleKind.BATTLE_REPORT,)
    ))
    assert len(out) == 1
    assert out[0].title == "B"


def test_search_by_tag_subset():
    c = WorldChronicle()
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="A", body="x",
        author_id="u", tags=["sea", "world_first"],
        published_at=1,
    )
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="B", body="x",
        author_id="u", tags=["sky"], published_at=2,
    )
    out = c.search(query=ChronicleQuery(tags=("sea",)))
    assert len(out) == 1
    assert out[0].title == "A"


def test_search_multi_tag_requires_all():
    c = WorldChronicle()
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="A", body="x",
        author_id="u", tags=["sea", "world_first"],
        published_at=1,
    )
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="B", body="x",
        author_id="u", tags=["sea"], published_at=2,
    )
    out = c.search(query=ChronicleQuery(
        tags=("sea", "world_first"),
    ))
    assert len(out) == 1
    assert out[0].title == "A"


def test_search_by_author():
    c = WorldChronicle()
    c.publish_article(
        kind=ArticleKind.BIOGRAPHY, title="A", body="x",
        author_id="ulmia", tags=[], published_at=1,
    )
    c.publish_article(
        kind=ArticleKind.BIOGRAPHY, title="B", body="x",
        author_id="joachim", tags=[], published_at=2,
    )
    out = c.search(query=ChronicleQuery(author_id="ulmia"))
    assert len(out) == 1


def test_search_title_substring():
    c = WorldChronicle()
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT,
        title="The Fall of Vorrak",
        body="x", author_id="u", tags=[], published_at=1,
    )
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT,
        title="Mirahna the Mirror",
        body="x", author_id="u", tags=[], published_at=2,
    )
    out = c.search(query=ChronicleQuery(title_substring="vorrak"))
    assert len(out) == 1


def test_search_since_seconds():
    c = WorldChronicle()
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="A", body="x",
        author_id="u", tags=[], published_at=10,
    )
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="B", body="x",
        author_id="u", tags=[], published_at=200,
    )
    out = c.search(query=ChronicleQuery(since_seconds=100))
    assert len(out) == 1
    assert out[0].title == "B"


def test_articles_by_author_index():
    c = WorldChronicle()
    c.publish_article(
        kind=ArticleKind.BIOGRAPHY, title="A", body="x",
        author_id="ulmia", tags=[], published_at=1,
    )
    c.publish_article(
        kind=ArticleKind.BIOGRAPHY, title="B", body="x",
        author_id="ulmia", tags=[], published_at=2,
    )
    out = c.articles_by_author(author_id="ulmia")
    assert len(out) == 2


def test_articles_with_tag_index():
    c = WorldChronicle()
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="A", body="x",
        author_id="u", tags=["sea"], published_at=1,
    )
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="B", body="x",
        author_id="u", tags=["sea", "vorrak"], published_at=2,
    )
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="C", body="x",
        author_id="u", tags=["sky"], published_at=3,
    )
    sea = c.articles_with_tag(tag="sea")
    assert len(sea) == 2
    sea_caps = c.articles_with_tag(tag="SEA")
    assert len(sea_caps) == 2  # tag-search is case-insensitive


def test_search_combined_filters():
    c = WorldChronicle()
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="The Fall of Vorrak",
        body="x", author_id="ulmia",
        tags=["sea", "world_first"], published_at=10,
    )
    c.publish_article(
        kind=ArticleKind.BATTLE_REPORT, title="Vorrak Returns",
        body="x", author_id="joachim",
        tags=["sea"], published_at=20,
    )
    out = c.search(query=ChronicleQuery(
        kinds=(ArticleKind.BATTLE_REPORT,),
        tags=("sea",), author_id="ulmia",
        title_substring="vorrak",
    ))
    assert len(out) == 1
    assert out[0].title == "The Fall of Vorrak"


def test_six_article_kinds():
    assert len(list(ArticleKind)) == 6
