"""ScenarioBeat / Scenario — playtest harness for MAGIC_BURST_SCENARIOS.md.

Each scenario from the doc is a frame-by-frame playtest script.
We encode the metadata + the canonical event sequence here so
playtest tooling can:
    - look up the expected systems-firing list
    - replay the sequence against a stubbed orchestrator
    - assert that each beat fires at the right T+ time

The scenarios are READ-ONLY catalog entries — designers update the
doc, and we mirror the changes here. The harness compares actual
runs against the canonical sequence.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ScenarioOutcome(str, enum.Enum):
    """High-level result of the scenario."""
    LESSON_LEARNED = "lesson_learned"           # player adapts
    TUTORIAL_COMPLETE = "tutorial_complete"
    HEROIC_SAVE = "heroic_save"
    CHAIN_BLOCKED = "chain_blocked"             # mob healer blocks
    SURVIVAL = "survival"                       # ambush/random world


@dataclasses.dataclass(frozen=True)
class ScenarioBeat:
    """One frame of a scenario timeline."""
    t_seconds: float
    actor_id: str
    event_kind: str              # 'check' / 'cast_start' / 'ws_open' / ...
    payload: t.Mapping[str, t.Any] = dataclasses.field(
        default_factory=dict)
    expected_callout: str = ""
    expected_systems: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class Scenario:
    """One playtest script."""
    scenario_id: str             # 's1' / 's2' / ...
    title: str
    setup: str
    location_zone: str
    player_level_band: tuple[int, int]
    party_jobs: tuple[str, ...]
    hostile_classes: tuple[str, ...]
    expected_outcome: ScenarioOutcome
    systems_firing: tuple[str, ...]    # design-doc 'Systems firing' list
    beats: tuple[ScenarioBeat, ...]
    duration_seconds: float

    def beats_at_or_before(self, t_seconds: float) -> tuple[ScenarioBeat, ...]:
        return tuple(b for b in self.beats if b.t_seconds <= t_seconds)

    def first_beat_kind(self, kind: str) -> t.Optional[ScenarioBeat]:
        for b in self.beats:
            if b.event_kind == kind:
                return b
        return None

    def involves_system(self, system_id: str) -> bool:
        return system_id in self.systems_firing
