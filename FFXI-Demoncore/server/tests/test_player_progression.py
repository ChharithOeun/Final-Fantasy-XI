"""Tests for player progression: skill mastery + unlock cadence + Genkai
tests + state.

Run:  python -m pytest server/tests/test_player_progression.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from player_progression import (
    GENKAI_TESTS,
    GenkaiTest,
    GenkaiTestManager,
    MASTERY_5_PERKS,
    MASTERY_XP_AWARDS,
    MASTERY_XP_THRESHOLDS,
    PlayerProgressionState,
    SkillFamily,
    SkillMastery,
    SkillMasteryTracker,
    UNLOCK_CADENCE,
    all_unlocked_up_to,
    newly_unlocked_at,
    system_unlocked,
)
from player_progression.unlock_cadence import next_unlock_after


# ----------------------------------------------------------------------
# Skill mastery
# ----------------------------------------------------------------------

def test_new_skill_starts_at_zero():
    t = SkillMasteryTracker()
    assert t.mastery_level("cure_iv") == 0


def test_mb_window_cast_grants_one_xp():
    t = SkillMasteryTracker()
    t.grant_xp("cure_iv", family=SkillFamily.HEALING,
                event_kind="mb_window_cast")
    skill = t.skills["cure_iv"]
    assert skill.mastery_xp == 1
    assert skill.mastery_level == 0   # not yet at threshold 50


def test_intervention_grants_three_xp():
    t = SkillMasteryTracker()
    t.grant_xp("cure_iv", family=SkillFamily.HEALING,
                event_kind="successful_intervention")
    assert t.skills["cure_iv"].mastery_xp == 3


def test_mastery_level_thresholds_match_doc():
    """50 / 150 / 350 / 700 / 1500 cumulative."""
    assert MASTERY_XP_THRESHOLDS == {1: 50, 2: 150, 3: 350, 4: 700, 5: 1500}


def test_50_xp_reaches_mastery_1():
    t = SkillMasteryTracker()
    for _ in range(50):
        t.grant_xp("cure_iv", family=SkillFamily.HEALING,
                    event_kind="mb_window_cast")
    assert t.mastery_level("cure_iv") == 1


def test_1500_xp_reaches_mastery_5():
    t = SkillMasteryTracker()
    # 500 interventions * 3 XP = 1500 XP
    for _ in range(500):
        t.grant_xp("cure_iv", family=SkillFamily.HEALING,
                    event_kind="successful_intervention")
    assert t.mastery_level("cure_iv") == 5
    assert t.has_mastery_5("cure_iv") is True


def test_mastery_5_grants_10pct_cast_time_reduction():
    t = SkillMasteryTracker()
    for _ in range(500):
        t.grant_xp("cure_iv", family=SkillFamily.HEALING,
                    event_kind="successful_intervention")
    assert t.cast_time_multiplier("cure_iv") == 0.90


def test_mastery_5_grants_veteran_voice():
    t = SkillMasteryTracker()
    for _ in range(500):
        t.grant_xp("cure_iv", family=SkillFamily.HEALING,
                    event_kind="successful_intervention")
    assert t.voice_variant_for("cure_iv") == "veteran"


def test_mastery_5_perks_match_doc():
    assert MASTERY_5_PERKS["cast_time_reduction"] == 0.10
    assert MASTERY_5_PERKS["voice_variant"] == "veteran"
    assert MASTERY_5_PERKS["animation_flag"] == "refined"


def test_unknown_event_kind_zero_xp():
    t = SkillMasteryTracker()
    t.grant_xp("cure_iv", family=SkillFamily.HEALING,
                event_kind="nonexistent_event")
    assert "cure_iv" not in t.skills or t.skills["cure_iv"].mastery_xp == 0


def test_resisted_cast_no_xp():
    t = SkillMasteryTracker()
    t.grant_xp("firaga_iii", family=SkillFamily.OFFENSE_MAGIC,
                event_kind="spell_cast_resisted")
    # Even if the skill record gets created, no XP awarded
    assert t.mastery_level("firaga_iii") == 0


def test_perfect_skillchain_close_grants_two_xp():
    t = SkillMasteryTracker()
    t.grant_xp("savage_blade", family=SkillFamily.OFFENSE_PHYSICAL,
                event_kind="perfect_skillchain_close")
    assert t.skills["savage_blade"].mastery_xp == 2


def test_xp_multiplier_scales_award():
    """Caller can pass a multiplier (e.g. role-bonus, mood-bonus)."""
    t = SkillMasteryTracker()
    new_level = t.grant_xp("cure_iv", family=SkillFamily.HEALING,
                              event_kind="successful_intervention",
                              multiplier=2.0)
    assert t.skills["cure_iv"].mastery_xp == 6
    assert new_level == 0   # still below threshold 50


def test_mastery_transfers_across_jobs():
    """Doc: 'mastery is tied to YOU, not your gear.'"""
    t = SkillMasteryTracker()
    for _ in range(50):
        t.grant_xp("cure", family=SkillFamily.HEALING,
                    event_kind="mb_window_cast")
    # Skill record exists regardless of current job
    assert t.transfer_eligible("cure") is True


def test_all_mastery_5_skills():
    t = SkillMasteryTracker()
    for skill_id in ("cure_iv", "savage_blade"):
        for _ in range(500):
            t.grant_xp(skill_id, family=SkillFamily.HEALING,
                        event_kind="successful_intervention")
    apex = t.all_mastery_5_skills()
    assert "cure_iv" in apex
    assert "savage_blade" in apex


# ----------------------------------------------------------------------
# Unlock cadence
# ----------------------------------------------------------------------

def test_visual_health_unlocked_at_lvl_1():
    assert system_unlocked("visual_health", player_level=1) is True


def test_skillchain_tier_2_locked_at_low_level():
    assert system_unlocked("skillchain_tier_2", player_level=20) is False


def test_skillchain_tier_2_unlocked_at_40():
    assert system_unlocked("skillchain_tier_2", player_level=40) is True


def test_permadeath_active_only_at_99():
    assert system_unlocked("hardcore_permadeath", player_level=98) is False
    assert system_unlocked("hardcore_permadeath", player_level=99) is True


def test_newly_unlocked_at_specific_level():
    """Lvl 12 unlocks the first skillchain tutorial."""
    unlocks = newly_unlocked_at(12)
    assert any(u.system_id == "skillchain_tutorial_lv1" for u in unlocks)


def test_newly_unlocked_at_off_level_empty():
    """Level 13 has no canonical unlocks."""
    unlocks = newly_unlocked_at(13)
    assert unlocks == []


def test_lvl_99_player_has_all_unlocks():
    unlocks = all_unlocked_up_to(99)
    system_ids = {u.system_id for u in unlocks}
    for required in ("visual_health", "weight",
                       "weapon_skill_first", "magic_burst_window",
                       "intervention_mb", "skillchain_tier_3",
                       "boss_critic_llm", "outlaw_bounty_pvp",
                       "hardcore_permadeath"):
        assert required in system_ids


def test_next_unlock_after_lookup():
    """At lvl 7 the next unlock is at lvl 8 (weapon skill first)."""
    nxt = next_unlock_after(7)
    assert nxt is not None
    level, unlock = nxt
    assert level == 8
    assert unlock.system_id == "weapon_skill_first"


def test_next_unlock_after_99_is_none():
    assert next_unlock_after(99) is None


def test_unlock_has_tutorial_npc():
    """Doc: each unlock 'is preceded by a tutorial NPC encounter'."""
    unlocks = newly_unlocked_at(50)
    assert len(unlocks) == 1
    assert unlocks[0].tutorial_npc is not None


def test_unlock_cadence_count():
    """Doc claims 21-ish checkpoints. Confirm we have the major ones."""
    distinct_levels = len(UNLOCK_CADENCE)
    assert distinct_levels >= 18


# ----------------------------------------------------------------------
# Genkai tests
# ----------------------------------------------------------------------

def test_five_genkai_tests():
    assert set(GENKAI_TESTS.keys()) == {1, 2, 3, 4, 5}


def test_genkai_1_is_maat_at_50():
    g = GENKAI_TESTS[1]
    assert g.test_npc == "maat"
    assert g.job_level_required == 50
    assert g.next_level_cap == 55


def test_genkai_5_is_maat_rematch():
    g = GENKAI_TESTS[5]
    assert g.test_npc == "maat"
    assert g.job_level_required == 70
    assert g.boss_mood == "gruff"
    # Tests 'everything'
    assert len(g.tests) >= 5


def test_genkai_solo_only():
    for g in GENKAI_TESTS.values():
        assert g.is_solo_only is True


def test_can_attempt_at_required_level():
    mgr = GenkaiTestManager()
    eligible, reason = mgr.can_attempt(
        actor_id="alice", job_level=50, genkai_level=1,
    )
    assert eligible is True
    assert reason == ""


def test_cannot_attempt_below_level():
    mgr = GenkaiTestManager()
    eligible, reason = mgr.can_attempt(
        actor_id="alice", job_level=49, genkai_level=1,
    )
    assert eligible is False
    assert "50" in reason


def test_must_pass_prior_genkai_first():
    """Sequential: can't attempt Genkai 2 without passing 1."""
    mgr = GenkaiTestManager()
    eligible, reason = mgr.can_attempt(
        actor_id="alice", job_level=55, genkai_level=2,
    )
    assert eligible is False
    assert "Genkai 1" in reason


def test_party_blocks_solo_only_attempt():
    mgr = GenkaiTestManager()
    blocked = mgr.is_party_blocked(genkai_level=1, party_size=2)
    assert blocked is True
    assert mgr.is_party_blocked(genkai_level=1, party_size=1) is False


def test_attempt_returns_attempt_record():
    mgr = GenkaiTestManager()
    allowed, reason, attempt = mgr.attempt(
        actor_id="alice", job_level=50, genkai_level=1,
        party_size=1, now=100,
    )
    assert allowed is True
    assert attempt is not None
    assert attempt.actor_id == "alice"
    assert attempt.attempted_at == 100


def test_attempt_blocked_in_party():
    mgr = GenkaiTestManager()
    allowed, reason, attempt = mgr.attempt(
        actor_id="alice", job_level=50, genkai_level=1,
        party_size=4, now=0,
    )
    assert allowed is False
    assert "solo" in reason.lower()


def test_pass_unlocks_next_cap():
    mgr = GenkaiTestManager()
    cap = mgr.notify_passed(actor_id="alice", genkai_level=1)
    assert cap == 55


def test_passing_all_5_unlocks_cap_75():
    mgr = GenkaiTestManager()
    for level in (1, 2, 3, 4, 5):
        mgr.notify_passed(actor_id="alice", genkai_level=level)
    assert mgr.current_level_cap(actor_id="alice", base_cap=50) == 75


def test_cannot_repeat_passed_genkai():
    mgr = GenkaiTestManager()
    mgr.notify_passed(actor_id="alice", genkai_level=1)
    eligible, reason = mgr.can_attempt(
        actor_id="alice", job_level=55, genkai_level=1,
    )
    assert eligible is False
    assert "already" in reason


def test_full_genkai_progression_chain():
    """Pass 1, then 2, then 3 in sequence — each unlocks the next."""
    mgr = GenkaiTestManager()
    for level in (1, 2, 3):
        eligible, _ = mgr.can_attempt(
            actor_id="alice", job_level=GENKAI_TESTS[level].job_level_required,
            genkai_level=level,
        )
        assert eligible is True
        mgr.notify_passed(actor_id="alice", genkai_level=level)
    assert mgr.current_level_cap(actor_id="alice", base_cap=50) == 65


# ----------------------------------------------------------------------
# PlayerProgressionState (combined)
# ----------------------------------------------------------------------

def test_state_starts_blank():
    state = PlayerProgressionState(actor_id="alice")
    assert state.job_level == 1
    assert state.genkais_passed == set()
    assert state.tutorials_completed == set()


def test_state_effective_level_cap_with_genkais():
    state = PlayerProgressionState(actor_id="alice")
    state.genkais_passed = {1, 2}
    assert state.effective_level_cap() == 60


def test_state_endgame_at_75():
    state = PlayerProgressionState(actor_id="alice", job_level=75)
    assert state.is_endgame() is True
    assert state.is_apex() is False


def test_state_apex_at_99():
    state = PlayerProgressionState(actor_id="alice", job_level=99)
    assert state.is_apex() is True


def test_state_tutorial_completion():
    state = PlayerProgressionState(actor_id="alice")
    assert state.has_completed("visual_health") is False
    state.mark_tutorial_complete("visual_health")
    assert state.has_completed("visual_health") is True


def test_state_carries_mastery_tracker():
    state = PlayerProgressionState(actor_id="alice")
    state.masteries.grant_xp(
        "cure_iv", family=SkillFamily.HEALING,
        event_kind="mb_window_cast",
    )
    assert state.masteries.skills["cure_iv"].mastery_xp == 1


# ----------------------------------------------------------------------
# Integration: WHM mastery exemplar from the doc
# ----------------------------------------------------------------------

def test_whm_lvl5_curei_mastery_1_scenario():
    """Doc exemplar: a new WHM at lvl 5 with Cure I mastery 1."""
    state = PlayerProgressionState(actor_id="alice", job="WHM",
                                      job_level=5)
    # 50 successful MB-window casts get to mastery 1
    for _ in range(50):
        state.masteries.grant_xp(
            "cure_i", family=SkillFamily.HEALING,
            event_kind="mb_window_cast",
        )
    assert state.masteries.mastery_level("cure_i") == 1
    # Voice still untrained until mastery 5
    assert state.masteries.voice_variant_for("cure_i") == "untrained"


def test_endgame_whm_apex_mastery():
    """Doc exemplar: lvl 99 WHM, mastery 5 across Cures."""
    state = PlayerProgressionState(actor_id="alice", job="WHM",
                                      job_level=99)
    # Push Cure V and Cure IV both to mastery 5
    for skill_id in ("cure_iv", "cure_v"):
        for _ in range(500):
            state.masteries.grant_xp(
                skill_id, family=SkillFamily.HEALING,
                event_kind="successful_intervention",
            )
    assert state.is_apex() is True
    assert state.masteries.has_mastery_5("cure_iv")
    assert state.masteries.has_mastery_5("cure_v")
    assert state.masteries.voice_variant_for("cure_v") == "veteran"
    # 10% cast-time reduction is the audible-difference perk
    assert state.masteries.cast_time_multiplier("cure_v") == 0.90
