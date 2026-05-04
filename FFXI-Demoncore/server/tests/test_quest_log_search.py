"""Tests for the quest log search."""
from __future__ import annotations

from server.quest_log_search import (
    QuestLogSearch,
    QuestSource,
)


def _seed(s: QuestLogSearch):
    s.index_quest(
        quest_id="cop_3_1",
        source=QuestSource.MSQ,
        expansion="cop",
        title="The Promised Pact",
        description="Confront Promathia in Al'Taieu.",
        level_min=70, level_max=75,
        status="in_progress",
    )
    s.index_quest(
        quest_id="ravens_of_zilart",
        source=QuestSource.SIDE,
        expansion="rotz",
        title="The Ravens of Zilart",
        description=(
            "Find the four crow-marked stones in Norvallen."
        ),
        level_min=50, level_max=99,
        status="in_progress",
        side_legibility="full",
    )
    s.index_quest(
        quest_id="bastok_1_1",
        source=QuestSource.MSQ,
        expansion="base",
        title="Smash the Orcish Scouts",
        description="Defeat orc scouts in Palborough.",
        level_min=10, level_max=15,
        status="complete",
    )
    s.index_quest(
        quest_id="ghost_quest",
        source=QuestSource.SIDE,
        expansion="rotz",
        title="???",
        description="",
        side_legibility="hidden",
    )


def test_total_indexed():
    s = QuestLogSearch()
    _seed(s)
    assert s.total_indexed() == 4


def test_search_term_finds_msq():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(query="promathia")
    ids = {h.quest_id for h in hits}
    assert "cop_3_1" in ids


def test_search_token_match_scores_higher():
    s = QuestLogSearch()
    _seed(s)
    # exact token "ravens" should score higher than partial
    hits = s.search(query="ravens")
    assert hits[0].quest_id == "ravens_of_zilart"


def test_search_filters_by_expansion():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(expansion="cop")
    assert len(hits) == 1
    assert hits[0].quest_id == "cop_3_1"


def test_search_filters_by_status():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(status="complete")
    assert len(hits) == 1
    assert hits[0].quest_id == "bastok_1_1"


def test_search_level_min_filter():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(level_min=70)
    ids = {h.quest_id for h in hits}
    # Only quests whose level_max >= 70
    assert "bastok_1_1" not in ids


def test_search_level_max_filter():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(level_max=20)
    ids = {h.quest_id for h in hits}
    # Only quests whose level_min <= 20
    assert "cop_3_1" not in ids


def test_search_side_only():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(side_only=True)
    sources = {h.source for h in hits}
    assert sources == {QuestSource.SIDE}


def test_search_msq_only():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(msq_only=True)
    sources = {h.source for h in hits}
    assert sources == {QuestSource.MSQ}


def test_side_only_and_msq_only_returns_empty():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(side_only=True, msq_only=True)
    assert hits == ()


def test_min_legibility_hides_unreadable_side_quests():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(min_legibility="partial_title")
    ids = {h.quest_id for h in hits}
    assert "ghost_quest" not in ids
    assert "ravens_of_zilart" in ids


def test_min_legibility_smell_includes_partial():
    s = QuestLogSearch()
    s.index_quest(
        quest_id="smell_q",
        source=QuestSource.SIDE,
        expansion="rotz",
        title="???", description="",
        side_legibility="smell",
    )
    hits = s.search(min_legibility="smell")
    assert len(hits) == 1


def test_search_zero_score_excluded():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(query="nonexistentword")
    assert hits == ()


def test_search_empty_query_returns_all_filtered():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search()
    assert len(hits) == 4


def test_max_results_cap():
    s = QuestLogSearch()
    _seed(s)
    hits = s.search(max_results=2)
    assert len(hits) == 2


def test_update_status():
    s = QuestLogSearch()
    _seed(s)
    s.update_status(
        quest_id="cop_3_1", status="complete",
    )
    hits = s.search(
        expansion="cop", status="complete",
    )
    assert len(hits) == 1


def test_update_status_unknown():
    s = QuestLogSearch()
    assert not s.update_status(
        quest_id="ghost", status="complete",
    )


def test_update_legibility():
    s = QuestLogSearch()
    _seed(s)
    s.update_status(
        quest_id="ghost_quest",
        side_legibility="full",
    )
    hits = s.search(min_legibility="full")
    ids = {h.quest_id for h in hits}
    assert "ghost_quest" in ids


def test_clear_index():
    s = QuestLogSearch()
    _seed(s)
    s.clear_index()
    assert s.total_indexed() == 0


def test_substring_match_scores():
    s = QuestLogSearch()
    s.index_quest(
        quest_id="x", source=QuestSource.MSQ,
        expansion="base", title="Promised Pact",
        description="",
    )
    # query "pact" appears as full token
    hits = s.search(query="pact")
    assert len(hits) == 1


def test_results_sort_deterministic():
    s = QuestLogSearch()
    s.index_quest(
        quest_id="b", source=QuestSource.MSQ,
        expansion="x", title="raven",
        description="",
    )
    s.index_quest(
        quest_id="a", source=QuestSource.MSQ,
        expansion="x", title="raven",
        description="",
    )
    hits = s.search(query="raven")
    # Same score → sorted by quest_id ascending
    assert hits[0].quest_id == "a"
