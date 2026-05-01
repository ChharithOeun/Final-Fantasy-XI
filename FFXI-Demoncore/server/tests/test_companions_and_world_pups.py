"""Tests for companions engine + extended trust catalog + world PUPs.

Run:  python -m pytest server/tests/test_companions_and_world_pups.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from trust_system import (
    COMPANION_CATALOG,
    CompanionAttachment,
    CompanionManager,
    CompanionRole,
    CompanionSpec,
    CompanionType,
    TRUST_CATALOG,
    companion_for,
    companions_by_type,
    trust_for,
)
from trust_system.catalog import trusts_for_nation
from world_pups import (
    PUP_NPC_CATALOG,
    ROGUE_AUTOMATON_NMS,
    ROGUE_AUTOMATON_RESPAWN_SECONDS,
    PupNpcSpec,
    RespawnTracker,
    RogueAutomatonNM,
    pup_npcs_in_zone,
    rogue_automaton_for,
)
from world_pups.rogue_automatons import (
    RogueAutomatonClass,
    rogue_automatons_in_zone,
)


# ----------------------------------------------------------------------
# Companion catalog
# ----------------------------------------------------------------------

def test_companion_catalog_has_all_types():
    types_present = {c.companion_type for c in COMPANION_CATALOG.values()}
    for required in (CompanionType.AUTOMATON, CompanionType.AVATAR,
                       CompanionType.JUG_PET, CompanionType.BLU_SPELL):
        assert required in types_present


def test_automaton_frame_count():
    """6 standard frames + 3 new (NIN/DRG/BLU) = 9 after the PUP overhaul."""
    automatons = companions_by_type(CompanionType.AUTOMATON)
    assert len(automatons) == 9


def test_nine_avatars_includes_carbuncle_and_primes():
    avatars = companions_by_type(CompanionType.AVATAR)
    avatar_names = {a.companion_id for a in avatars}
    assert "avatar_carbuncle" in avatar_names
    for prime in ("avatar_ifrit", "avatar_shiva", "avatar_ramuh",
                    "avatar_garuda", "avatar_titan",
                    "avatar_leviathan", "avatar_fenrir"):
        assert prime in avatar_names


def test_diabolos_is_dream_prime():
    diabolos = companion_for("avatar_diabolos")
    assert diabolos is not None
    assert diabolos.role == CompanionRole.UTILITY


def test_jug_pets_have_durations():
    """Jug pets are timed companions (15min default)."""
    jug = companion_for("jug_carrie")
    assert jug.duration_seconds is not None
    assert jug.duration_seconds == 900.0


def test_blu_spells_no_attachment():
    """BLU spells live in the catalog but aren't 'attached'."""
    cocoon = companion_for("blu_cocoon")
    assert cocoon is not None
    assert cocoon.companion_type == CompanionType.BLU_SPELL


def test_companion_for_unknown_returns_none():
    assert companion_for("avatar_ultros") is None


# ----------------------------------------------------------------------
# Extended trust roster — pet trusts
# ----------------------------------------------------------------------

def test_aphmau_has_two_automatons():
    """User direction: 'Aphmau should be able to activate both her automatons'."""
    aphmau = trust_for("aphmau")
    assert aphmau is not None
    assert "automaton_mnejing" in aphmau.companions
    assert "automaton_sharpshot" in aphmau.companions
    assert aphmau.auto_activate_companions is True


def test_iroha_has_two_automatons_too():
    iroha = trust_for("iroha_pup")
    assert iroha is not None
    assert len(iroha.companions) == 2


def test_smn_trust_has_all_primes():
    smn = trust_for("esha_smn")
    assert smn is not None
    # Should reference at least 8 elemental avatars + Carbuncle + Diabolos
    assert len(smn.companions) >= 9
    assert "avatar_carbuncle" in smn.companions
    assert "avatar_ifrit" in smn.companions


def test_blu_trust_has_spell_library():
    blu = trust_for("jakoh_blu")
    assert blu is not None
    assert len(blu.companions) >= 5
    assert all(c.startswith("blu_") for c in blu.companions)


def test_bst_trust_has_jugs_and_charm():
    bst = trust_for("max_bst")
    assert bst is not None
    assert "jug_carrie" in bst.companions
    assert "charmed_wild_target" in bst.companions


def test_pet_trusts_balance_role_distribution():
    """Pet-class additions should expand without duplicating
    existing role coverage."""
    pup_count = sum(1 for t in TRUST_CATALOG.values() if t.job == "PUP")
    assert pup_count >= 4   # Aphmau + 3 new


# ----------------------------------------------------------------------
# CompanionManager — activation rules
# ----------------------------------------------------------------------

def test_aphmau_can_activate_three_automatons():
    """Aphmau is the unique 3-slot exception per the user direction."""
    mgr = CompanionManager()
    a1 = mgr.activate(
        companion_id="automaton_mnejing", owner_id="aphmau",
        owner_kind="trust", now=0,
    )
    a2 = mgr.activate(
        companion_id="automaton_sharpshot", owner_id="aphmau",
        owner_kind="trust", now=0,
    )
    a3 = mgr.activate(
        companion_id="automaton_valoredge", owner_id="aphmau",
        owner_kind="trust", now=0,
    )
    assert a1 is not None
    assert a2 is not None
    assert a3 is not None
    assert len(mgr.active_for_owner("aphmau")) == 3


def test_default_pup_blocked_at_one():
    """Per user direction: non-Aphmau PUPs default to 1 active
    automaton. The second activation is blocked unless the caller
    explicitly raises max_active_for_pup via pup_progression."""
    mgr = CompanionManager()
    a1 = mgr.activate(companion_id="automaton_mnejing",
                       owner_id="alice", now=0)
    a2 = mgr.activate(companion_id="automaton_sharpshot",
                       owner_id="alice", now=0)
    assert a1 is not None
    assert a2 is None    # blocked at default cap of 1


def test_clockwork_sage_triple_deploy():
    """The Clockwork Sage NPC deploys 3 frames (unique). Can override
    via max_active_for_pup parameter."""
    mgr = CompanionManager()
    mgr.activate(companion_id="automaton_valoredge",
                  owner_id="clockwork_sage", now=0,
                  max_active_for_pup=3)
    mgr.activate(companion_id="automaton_soulsoother",
                  owner_id="clockwork_sage", now=0,
                  max_active_for_pup=3)
    third = mgr.activate(companion_id="automaton_spiritreaver",
                           owner_id="clockwork_sage", now=0,
                           max_active_for_pup=3)
    assert third is not None
    assert len(mgr.active_for_owner("clockwork_sage")) == 3


def test_smn_avatar_replaces_existing():
    """Summoning a second avatar releases the first (canonical FFXI)."""
    mgr = CompanionManager()
    first = mgr.activate(companion_id="avatar_ifrit",
                          owner_id="esha", now=0)
    second = mgr.activate(companion_id="avatar_shiva",
                           owner_id="esha", now=10)
    assert first.is_active is False    # released
    assert second.is_active is True
    # Only the new avatar is in the active list
    active = mgr.active_for_owner("esha")
    assert len(active) == 1
    assert active[0].spec.companion_id == "avatar_shiva"


def test_avatar_expires_after_duration():
    mgr = CompanionManager()
    att = mgr.activate(companion_id="avatar_ifrit",
                        owner_id="esha", now=0)
    # 599s in: still active
    expired = mgr.tick_expirations(now=599)
    assert "avatar_ifrit" not in expired
    assert att.is_active is True
    # 601s in: expired
    expired = mgr.tick_expirations(now=601)
    assert "avatar_ifrit" in expired
    assert att.is_active is False


def test_jug_pet_has_900_second_duration():
    jug = companion_for("jug_carrie")
    assert jug.duration_seconds == 900.0


def test_blu_spell_path_returns_none_for_activate():
    """BLU spells aren't attached; activate() refuses."""
    mgr = CompanionManager()
    result = mgr.activate(companion_id="blu_cocoon",
                            owner_id="jakoh", now=0)
    assert result is None


def test_blu_spell_lookup_via_cast_path():
    """The dedicated cast_blu_spell path returns the spell spec."""
    spell = CompanionManager.cast_blu_spell("blu_1000_needles")
    assert spell is not None
    assert spell.base_damage == 1000


def test_release_all_for_owner():
    mgr = CompanionManager()
    # Use a 2-slot owner so we have 2 active to release
    mgr.activate(companion_id="automaton_mnejing", owner_id="alice", now=0,
                  max_active_for_pup=2)
    mgr.activate(companion_id="automaton_sharpshot", owner_id="alice", now=0,
                  max_active_for_pup=2)
    count = mgr.release_all("alice")
    assert count == 2
    assert mgr.active_for_owner("alice") == []


def test_release_specific_companion():
    mgr = CompanionManager()
    mgr.activate(companion_id="automaton_mnejing", owner_id="alice", now=0,
                  max_active_for_pup=2)
    mgr.activate(companion_id="automaton_sharpshot", owner_id="alice", now=0,
                  max_active_for_pup=2)
    mgr.release("alice", "automaton_mnejing")
    active = mgr.active_for_owner("alice")
    assert len(active) == 1
    assert active[0].spec.companion_id == "automaton_sharpshot"


def test_fomor_can_use_companion_engine():
    """Per user direction: 'fomors that are smn, pup, bst can also
    use the same skills'. Engine is owner-kind agnostic."""
    mgr = CompanionManager()
    att = mgr.activate(
        companion_id="avatar_fenrir",
        owner_id="fomor_smn_42", owner_kind="fomor",
        now=0,
    )
    assert att is not None
    assert att.owner_kind == "fomor"


# ----------------------------------------------------------------------
# World PUPs
# ----------------------------------------------------------------------

def test_world_pup_catalog_size():
    """Per user direction: 'a whole bunch of them scattered'."""
    assert len(PUP_NPC_CATALOG) >= 10


def test_world_pups_span_multiple_zones():
    zones = {npc.zone for npc in PUP_NPC_CATALOG.values()}
    assert len(zones) >= 8


def test_world_pups_span_multiple_levels():
    levels = sorted(npc.level for npc in PUP_NPC_CATALOG.values())
    # Should span low-to-apex
    assert min(levels) <= 30
    assert max(levels) >= 90


def test_world_pup_clockwork_sage_deploys_three():
    sage = PUP_NPC_CATALOG["the_clockwork_sage"]
    assert len(sage.automatons) == 3


def test_pup_npcs_in_zone_lookup():
    woods = pup_npcs_in_zone("windurst_woods")
    assert any(npc.pup_id == "puhloh_apolloh" for npc in woods)


def test_pup_npc_behaviors_diverse():
    behaviors = {npc.behavior for npc in PUP_NPC_CATALOG.values()}
    assert {"vendor", "questgiver", "patrol", "duelist"} <= behaviors


# ----------------------------------------------------------------------
# Rogue Automaton NMs
# ----------------------------------------------------------------------

def test_rogue_automaton_catalog_has_at_least_10():
    assert len(ROGUE_AUTOMATON_NMS) >= 10


def test_every_rogue_has_guaranteed_drop():
    """Per user direction: 'they always drop an insane reward'."""
    for nm in ROGUE_AUTOMATON_NMS.values():
        assert nm.guaranteed_drop != ""


def test_apex_rogues_drop_apex_core():
    """The PROTOTYPE-class rogues drop the apex core."""
    apex = [nm for nm in ROGUE_AUTOMATON_NMS.values()
              if nm.rogue_class == RogueAutomatonClass.PROTOTYPE]
    for nm in apex:
        assert nm.guaranteed_drop == "rogue_automaton_core_apex"


def test_brass_phoenix_revives_once():
    nm = rogue_automaton_for("the_brass_phoenix")
    assert nm is not None
    assert "rebirth_at_zero" in nm.primary_abilities


def test_witness_zero_apex_difficulty():
    nm = rogue_automaton_for("the_witness_zero")
    assert nm is not None
    assert nm.level == 99
    assert nm.hp_pool >= 400000


def test_rogue_automatons_in_zone_lookup():
    sky_rogues = rogue_automatons_in_zone("sky_ruaun")
    assert len(sky_rogues) >= 1


# ----------------------------------------------------------------------
# Respawn tracker — 24hr earth time
# ----------------------------------------------------------------------

def test_respawn_constant_is_24h():
    assert ROGUE_AUTOMATON_RESPAWN_SECONDS == 24 * 3600


def test_unkilled_nm_is_spawned():
    tracker = RespawnTracker()
    assert tracker.is_spawned("iron_widow", now=0) is True


def test_kill_starts_24h_timer():
    tracker = RespawnTracker()
    rec = tracker.notify_killed("iron_widow", now=1000)
    assert rec.next_spawn_at == 1000 + 24 * 3600
    # 23h in: not spawned
    assert tracker.is_spawned("iron_widow", now=1000 + 23 * 3600) is False
    # 24h+1s: spawned
    assert tracker.is_spawned("iron_widow",
                                 now=1000 + 24 * 3600 + 1) is True


def test_time_until_spawn():
    tracker = RespawnTracker()
    tracker.notify_killed("iron_widow", now=0)
    remaining = tracker.time_until_spawn("iron_widow", now=3600)
    # 24h - 1h = 23h
    assert remaining == 23 * 3600
    # Past respawn
    assert tracker.time_until_spawn("iron_widow",
                                       now=25 * 3600) == 0.0


def test_force_spawn_clears_record():
    tracker = RespawnTracker()
    tracker.notify_killed("iron_widow", now=0)
    cleared = tracker.force_spawn("iron_widow")
    assert cleared is True
    assert tracker.is_spawned("iron_widow", now=1) is True


def test_last_killed_at_lookup():
    tracker = RespawnTracker()
    tracker.notify_killed("iron_widow", now=42)
    assert tracker.last_killed_at("iron_widow") == 42
    assert tracker.last_killed_at("nonexistent") is None


# ----------------------------------------------------------------------
# Integration: full PUP workflow
# ----------------------------------------------------------------------

def test_aphmau_summon_and_deploy_both_automatons():
    """End-to-end: spec says auto-activate, manager activates both."""
    aphmau = trust_for("aphmau")
    assert aphmau.auto_activate_companions is True

    mgr = CompanionManager()
    for companion_id in aphmau.companions:
        mgr.activate(companion_id=companion_id,
                      owner_id="aphmau", owner_kind="trust",
                      now=0)
    active = mgr.active_for_owner("aphmau")
    assert len(active) == 2
    active_ids = {a.spec.companion_id for a in active}
    assert "automaton_mnejing" in active_ids
    assert "automaton_sharpshot" in active_ids


def test_summoner_full_avatar_rotation():
    """Esha'ntarl summons Ifrit, then swaps to Shiva, then Garuda."""
    esha = trust_for("esha_smn")
    assert esha is not None
    mgr = CompanionManager()
    for avatar_id in ("avatar_ifrit", "avatar_shiva", "avatar_garuda"):
        mgr.activate(companion_id=avatar_id, owner_id="esha", now=0)
    active = mgr.active_for_owner("esha")
    # Only Garuda remains active
    assert len(active) == 1
    assert active[0].spec.companion_id == "avatar_garuda"


def test_rogue_kill_and_24h_respawn_flow():
    """Iron Widow is killed; doesn't respawn until 24h pass."""
    tracker = RespawnTracker()
    assert tracker.is_spawned("iron_widow", now=0) is True
    tracker.notify_killed("iron_widow", now=0)
    # Stays dead for 24 hours
    for hours in (1, 6, 12, 23):
        assert tracker.is_spawned("iron_widow",
                                     now=hours * 3600) is False
    # Respawns
    assert tracker.is_spawned("iron_widow", now=25 * 3600) is True
