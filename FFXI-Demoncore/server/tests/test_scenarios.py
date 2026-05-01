"""Tests for server.scenarios — 5-scenario playtest harness."""
from __future__ import annotations

from server.scenarios import (
    SCENARIO_1_ANTI_CHEESE,
    SCENARIO_2_FIRST_SC,
    SCENARIO_3_THE_SAVE,
    SCENARIO_4_MOB_HEALER,
    SCENARIO_5_OPEN_WORLD,
    SCENARIOS,
    SCENARIOS_BY_ID,
    Scenario,
    ScenarioOutcome,
    assert_doc_alignment,
    get_scenario,
    run_scenario,
    scenarios_using_system,
)


class TestCatalog:

    def test_five_scenarios(self):
        # Doc names exactly 5
        assert len(SCENARIOS) == 5

    def test_scenario_ids_unique(self):
        ids = [s.scenario_id for s in SCENARIOS]
        assert len(set(ids)) == 5
        assert ids == ["s1", "s2", "s3", "s4", "s5"]

    def test_anti_cheese_outcome(self):
        assert SCENARIO_1_ANTI_CHEESE.expected_outcome == ScenarioOutcome.LESSON_LEARNED

    def test_first_sc_outcome(self):
        assert SCENARIO_2_FIRST_SC.expected_outcome == ScenarioOutcome.TUTORIAL_COMPLETE

    def test_the_save_outcome(self):
        assert SCENARIO_3_THE_SAVE.expected_outcome == ScenarioOutcome.HEROIC_SAVE

    def test_mob_healer_outcome(self):
        assert SCENARIO_4_MOB_HEALER.expected_outcome == ScenarioOutcome.CHAIN_BLOCKED

    def test_open_world_outcome(self):
        assert SCENARIO_5_OPEN_WORLD.expected_outcome == ScenarioOutcome.SURVIVAL

    def test_get_scenario_lookup(self):
        s = get_scenario("s3")
        assert s.title.startswith("The Save")

    def test_systems_using_intervention_mb(self):
        ss = scenarios_using_system("INTERVENTION_MB")
        assert SCENARIO_3_THE_SAVE in ss
        assert SCENARIO_4_MOB_HEALER in ss
        assert SCENARIO_1_ANTI_CHEESE not in ss

    def test_doc_alignment_clean(self):
        for s in SCENARIOS:
            complaints = assert_doc_alignment(s)
            assert complaints == [], f"{s.scenario_id}: {complaints}"

    def test_anti_cheese_systems(self):
        s = SCENARIO_1_ANTI_CHEESE
        assert "VISUAL_HEALTH_SYSTEM" in s.systems_firing
        assert "WEIGHT_PHYSICS" in s.systems_firing
        assert "NIN_HAND_SIGNS" in s.systems_firing

    def test_save_scenario_predicted_damage(self):
        # Doc opener: 8000 damage incoming
        s = SCENARIO_3_THE_SAVE
        ws_close = s.first_beat_kind("ws_close")
        assert ws_close.payload["predicted_mb_damage"] == 8000

    def test_mob_healer_chain_block(self):
        s = SCENARIO_4_MOB_HEALER
        cancel = next((b for b in s.beats
                          if b.event_kind == "damage_cancelled"), None)
        assert cancel is not None
        assert cancel.payload["actual_damage"] == 0


class TestRunner:

    def test_run_full_scenario(self):
        result = run_scenario(SCENARIO_3_THE_SAVE)
        assert result.scenario_id == "s3"
        assert result.beats_fired == len(SCENARIO_3_THE_SAVE.beats)
        assert "Magic Burst — Cure!" in result.callouts_emitted
        assert "INTERVENTION_MB" in result.systems_observed

    def test_run_scenario_with_callback(self):
        observed: list[str] = []
        run_scenario(SCENARIO_2_FIRST_SC,
                       on_beat=lambda b: observed.append(b.event_kind))
        # Walked all beats
        assert len(observed) == len(SCENARIO_2_FIRST_SC.beats)
        assert "ws_open" in observed
        assert "ws_close" in observed

    def test_run_until_t_seconds(self):
        # Stop at 3 seconds — only beats up to that mark fire
        result = run_scenario(SCENARIO_2_FIRST_SC, until_t_seconds=3.0)
        assert result.beats_fired < len(SCENARIO_2_FIRST_SC.beats)
        # ws_open (T+3) is included; later beats are not
        for b in SCENARIO_2_FIRST_SC.beats[:result.beats_fired]:
            assert b.t_seconds <= 3.0

    def test_run_callouts_collected(self):
        result = run_scenario(SCENARIO_2_FIRST_SC)
        assert "Skillchain open!" in result.callouts_emitted
        assert "Closing — Compression!" in result.callouts_emitted
