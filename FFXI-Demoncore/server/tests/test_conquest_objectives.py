"""Tests for conquest objectives."""
from __future__ import annotations

from server.conquest_objectives import (
    ConquestObjectives,
    Objective,
    ObjectiveKind,
    OXYGEN_TANK_BONUS_SECONDS,
    OXYGEN_TANK_RADIUS_YALMS,
)


def _seed_chain():
    return [
        Objective(
            objective_id="o1", kind=ObjectiveKind.KILL_NM,
            label="Kill Sahagin Marauder",
            nm_id="sahagin_marauder", oxygen_drop=True,
        ),
        Objective(
            objective_id="o2", kind=ObjectiveKind.MINIGAME,
            label="Solve tide puzzle",
            minigame_seconds=120,
        ),
        Objective(
            objective_id="o3", kind=ObjectiveKind.KILL_NM,
            label="Kill Sahagin Captain",
            nm_id="sahagin_captain", oxygen_drop=False,
        ),
        Objective(
            objective_id="o4", kind=ObjectiveKind.QUEST_STEP,
            label="Free mermaid scout",
        ),
    ]


def test_register_chain_happy():
    c = ConquestObjectives()
    assert c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    ) is True


def test_register_blank_id():
    c = ConquestObjectives()
    assert c.register_chain(
        chain_id="", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    ) is False


def test_register_no_objectives():
    c = ConquestObjectives()
    assert c.register_chain(
        chain_id="c1", zone_id="reef", phase=1, objectives=[],
    ) is False


def test_register_double_blocked():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    assert c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    ) is False


def test_kill_nm_without_nm_id_blocked():
    c = ConquestObjectives()
    bad = [Objective(
        objective_id="o1", kind=ObjectiveKind.KILL_NM,
        label="bad", nm_id=None,
    )]
    assert c.register_chain(
        chain_id="c1", zone_id="reef", phase=1, objectives=bad,
    ) is False


def test_complete_first_in_order():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    out = c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="sahagin_marauder",
    )
    assert out.accepted is True
    assert out.oxygen_tank_dropped is True
    assert out.next_objective_id == "o2"


def test_out_of_order_fails_chain():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    out = c.complete_objective(
        chain_id="c1", objective_id="o3",
        killed_nm_id="sahagin_captain",
    )
    assert out.accepted is False
    assert out.chain_failed is True


def test_wrong_nm_kill_fails_chain():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    out = c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="wrong_nm",
    )
    assert out.accepted is False
    assert out.chain_failed is True


def test_oxygen_drops_only_on_marked_kills():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="sahagin_marauder",
    )
    c.complete_objective(chain_id="c1", objective_id="o2")
    out = c.complete_objective(
        chain_id="c1", objective_id="o3",
        killed_nm_id="sahagin_captain",
    )
    assert out.accepted is True
    # o3 has oxygen_drop=False
    assert out.oxygen_tank_dropped is False


def test_minigame_step_no_nm_required():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="sahagin_marauder",
    )
    out = c.complete_objective(chain_id="c1", objective_id="o2")
    assert out.accepted is True


def test_current_objective_advances():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    assert c.current_objective(chain_id="c1").objective_id == "o1"
    c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="sahagin_marauder",
    )
    assert c.current_objective(chain_id="c1").objective_id == "o2"


def test_current_objective_none_after_failure():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    c.complete_objective(
        chain_id="c1", objective_id="o3",
        killed_nm_id="sahagin_captain",
    )
    assert c.current_objective(chain_id="c1") is None


def test_all_complete_after_all_done():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="sahagin_marauder",
    )
    c.complete_objective(chain_id="c1", objective_id="o2")
    c.complete_objective(
        chain_id="c1", objective_id="o3",
        killed_nm_id="sahagin_captain",
    )
    c.complete_objective(chain_id="c1", objective_id="o4")
    assert c.all_complete(chain_id="c1") is True


def test_complete_after_done_fails():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=[_seed_chain()[0]],
    )
    c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="sahagin_marauder",
    )
    out = c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="sahagin_marauder",
    )
    assert out.accepted is False


def test_progress_for_grows():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    assert c.progress_for(chain_id="c1") == ()
    c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="sahagin_marauder",
    )
    assert len(c.progress_for(chain_id="c1")) == 1


def test_oxygen_tank_constants():
    assert OXYGEN_TANK_BONUS_SECONDS == 300
    assert OXYGEN_TANK_RADIUS_YALMS == 30


def test_unknown_chain_actions():
    c = ConquestObjectives()
    out = c.complete_objective(
        chain_id="ghost", objective_id="o1",
    )
    assert out.accepted is False
    assert c.current_objective(chain_id="ghost") is None
    assert c.all_complete(chain_id="ghost") is False
