"""Public works — community-funded zone improvements.

A bridge across the Sandy/Bastok river. A monument to
the players who fell in the Crystal War. A new fountain
in the Tenshodo plaza. Public_works are projects players
collectively fund and that PERSIST in the world after
funding completes — gameplay benefits, lore plaques
crediting top contributors, sometimes new pathways.

A WorksProject has:
    project_id, zone_id, kind (BRIDGE / MONUMENT /
    FOUNTAIN / GUARDPOST / LIGHTHOUSE / SHRINE / DOCK),
    title, description, funding_goal_gil,
    contribution_caps (max per single contributor),
    benefit_summary (the gameplay effect once built —
    e.g. "Reduces travel time Bastok->Sandy by 30%").

State machine:
    PROPOSED        listed on the board, accepting
                    contributions
    UNDER_CONSTRUCTION funding goal hit; build clock
                    starts (default 7 days game time)
    COMPLETED       active; benefit applies
    DECAYED         optional later state — works can
                    decay if the world's economy state
                    pulls funding (out of scope here;
                    we expose the transition for callers)

Per-project ledger of contributions: which player gave
how much. The TOP CONTRIBUTOR (or top 3) get inscribed
on a plaque — read in environment_storytelling.

Public surface
--------------
    WorksKind enum
    WorksState enum
    WorksProject dataclass (frozen)
    Contribution dataclass (frozen)
    PublicWorks
        .propose(project) -> bool
        .contribute(player_id, project_id, amount_gil) -> bool
        .start_construction(project_id) -> bool
        .complete(project_id) -> bool
        .decay(project_id) -> bool
        .state(project_id) -> Optional[WorksState]
        .total_funded(project_id) -> int
        .top_contributors(project_id, n=3) -> list[(player_id, amount)]
        .projects_in_zone(zone_id) -> list[WorksProject]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class WorksKind(str, enum.Enum):
    BRIDGE = "bridge"
    MONUMENT = "monument"
    FOUNTAIN = "fountain"
    GUARDPOST = "guardpost"
    LIGHTHOUSE = "lighthouse"
    SHRINE = "shrine"
    DOCK = "dock"


class WorksState(str, enum.Enum):
    PROPOSED = "proposed"
    UNDER_CONSTRUCTION = "under_construction"
    COMPLETED = "completed"
    DECAYED = "decayed"


@dataclasses.dataclass(frozen=True)
class WorksProject:
    project_id: str
    zone_id: str
    kind: WorksKind
    title: str
    description: str
    funding_goal_gil: int
    per_contributor_cap_gil: int
    benefit_summary: str


@dataclasses.dataclass(frozen=True)
class Contribution:
    player_id: str
    amount_gil: int


@dataclasses.dataclass
class _ProjectState:
    spec: WorksProject
    state: WorksState = WorksState.PROPOSED
    contributions: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def total(self) -> int:
        return sum(self.contributions.values())


@dataclasses.dataclass
class PublicWorks:
    _projects: dict[str, _ProjectState] = dataclasses.field(
        default_factory=dict,
    )

    def propose(self, project: WorksProject) -> bool:
        if not project.project_id or not project.zone_id:
            return False
        if not project.title or not project.description:
            return False
        if project.funding_goal_gil <= 0:
            return False
        if project.per_contributor_cap_gil <= 0:
            return False
        if (project.per_contributor_cap_gil
                > project.funding_goal_gil):
            return False
        if project.project_id in self._projects:
            return False
        self._projects[project.project_id] = _ProjectState(
            spec=project,
        )
        return True

    def contribute(
        self, *, player_id: str, project_id: str,
        amount_gil: int,
    ) -> bool:
        if not player_id or amount_gil <= 0:
            return False
        if project_id not in self._projects:
            return False
        st = self._projects[project_id]
        if st.state != WorksState.PROPOSED:
            return False
        cur_for_player = st.contributions.get(player_id, 0)
        new_for_player = cur_for_player + amount_gil
        if (new_for_player
                > st.spec.per_contributor_cap_gil):
            return False
        # Don't accept past the goal
        if (st.total() + amount_gil
                > st.spec.funding_goal_gil):
            return False
        st.contributions[player_id] = new_for_player
        return True

    def start_construction(
        self, *, project_id: str,
    ) -> bool:
        if project_id not in self._projects:
            return False
        st = self._projects[project_id]
        if st.state != WorksState.PROPOSED:
            return False
        if st.total() < st.spec.funding_goal_gil:
            return False
        st.state = WorksState.UNDER_CONSTRUCTION
        return True

    def complete(self, *, project_id: str) -> bool:
        if project_id not in self._projects:
            return False
        st = self._projects[project_id]
        if st.state != WorksState.UNDER_CONSTRUCTION:
            return False
        st.state = WorksState.COMPLETED
        return True

    def decay(self, *, project_id: str) -> bool:
        if project_id not in self._projects:
            return False
        st = self._projects[project_id]
        if st.state != WorksState.COMPLETED:
            return False
        st.state = WorksState.DECAYED
        return True

    def state(
        self, *, project_id: str,
    ) -> t.Optional[WorksState]:
        if project_id not in self._projects:
            return None
        return self._projects[project_id].state

    def total_funded(self, *, project_id: str) -> int:
        if project_id not in self._projects:
            return 0
        return self._projects[project_id].total()

    def top_contributors(
        self, *, project_id: str, n: int = 3,
    ) -> list[tuple[str, int]]:
        if project_id not in self._projects:
            return []
        st = self._projects[project_id]
        sorted_contribs = sorted(
            st.contributions.items(),
            key=lambda p: -p[1],
        )
        return sorted_contribs[:n]

    def projects_in_zone(
        self, *, zone_id: str,
    ) -> list[WorksProject]:
        return sorted(
            (st.spec for st in self._projects.values()
             if st.spec.zone_id == zone_id),
            key=lambda p: p.project_id,
        )


__all__ = [
    "WorksKind", "WorksState", "WorksProject",
    "Contribution", "PublicWorks",
]
