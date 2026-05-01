"""Scenario runner — playtest harness for replay + assertion.

The runner walks a scenario's beats in order and pushes them to a
recorder. The recorder is a callable that the test harness or live
playtest tooling supplies; it observes each beat firing.

Used during end-to-end integration tests (test_end_to_end_integration.py
already exists in the suite) to validate that the orchestrator's
behavior matches the doc's canonical scripts.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .scenario import Scenario, ScenarioBeat


@dataclasses.dataclass
class RunResult:
    """One scenario replay's output."""
    scenario_id: str
    beats_fired: int
    callouts_emitted: tuple[str, ...]
    systems_observed: set[str]


def run_scenario(
    scenario: Scenario,
    *,
    on_beat: t.Optional[t.Callable[[ScenarioBeat], None]] = None,
    until_t_seconds: t.Optional[float] = None,
) -> RunResult:
    """Walk the scenario's beats in order.

    `until_t_seconds` clamps how far we walk (None = whole scenario).
    `on_beat` is invoked once per beat. Returns aggregate counts.
    """
    beats_fired = 0
    callouts: list[str] = []
    systems: set[str] = set()
    for beat in scenario.beats:
        if (until_t_seconds is not None
                and beat.t_seconds > until_t_seconds):
            break
        if on_beat is not None:
            on_beat(beat)
        beats_fired += 1
        if beat.expected_callout:
            callouts.append(beat.expected_callout)
        for s in beat.expected_systems:
            systems.add(s)
    return RunResult(
        scenario_id=scenario.scenario_id,
        beats_fired=beats_fired,
        callouts_emitted=tuple(callouts),
        systems_observed=systems,
    )


def assert_doc_alignment(scenario: Scenario) -> list[str]:
    """Verify each scenario beat references a system that's in the
    scenario's top-level systems_firing list.

    Returns a list of complaint strings (empty list = aligned). Used
    by CI to keep the catalog honest as the doc evolves.
    """
    complaints: list[str] = []
    expected = set(scenario.systems_firing)
    for i, beat in enumerate(scenario.beats):
        for s in beat.expected_systems:
            if s not in expected:
                complaints.append(
                    f"{scenario.scenario_id} beat #{i} cites "
                    f"'{s}' but scenario systems_firing has only "
                    f"{sorted(expected)}"
                )
    return complaints
