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


def test_out_of_order_revives_chain():
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
    assert out.chain_revived is True
    assert out.chain_failed is False
    assert out.retry_count == 1
    # cursor reset to first objective
    assert out.next_objective_id == "o1"
    assert c.retries_used(chain_id="c1") == 1


def test_wrong_nm_kill_revives_chain():
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
    assert out.chain_revived is True
    assert out.chain_failed is False
    assert out.retry_count == 1
    assert c.retries_used(chain_id="c1") == 1


def test_revived_chain_completable_on_retry():
    """After a wrong-NM revive, alliance can clear the chain."""
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    # mistake: kill captain first
    c.complete_objective(
        chain_id="c1", objective_id="o3",
        killed_nm_id="sahagin_captain",
    )
    # chain revived — current obj is o1 again
    assert c.current_objective(chain_id="c1").objective_id == "o1"
    # try again, in correct order this time
    o1 = c.complete_objective(
        chain_id="c1", objective_id="o1",
        killed_nm_id="sahagin_marauder",
    )
    assert o1.accepted is True
    assert o1.oxygen_tank_dropped is True
    o2 = c.complete_objective(chain_id="c1", objective_id="o2")
    assert o2.accepted is True
    o3 = c.complete_objective(
        chain_id="c1", objective_id="o3",
        killed_nm_id="sahagin_captain",
    )
    assert o3.accepted is True
    o4 = c.complete_objective(chain_id="c1", objective_id="o4")
    assert o4.accepted is True
    assert c.all_complete(chain_id="c1") is True


def test_multiple_revives_increment_retry_count():
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    for _ in range(3):
        c.complete_objective(
            chain_id="c1", objective_id="o3",
            killed_nm_id="sahagin_captain",
        )
    assert c.retries_used(chain_id="c1") == 3


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


def test_current_objective_resets_to_first_after_revive():
    """Out-of-order kill revives the chain — cursor is back at o1."""
    c = ConquestObjectives()
    c.register_chain(
        chain_id="c1", zone_id="reef", phase=1,
        objectives=_seed_chain(),
    )
    c.complete_objective(
        chain_id="c1", objective_id="o3",
        killed_nm_id="sahagin_captain",
    )
    # not None — revive, not fail
    cur = c.current_objective(chain_id="c1")
    assert cur is not None
    assert cur.objective_id == "o1"


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
