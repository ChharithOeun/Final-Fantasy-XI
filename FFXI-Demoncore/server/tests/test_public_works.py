"""Tests for public_works."""
from __future__ import annotations

from server.public_works import (
    PublicWorks, WorksKind, WorksProject, WorksState,
)


def _bridge(pid="bastok_river_bridge", zid="bastok",
            goal=100000, cap=20000):
    return WorksProject(
        project_id=pid, zone_id=zid,
        kind=WorksKind.BRIDGE,
        title="Cross-River Bridge",
        description="A sturdy stone span.",
        funding_goal_gil=goal,
        per_contributor_cap_gil=cap,
        benefit_summary="-30% travel time Bastok->Sandy.",
    )


def test_propose_happy():
    p = PublicWorks()
    assert p.propose(_bridge()) is True


def test_propose_blank_id_blocked():
    p = PublicWorks()
    bad = WorksProject(
        project_id="", zone_id="z", kind=WorksKind.BRIDGE,
        title="t", description="d", funding_goal_gil=1000,
        per_contributor_cap_gil=100, benefit_summary="b",
    )
    assert p.propose(bad) is False


def test_propose_zero_goal_blocked():
    p = PublicWorks()
    bad = WorksProject(
        project_id="x", zone_id="z", kind=WorksKind.BRIDGE,
        title="t", description="d", funding_goal_gil=0,
        per_contributor_cap_gil=100, benefit_summary="b",
    )
    assert p.propose(bad) is False


def test_propose_cap_above_goal_blocked():
    p = PublicWorks()
    bad = WorksProject(
        project_id="x", zone_id="z", kind=WorksKind.BRIDGE,
        title="t", description="d",
        funding_goal_gil=1000,
        per_contributor_cap_gil=2000,
        benefit_summary="b",
    )
    assert p.propose(bad) is False


def test_propose_dup_blocked():
    p = PublicWorks()
    p.propose(_bridge())
    assert p.propose(_bridge()) is False


def test_contribute():
    p = PublicWorks()
    p.propose(_bridge())
    assert p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=5000,
    ) is True
    assert p.total_funded(
        project_id="bastok_river_bridge",
    ) == 5000


def test_contribute_zero_blocked():
    p = PublicWorks()
    p.propose(_bridge())
    assert p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=0,
    ) is False


def test_contribute_blank_player_blocked():
    p = PublicWorks()
    p.propose(_bridge())
    assert p.contribute(
        player_id="",
        project_id="bastok_river_bridge",
        amount_gil=1000,
    ) is False


def test_contribute_unknown_project():
    p = PublicWorks()
    assert p.contribute(
        player_id="bob", project_id="ghost",
        amount_gil=1000,
    ) is False


def test_contribute_past_cap_blocked():
    p = PublicWorks()
    p.propose(_bridge(cap=20000))
    p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=15000,
    )
    blocked = p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=10000,
    )
    assert blocked is False


def test_contribute_past_goal_blocked():
    p = PublicWorks()
    p.propose(_bridge(goal=50000, cap=30000))
    p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=30000,
    )
    p.contribute(
        player_id="cara",
        project_id="bastok_river_bridge",
        amount_gil=15000,
    )
    # Total 45000, room for 5000; but cara tries 10000
    blocked = p.contribute(
        player_id="cara",
        project_id="bastok_river_bridge",
        amount_gil=10000,
    )
    assert blocked is False


def test_contribute_after_construction_blocked():
    p = PublicWorks()
    p.propose(_bridge(goal=10000, cap=10000))
    p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=10000,
    )
    p.start_construction(
        project_id="bastok_river_bridge",
    )
    blocked = p.contribute(
        player_id="cara",
        project_id="bastok_river_bridge",
        amount_gil=1000,
    )
    assert blocked is False


def test_start_construction_short_funded_blocked():
    p = PublicWorks()
    p.propose(_bridge(goal=100000, cap=20000))
    p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=20000,
    )
    blocked = p.start_construction(
        project_id="bastok_river_bridge",
    )
    assert blocked is False


def test_start_construction_funded():
    p = PublicWorks()
    p.propose(_bridge(goal=10000, cap=10000))
    p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=10000,
    )
    assert p.start_construction(
        project_id="bastok_river_bridge",
    ) is True
    assert p.state(
        project_id="bastok_river_bridge",
    ) == WorksState.UNDER_CONSTRUCTION


def test_complete():
    p = PublicWorks()
    p.propose(_bridge(goal=10000, cap=10000))
    p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=10000,
    )
    p.start_construction(project_id="bastok_river_bridge")
    assert p.complete(
        project_id="bastok_river_bridge",
    ) is True
    assert p.state(
        project_id="bastok_river_bridge",
    ) == WorksState.COMPLETED


def test_complete_before_construction_blocked():
    p = PublicWorks()
    p.propose(_bridge())
    assert p.complete(
        project_id="bastok_river_bridge",
    ) is False


def test_decay():
    p = PublicWorks()
    p.propose(_bridge(goal=10000, cap=10000))
    p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=10000,
    )
    p.start_construction(project_id="bastok_river_bridge")
    p.complete(project_id="bastok_river_bridge")
    assert p.decay(
        project_id="bastok_river_bridge",
    ) is True
    assert p.state(
        project_id="bastok_river_bridge",
    ) == WorksState.DECAYED


def test_decay_uncomplete_blocked():
    p = PublicWorks()
    p.propose(_bridge())
    assert p.decay(
        project_id="bastok_river_bridge",
    ) is False


def test_top_contributors():
    p = PublicWorks()
    p.propose(_bridge(goal=100000, cap=20000))
    p.contribute(
        player_id="bob",
        project_id="bastok_river_bridge",
        amount_gil=20000,
    )
    p.contribute(
        player_id="cara",
        project_id="bastok_river_bridge",
        amount_gil=15000,
    )
    p.contribute(
        player_id="dave",
        project_id="bastok_river_bridge",
        amount_gil=5000,
    )
    top = p.top_contributors(
        project_id="bastok_river_bridge", n=2,
    )
    assert top == [("bob", 20000), ("cara", 15000)]


def test_top_contributors_no_project():
    p = PublicWorks()
    assert p.top_contributors(
        project_id="ghost",
    ) == []


def test_projects_in_zone():
    p = PublicWorks()
    p.propose(_bridge("a", "bastok"))
    p.propose(_bridge("b", "bastok"))
    p.propose(_bridge("c", "sandy"))
    out = p.projects_in_zone(zone_id="bastok")
    assert {pr.project_id for pr in out} == {"a", "b"}


def test_seven_works_kinds():
    assert len(list(WorksKind)) == 7


def test_four_works_states():
    assert len(list(WorksState)) == 4
