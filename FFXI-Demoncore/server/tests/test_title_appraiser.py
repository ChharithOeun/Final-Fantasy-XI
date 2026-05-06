"""Tests for title_appraiser."""
from __future__ import annotations

from server.hero_titles import HeroTitleRegistry, TitleTier
from server.server_history_log import EventKind, ServerHistoryLog
from server.title_appraiser import (
    HasKindAndBossPredicate,
    HasKindPredicate,
    NationVictoryPredicate,
    SpeedRecordUnderPredicate,
    TitleAppraiser,
)


def _setup():
    log = ServerHistoryLog()
    titles = HeroTitleRegistry()
    titles.define_title(
        title_id="dragonslayer", name="Dragonslayer",
        tier=TitleTier.LEGENDARY,
    )
    titles.define_title(
        title_id="vorraks_bane", name="Vorrak's Bane",
        tier=TitleTier.MYTHIC,
    )
    titles.define_title(
        title_id="speed_demon", name="Speed Demon",
        tier=TitleTier.EPIC,
    )
    titles.define_title(
        title_id="liberator", name="Liberator",
        tier=TitleTier.LEGENDARY,
    )
    return log, titles


def test_register_rule_happy():
    a = TitleAppraiser()
    ok = a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="dragonslayer",
    )
    assert ok is True
    assert a.registered_count() == 1


def test_register_blank_title_rejected():
    a = TitleAppraiser()
    ok = a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="",
    )
    assert ok is False


def test_appraise_grants_for_world_first():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="X", participants=["alice", "bob"],
        recorded_at=10, boss_id="vorrak",
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="dragonslayer",
    )
    granted = a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    )
    assert granted == 2
    assert "alice" in titles.holders_of(title_id="dragonslayer")
    assert "bob" in titles.holders_of(title_id="dragonslayer")


def test_appraise_idempotent():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="X", participants=["alice"],
        recorded_at=10, boss_id="vorrak",
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="dragonslayer",
    )
    g1 = a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    )
    g2 = a.appraise(
        history_log=log, title_registry=titles, now_seconds=200,
    )
    assert g1 == 1
    assert g2 == 0  # no new grants on second pass


def test_kind_and_boss_filter():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="X", participants=["alice"],
        recorded_at=10, boss_id="vorrak",
    )
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="X", participants=["bob"],
        recorded_at=20, boss_id="mirahna",
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=HasKindAndBossPredicate(
            kind=EventKind.WORLD_FIRST_KILL, boss_id="vorrak",
        ),
        title_id="vorraks_bane",
    )
    granted = a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    )
    assert granted == 1  # only alice
    holders = titles.holders_of(title_id="vorraks_bane")
    assert holders == ("alice",)


def test_speed_record_under_predicate():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.SPEED_RECORD,
        summary="under", participants=["alice"],
        recorded_at=10, boss_id="vorrak", value=240,
    )
    log.record_event(
        kind=EventKind.SPEED_RECORD,
        summary="over", participants=["bob"],
        recorded_at=20, boss_id="vorrak", value=400,
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=SpeedRecordUnderPredicate(
            boss_id="vorrak", under_seconds=300,
        ),
        title_id="speed_demon",
    )
    granted = a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    )
    assert granted == 1
    holders = titles.holders_of(title_id="speed_demon")
    assert holders == ("alice",)


def test_speed_record_no_value_no_match():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.SPEED_RECORD,
        summary="missing value", participants=["alice"],
        recorded_at=10, boss_id="vorrak", value=None,
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=SpeedRecordUnderPredicate(
            boss_id="vorrak", under_seconds=300,
        ),
        title_id="speed_demon",
    )
    assert a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    ) == 0


def test_nation_victory_predicate():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.NATION_VICTORY,
        summary="zeruhn", participants=["alice", "bob"],
        recorded_at=10, region_id="zeruhn",
    )
    log.record_event(
        kind=EventKind.NATION_VICTORY,
        summary="ronfaure", participants=["carol"],
        recorded_at=20, region_id="ronfaure",
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=NationVictoryPredicate(region_id="zeruhn"),
        title_id="liberator",
    )
    granted = a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    )
    assert granted == 2


def test_unknown_title_no_grants():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="X", participants=["alice"],
        recorded_at=10, boss_id="vorrak",
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="ghost_title",  # not defined
    )
    granted = a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    )
    assert granted == 0


def test_multiple_rules_different_titles():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="X", participants=["alice"],
        recorded_at=10, boss_id="vorrak",
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="dragonslayer",
    )
    a.register_rule(
        predicate=HasKindAndBossPredicate(
            kind=EventKind.WORLD_FIRST_KILL, boss_id="vorrak",
        ),
        title_id="vorraks_bane",
    )
    granted = a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    )
    assert granted == 2  # alice gets both


def test_grants_carry_source_entry_id():
    log, titles = _setup()
    eid = log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="X", participants=["alice"],
        recorded_at=10, boss_id="vorrak",
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="dragonslayer",
    )
    a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    )
    grants = titles.titles_for_player(player_id="alice")
    assert grants[0].source_entry_id == eid


def test_no_history_no_grants():
    log, titles = _setup()
    a = TitleAppraiser()
    a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="dragonslayer",
    )
    assert a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    ) == 0


def test_no_rules_no_grants():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.WORLD_FIRST_KILL,
        summary="X", participants=["alice"],
        recorded_at=10, boss_id="vorrak",
    )
    a = TitleAppraiser()
    assert a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    ) == 0


def test_predicate_skips_non_matching_kinds():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.PERFECT_RUN,
        summary="X", participants=["alice"],
        recorded_at=10, boss_id="vorrak",
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="dragonslayer",
    )
    assert a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    ) == 0


def test_registered_count():
    a = TitleAppraiser()
    assert a.registered_count() == 0
    a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.WORLD_FIRST_KILL),
        title_id="t",
    )
    a.register_rule(
        predicate=HasKindPredicate(kind=EventKind.PERFECT_RUN),
        title_id="t2",
    )
    assert a.registered_count() == 2


def test_speed_record_wrong_boss_no_match():
    log, titles = _setup()
    log.record_event(
        kind=EventKind.SPEED_RECORD,
        summary="X", participants=["alice"],
        recorded_at=10, boss_id="mirahna", value=200,
    )
    a = TitleAppraiser()
    a.register_rule(
        predicate=SpeedRecordUnderPredicate(
            boss_id="vorrak", under_seconds=300,
        ),
        title_id="speed_demon",
    )
    assert a.appraise(
        history_log=log, title_registry=titles, now_seconds=100,
    ) == 0
