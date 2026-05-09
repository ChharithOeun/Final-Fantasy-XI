"""Tests for nation_intelligence."""
from __future__ import annotations

from server.nation_intelligence import (
    NationIntelligenceSystem, AgentState,
    OperationKind, OperationState,
)


def _recruit(s, **overrides):
    args = dict(
        agent_id="agent_007", nation_id="bastok",
        handler_id="naji",
        cover_name="Travelling Merchant",
    )
    args.update(overrides)
    return s.recruit_agent(**args)


def test_recruit_happy():
    s = NationIntelligenceSystem()
    assert _recruit(s) is True


def test_recruit_blank_id():
    s = NationIntelligenceSystem()
    assert _recruit(s, agent_id="") is False


def test_recruit_blank_handler():
    s = NationIntelligenceSystem()
    assert _recruit(s, handler_id="") is False


def test_recruit_dup_blocked():
    s = NationIntelligenceSystem()
    _recruit(s)
    assert _recruit(s) is False


def test_plant_happy():
    s = NationIntelligenceSystem()
    _recruit(s)
    assert s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    ) is True


def test_plant_unknown_blocked():
    s = NationIntelligenceSystem()
    assert s.plant_agent(
        agent_id="ghost", target_city="windy",
        now_day=10,
    ) is False


def test_plant_already_planted():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    assert s.plant_agent(
        agent_id="agent_007", target_city="sandy",
        now_day=20,
    ) is False


def test_begin_exfil():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    assert s.begin_exfil(
        agent_id="agent_007", now_day=100,
    ) is True


def test_complete_exfil_to_retired():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    s.begin_exfil(
        agent_id="agent_007", now_day=100,
    )
    s.complete_exfil(
        agent_id="agent_007", now_day=110,
    )
    assert s.agent(
        agent_id="agent_007",
    ).state == AgentState.RETIRED


def test_burn_agent():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    assert s.burn_agent(
        agent_id="agent_007", now_day=50,
    ) is True


def test_burn_after_retired_blocked():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    s.begin_exfil(
        agent_id="agent_007", now_day=100,
    )
    s.complete_exfil(
        agent_id="agent_007", now_day=110,
    )
    assert s.burn_agent(
        agent_id="agent_007", now_day=120,
    ) is False


def test_plan_operation_happy():
    s = NationIntelligenceSystem()
    _recruit(s)
    assert s.plan_operation(
        op_id="op_1", nation_id="bastok",
        kind=OperationKind.SURVEILLANCE,
        target="windy_council",
        agent_ids=["agent_007"],
    ) is True


def test_plan_unknown_agent():
    s = NationIntelligenceSystem()
    assert s.plan_operation(
        op_id="op_1", nation_id="bastok",
        kind=OperationKind.SURVEILLANCE,
        target="windy", agent_ids=["ghost"],
    ) is False


def test_plan_wrong_nation_agent():
    s = NationIntelligenceSystem()
    _recruit(s, nation_id="windy")
    assert s.plan_operation(
        op_id="op_1", nation_id="bastok",
        kind=OperationKind.SURVEILLANCE,
        target="windy", agent_ids=["agent_007"],
    ) is False


def test_plan_no_agents_blocked():
    s = NationIntelligenceSystem()
    assert s.plan_operation(
        op_id="op_1", nation_id="bastok",
        kind=OperationKind.SURVEILLANCE,
        target="windy", agent_ids=[],
    ) is False


def test_launch_unplanted_blocked():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plan_operation(
        op_id="op_1", nation_id="bastok",
        kind=OperationKind.SURVEILLANCE,
        target="windy", agent_ids=["agent_007"],
    )
    # Agent not yet planted
    assert s.launch_operation(
        op_id="op_1", now_day=20,
    ) is False


def test_launch_happy():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    s.plan_operation(
        op_id="op_1", nation_id="bastok",
        kind=OperationKind.SURVEILLANCE,
        target="windy", agent_ids=["agent_007"],
    )
    assert s.launch_operation(
        op_id="op_1", now_day=15,
    ) is True


def test_conclude_success():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    s.plan_operation(
        op_id="op_1", nation_id="bastok",
        kind=OperationKind.SABOTAGE, target="x",
        agent_ids=["agent_007"],
    )
    s.launch_operation(op_id="op_1", now_day=15)
    s.conclude_operation(
        op_id="op_1", success=True,
        note="warehouse burned", now_day=20,
    )
    o = s.operation(op_id="op_1")
    assert o.state == OperationState.COMPLETED


def test_conclude_failure():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    s.plan_operation(
        op_id="op_1", nation_id="bastok",
        kind=OperationKind.SABOTAGE, target="x",
        agent_ids=["agent_007"],
    )
    s.launch_operation(op_id="op_1", now_day=15)
    s.conclude_operation(
        op_id="op_1", success=False,
        note="agent caught", now_day=20,
    )
    assert s.operation(
        op_id="op_1",
    ).state == OperationState.FAILED


def test_file_report_happy():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    rid = s.file_report(
        agent_id="agent_007", target="windy_council",
        summary="3 ships sailed",
        reliability_pct=80, reported_day=15,
    )
    assert rid is not None


def test_file_report_unplanted_blocked():
    s = NationIntelligenceSystem()
    _recruit(s)
    rid = s.file_report(
        agent_id="agent_007", target="x",
        summary="x", reliability_pct=80,
        reported_day=15,
    )
    assert rid is None


def test_file_report_invalid_reliability():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    rid = s.file_report(
        agent_id="agent_007", target="x",
        summary="x", reliability_pct=120,
        reported_day=15,
    )
    assert rid is None


def test_reports_about_sorted_recent_first():
    s = NationIntelligenceSystem()
    _recruit(s)
    s.plant_agent(
        agent_id="agent_007", target_city="windy",
        now_day=10,
    )
    s.file_report(
        agent_id="agent_007", target="windy",
        summary="r1", reliability_pct=80,
        reported_day=15,
    )
    s.file_report(
        agent_id="agent_007", target="windy",
        summary="r2", reliability_pct=80,
        reported_day=20,
    )
    out = s.reports_about(target="windy")
    assert out[0].reported_day == 20
    assert out[1].reported_day == 15


def test_agent_unknown():
    s = NationIntelligenceSystem()
    assert s.agent(agent_id="ghost") is None


def test_operation_unknown():
    s = NationIntelligenceSystem()
    assert s.operation(op_id="ghost") is None


def test_enum_counts():
    assert len(list(AgentState)) == 5
    assert len(list(OperationKind)) == 5
    assert len(list(OperationState)) == 4
