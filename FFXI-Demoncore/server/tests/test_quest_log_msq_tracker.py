"""Tests for the MSQ quest log tracker."""
from __future__ import annotations

from server.quest_log_msq_tracker import (
    Expansion,
    MissionStatus,
    MissionStep,
    QuestLogMSQTracker,
    StepKind,
    WaypointPos,
)


def _bastok_steps():
    return (
        MissionStep(
            step_index=0, kind=StepKind.TALK,
            description="Speak with Cid in the Metalworks",
            who_to_talk_to="cid",
            waypoint=WaypointPos(
                zone_id="metalworks", x=10, y=20,
            ),
        ),
        MissionStep(
            step_index=1, kind=StepKind.KILL,
            description="Defeat Quadav in Palborough",
            waypoint=WaypointPos(
                zone_id="palborough_mines", x=300, y=80,
            ),
            required_level=10,
        ),
        MissionStep(
            step_index=2, kind=StepKind.CUTSCENE,
            description="Report back",
            who_to_talk_to="cid",
            waypoint=WaypointPos(
                zone_id="metalworks", x=10, y=20,
            ),
        ),
    )


def test_register_mission():
    t = QuestLogMSQTracker()
    m = t.register_mission(
        mission_id="bastok_1_1",
        expansion=Expansion.BASE,
        chapter_index=1, title="Smash the Orcish Scouts",
        steps=_bastok_steps(),
    )
    assert m is not None
    assert m.title.startswith("Smash")


def test_register_no_steps_rejected():
    t = QuestLogMSQTracker()
    assert t.register_mission(
        mission_id="empty", expansion=Expansion.BASE,
        chapter_index=1, title="", steps=(),
    ) is None


def test_register_non_contiguous_steps_rejected():
    t = QuestLogMSQTracker()
    bad = (
        MissionStep(
            step_index=0, kind=StepKind.TALK,
            description="a",
        ),
        MissionStep(
            step_index=2, kind=StepKind.KILL,
            description="b",
        ),
    )
    assert t.register_mission(
        mission_id="bad", expansion=Expansion.BASE,
        chapter_index=1, title="x", steps=bad,
    ) is None


def test_double_register_rejected():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    second = t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="y",
        steps=_bastok_steps(),
    )
    assert second is None


def test_start_mission_succeeds():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    prog = t.start_mission(
        player_id="alice", mission_id="m",
    )
    assert prog is not None
    assert prog.status == MissionStatus.IN_PROGRESS


def test_start_unknown_mission_rejected():
    t = QuestLogMSQTracker()
    assert t.start_mission(
        player_id="alice", mission_id="ghost",
    ) is None


def test_double_start_rejected():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    t.start_mission(player_id="alice", mission_id="m")
    second = t.start_mission(
        player_id="alice", mission_id="m",
    )
    assert second is None


def test_next_for_mission_shows_first_step():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    t.start_mission(player_id="alice", mission_id="m")
    hint = t.next_for_mission(
        player_id="alice", mission_id="m",
    )
    assert hint is not None
    assert hint.step_index == 0
    assert hint.who_to_talk_to == "cid"
    assert hint.waypoint.zone_id == "metalworks"


def test_complete_step_advances():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    t.start_mission(player_id="alice", mission_id="m")
    next_hint = t.complete_step(
        player_id="alice", mission_id="m",
    )
    assert next_hint is not None
    assert next_hint.step_index == 1
    assert next_hint.required_level == 10


def test_complete_final_step_marks_complete():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    t.start_mission(player_id="alice", mission_id="m")
    t.complete_step(player_id="alice", mission_id="m")
    t.complete_step(player_id="alice", mission_id="m")
    final = t.complete_step(
        player_id="alice", mission_id="m",
    )
    assert final is None    # no further step
    prog = t.progress_for(
        player_id="alice", mission_id="m",
    )
    assert prog.status == MissionStatus.COMPLETE


def test_complete_step_unknown_mission():
    t = QuestLogMSQTracker()
    assert t.complete_step(
        player_id="alice", mission_id="ghost",
    ) is None


def test_complete_step_not_in_progress():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    assert t.complete_step(
        player_id="alice", mission_id="m",
    ) is None


def test_next_for_mission_after_completion_returns_none():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    t.start_mission(player_id="alice", mission_id="m")
    t.complete_step(player_id="alice", mission_id="m")
    t.complete_step(player_id="alice", mission_id="m")
    t.complete_step(player_id="alice", mission_id="m")
    assert t.next_for_mission(
        player_id="alice", mission_id="m",
    ) is None


def test_active_msqs_for_sorted_by_expansion():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="cop_1", expansion=Expansion.CHAINS_OF_PROMATHIA,
        chapter_index=1, title="cop start",
        steps=_bastok_steps(),
    )
    t.register_mission(
        mission_id="base_1", expansion=Expansion.BASE,
        chapter_index=1, title="base start",
        steps=_bastok_steps(),
    )
    t.register_mission(
        mission_id="rotz_1", expansion=Expansion.RISE_OF_THE_ZILART,
        chapter_index=1, title="rotz start",
        steps=_bastok_steps(),
    )
    for mid in ("cop_1", "base_1", "rotz_1"):
        t.start_mission(player_id="alice", mission_id=mid)
    actives = t.active_msqs_for("alice")
    # sorted by expansion enum value then chapter
    expansions = [h.expansion for h in actives]
    assert Expansion.BASE in expansions
    # cop comes before rotz alphabetically by enum value
    assert (
        expansions.index(Expansion.CHAINS_OF_PROMATHIA)
        < expansions.index(Expansion.RISE_OF_THE_ZILART)
    )


def test_active_msqs_only_in_progress():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m1", expansion=Expansion.BASE,
        chapter_index=1, title="a",
        steps=_bastok_steps(),
    )
    t.register_mission(
        mission_id="m2", expansion=Expansion.BASE,
        chapter_index=2, title="b",
        steps=_bastok_steps(),
    )
    t.start_mission(player_id="alice", mission_id="m1")
    t.start_mission(player_id="alice", mission_id="m2")
    # Complete m1
    for _ in range(3):
        t.complete_step(
            player_id="alice", mission_id="m1",
        )
    actives = t.active_msqs_for("alice")
    assert len(actives) == 1
    assert actives[0].mission_id == "m2"


def test_next_step_carries_waypoint_pos():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    t.start_mission(player_id="alice", mission_id="m")
    t.complete_step(player_id="alice", mission_id="m")
    hint = t.next_for_mission(
        player_id="alice", mission_id="m",
    )
    assert hint.waypoint.zone_id == "palborough_mines"
    assert hint.waypoint.x == 300


def test_progress_for_unknown_returns_none():
    t = QuestLogMSQTracker()
    assert t.progress_for(
        player_id="alice", mission_id="ghost",
    ) is None


def test_total_missions():
    t = QuestLogMSQTracker()
    t.register_mission(
        mission_id="m1", expansion=Expansion.BASE,
        chapter_index=1, title="x",
        steps=_bastok_steps(),
    )
    t.register_mission(
        mission_id="m2", expansion=Expansion.DEMONCORE,
        chapter_index=1, title="y",
        steps=_bastok_steps(),
    )
    assert t.total_missions() == 2
