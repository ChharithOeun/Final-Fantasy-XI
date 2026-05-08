"""Server age milestones — anniversary-driven events.

The server itself has a lifetime. Demoncore tracks how
many real days have passed since launch and fires
auto-events at milestones — server-anniversary
broadcasts, retrospective bonuses, special items
distributed to all active players, retrospective
chronicle entries.

Default milestones:
    DAY_30        first month — newbie celebration
    DAY_90        first quarter — server economic check
    DAY_180       half-year — retrospective banner
    DAY_365       first anniversary — full festival
    DAY_730       second anniversary — exotic gift
    DAY_1095      third anniversary — legendary memento
    DAY_1825      five-year anniversary — Epic chronicle
                  entry, all-server gift

A milestone fires ONCE. Tick the module daily; it auto-
fires any milestones whose threshold has just been
crossed. Each fire emits a MilestoneEvent the caller
routes to delivery_box (gift), seasonal_events (festival
schedule), and server_chronicle (retrospective entry).

Public surface
--------------
    Milestone enum
    MilestoneEvent dataclass (frozen)
    ServerAgeMilestones
        .set_launch_day(day) -> bool
        .tick(now_day) -> list[MilestoneEvent]
        .next_milestone(now_day) -> Optional[Milestone]
        .age_in_days(now_day) -> int
        .fired_milestones() -> list[Milestone]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Milestone(str, enum.Enum):
    DAY_30 = "day_30"
    DAY_90 = "day_90"
    DAY_180 = "day_180"
    DAY_365 = "day_365"
    DAY_730 = "day_730"
    DAY_1095 = "day_1095"
    DAY_1825 = "day_1825"


_THRESHOLDS = [
    (Milestone.DAY_30, 30),
    (Milestone.DAY_90, 90),
    (Milestone.DAY_180, 180),
    (Milestone.DAY_365, 365),
    (Milestone.DAY_730, 730),
    (Milestone.DAY_1095, 1095),
    (Milestone.DAY_1825, 1825),
]


@dataclasses.dataclass(frozen=True)
class MilestoneEvent:
    milestone: Milestone
    fired_on_day: int
    server_age_days: int


@dataclasses.dataclass
class ServerAgeMilestones:
    _launch_day: t.Optional[int] = None
    _fired: set[Milestone] = dataclasses.field(
        default_factory=set,
    )

    def set_launch_day(self, *, day: int) -> bool:
        if day < 0:
            return False
        if self._launch_day is not None:
            return False  # immutable once set
        self._launch_day = day
        return True

    def age_in_days(self, *, now_day: int) -> int:
        if self._launch_day is None:
            return 0
        return max(0, now_day - self._launch_day)

    def tick(
        self, *, now_day: int,
    ) -> list[MilestoneEvent]:
        if self._launch_day is None:
            return []
        age = self.age_in_days(now_day=now_day)
        events: list[MilestoneEvent] = []
        for milestone, threshold in _THRESHOLDS:
            if milestone in self._fired:
                continue
            if age >= threshold:
                self._fired.add(milestone)
                events.append(MilestoneEvent(
                    milestone=milestone,
                    fired_on_day=now_day,
                    server_age_days=age,
                ))
        return events

    def next_milestone(
        self, *, now_day: int,
    ) -> t.Optional[Milestone]:
        if self._launch_day is None:
            return None
        age = self.age_in_days(now_day=now_day)
        for milestone, threshold in _THRESHOLDS:
            if milestone in self._fired:
                continue
            if age < threshold:
                return milestone
        return None

    def fired_milestones(self) -> list[Milestone]:
        return [
            m for m, _ in _THRESHOLDS if m in self._fired
        ]


__all__ = [
    "Milestone", "MilestoneEvent", "ServerAgeMilestones",
]
