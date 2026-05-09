"""Nation intelligence — spy network and intel reports.

Each nation runs a covert SPY AGENCY: registry of
agents (NPC operatives, possibly with player handlers),
ACTIVE OPERATIONS, and INTEL REPORTS. Agents may be
PLANTED in foreign cities and run for years; their
output is timed reports the agency processes for
diplomatic, military, and economic decisions.

Agent states:
    RECRUITED     enlisted, awaiting placement
    PLANTED       in target territory, gathering
    EXFIL         being extracted
    BURNED        cover blown, no further intel
    RETIRED       honorably discharged

Operation kinds:
    SURVEILLANCE   passive watch
    SABOTAGE       targeted destruction
    EXFILTRATION   asset extraction
    DISINFORMATION rumor planting
    ASSASSINATION  hostile target neutralization

IntelReports come back from PLANTED agents:
    report_id, agent_id, target, summary,
    reliability_pct (0..100), reported_day

Public surface
--------------
    AgentState enum
    OperationKind enum
    OperationState enum (PLANNED / ACTIVE /
                          COMPLETED / FAILED)
    Agent dataclass (frozen)
    Operation dataclass (frozen)
    IntelReport dataclass (frozen)
    NationIntelligenceSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AgentState(str, enum.Enum):
    RECRUITED = "recruited"
    PLANTED = "planted"
    EXFIL = "exfil"
    BURNED = "burned"
    RETIRED = "retired"


class OperationKind(str, enum.Enum):
    SURVEILLANCE = "surveillance"
    SABOTAGE = "sabotage"
    EXFILTRATION = "exfiltration"
    DISINFORMATION = "disinformation"
    ASSASSINATION = "assassination"


class OperationState(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclasses.dataclass(frozen=True)
class Agent:
    agent_id: str
    nation_id: str
    handler_id: str
    cover_name: str
    placed_in: str
    planted_day: t.Optional[int]
    state: AgentState


@dataclasses.dataclass(frozen=True)
class Operation:
    op_id: str
    nation_id: str
    kind: OperationKind
    target: str
    agent_ids: tuple[str, ...]
    started_day: int
    ended_day: t.Optional[int]
    state: OperationState
    outcome_note: str


@dataclasses.dataclass(frozen=True)
class IntelReport:
    report_id: str
    agent_id: str
    target: str
    summary: str
    reliability_pct: int
    reported_day: int


@dataclasses.dataclass
class NationIntelligenceSystem:
    _agents: dict[str, Agent] = dataclasses.field(
        default_factory=dict,
    )
    _ops: dict[str, Operation] = dataclasses.field(
        default_factory=dict,
    )
    _reports: dict[str, IntelReport] = (
        dataclasses.field(default_factory=dict)
    )
    _next_report: int = 1

    def recruit_agent(
        self, *, agent_id: str, nation_id: str,
        handler_id: str, cover_name: str,
    ) -> bool:
        if not agent_id or not nation_id:
            return False
        if not handler_id or not cover_name:
            return False
        if agent_id in self._agents:
            return False
        self._agents[agent_id] = Agent(
            agent_id=agent_id, nation_id=nation_id,
            handler_id=handler_id,
            cover_name=cover_name, placed_in="",
            planted_day=None,
            state=AgentState.RECRUITED,
        )
        return True

    def plant_agent(
        self, *, agent_id: str, target_city: str,
        now_day: int,
    ) -> bool:
        if agent_id not in self._agents:
            return False
        if not target_city:
            return False
        a = self._agents[agent_id]
        if a.state != AgentState.RECRUITED:
            return False
        self._agents[agent_id] = dataclasses.replace(
            a, placed_in=target_city,
            planted_day=now_day,
            state=AgentState.PLANTED,
        )
        return True

    def begin_exfil(
        self, *, agent_id: str, now_day: int,
    ) -> bool:
        if agent_id not in self._agents:
            return False
        a = self._agents[agent_id]
        if a.state != AgentState.PLANTED:
            return False
        self._agents[agent_id] = dataclasses.replace(
            a, state=AgentState.EXFIL,
        )
        return True

    def complete_exfil(
        self, *, agent_id: str, now_day: int,
    ) -> bool:
        if agent_id not in self._agents:
            return False
        a = self._agents[agent_id]
        if a.state != AgentState.EXFIL:
            return False
        self._agents[agent_id] = dataclasses.replace(
            a, placed_in="",
            state=AgentState.RETIRED,
        )
        return True

    def burn_agent(
        self, *, agent_id: str, now_day: int,
    ) -> bool:
        if agent_id not in self._agents:
            return False
        a = self._agents[agent_id]
        if a.state in (
            AgentState.BURNED, AgentState.RETIRED,
        ):
            return False
        self._agents[agent_id] = dataclasses.replace(
            a, state=AgentState.BURNED,
        )
        return True

    def plan_operation(
        self, *, op_id: str, nation_id: str,
        kind: OperationKind, target: str,
        agent_ids: t.Sequence[str],
    ) -> bool:
        if not op_id or not nation_id:
            return False
        if not target or not agent_ids:
            return False
        if op_id in self._ops:
            return False
        # All agents must exist and belong to this
        # nation
        for aid in agent_ids:
            if aid not in self._agents:
                return False
            if self._agents[aid].nation_id != nation_id:
                return False
        self._ops[op_id] = Operation(
            op_id=op_id, nation_id=nation_id,
            kind=kind, target=target,
            agent_ids=tuple(agent_ids),
            started_day=0, ended_day=None,
            state=OperationState.PLANNED,
            outcome_note="",
        )
        return True

    def launch_operation(
        self, *, op_id: str, now_day: int,
    ) -> bool:
        if op_id not in self._ops:
            return False
        o = self._ops[op_id]
        if o.state != OperationState.PLANNED:
            return False
        # Every agent must be PLANTED
        for aid in o.agent_ids:
            if (self._agents[aid].state
                    != AgentState.PLANTED):
                return False
        self._ops[op_id] = dataclasses.replace(
            o, started_day=now_day,
            state=OperationState.ACTIVE,
        )
        return True

    def conclude_operation(
        self, *, op_id: str, success: bool,
        note: str, now_day: int,
    ) -> bool:
        if op_id not in self._ops:
            return False
        o = self._ops[op_id]
        if o.state != OperationState.ACTIVE:
            return False
        new_state = (
            OperationState.COMPLETED if success
            else OperationState.FAILED
        )
        self._ops[op_id] = dataclasses.replace(
            o, ended_day=now_day, state=new_state,
            outcome_note=note,
        )
        return True

    def file_report(
        self, *, agent_id: str, target: str,
        summary: str, reliability_pct: int,
        reported_day: int,
    ) -> t.Optional[str]:
        if agent_id not in self._agents:
            return None
        if not target or not summary:
            return None
        if (reliability_pct < 0
                or reliability_pct > 100):
            return None
        if reported_day < 0:
            return None
        a = self._agents[agent_id]
        if a.state != AgentState.PLANTED:
            return None
        rid = f"intel_{self._next_report}"
        self._next_report += 1
        self._reports[rid] = IntelReport(
            report_id=rid, agent_id=agent_id,
            target=target, summary=summary,
            reliability_pct=reliability_pct,
            reported_day=reported_day,
        )
        return rid

    def reports_about(
        self, *, target: str,
    ) -> list[IntelReport]:
        return sorted(
            (r for r in self._reports.values()
             if r.target == target),
            key=lambda r: -r.reported_day,
        )

    def agent(
        self, *, agent_id: str,
    ) -> t.Optional[Agent]:
        return self._agents.get(agent_id)

    def operation(
        self, *, op_id: str,
    ) -> t.Optional[Operation]:
        return self._ops.get(op_id)

    def report(
        self, *, report_id: str,
    ) -> t.Optional[IntelReport]:
        return self._reports.get(report_id)


__all__ = [
    "AgentState", "OperationKind", "OperationState",
    "Agent", "Operation", "IntelReport",
    "NationIntelligenceSystem",
]
