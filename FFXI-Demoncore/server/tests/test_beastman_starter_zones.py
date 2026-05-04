"""Tests for beastman starter zones."""
from __future__ import annotations

from server.beastman_playable_races import BeastmanRace
from server.beastman_starter_zones import (
    BeastmanStarterZones,
    StarterChapterKind,
)


def test_seed_default_tutorials():
    s = BeastmanStarterZones()
    n = s.seed_default_tutorials()
    assert n == 4
    # Re-seeding doesn't add duplicates
    assert s.seed_default_tutorials() == 0


def test_total_tutorials_after_seed():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    assert s.total_tutorials() == 4


def test_tutorial_for_each_race():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    for race in BeastmanRace:
        tut = s.tutorial_for(race=race)
        assert tut is not None
        assert tut.zone_id


def test_tutorial_for_unknown_race():
    s = BeastmanStarterZones()
    assert s.tutorial_for(race=BeastmanRace.YAGUDO) is None


def test_yagudo_zone_id():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    tut = s.tutorial_for(race=BeastmanRace.YAGUDO)
    assert tut.zone_id == "oztroja_seminary"


def test_orc_zone_id():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    tut = s.tutorial_for(race=BeastmanRace.ORC)
    assert tut.zone_id == "davoi_iron_cradle"


def test_chapters_in_canonical_order():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    tut = s.tutorial_for(race=BeastmanRace.QUADAV)
    expected = list(StarterChapterKind)
    actual = [ch.kind for ch in tut.chapters]
    assert actual == expected


def test_start_tutorial():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    assert s.start(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )


def test_start_unknown_race():
    s = BeastmanStarterZones()
    assert not s.start(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )


def test_double_start_rejected():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    s.start(player_id="alice", race=BeastmanRace.YAGUDO)
    assert not s.start(
        player_id="alice", race=BeastmanRace.YAGUDO,
    )


def test_complete_chapter_in_order():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    s.start(player_id="alice", race=BeastmanRace.YAGUDO)
    assert s.complete_chapter(
        player_id="alice", race=BeastmanRace.YAGUDO,
        chapter_kind=StarterChapterKind.AWAKENING,
    )


def test_complete_chapter_out_of_order():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    s.start(player_id="alice", race=BeastmanRace.YAGUDO)
    assert not s.complete_chapter(
        player_id="alice", race=BeastmanRace.YAGUDO,
        chapter_kind=StarterChapterKind.HANDOFF_TO_CITY,
    )


def test_complete_chapter_unstarted():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    assert not s.complete_chapter(
        player_id="alice", race=BeastmanRace.YAGUDO,
        chapter_kind=StarterChapterKind.AWAKENING,
    )


def test_full_tutorial_completion():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    s.start(player_id="alice", race=BeastmanRace.LAMIA)
    for chapter in StarterChapterKind:
        s.complete_chapter(
            player_id="alice", race=BeastmanRace.LAMIA,
            chapter_kind=chapter,
        )
    assert s.is_complete(
        player_id="alice", race=BeastmanRace.LAMIA,
    )


def test_complete_after_finished_rejected():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    s.start(player_id="alice", race=BeastmanRace.LAMIA)
    for chapter in StarterChapterKind:
        s.complete_chapter(
            player_id="alice", race=BeastmanRace.LAMIA,
            chapter_kind=chapter,
        )
    assert not s.complete_chapter(
        player_id="alice", race=BeastmanRace.LAMIA,
        chapter_kind=StarterChapterKind.AWAKENING,
    )


def test_is_complete_in_progress():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    s.start(player_id="alice", race=BeastmanRace.ORC)
    assert not s.is_complete(
        player_id="alice", race=BeastmanRace.ORC,
    )


def test_is_complete_unstarted():
    s = BeastmanStarterZones()
    assert not s.is_complete(
        player_id="alice", race=BeastmanRace.ORC,
    )


def test_progress_for_returns_record():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    s.start(player_id="alice", race=BeastmanRace.ORC)
    s.complete_chapter(
        player_id="alice", race=BeastmanRace.ORC,
        chapter_kind=StarterChapterKind.AWAKENING,
    )
    prog = s.progress_for(
        player_id="alice", race=BeastmanRace.ORC,
    )
    assert prog is not None
    assert StarterChapterKind.AWAKENING in (
        prog.completed_chapters
    )


def test_per_player_isolation():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    s.start(player_id="alice", race=BeastmanRace.YAGUDO)
    s.start(player_id="bob", race=BeastmanRace.YAGUDO)
    assert s.total_progress_records() == 2


def test_per_race_isolation():
    s = BeastmanStarterZones()
    s.seed_default_tutorials()
    s.start(player_id="alice", race=BeastmanRace.YAGUDO)
    s.start(player_id="alice", race=BeastmanRace.ORC)
    assert s.total_progress_records() == 2
