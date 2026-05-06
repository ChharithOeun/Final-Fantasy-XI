"""Tests for wayfarer_titles."""
from __future__ import annotations

from server.exploration_journal import EntryKind, ExplorationJournal
from server.hero_titles import HeroTitleRegistry, TitleTier
from server.wayfarer_titles import (
    WayfarerTitleAppraiser,
    predicate_distinct_zones,
    predicate_kind_count,
    predicate_zone_prefix,
)


def _setup_titles():
    r = HeroTitleRegistry()
    r.define_title(
        title_id="well_traveled", name="Well-Traveled",
        tier=TitleTier.RARE,
    )
    r.define_title(
        title_id="cartographer", name="Cartographer",
        tier=TitleTier.EPIC,
    )
    r.define_title(
        title_id="spelunker", name="Spelunker",
        tier=TitleTier.RARE,
    )
    r.define_title(
        title_id="sea_dog", name="Sea Dog",
        tier=TitleTier.RARE,
    )
    r.define_title(
        title_id="pilgrim", name="Pilgrim",
        tier=TitleTier.RARE,
    )
    return r


def _visit(j, player, zone, t):
    j.record(
        player_id=player, kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id=zone, zone_id=zone, discovered_at=t,
    )


def test_register_milestone_happy():
    a = WayfarerTitleAppraiser()
    ok = a.register_milestone(
        title_id="well_traveled", name="Well-Traveled",
        predicate=predicate_distinct_zones(10),
    )
    assert ok is True


def test_register_blank_blocked():
    a = WayfarerTitleAppraiser()
    out = a.register_milestone(
        title_id="", name="X",
        predicate=predicate_distinct_zones(10),
    )
    assert out is False


def test_total_milestones():
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="a", name="A",
        predicate=predicate_distinct_zones(5),
    )
    a.register_milestone(
        title_id="b", name="B",
        predicate=predicate_distinct_zones(10),
    )
    assert a.total_milestones() == 2


def test_distinct_zones_grants_title():
    titles = _setup_titles()
    j = ExplorationJournal()
    for i in range(10):
        _visit(j, "alice", f"zone_{i}", i)
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="well_traveled", name="Well-Traveled",
        predicate=predicate_distinct_zones(10),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 1
    assert "alice" in titles.holders_of(title_id="well_traveled")


def test_distinct_zones_below_threshold():
    titles = _setup_titles()
    j = ExplorationJournal()
    for i in range(5):
        _visit(j, "alice", f"zone_{i}", i)
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="well_traveled", name="Well-Traveled",
        predicate=predicate_distinct_zones(10),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 0


def test_idempotent():
    titles = _setup_titles()
    j = ExplorationJournal()
    for i in range(10):
        _visit(j, "alice", f"zone_{i}", i)
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="well_traveled", name="Well-Traveled",
        predicate=predicate_distinct_zones(10),
    )
    g1 = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    g2 = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=200,
    )
    assert g1 == 1
    assert g2 == 0  # already holds it


def test_kind_count_predicate_landmark():
    titles = _setup_titles()
    j = ExplorationJournal()
    for i in range(5):
        j.record(
            player_id="alice", kind=EntryKind.LANDMARK_FOUND,
            ref_id=f"cave_{i}", zone_id="z", discovered_at=i,
        )
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="spelunker", name="Spelunker",
        predicate=predicate_kind_count(
            EntryKind.LANDMARK_FOUND, 5,
        ),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 1


def test_zone_prefix_predicate():
    titles = _setup_titles()
    j = ExplorationJournal()
    for i in range(5):
        _visit(j, "alice", f"ocean_{i}", i)
    _visit(j, "alice", "land_zone", 100)
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="sea_dog", name="Sea Dog",
        predicate=predicate_zone_prefix("ocean_", 5),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 1


def test_multiple_milestones():
    titles = _setup_titles()
    j = ExplorationJournal()
    for i in range(25):
        _visit(j, "alice", f"zone_{i}", i)
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="well_traveled", name="W-T",
        predicate=predicate_distinct_zones(10),
    )
    a.register_milestone(
        title_id="cartographer", name="C",
        predicate=predicate_distinct_zones(25),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 2


def test_blank_player_no_grants():
    titles = _setup_titles()
    j = ExplorationJournal()
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="well_traveled", name="W-T",
        predicate=predicate_distinct_zones(10),
    )
    granted = a.appraise(
        player_id="", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 0


def test_unknown_title_no_grants():
    titles = _setup_titles()
    j = ExplorationJournal()
    for i in range(10):
        _visit(j, "alice", f"z{i}", i)
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="ghost_title", name="ghost",
        predicate=predicate_distinct_zones(10),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 0


def test_pilgrimage_kind_count():
    titles = _setup_titles()
    j = ExplorationJournal()
    j.record(
        player_id="alice", kind=EntryKind.PILGRIMAGE_DONE,
        ref_id="hero_path", zone_id="bastok", discovered_at=10,
    )
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="pilgrim", name="Pilgrim",
        predicate=predicate_kind_count(
            EntryKind.PILGRIMAGE_DONE, 1,
        ),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 1


def test_no_journal_no_grants():
    titles = _setup_titles()
    j = ExplorationJournal()
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="well_traveled", name="W-T",
        predicate=predicate_distinct_zones(10),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 0


def test_partial_progress_no_grant():
    titles = _setup_titles()
    j = ExplorationJournal()
    for i in range(7):
        _visit(j, "alice", f"z{i}", i)
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="well_traveled", name="W-T",
        predicate=predicate_distinct_zones(10),
    )
    a.register_milestone(
        title_id="cartographer", name="C",
        predicate=predicate_distinct_zones(25),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 0


def test_dup_zones_count_once():
    titles = _setup_titles()
    j = ExplorationJournal()
    # ZONE_FIRST_VISIT already de-dups by ref_id, but we
    # also confirm the predicate's distinctness
    for i in range(10):
        _visit(j, "alice", f"z{i}", i)
    # second call to same zone is a no-op in the journal anyway
    j.record(
        player_id="alice", kind=EntryKind.ZONE_FIRST_VISIT,
        ref_id="z0", zone_id="z0", discovered_at=99,
    )
    a = WayfarerTitleAppraiser()
    a.register_milestone(
        title_id="well_traveled", name="W-T",
        predicate=predicate_distinct_zones(10),
    )
    granted = a.appraise(
        player_id="alice", journal=j,
        title_registry=titles, now_seconds=100,
    )
    assert granted == 1
