"""Tests for server.tutorial_bastok_mines — the 7-gate first-90-min tutorial."""
from __future__ import annotations

import pytest

from server.tutorial_bastok_mines import (
    CHAIN_GATE_CLOSES_REQUIRED,
    DEFAULT_REVEAL_SKILL,
    GATE_TABLE,
    GATE_TO_BEAT,
    GOBLIN_SMITHY,
    GOBLIN_SMITHY_ATTACKS,
    GOBLIN_SMITHY_PHASES,
    REVEAL_SKILL_BY_JOB,
    TUTORIAL_AGE_OUT_MINUTES,
    FlowEvent,
    FlowResult,
    TutorialFlow,
    TutorialGate,
    TutorialPhase,
    TutorialSession,
    all_layered_scene_tags,
    first_gate,
    gate_after,
    get_beat,
    hammer_slam_cast_sequence,
    last_gate,
    named_attacks,
    pick_reveal_skill,
    total_phases,
)


# ----------------------------------------------------------------------
# gates
# ----------------------------------------------------------------------

class TestGates:

    def test_seven_gates(self):
        # Doc: 7 gates, 1..7 ordered
        assert len(GATE_TABLE) == 7
        ids = [b.gate for b in GATE_TABLE]
        assert ids == [
            TutorialGate.ARRIVAL, TutorialGate.WEIGHT,
            TutorialGate.FIRST_COMBAT, TutorialGate.REVEAL_SKILL,
            TutorialGate.INTERVENTION, TutorialGate.CHAIN,
            TutorialGate.BOSS,
        ]

    def test_first_and_last(self):
        assert first_gate() == TutorialGate.ARRIVAL
        assert last_gate() == TutorialGate.BOSS

    def test_gate_after(self):
        assert gate_after(TutorialGate.ARRIVAL) == TutorialGate.WEIGHT
        assert gate_after(TutorialGate.WEIGHT) == TutorialGate.FIRST_COMBAT
        assert gate_after(TutorialGate.FIRST_COMBAT) == TutorialGate.REVEAL_SKILL
        assert gate_after(TutorialGate.REVEAL_SKILL) == TutorialGate.INTERVENTION
        assert gate_after(TutorialGate.INTERVENTION) == TutorialGate.CHAIN
        assert gate_after(TutorialGate.CHAIN) == TutorialGate.BOSS
        assert gate_after(TutorialGate.BOSS) is None

    def test_get_beat_lookup(self):
        beat = get_beat(TutorialGate.ARRIVAL)
        assert beat.tutorial_npc == "cid"
        assert beat.layered_scene_tag == "Tutorial:gate_arrival"
        assert beat.completion_event == "cinematic_arrival_finished"
        # Doc anchors min 0-3 for arrival
        assert beat.minute_window == (0, 3)

    def test_each_gate_has_unique_tag_and_event(self):
        tags = [b.layered_scene_tag for b in GATE_TABLE]
        events = [b.completion_event for b in GATE_TABLE]
        assert len(set(tags)) == len(tags)
        assert len(set(events)) == len(events)

    def test_all_layered_scene_tags(self):
        tags = all_layered_scene_tags()
        assert len(tags) == 7
        # Doc-named tags
        assert "Tutorial:gate_arrival" in tags
        assert "Tutorial:gate_weight" in tags
        assert "Tutorial:gate_first_combat" in tags
        assert "Tutorial:gate_reveal_skill" in tags
        assert "Tutorial:gate_intervention" in tags
        assert "Tutorial:gate_chain" in tags
        assert "Tutorial:gate_boss" in tags

    def test_minute_windows_are_monotonic(self):
        # Each gate's window should not start before the previous
        # gate's window started — they cascade through the 90 min.
        prev_start = -1
        for b in GATE_TABLE:
            assert b.minute_window[0] > prev_start
            prev_start = b.minute_window[0]
        # The last gate must end at or before the age-out boundary.
        assert GATE_TABLE[-1].minute_window[1] <= TUTORIAL_AGE_OUT_MINUTES

    def test_chain_gate_threshold(self):
        # Doc: '3-5 successful chain closes'. We anchor at 3.
        assert CHAIN_GATE_CLOSES_REQUIRED == 3

    def test_age_out_is_90_min(self):
        # Doc: 'first 90 minutes'.
        assert TUTORIAL_AGE_OUT_MINUTES == 90

    def test_gate_to_beat_complete(self):
        # Sanity: every gate appears in the lookup
        for gate in TutorialGate:
            assert gate in GATE_TO_BEAT


# ----------------------------------------------------------------------
# reveal_skill_pick
# ----------------------------------------------------------------------

class TestRevealSkill:

    def test_whm_gets_scan(self):
        rs = pick_reveal_skill("WHM")
        assert rs.skill_id == "scan"
        assert rs.is_command is False

    def test_blm_gets_drain(self):
        rs = pick_reveal_skill("BLM")
        assert rs.skill_id == "drain"

    def test_thf_gets_mug(self):
        rs = pick_reveal_skill("THF")
        assert rs.skill_id == "mug"
        # Doc: 'introduced at lvl 25, used in tutorial early'
        assert rs.job_unlock_level == 25

    def test_war_gets_check_command(self):
        rs = pick_reveal_skill("WAR")
        assert rs.skill_id == "check"
        assert rs.is_command is True

    def test_pld_also_check(self):
        rs = pick_reveal_skill("PLD")
        assert rs.skill_id == "check"

    def test_unknown_job_falls_back_to_check(self):
        # Doc: '/check command' is the universal fallback
        rs = pick_reveal_skill("DRG")
        assert rs == DEFAULT_REVEAL_SKILL
        rs2 = pick_reveal_skill("NIN")
        assert rs2 == DEFAULT_REVEAL_SKILL

    def test_case_insensitive(self):
        assert pick_reveal_skill("whm").skill_id == "scan"
        assert pick_reveal_skill("Blm").skill_id == "drain"

    def test_table_covers_all_doc_jobs(self):
        for job in ("WHM", "BLM", "THF", "WAR", "PLD"):
            assert job in REVEAL_SKILL_BY_JOB


# ----------------------------------------------------------------------
# boss_smithy
# ----------------------------------------------------------------------

class TestBossSmithy:

    def test_recipe_minimum_per_doc(self):
        # Doc: 'lvl 5, 4 attacks, 3 phases, no critic'
        assert GOBLIN_SMITHY.level == 5
        assert len(GOBLIN_SMITHY.attacks) == 4
        assert len(GOBLIN_SMITHY.phases) == 3
        assert GOBLIN_SMITHY.has_critic_llm is False

    def test_named_attack_is_hammer_slam(self):
        named = named_attacks(GOBLIN_SMITHY)
        assert len(named) == 1
        slam = named[0]
        assert slam.name == "hammer_slam"
        assert slam.is_named is True
        assert slam.cast_time_seconds == 1.5
        assert slam.telegraph_shape == "cone"

    def test_other_attacks_are_unnamed(self):
        unnamed = [a for a in GOBLIN_SMITHY_ATTACKS if not a.is_named]
        assert len(unnamed) == 3
        for a in unnamed:
            assert a.cast_time_seconds == 0.0
            assert a.telegraph_shape is None

    def test_three_phases_at_correct_thresholds(self):
        # Phase boundaries at 100% / 66% / 33%
        thresholds = [p.triggered_at_hp_fraction
                       for p in GOBLIN_SMITHY_PHASES]
        assert thresholds == [1.0, 0.66, 0.33]

    def test_phase_visible_states_per_doc(self):
        labels = [p.visible_state_label for p in GOBLIN_SMITHY_PHASES]
        # Doc: 'pristine -> scuffed -> wounded'
        assert labels == ["pristine", "scuffed", "wounded"]

    def test_hammer_slam_cast_sequence(self):
        seq = hammer_slam_cast_sequence()
        assert seq == ("hit", "dodge", "dodge")

    def test_total_phases_helper(self):
        assert total_phases(GOBLIN_SMITHY) == 3

    def test_intro_cinematic_seconds(self):
        # Doc: '4 seconds' cinematic entrance
        assert GOBLIN_SMITHY.cinematic_intro_seconds == 4.0

    def test_closing_drop_and_line(self):
        # Doc: drops Bronze Ore; Cid says 'mining work, kid. Welcome.'
        assert GOBLIN_SMITHY.drop_id == "bronze_ore_small"
        assert GOBLIN_SMITHY.closing_line_npc == "cid"
        assert "Welcome" in GOBLIN_SMITHY.closing_line


# ----------------------------------------------------------------------
# state_machine — TutorialSession
# ----------------------------------------------------------------------

class TestSessionLifecycle:

    def test_initial_state(self):
        s = TutorialSession(actor_id="player_1", job="WAR")
        assert s.phase == TutorialPhase.NOT_STARTED
        assert s.current_gate is None
        assert s.completed_gates == []

    def test_start_enters_arrival_gate(self):
        s = TutorialSession(actor_id="player_1", job="WAR")
        s.start(now_minutes=0.0)
        assert s.phase == TutorialPhase.IN_PROGRESS
        assert s.current_gate == TutorialGate.ARRIVAL
        assert s.started_at_minutes == 0.0

    def test_start_idempotent(self):
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        s.start(now_minutes=99.0)   # second start no-op
        assert s.started_at_minutes == 0.0

    def test_complete_simple_gate(self):
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        ok = s.complete_current_gate(now_minutes=2.0)
        assert ok is True
        assert s.has_completed(TutorialGate.ARRIVAL)
        assert s.current_gate == TutorialGate.WEIGHT
        assert s.completed_gate_minutes[TutorialGate.ARRIVAL] == 2.0

    def test_chain_gate_blocks_until_threshold(self):
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        # Fast-forward through gates 1-5
        for _ in range(5):
            s.complete_current_gate(now_minutes=10.0)
        assert s.current_gate == TutorialGate.CHAIN
        # First 2 closes don't satisfy
        s.log_chain_close()
        s.log_chain_close()
        assert s.chain_gate_satisfied() is False
        ok = s.complete_current_gate(now_minutes=60.0)
        assert ok is False
        # Third close hits threshold
        s.log_chain_close()
        assert s.chain_gate_satisfied() is True
        ok = s.complete_current_gate(now_minutes=65.0)
        assert ok is True
        assert s.current_gate == TutorialGate.BOSS

    def test_log_chain_close_only_in_chain_gate(self):
        # Outside the CHAIN gate, log_chain_close shouldn't bump
        # the counter — protects against orphaned events.
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        # In ARRIVAL gate
        result = s.log_chain_close()
        assert result == 0
        assert s.chain_closes_logged == 0

    def test_full_clear(self):
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        # Clear gates 1-5
        for _ in range(5):
            s.complete_current_gate(now_minutes=10.0)
        # Clear chain gate
        for _ in range(CHAIN_GATE_CLOSES_REQUIRED):
            s.log_chain_close()
        s.complete_current_gate(now_minutes=60.0)
        # Clear boss gate
        s.complete_current_gate(now_minutes=85.0)
        assert s.phase == TutorialPhase.COMPLETED
        assert s.current_gate is None
        assert len(s.completed_gates) == 7

    def test_age_out_after_90_min(self):
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        # Complete 1 gate then go past 90 min
        s.complete_current_gate(now_minutes=2.0)
        changed = s.maybe_age_out(now_minutes=95.0)
        assert changed is True
        assert s.phase == TutorialPhase.AGED_OUT
        assert s.current_gate is None

    def test_age_out_does_not_fire_when_completed(self):
        # If the session already finished cleanly, do not flip to
        # AGED_OUT after the 90-min mark.
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        for _ in range(5):
            s.complete_current_gate(now_minutes=10.0)
        for _ in range(CHAIN_GATE_CLOSES_REQUIRED):
            s.log_chain_close()
        s.complete_current_gate(now_minutes=60.0)
        s.complete_current_gate(now_minutes=85.0)
        assert s.phase == TutorialPhase.COMPLETED
        s.maybe_age_out(now_minutes=200.0)
        assert s.phase == TutorialPhase.COMPLETED

    def test_abandon(self):
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        s.abandon()
        assert s.phase == TutorialPhase.ABANDONED
        assert s.current_gate is None

    def test_complete_in_aged_out_no_op(self):
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        s.maybe_age_out(now_minutes=200.0)
        ok = s.complete_current_gate(now_minutes=201.0)
        assert ok is False

    def test_remaining_gates(self):
        s = TutorialSession(actor_id="p", job="WAR")
        s.start(now_minutes=0.0)
        assert len(s.remaining_gates()) == 7
        s.complete_current_gate(now_minutes=2.0)
        assert len(s.remaining_gates()) == 6
        assert s.remaining_gates()[0] == TutorialGate.WEIGHT

    def test_progress_summary(self):
        s = TutorialSession(actor_id="p_42", job="WHM")
        s.start(now_minutes=0.0)
        s.complete_current_gate(now_minutes=2.0)
        summary = s.progress_summary()
        assert summary["actor_id"] == "p_42"
        assert summary["job"] == "WHM"
        assert summary["phase"] == TutorialPhase.IN_PROGRESS
        assert summary["current_gate"] == "WEIGHT"
        assert summary["completed_gates"] == ["ARRIVAL"]
        assert summary["completed_count"] == 1


# ----------------------------------------------------------------------
# flow — orchestrator hook
# ----------------------------------------------------------------------

class TestTutorialFlow:

    def _flow(self, *, job="WAR"):
        return TutorialFlow(TutorialSession(actor_id="p", job=job))

    def test_reveal_skill_for_player(self):
        flow = self._flow(job="WHM")
        assert flow.reveal_skill_for_player().skill_id == "scan"
        flow2 = self._flow(job="THF")
        assert flow2.reveal_skill_for_player().skill_id == "mug"

    def test_begin_starts_session(self):
        flow = self._flow()
        flow.begin(now_minutes=0.0)
        assert flow.session.phase == TutorialPhase.IN_PROGRESS

    def test_event_unrelated_to_gate_no_advance(self):
        flow = self._flow()
        flow.begin(now_minutes=0.0)
        result = flow.on_event(FlowEvent(
            event_kind="random_unrelated",
            actor_id="p", at_minutes=1.0,
        ))
        assert result.advanced is False
        assert flow.session.current_gate == TutorialGate.ARRIVAL

    def test_arrival_event_advances(self):
        flow = self._flow()
        flow.begin(now_minutes=0.0)
        result = flow.on_event(FlowEvent(
            event_kind="cinematic_arrival_finished",
            actor_id="p", at_minutes=2.5,
        ))
        assert result.advanced is True
        assert result.new_gate == TutorialGate.WEIGHT
        assert flow.session.has_completed(TutorialGate.ARRIVAL)

    def test_chain_event_accumulates_then_advances(self):
        flow = self._flow()
        flow.begin(now_minutes=0.0)
        # Fast-forward through gates 1-5 by direct event dispatch.
        events_to_clear = [
            "cinematic_arrival_finished",
            "hammer_delivered_doublet_received",
            "goblin_pickpocket_defeated",
            "reveal_skill_used_on_fomor",
            "cure_cast_on_wounded_miner",
        ]
        for ek in events_to_clear:
            flow.on_event(FlowEvent(event_kind=ek, actor_id="p",
                                       at_minutes=20.0))
        assert flow.session.current_gate == TutorialGate.CHAIN
        # 1st & 2nd close don't advance
        r1 = flow.on_event(FlowEvent(event_kind="chain_closed",
                                          actor_id="p", at_minutes=58.0))
        assert r1.advanced is False
        assert "chain close logged" in r1.note
        r2 = flow.on_event(FlowEvent(event_kind="chain_closed",
                                          actor_id="p", at_minutes=60.0))
        assert r2.advanced is False
        # 3rd close hits threshold
        r3 = flow.on_event(FlowEvent(event_kind="chain_closed",
                                          actor_id="p", at_minutes=62.0))
        assert r3.advanced is True
        assert r3.new_gate == TutorialGate.BOSS

    def test_age_out_blocks_event_handling(self):
        flow = self._flow()
        flow.begin(now_minutes=0.0)
        # Event arriving at minute 95 trips age-out
        result = flow.on_event(FlowEvent(
            event_kind="cinematic_arrival_finished",
            actor_id="p", at_minutes=95.0,
        ))
        assert result.aged_out is True
        assert result.advanced is False
        assert flow.session.phase == TutorialPhase.AGED_OUT

    def test_event_after_completion_is_no_op(self):
        flow = self._flow()
        flow.begin(now_minutes=0.0)
        # Roll through all 7 gates
        events_to_clear = [
            "cinematic_arrival_finished",
            "hammer_delivered_doublet_received",
            "goblin_pickpocket_defeated",
            "reveal_skill_used_on_fomor",
            "cure_cast_on_wounded_miner",
        ]
        for ek in events_to_clear:
            flow.on_event(FlowEvent(event_kind=ek, actor_id="p",
                                       at_minutes=20.0))
        for _ in range(CHAIN_GATE_CLOSES_REQUIRED):
            flow.on_event(FlowEvent(event_kind="chain_closed",
                                       actor_id="p", at_minutes=60.0))
        flow.on_event(FlowEvent(event_kind="goblin_smithy_defeated",
                                  actor_id="p", at_minutes=85.0))
        assert flow.is_completed()

        result = flow.on_event(FlowEvent(
            event_kind="cinematic_arrival_finished",
            actor_id="p", at_minutes=86.0,
        ))
        assert result.advanced is False
        assert flow.session.phase == TutorialPhase.COMPLETED

    def test_layered_scene_tags_only_during_in_progress(self):
        flow = self._flow()
        # Before start: no tags
        assert flow.active_layered_scene_tags() == ()
        flow.begin(now_minutes=0.0)
        # ARRIVAL gate -> only its tag is emitted
        tags = flow.active_layered_scene_tags()
        assert tags == ("Tutorial:gate_arrival",)
        flow.on_event(FlowEvent(
            event_kind="cinematic_arrival_finished",
            actor_id="p", at_minutes=2.5,
        ))
        assert flow.active_layered_scene_tags() == ("Tutorial:gate_weight",)
        # After abandon -> no tags
        flow.session.abandon()
        assert flow.active_layered_scene_tags() == ()

    def test_all_possible_tags_static(self):
        flow = self._flow()
        all_tags = flow.all_possible_tags()
        assert len(all_tags) == 7
        assert "Tutorial:gate_chain" in all_tags

    def test_chain_gate_ignores_unrelated_events(self):
        # While inside CHAIN gate, an unrelated event_kind must not
        # accidentally advance.
        flow = self._flow()
        flow.begin(now_minutes=0.0)
        events_to_clear = [
            "cinematic_arrival_finished",
            "hammer_delivered_doublet_received",
            "goblin_pickpocket_defeated",
            "reveal_skill_used_on_fomor",
            "cure_cast_on_wounded_miner",
        ]
        for ek in events_to_clear:
            flow.on_event(FlowEvent(event_kind=ek, actor_id="p",
                                       at_minutes=20.0))
        result = flow.on_event(FlowEvent(
            event_kind="goblin_smithy_defeated",  # wrong gate's event
            actor_id="p", at_minutes=60.0,
        ))
        assert result.advanced is False
        assert flow.session.current_gate == TutorialGate.CHAIN


# ----------------------------------------------------------------------
# Composition: full happy-path runthrough
# ----------------------------------------------------------------------

class TestHappyPath:
    """A complete walkthrough of all 7 gates as the orchestrator
    would dispatch them."""

    def test_war_player_clears_all_seven_gates(self):
        flow = TutorialFlow(TutorialSession(actor_id="hero", job="WAR"))
        flow.begin(now_minutes=0.0)

        # Gate 1: ARRIVAL
        r = flow.on_event(FlowEvent(
            event_kind="cinematic_arrival_finished",
            actor_id="hero", at_minutes=2.5,
        ))
        assert r.advanced is True

        # Gate 2: WEIGHT
        r = flow.on_event(FlowEvent(
            event_kind="hammer_delivered_doublet_received",
            actor_id="hero", at_minutes=8.0,
        ))
        assert r.advanced is True

        # Gate 3: FIRST_COMBAT
        r = flow.on_event(FlowEvent(
            event_kind="goblin_pickpocket_defeated",
            actor_id="hero", at_minutes=22.0,
        ))
        assert r.advanced is True

        # Gate 4: REVEAL_SKILL  (WAR -> /check)
        rs = flow.reveal_skill_for_player()
        assert rs.skill_id == "check"
        r = flow.on_event(FlowEvent(
            event_kind="reveal_skill_used_on_fomor",
            actor_id="hero", at_minutes=35.0,
        ))
        assert r.advanced is True

        # Gate 5: INTERVENTION
        r = flow.on_event(FlowEvent(
            event_kind="cure_cast_on_wounded_miner",
            actor_id="hero", at_minutes=50.0,
        ))
        assert r.advanced is True

        # Gate 6: CHAIN — 3 closes required
        for i in range(CHAIN_GATE_CLOSES_REQUIRED):
            r = flow.on_event(FlowEvent(
                event_kind="chain_closed",
                actor_id="hero", at_minutes=60.0 + i,
            ))
        assert r.advanced is True
        assert flow.session.current_gate == TutorialGate.BOSS

        # Gate 7: BOSS
        r = flow.on_event(FlowEvent(
            event_kind="goblin_smithy_defeated",
            actor_id="hero", at_minutes=87.0,
        ))
        assert r.advanced is True
        assert flow.is_completed()
        assert flow.session.phase == TutorialPhase.COMPLETED
        assert len(flow.session.completed_gates) == 7
        # No more layered-scene tags after completion
        assert flow.active_layered_scene_tags() == ()
