"""Scenarios — 5-script playtest catalog from MAGIC_BURST_SCENARIOS.md.

Each scenario is a frame-by-frame combat script that exercises a
specific Demoncore system stack. Used as a playtest harness during
end-to-end integration tests.

Module layout:
    scenario.py - Scenario / ScenarioBeat / ScenarioOutcome
    catalog.py  - 5 scripts (s1..s5)
    runner.py   - replay walker + doc-alignment validator
"""
from .catalog import (
    SCENARIO_1_ANTI_CHEESE,
    SCENARIO_2_FIRST_SC,
    SCENARIO_3_THE_SAVE,
    SCENARIO_4_MOB_HEALER,
    SCENARIO_5_OPEN_WORLD,
    SCENARIOS,
    SCENARIOS_BY_ID,
    get_scenario,
    scenarios_using_system,
)
from .runner import RunResult, assert_doc_alignment, run_scenario
from .scenario import Scenario, ScenarioBeat, ScenarioOutcome

__all__ = [
    "Scenario", "ScenarioBeat", "ScenarioOutcome",
    "SCENARIOS", "SCENARIOS_BY_ID",
    "SCENARIO_1_ANTI_CHEESE", "SCENARIO_2_FIRST_SC",
    "SCENARIO_3_THE_SAVE", "SCENARIO_4_MOB_HEALER",
    "SCENARIO_5_OPEN_WORLD",
    "get_scenario", "scenarios_using_system",
    "RunResult", "run_scenario", "assert_doc_alignment",
]
