"""Tests for permadeath_obituary."""
from __future__ import annotations

from server.permadeath_obituary import (
    DeathKind,
    DeathRecord,
    PermadeathObituary,
)
from server.server_history_log import EventKind, ServerHistoryLog
from server.world_chronicle import ArticleKind, WorldChronicle


def _hero(level=87, death_kind=DeathKind.HEROIC):
    return DeathRecord(
        player_id="alice",
        player_name="Alice the Bold",
        race="Mithra", job="THF",
        level=level,
        cause="Vorrak's claw",
        death_kind=death_kind,
        died_at=1000, born_at=100,
    )


def test_compose_happy():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    aid = obit.compose(
        death=_hero(),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    assert aid != ""
    assert obit.total_published() == 1


def test_below_30_skipped():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    aid = obit.compose(
        death=_hero(level=29),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    assert aid == ""
    assert obit.total_published() == 0


def test_blank_player_id_skipped():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    bad = DeathRecord(
        player_id="", player_name="X", race="hume",
        job="war", level=50, cause="x",
        death_kind=DeathKind.HEROIC, died_at=10,
    )
    assert obit.compose(
        death=bad, history_log=log,
        world_chronicle=chronicle, published_at=10,
    ) == ""


def test_deeds_included_in_body():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="Vorrak's Fall",
        participants=["alice"], recorded_at=500,
        boss_id="vorrak",
    )
    obit = PermadeathObituary()
    aid = obit.compose(
        death=_hero(),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    art = chronicle.get(article_id=aid)
    assert art is not None
    assert "Vorrak's Fall" in art.body


def test_no_deeds_remembered_anyway():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    aid = obit.compose(
        death=_hero(),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    art = chronicle.get(article_id=aid)
    assert art is not None
    assert "remembered" in art.body.lower()


def test_obituary_has_obituary_tag():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    aid = obit.compose(
        death=_hero(),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    art = chronicle.get(article_id=aid)
    assert art is not None
    assert "obituary" in art.tags


def test_article_kind_is_obituary():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    aid = obit.compose(
        death=_hero(),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    art = chronicle.get(article_id=aid)
    assert art is not None
    assert art.kind == ArticleKind.OBITUARY


def test_title_includes_player_name():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    aid = obit.compose(
        death=_hero(),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    art = chronicle.get(article_id=aid)
    assert art is not None
    assert "Alice the Bold" in art.title


def test_epitaph_varies_by_death_kind():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    aid_h = obit.compose(
        death=_hero(death_kind=DeathKind.HEROIC),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    obit2 = PermadeathObituary()
    aid_o = obit2.compose(
        death=DeathRecord(
            player_id="bob", player_name="Bob",
            race="Hume", job="WAR", level=50,
            cause="bandit knife",
            death_kind=DeathKind.OUTLAW, died_at=10,
        ),
        history_log=log, world_chronicle=chronicle,
        published_at=10,
    )
    a_h = chronicle.get(article_id=aid_h)
    a_o = chronicle.get(article_id=aid_o)
    assert a_h is not None and a_o is not None
    assert a_h.body != a_o.body


def test_lifespan_when_born_at_set():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    aid = obit.compose(
        death=_hero(),  # born_at=100, died_at=1000
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    art = chronicle.get(article_id=aid)
    assert art is not None
    assert "900" in art.body


def test_lifespan_omitted_when_unknown_birth():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    death = DeathRecord(
        player_id="bob", player_name="Bob", race="hume",
        job="war", level=50, cause="x",
        death_kind=DeathKind.HEROIC, died_at=10, born_at=0,
    )
    aid = obit.compose(
        death=death, history_log=log,
        world_chronicle=chronicle, published_at=10,
    )
    art = chronicle.get(article_id=aid)
    assert art is not None
    assert "Lifespan:" not in art.body


def test_only_3_deeds_included():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    for i in range(5):
        log.record_event(
            kind=EventKind.WORLD_FIRST_KILL,
            summary=f"deed-{i}",
            participants=["alice"], recorded_at=i,
            boss_id=f"b-{i}",
        )
    obit = PermadeathObituary()
    aid = obit.compose(
        death=_hero(),
        history_log=log, world_chronicle=chronicle,
        published_at=100,
    )
    art = chronicle.get(article_id=aid)
    assert art is not None
    # 3 deed lines included; deed-3 and deed-4 omitted
    deed_count = sum(1 for i in range(5) if f"deed-{i}" in art.body)
    assert deed_count == 3


def test_six_death_kinds():
    assert len(list(DeathKind)) == 6


def test_indexed_by_obituary_tag():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    obit.compose(
        death=_hero(),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    obits = chronicle.articles_with_tag(tag="obituary")
    assert len(obits) == 1


def test_total_published_increments():
    log = ServerHistoryLog()
    chronicle = WorldChronicle()
    obit = PermadeathObituary()
    obit.compose(
        death=_hero(),
        history_log=log, world_chronicle=chronicle,
        published_at=1000,
    )
    obit.compose(
        death=DeathRecord(
            player_id="bob", player_name="Bob", race="elvaan",
            job="pld", level=80, cause="dragon breath",
            death_kind=DeathKind.HEROIC, died_at=2000,
        ),
        history_log=log, world_chronicle=chronicle,
        published_at=2000,
    )
    assert obit.total_published() == 2
