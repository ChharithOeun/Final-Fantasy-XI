"""Tests for the trust system: catalog + party + AI + PvP guard.

Run:  python -m pytest server/tests/test_trust_system.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from trust_system import (
    AIDecision,
    AIPriority,
    DEFAULT_HEAL_THRESHOLDS,
    DespawnReason,
    MAX_TRUST_SLOTS,
    PartyMemberState,
    TRUST_CATALOG,
    TrustAIBrain,
    TrustParty,
    TrustPvpGuard,
    TrustRole,
    TrustSnapshot,
    TrustSpec,
    trust_for,
)
from trust_system.catalog import trusts_for_nation


# ----------------------------------------------------------------------
# Catalog
# ----------------------------------------------------------------------

def test_catalog_has_at_least_18_trusts():
    """Doc target: 18-entry roster spanning all 5 nations + outlaw."""
    assert len(TRUST_CATALOG) >= 18


def test_each_nation_has_at_least_one_trust():
    nations = {spec.nation for spec in TRUST_CATALOG.values()}
    for required in ("bastok", "sandoria", "windurst", "ahturhgan", "norg"):
        assert required in nations, f"missing nation: {required}"


def test_canonical_trusts_are_present():
    """Spot-check the headline canonical roster entries."""
    for trust_id in ("trion", "volker", "curilla", "cid", "ayame",
                       "yoran_oran", "naja_salaheem", "shantotto"):
        assert trust_id in TRUST_CATALOG


def test_demoncore_outlaw_trusts_flagged():
    shadow_wolf = trust_for("shadow_wolf")
    assert shadow_wolf is not None
    assert shadow_wolf.outlaw_aligned is True
    assert shadow_wolf.canonical is False


def test_trust_for_unknown_returns_none():
    assert trust_for("plasma_wolf") is None


def test_trust_for_case_insensitive():
    assert trust_for("TRION") is not None


def test_trusts_for_nation_excludes_outlaw_for_citizen():
    norg_citizen = trusts_for_nation("norg", outlaw_summoner=False)
    assert all(not t.outlaw_aligned for t in norg_citizen)


def test_trusts_for_nation_includes_outlaw_for_outlaw():
    norg_outlaw = trusts_for_nation("norg", outlaw_summoner=True)
    has_outlaw = any(t.outlaw_aligned for t in norg_outlaw)
    assert has_outlaw is True


def test_role_distribution_covers_all_roles():
    """The roster should give the player options for every role."""
    roles = {spec.role for spec in TRUST_CATALOG.values()}
    for required in (TrustRole.TANK, TrustRole.HEALER,
                       TrustRole.MELEE_DPS, TrustRole.NUKER,
                       TrustRole.SUPPORT):
        assert required in roles


# ----------------------------------------------------------------------
# TrustParty
# ----------------------------------------------------------------------

def test_party_starts_empty():
    party = TrustParty(owner_id="alice")
    assert party.is_empty()
    assert party.slot_count() == MAX_TRUST_SLOTS


def test_summon_adds_trust():
    party = TrustParty(owner_id="alice")
    snap = party.summon(trust_for("trion"), owner_level=75, now=0)
    assert snap is not None
    assert snap.trust_id == "trion"
    assert snap.is_alive
    assert party.slot_count() == MAX_TRUST_SLOTS - 1


def test_summon_full_party_blocked():
    party = TrustParty(owner_id="alice")
    five = ["trion", "yoran_oran", "volker", "ayame", "shantotto"]
    for tid in five:
        party.summon(trust_for(tid), owner_level=75, now=0)
    # 6th: blocked
    sixth = party.summon(trust_for("zeid"), owner_level=75, now=0)
    assert sixth is None


def test_summon_outlaw_trust_blocked_for_citizen():
    party = TrustParty(owner_id="alice")
    snap = party.summon(trust_for("shadow_wolf"), owner_level=80, now=0,
                          outlaw_summoner=False)
    assert snap is None


def test_summon_outlaw_trust_allowed_for_outlaw():
    party = TrustParty(owner_id="alice")
    snap = party.summon(trust_for("shadow_wolf"), owner_level=80, now=0,
                          outlaw_summoner=True)
    assert snap is not None


def test_summon_same_trust_refreshes_in_place():
    party = TrustParty(owner_id="alice")
    snap1 = party.summon(trust_for("trion"), owner_level=75, now=10)
    snap2 = party.summon(trust_for("trion"), owner_level=75, now=20)
    assert snap1 is snap2
    assert snap1.summoned_at == 20


def test_despawn_removes_one():
    party = TrustParty(owner_id="alice")
    party.summon(trust_for("trion"), owner_level=75, now=0)
    party.summon(trust_for("yoran_oran"), owner_level=75, now=0)
    party.despawn("trion", DespawnReason.OWNER_REQUEST)
    assert not party.has("trion")
    assert party.has("yoran_oran")


def test_despawn_all_clears_party():
    party = TrustParty(owner_id="alice")
    party.summon(trust_for("trion"), owner_level=75, now=0)
    party.summon(trust_for("yoran_oran"), owner_level=75, now=0)
    removed = party.despawn_all(DespawnReason.OWNER_DIED)
    assert "trion" in removed
    assert "yoran_oran" in removed
    assert party.is_empty()


def test_hp_scales_with_owner_level():
    party_low = TrustParty(owner_id="alice")
    snap_low = party_low.summon(trust_for("trion"), owner_level=30, now=0)
    party_high = TrustParty(owner_id="bob")
    snap_high = party_high.summon(trust_for("trion"), owner_level=99, now=0)
    assert snap_high.max_hp > snap_low.max_hp


def test_healer_has_more_mp_than_dps():
    party = TrustParty(owner_id="alice")
    healer = party.summon(trust_for("yoran_oran"), owner_level=75, now=0)
    dps = party.summon(trust_for("volker"), owner_level=75, now=0)
    assert healer.max_mp > dps.max_mp


# ----------------------------------------------------------------------
# AI brain — priority ladder
# ----------------------------------------------------------------------

def _new_party(owner_level: int = 75) -> tuple[TrustParty, dict]:
    party = TrustParty(owner_id="alice")
    snaps = {}
    for tid in ("trion", "yoran_oran", "volker", "shantotto", "joachim"):
        snaps[tid] = party.summon(trust_for(tid),
                                     owner_level=owner_level, now=0)
    return party, snaps


def _make_party_state(player_hp_pct: float = 1.0,
                       trion_hp_pct: float = 1.0,
                       volker_hp_pct: float = 1.0) -> list[PartyMemberState]:
    return [
        PartyMemberState(
            member_id="alice", is_player=True,
            current_hp=int(2000 * player_hp_pct), max_hp=2000,
            is_alive=True,
        ),
        PartyMemberState(
            member_id="trion", is_player=False,
            current_hp=int(700 * trion_hp_pct), max_hp=700,
        ),
        PartyMemberState(
            member_id="volker", is_player=False,
            current_hp=int(625 * volker_hp_pct), max_hp=625,
        ),
    ]


def test_self_preservation_takes_priority():
    """Trust at 25% HP self-heals before doing anything else."""
    _, snaps = _new_party()
    snap = snaps["trion"]
    snap.current_hp = int(snap.max_hp * 0.25)
    brain = TrustAIBrain()
    decision = brain.tick(
        trust=snap, party=_make_party_state(),
        now=0, skillchain_window_open=False,
    )
    assert decision.priority == AIPriority.SELF_PRESERVATION


def test_healer_picks_lowest_hp_party_member():
    """Yoran-Oran heals the lowest-HP injured member."""
    _, snaps = _new_party()
    healer = snaps["yoran_oran"]
    party_state = _make_party_state(
        player_hp_pct=0.30, volker_hp_pct=0.40,
    )
    brain = TrustAIBrain()
    decision = brain.tick(
        trust=healer, party=party_state, now=0,
    )
    assert decision.priority == AIPriority.PARTY_HEAL
    # Player is lowest at 30%
    assert decision.target_id == "alice"


def test_intervention_mb_fires_on_predicted_damage():
    """Curilla has intervention_mb; she'll fire it when an ally has
    incoming damage predicted."""
    party = TrustParty(owner_id="alice")
    curilla = party.summon(trust_for("curilla"), owner_level=80, now=0)
    party_state = [
        PartyMemberState(
            member_id="alice", is_player=True,
            current_hp=2000, max_hp=2000,
            incoming_damage_predicted=1500,
        ),
    ]
    brain = TrustAIBrain()
    decision = brain.tick(trust=curilla, party=party_state, now=0)
    assert decision.priority == AIPriority.INTERVENTION_MB
    assert decision.spell_or_ability == "intervention_mb"


def test_skillchain_opener_during_window():
    """sc_priority trust (Volker) opens a skillchain when the window
    is open."""
    _, snaps = _new_party()
    volker = snaps["volker"]
    brain = TrustAIBrain()
    decision = brain.tick(
        trust=volker, party=_make_party_state(),
        now=0, skillchain_window_open=True,
        enemy_target_id="goblin_1",
    )
    assert decision.priority == AIPriority.SKILLCHAIN_OPENER
    assert decision.action == "weapon_skill"


def test_nuker_magic_bursts_during_sc_window():
    """Shantotto MBs during a skillchain window."""
    _, snaps = _new_party()
    shantotto = snaps["shantotto"]
    brain = TrustAIBrain()
    decision = brain.tick(
        trust=shantotto, party=_make_party_state(),
        now=0, skillchain_window_open=True,
        enemy_target_id="goblin_1",
    )
    assert decision.priority == AIPriority.MAGIC_BURST
    assert decision.action == "cast"


def test_support_buffs_when_idle():
    """Joachim (BRD) maintains buffs when nothing urgent."""
    _, snaps = _new_party()
    joachim = snaps["joachim"]
    brain = TrustAIBrain()
    decision = brain.tick(
        trust=joachim, party=_make_party_state(),
        now=0, skillchain_window_open=False,
        enemy_target_id="goblin_1",
    )
    assert decision.priority == AIPriority.BUFF


def test_default_melee_for_dps():
    """Volker with no special context defaults to melee."""
    _, snaps = _new_party()
    volker = snaps["volker"]
    brain = TrustAIBrain()
    decision = brain.tick(
        trust=volker, party=_make_party_state(),
        now=0, skillchain_window_open=False,
        enemy_target_id="goblin_1",
    )
    assert decision.action == "melee"


def test_healer_waits_when_no_one_needs_healing():
    """Yoran-Oran with everyone full HP and nothing urgent: WAIT."""
    _, snaps = _new_party()
    healer = snaps["yoran_oran"]
    brain = TrustAIBrain()
    decision = brain.tick(
        trust=healer,
        party=_make_party_state(player_hp_pct=1.0,
                                  trion_hp_pct=1.0, volker_hp_pct=1.0),
        now=0, skillchain_window_open=False,
    )
    # Healer with full party and no SC window → WAIT
    assert decision.priority == AIPriority.WAIT


def test_heal_threshold_per_role_table():
    """The role-default heal threshold table covers every role."""
    for role in TrustRole:
        assert role in DEFAULT_HEAL_THRESHOLDS


def test_tank_heal_threshold_lower_than_dps():
    """Tanks have lower threshold (40%) than DPS (55%) — DPS heals
    earlier because squishier."""
    assert DEFAULT_HEAL_THRESHOLDS[TrustRole.TANK] < DEFAULT_HEAL_THRESHOLDS[TrustRole.MELEE_DPS]


# ----------------------------------------------------------------------
# PvP guard
# ----------------------------------------------------------------------

def test_pvp_attack_despawns_all_trusts():
    party = TrustParty(owner_id="alice")
    party.summon(trust_for("trion"), owner_level=75, now=0)
    party.summon(trust_for("yoran_oran"), owner_level=75, now=0)
    guard = TrustPvpGuard()
    removed = guard.notify_owner_attacked_player(
        party, target_player_id="bob", now=100,
    )
    assert "trion" in removed
    assert "yoran_oran" in removed
    assert party.is_empty()


def test_pvp_attack_no_op_when_no_trusts():
    party = TrustParty(owner_id="alice")
    guard = TrustPvpGuard()
    removed = guard.notify_owner_attacked_player(
        party, target_player_id="bob", now=100,
    )
    assert removed == []


def test_summon_in_pvp_zone_blocked():
    guard = TrustPvpGuard()
    assert guard.can_summon_in_zone("ballista_jugner") is False
    assert guard.can_summon_in_zone("brenner_arena") is False
    assert guard.can_summon_in_zone("ronfaure_east") is True


def test_zoning_into_pvp_zone_despawns():
    party = TrustParty(owner_id="alice")
    party.summon(trust_for("trion"), owner_level=75, now=0)
    guard = TrustPvpGuard()
    removed = guard.notify_zoned_into_pvp_area(party, zone="ballista_jugner")
    assert "trion" in removed
    assert party.is_empty()


def test_zoning_into_safe_zone_no_despawn():
    party = TrustParty(owner_id="alice")
    party.summon(trust_for("trion"), owner_level=75, now=0)
    guard = TrustPvpGuard()
    removed = guard.notify_zoned_into_pvp_area(party, zone="ronfaure_east")
    assert removed == []
    assert party.has("trion")


# ----------------------------------------------------------------------
# Integration: smart heal + SC + MB scenario
# ----------------------------------------------------------------------

def test_full_party_skillchain_scenario():
    """Player + Volker (opener) + Shantotto (MB) + Yoran-Oran (heal)
    coordinate during a skillchain window. Verify each AI picks the
    right action this tick."""
    _, snaps = _new_party()
    brain = TrustAIBrain()

    party_state = [
        PartyMemberState(
            member_id="alice", is_player=True,
            current_hp=2000, max_hp=2000,
        ),
        # Volker just took a hit; hp 60% — above heal threshold (55%).
        # Shouldn't trigger party_heal.
        PartyMemberState(
            member_id="volker", is_player=False,
            current_hp=int(625 * 0.60), max_hp=625,
        ),
    ]

    # Volker: opens the skillchain
    volker_decision = brain.tick(
        trust=snaps["volker"], party=party_state, now=0,
        skillchain_window_open=True, enemy_target_id="boss",
    )
    assert volker_decision.priority == AIPriority.SKILLCHAIN_OPENER

    # Shantotto: MBs into the chain
    shantotto_decision = brain.tick(
        trust=snaps["shantotto"], party=party_state, now=0,
        skillchain_window_open=True, enemy_target_id="boss",
    )
    assert shantotto_decision.priority == AIPriority.MAGIC_BURST

    # Yoran-Oran: nobody below threshold; should idle (WAIT)
    yoran_decision = brain.tick(
        trust=snaps["yoran_oran"], party=party_state, now=0,
        skillchain_window_open=True, enemy_target_id="boss",
    )
    assert yoran_decision.priority == AIPriority.WAIT


def test_pvp_guard_full_workflow():
    """Player has trusts up, attacks another player → trusts gone
    immediately. Tries to summon in PvP zone afterward → blocked."""
    party = TrustParty(owner_id="alice")
    party.summon(trust_for("trion"), owner_level=80, now=0)
    party.summon(trust_for("yoran_oran"), owner_level=80, now=0)
    assert not party.is_empty()

    guard = TrustPvpGuard()
    guard.notify_owner_attacked_player(
        party, target_player_id="bob", now=100,
    )
    assert party.is_empty()

    # Now in a PvP zone, can't even start summoning
    assert guard.can_summon_in_zone("ballista_meriphataud") is False


def test_max_trust_slots_constant_matches_party_size():
    """Standard party = 6, so max trusts = 5."""
    assert MAX_TRUST_SLOTS == 5
