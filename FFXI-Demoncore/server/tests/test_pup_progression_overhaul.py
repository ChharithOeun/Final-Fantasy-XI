"""Tests for the PUP overhaul: progression rules + automaton catalog
extensions + neutral WHM rogues + Aphmau special-case.

Run:  python -m pytest server/tests/test_pup_progression_overhaul.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pup_progression import (
    APHMAU_SLOT_COUNT,
    AUTOMATON_BASE_SLOTS,
    AUTOMATON_CAST_RANGE_BONUS,
    AUTOMATON_CAST_TIME_REDUCTION,
    AUTOMATON_CURE_POTENCY_BONUS,
    AUTOMATON_DAMAGE_BUFF,
    BASE_ATTACHMENT_SLOTS,
    MAX_ATTACHMENT_SLOTS,
    MAX_ELEMENTAL_CAPACITY_BONUS,
    ATTACHMENT_SLOT_LEVEL_GATES,
    H2H_DUAL_WIELD_JOBS,
    H2H_WEAPON_CLASSES,
    MANEUVER_BURDEN_REDUCTION,
    PupProgressionState,
    additional_elemental_capacity,
    attachment_slot_capacity,
    automaton_slot_capacity,
    boosted_cure,
    buffed_damage,
    can_use_frame,
    effective_burden,
    elemental_capacity_for,
    extended_cast_range,
    h2h_requires_dual_wield,
    is_dual_wield_complete,
    reduced_cast_time,
)
from trust_system.companions import (
    APHMAU_OWNER_IDS,
    AUTOMATON_MB_BY_SC_TIER,
    AUTOMATON_SC_CLOSE_MB_WINDOW_SECONDS,
    AUTOMATON_SC_OPEN_WINDOW_SECONDS,
    COMPANION_CATALOG,
    CompanionManager,
    CompanionType,
    TANK_AOE_HATE_BASE_MULTIPLIER,
    TANK_AOE_HATE_PER_FIRE_OR_LIGHT_MANEUVER,
    companion_for,
    companions_by_type,
)
from trust_system import trust_for
from world_pups import (
    HEAL_PULSE_INTERVAL_SECONDS,
    NEUTRAL_WHM_ROGUES,
    NeutralRogueState,
    NeutralWhmRogueManager,
)


# ----------------------------------------------------------------------
# Aphmau is the unique 3-slot exception
# ----------------------------------------------------------------------

def test_aphmau_state_yields_three_slots():
    state = PupProgressionState(actor_id="aphmau", is_aphmau=True,
                                  job_level=20, master_level=0)
    assert automaton_slot_capacity(state) == APHMAU_SLOT_COUNT


def test_other_pup_starts_at_one_slot():
    state = PupProgressionState(actor_id="alice", job_level=99,
                                  master_level=24)
    assert automaton_slot_capacity(state) == AUTOMATON_BASE_SLOTS


def test_ml25_unlocks_two_slots_with_quest():
    """ML25 alone is not enough — quest gate must also be cleared."""
    state = PupProgressionState(actor_id="alice", job_level=99,
                                  master_level=25,
                                  second_automaton_unlocked=False)
    assert automaton_slot_capacity(state) == 1   # quest not done yet
    state.second_automaton_unlocked = True
    assert automaton_slot_capacity(state) == 2


def test_ml50_unlocks_three_slots_with_both_quests():
    state = PupProgressionState(actor_id="alice", job_level=99,
                                  master_level=50,
                                  second_automaton_unlocked=True,
                                  third_automaton_unlocked=True)
    assert automaton_slot_capacity(state) == 3


def test_aphmau_owner_id_special_case_in_manager():
    """The CompanionManager auto-bumps the cap to 3 for Aphmau."""
    mgr = CompanionManager()
    a1 = mgr.activate(companion_id="automaton_mnejing",
                       owner_id="aphmau", now=0)
    a2 = mgr.activate(companion_id="automaton_sharpshot",
                       owner_id="aphmau", now=0)
    a3 = mgr.activate(companion_id="automaton_valoredge",
                       owner_id="aphmau", now=0)
    assert a1 is not None
    assert a2 is not None
    assert a3 is not None     # 3rd allowed without explicit cap
    assert "aphmau" in APHMAU_OWNER_IDS


def test_default_pup_caps_at_one():
    """Other PUPs default to 1 active automaton."""
    mgr = CompanionManager()
    a1 = mgr.activate(companion_id="automaton_valoredge",
                       owner_id="alice", now=0)
    a2 = mgr.activate(companion_id="automaton_soulsoother",
                       owner_id="alice", now=0)
    # Default max_active_for_pup=1: second activation blocked
    assert a1 is not None
    assert a2 is None


# ----------------------------------------------------------------------
# Frame unlocks — NIN / DRG / BLU
# ----------------------------------------------------------------------

def test_standard_frames_always_available():
    state = PupProgressionState(actor_id="alice", job_level=20)
    for frame in ("automaton_valoredge", "automaton_sharpshot",
                    "automaton_soulsoother", "automaton_spiritreaver",
                    "automaton_stormwaker"):
        assert can_use_frame(state, frame) is True


def test_nin_frame_requires_lvl_75_full_merit_plus_quests():
    state = PupProgressionState(actor_id="alice", job_level=70,
                                  is_fully_merit=True,
                                  nin_head_unlocked=True,
                                  nin_frame_unlocked=True)
    assert can_use_frame(state, "automaton_ninja") is False  # lvl too low

    state.job_level = 75
    state.is_fully_merit = False
    assert can_use_frame(state, "automaton_ninja") is False  # not fully merit

    state.is_fully_merit = True
    state.nin_frame_unlocked = False
    assert can_use_frame(state, "automaton_ninja") is False  # frame quest

    state.nin_frame_unlocked = True
    assert can_use_frame(state, "automaton_ninja") is True


def test_drg_frame_hidden_at_99_mastered():
    state = PupProgressionState(actor_id="alice", job_level=99,
                                  job_mastered=True,
                                  drg_head_unlocked=True,
                                  drg_frame_unlocked=True)
    assert can_use_frame(state, "automaton_dragoon") is True
    state.job_mastered = False
    assert can_use_frame(state, "automaton_dragoon") is False


def test_blu_frame_hidden_at_99_mastered():
    state = PupProgressionState(actor_id="alice", job_level=99,
                                  job_mastered=True,
                                  blu_head_unlocked=True,
                                  blu_frame_unlocked=True)
    assert can_use_frame(state, "automaton_blue") is True


def test_unknown_frame_refused():
    state = PupProgressionState(actor_id="alice", job_level=99,
                                  job_mastered=True)
    assert can_use_frame(state, "automaton_godking") is False


# ----------------------------------------------------------------------
# Attachment slots — lvl 80/85/90/95 gates
# ----------------------------------------------------------------------

def test_base_attachment_slots_match_retail_cap():
    """Retail FFXI cap is 8; that's the new base per user direction."""
    assert BASE_ATTACHMENT_SLOTS == 8
    state = PupProgressionState(actor_id="alice", job_level=75)
    assert attachment_slot_capacity(state) == 8


def test_each_quest_unlocks_one_slot():
    state = PupProgressionState(actor_id="alice", job_level=80)
    state.attachment_slots_unlocked = {80}
    assert attachment_slot_capacity(state) == 9          # 8 + 1
    state.attachment_slots_unlocked = {80, 85, 90, 95}
    assert attachment_slot_capacity(state) == 12         # apex


def test_attachment_max_apex_is_12():
    assert MAX_ATTACHMENT_SLOTS == 12


def test_attachment_slot_gates_match_doc():
    assert ATTACHMENT_SLOT_LEVEL_GATES == (80, 85, 90, 95)


# ----------------------------------------------------------------------
# Elemental capacity — base 10 + 30 across lvl 99 / ML25 / ML50
# ----------------------------------------------------------------------

def test_no_bonus_below_99():
    """Per user correction: progression bonus is purely additive on top
    of whatever retail base capacity exists. Below lvl 99, the bonus
    is 0 — caller still sees the retail base."""
    state = PupProgressionState(actor_id="alice", job_level=75)
    assert additional_elemental_capacity(state) == 0
    # With a retail base of 30, total is just 30
    assert elemental_capacity_for(state, retail_base=30) == 30


def test_lvl99_adds_10_bonus():
    state = PupProgressionState(actor_id="alice", job_level=99)
    assert additional_elemental_capacity(state) == 10
    # Retail base 30 + bonus 10 = 40
    assert elemental_capacity_for(state, retail_base=30) == 40


def test_ml25_adds_another_10_bonus():
    state = PupProgressionState(actor_id="alice", job_level=99,
                                  master_level=25)
    assert additional_elemental_capacity(state) == 20
    assert elemental_capacity_for(state, retail_base=30) == 50


def test_ml50_apex_bonus_30():
    state = PupProgressionState(actor_id="alice", job_level=99,
                                  master_level=50)
    assert additional_elemental_capacity(state) == 30
    assert elemental_capacity_for(state, retail_base=30) == 60


def test_max_elemental_bonus_constant():
    assert MAX_ELEMENTAL_CAPACITY_BONUS == 30


# ----------------------------------------------------------------------
# Maneuver burden — 70% reduction
# ----------------------------------------------------------------------

def test_burden_reduced_by_70_percent():
    assert MANEUVER_BURDEN_REDUCTION == 0.70
    assert effective_burden(100.0) == pytest.approx(30.0)


def test_zero_burden_stays_zero():
    assert effective_burden(0.0) == 0.0


# ----------------------------------------------------------------------
# Damage buff — +25% global
# ----------------------------------------------------------------------

def test_damage_buff_25_pct():
    assert AUTOMATON_DAMAGE_BUFF == 0.25
    assert buffed_damage(100.0) == 125.0


# ----------------------------------------------------------------------
# H2H dual wield
# ----------------------------------------------------------------------

def test_h2h_dual_wield_jobs_match_user_correction():
    """Per user correction: only MNK / PUP / WAR / RDM / NIN."""
    assert H2H_DUAL_WIELD_JOBS == frozenset({"MNK", "PUP", "WAR", "RDM", "NIN"})


def test_pup_with_h2h_requires_dual_wield():
    assert h2h_requires_dual_wield("PUP", "hand_to_hand") is True


def test_mnk_with_h2h_requires_dual_wield():
    assert h2h_requires_dual_wield("MNK", "fists") is True
    assert h2h_requires_dual_wield("MNK", "knuckles") is True


def test_war_with_h2h_requires_dual_wield():
    """User direction explicitly includes WAR using H2H."""
    assert h2h_requires_dual_wield("WAR", "fists") is True


def test_rdm_with_h2h_requires_dual_wield():
    """RDM is on the H2H list per the correction."""
    assert h2h_requires_dual_wield("RDM", "fists") is True


def test_nin_with_h2h_requires_dual_wield():
    """NIN is on the H2H list per the correction."""
    assert h2h_requires_dual_wield("NIN", "knuckles") is True


def test_sch_no_longer_on_h2h_list():
    """SCH was on the original list; user removed it."""
    assert h2h_requires_dual_wield("SCH", "fists") is False


def test_blm_h2h_no_rule():
    """A BLM in fists isn't a canonical H2H job."""
    assert h2h_requires_dual_wield("BLM", "fists") is False


def test_mnk_with_staff_no_dual_wield():
    """Off-class weapon for an H2H job: rule doesn't apply."""
    assert h2h_requires_dual_wield("MNK", "staff") is False


def test_dual_wield_complete_check():
    assert is_dual_wield_complete(main_hand_class="cesti",
                                     off_hand_class="cesti") is True
    assert is_dual_wield_complete(main_hand_class="cesti",
                                     off_hand_class=None) is False
    assert is_dual_wield_complete(main_hand_class="cesti",
                                     off_hand_class="staff") is False


# ----------------------------------------------------------------------
# Automaton tuning — cast time / range / cure potency
# ----------------------------------------------------------------------

def test_cast_time_minus_50_pct():
    assert AUTOMATON_CAST_TIME_REDUCTION == 0.50
    assert reduced_cast_time(4.0) == 2.0
    assert reduced_cast_time(2.0) == 1.0


def test_instant_cast_unaffected_by_reduction():
    """base 0 stays 0."""
    assert reduced_cast_time(0) == 0.0
    assert reduced_cast_time(-1) == 0.0


def test_cast_range_plus_15_pct():
    assert AUTOMATON_CAST_RANGE_BONUS == 0.15
    assert extended_cast_range(1000.0) == pytest.approx(1150.0)


def test_cure_potency_plus_25_pct():
    assert AUTOMATON_CURE_POTENCY_BONUS == 0.25
    assert boosted_cure(400.0) == 500.0


def test_zero_cast_range_stays_zero():
    assert extended_cast_range(0.0) == 0.0


# ----------------------------------------------------------------------
# Companion catalog extensions — new frames
# ----------------------------------------------------------------------

def test_ninja_frame_in_catalog():
    nin = companion_for("automaton_ninja")
    assert nin is not None
    assert "utsusemi_san_no_tools" in nin.abilities
    assert "throwing_assault" in nin.abilities


def test_dragoon_frame_in_catalog():
    drg = companion_for("automaton_dragoon")
    assert drg is not None
    assert "jump" in drg.abilities


def test_blu_frame_in_catalog():
    blu = companion_for("automaton_blue")
    assert blu is not None
    assert "self_skillchain_starter" in blu.abilities
    assert "self_magic_burst" in blu.abilities


def test_now_have_nine_automaton_frames():
    """6 standard + 3 new = 9."""
    automatons = companions_by_type(CompanionType.AUTOMATON)
    assert len(automatons) == 9


# ----------------------------------------------------------------------
# Healer + tank automaton ability extensions
# ----------------------------------------------------------------------

def test_soulsoother_can_heal_other_automatons():
    """Per user direction: automatons can cure/heal/revive other
    automatons."""
    healer = companion_for("automaton_soulsoother")
    assert "cure_other_automaton" in healer.abilities
    assert "regen_other_automaton" in healer.abilities
    assert "raise_other_automaton" in healer.abilities


def test_tank_automatons_have_aoe_hate_kit():
    """Mnejing + Valoredge get AOE flash/provoke/strobe."""
    for tank_id in ("automaton_mnejing", "automaton_valoredge"):
        tank = companion_for(tank_id)
        assert "aoe_provoke" in tank.abilities
        assert "aoe_flash" in tank.abilities
        assert "aoe_strobe" in tank.abilities


def test_tank_aoe_hate_constants_match_spec():
    """Per user direction: 3x base, +1x per fire/light maneuver."""
    assert TANK_AOE_HATE_BASE_MULTIPLIER == 3.0
    assert TANK_AOE_HATE_PER_FIRE_OR_LIGHT_MANEUVER == 1.0


# ----------------------------------------------------------------------
# Automaton SC + MB windows
# ----------------------------------------------------------------------

def test_sc_open_window_5_seconds():
    assert AUTOMATON_SC_OPEN_WINDOW_SECONDS == 5.0


def test_sc_close_mb_window_15_seconds():
    assert AUTOMATON_SC_CLOSE_MB_WINDOW_SECONDS == 15.0


def test_mb_count_scales_with_sc_tier():
    """Tier 1 = 1 MB, Tier 2 = 2 MBs, Tier 3+ = 3 MBs."""
    assert AUTOMATON_MB_BY_SC_TIER[1] == 1
    assert AUTOMATON_MB_BY_SC_TIER[2] == 2
    assert AUTOMATON_MB_BY_SC_TIER[3] == 3


# ----------------------------------------------------------------------
# BLU trust self-SC + 3-stage MB
# ----------------------------------------------------------------------

def test_blu_trust_has_sc_capable_spells():
    """Jakoh's spell book includes both opener and closer for self-SC."""
    blu = trust_for("jakoh_blu")
    assert blu is not None
    # opener spells
    assert any(s in blu.companions
                 for s in ("blu_quad_continuum", "blu_hysteric_barrage"))
    # closer spells
    assert any(s in blu.companions
                 for s in ("blu_disseverment", "blu_chant_du_cygne"))


def test_blu_trust_has_mb_capable_nukes():
    blu = trust_for("jakoh_blu")
    for nuke in ("blu_blastbomb", "blu_thunderbolt", "blu_silent_storm"):
        assert nuke in blu.companions


def test_blu_trust_has_azure_lore_sp():
    blu = trust_for("jakoh_blu")
    assert "blu_azure_lore_sp" in blu.companions
    sp = companion_for("blu_azure_lore_sp")
    assert "self_skillchain_window" in sp.abilities


def test_blu_self_sc_chain_metadata():
    """The new BLU spells carry skillchain_starter/closer tags so the
    AI brain can pair them correctly."""
    quad = companion_for("blu_quad_continuum")
    assert "skillchain_starter_fragmentation" in quad.abilities
    cygne = companion_for("blu_chant_du_cygne")
    assert "skillchain_closer_light" in cygne.abilities


# ----------------------------------------------------------------------
# Ovjang renamed
# ----------------------------------------------------------------------

def test_ovjang_renamed():
    """The 'Ovjang' name was taken in canonical FFXI; renamed to
    Talgarazz the Fixer."""
    from world_pups import PUP_NPC_CATALOG
    assert "ovjang_the_fixer" not in PUP_NPC_CATALOG
    assert "talgarazz_the_fixer" in PUP_NPC_CATALOG


# ----------------------------------------------------------------------
# Neutral WHM Rogue Automatons — 1 per continent
# ----------------------------------------------------------------------

def test_four_continental_neutral_rogues():
    assert len(NEUTRAL_WHM_ROGUES) == 4
    continents = {spec.continent for spec in NEUTRAL_WHM_ROGUES.values()}
    assert continents == {"quon", "mindartia", "aradjiah", "ulbuka"}


def test_each_neutral_rogue_has_alarm_party():
    for spec in NEUTRAL_WHM_ROGUES.values():
        assert len(spec.alarm_party) >= 4


def test_neutral_rogue_starts_neutral():
    mgr = NeutralWhmRogueManager()
    rt = mgr.get("the_quon_handmaid")
    assert rt is not None
    assert rt.state == NeutralRogueState.NEUTRAL


def test_attacking_neutral_rogue_triggers_alarm():
    mgr = NeutralWhmRogueManager()
    alarm_party = mgr.notify_attacked(
        "the_quon_handmaid", attacker_id="alice", now=100,
    )
    assert alarm_party is not None
    assert len(alarm_party) >= 4
    assert mgr.get("the_quon_handmaid").state == NeutralRogueState.ALARMED


def test_already_alarmed_no_op():
    """Repeat attacks don't re-trigger the alarm."""
    mgr = NeutralWhmRogueManager()
    mgr.notify_attacked("the_quon_handmaid", attacker_id="alice", now=100)
    second = mgr.notify_attacked(
        "the_quon_handmaid", attacker_id="bob", now=200,
    )
    assert second is None


def test_heal_pulse_fires_for_nearby_player():
    mgr = NeutralWhmRogueManager()
    pulse = mgr.maybe_heal_pulse(
        "the_quon_handmaid", now=200,
        nearby_player_ids=["alice"],
        nearby_downed_player_ids=[],
    )
    assert pulse is not None
    assert "alice" in pulse["healed"]
    assert pulse["heal_amount"] > 0


def test_heal_pulse_raises_downed_players():
    mgr = NeutralWhmRogueManager()
    pulse = mgr.maybe_heal_pulse(
        "the_quon_handmaid", now=200,
        nearby_player_ids=[],
        nearby_downed_player_ids=["bob"],
    )
    assert pulse is not None
    assert "bob" in pulse["raised"]


def test_heal_pulse_cooldown():
    mgr = NeutralWhmRogueManager()
    first = mgr.maybe_heal_pulse(
        "the_quon_handmaid", now=0,
        nearby_player_ids=["alice"],
        nearby_downed_player_ids=[],
    )
    assert first is not None
    # Within cooldown: blocked
    second = mgr.maybe_heal_pulse(
        "the_quon_handmaid", now=30,
        nearby_player_ids=["alice"],
        nearby_downed_player_ids=[],
    )
    assert second is None
    # After cooldown: fires
    third = mgr.maybe_heal_pulse(
        "the_quon_handmaid", now=HEAL_PULSE_INTERVAL_SECONDS + 1,
        nearby_player_ids=["alice"],
        nearby_downed_player_ids=[],
    )
    assert third is not None


def test_alarmed_rogue_doesnt_heal_pulse():
    mgr = NeutralWhmRogueManager()
    mgr.notify_attacked("the_quon_handmaid", attacker_id="alice", now=0)
    pulse = mgr.maybe_heal_pulse(
        "the_quon_handmaid", now=200,
        nearby_player_ids=["alice", "bob"],
        nearby_downed_player_ids=[],
    )
    assert pulse is None   # alarmed = no heal


def test_reset_to_neutral_clears_alarm():
    mgr = NeutralWhmRogueManager()
    mgr.notify_attacked("the_quon_handmaid", attacker_id="alice", now=0)
    mgr.reset_to_neutral("the_quon_handmaid")
    assert mgr.is_neutral("the_quon_handmaid") is True


# ----------------------------------------------------------------------
# Integration: Aphmau-class deploy with three frames
# ----------------------------------------------------------------------

def test_aphmau_three_frame_deploy_end_to_end():
    """Aphmau deploys 3 different automatons via the manager."""
    mgr = CompanionManager()
    deployed = []
    for frame_id in ("automaton_mnejing", "automaton_sharpshot",
                       "automaton_soulsoother"):
        att = mgr.activate(companion_id=frame_id, owner_id="aphmau",
                            owner_kind="trust", now=0)
        assert att is not None
        deployed.append(att)
    active = mgr.active_for_owner("aphmau")
    assert len(active) == 3


def test_other_pup_with_ml50_progression_three_slots():
    """A non-Aphmau PUP with full ML50 progression also deploys 3."""
    state = PupProgressionState(
        actor_id="alice", job_level=99, master_level=50,
        second_automaton_unlocked=True,
        third_automaton_unlocked=True,
    )
    assert automaton_slot_capacity(state) == 3
    mgr = CompanionManager()
    for frame_id in ("automaton_valoredge", "automaton_soulsoother",
                       "automaton_spiritreaver"):
        att = mgr.activate(companion_id=frame_id, owner_id="alice",
                            now=0,
                            max_active_for_pup=automaton_slot_capacity(state))
        assert att is not None
    assert len(mgr.active_for_owner("alice")) == 3
