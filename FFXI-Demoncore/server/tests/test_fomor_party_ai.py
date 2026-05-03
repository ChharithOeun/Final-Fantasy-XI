"""Tests for Fomor party AI — group movement, chain intent
broadcasts, magic-burst window coordination."""
from __future__ import annotations

from server.fomor_party_ai import (
    DEFAULT_CHAIN_LEAD_SECONDS,
    MAX_FOMOR_PARTY_SIZE,
    FomorParty,
    FomorRole,
    FormationSlot,
)
from server.magic_burst_window import SkillchainElement


def _build_party() -> FomorParty:
    p = FomorParty(party_id="fomor_alpha")
    p.add_member(
        mob_id="leader_1", role=FomorRole.LEADER,
        slot=FormationSlot.POINT,
    )
    p.add_member(
        mob_id="melee_1", role=FomorRole.MELEE,
        slot=FormationSlot.LEFT,
    )
    p.add_member(
        mob_id="melee_2", role=FomorRole.MELEE,
        slot=FormationSlot.RIGHT,
    )
    p.add_member(
        mob_id="caster_1", role=FomorRole.CASTER,
        slot=FormationSlot.REAR,
    )
    p.add_member(
        mob_id="healer_1", role=FomorRole.HEALER,
        slot=FormationSlot.PROTECT_HEALER,
    )
    return p


def test_add_member_basic():
    p = FomorParty(party_id="alpha")
    res = p.add_member(mob_id="m1", role=FomorRole.LEADER)
    assert res.accepted
    assert res.member.mob_id == "m1"
    assert p.leader_id == "m1"


def test_add_member_duplicate_rejected():
    p = FomorParty(party_id="alpha")
    p.add_member(mob_id="m1", role=FomorRole.MELEE)
    res = p.add_member(mob_id="m1", role=FomorRole.MELEE)
    assert not res.accepted
    assert res.reason == "duplicate"


def test_party_caps_at_max_size():
    p = FomorParty(party_id="alpha")
    for i in range(MAX_FOMOR_PARTY_SIZE):
        r = p.add_member(mob_id=f"m{i}", role=FomorRole.MELEE)
        assert r.accepted
    overflow = p.add_member(mob_id="extra", role=FomorRole.MELEE)
    assert not overflow.accepted
    assert overflow.reason == "party full"


def test_set_leader_demotes_prior():
    p = _build_party()
    assert p.leader_id == "leader_1"
    ok = p.set_leader(mob_id="melee_1")
    assert ok
    assert p.leader_id == "melee_1"
    # Prior leader demoted to MELEE
    prior = next(m for m in p.members if m.mob_id == "leader_1")
    assert prior.role == FomorRole.MELEE
    new_leader = next(m for m in p.members if m.mob_id == "melee_1")
    assert new_leader.role == FomorRole.LEADER


def test_set_leader_unknown_fails():
    p = _build_party()
    assert not p.set_leader(mob_id="ghost")


def test_set_focus_target():
    p = _build_party()
    ok = p.set_focus_target(target_id="player_alice")
    assert ok
    assert p.focus_target_id == "player_alice"


def test_set_focus_target_empty_rejected():
    p = _build_party()
    assert not p.set_focus_target(target_id="")


def test_members_in_role():
    p = _build_party()
    melees = p.members_in_role(FomorRole.MELEE)
    assert len(melees) == 2
    assert {m.mob_id for m in melees} == {"melee_1", "melee_2"}


def test_broadcast_chain_intent():
    p = _build_party()
    intent = p.broadcast_chain_intent(
        leader_id="leader_1",
        skillchain_element=SkillchainElement.FIRE,
        weapon_skill_id="raging_rush",
        now_seconds=100.0,
    )
    assert intent.leader_id == "leader_1"
    assert intent.skillchain_element == SkillchainElement.FIRE
    assert intent.weapon_skill_id == "raging_rush"
    # Default lead time
    assert intent.intended_at_seconds == 100.0 + DEFAULT_CHAIN_LEAD_SECONDS
    assert p.latest_chain_intent() == intent


def test_broadcast_chain_intent_custom_lead():
    p = _build_party()
    intent = p.broadcast_chain_intent(
        leader_id="leader_1",
        skillchain_element=SkillchainElement.LIGHT,
        weapon_skill_id="savage_blade",
        now_seconds=50.0,
        lead_seconds=10.0,
    )
    assert intent.intended_at_seconds == 60.0


def test_broadcast_burst_intent():
    p = _build_party()
    burst = p.broadcast_burst_intent(
        caster_id="caster_1",
        burst_element=SkillchainElement.FIRE,
        spell_id="fire_v",
        intended_at_seconds=120.0,
    )
    assert burst.caster_id == "caster_1"
    assert burst.burst_element == SkillchainElement.FIRE
    assert burst.spell_id == "fire_v"
    assert p.burst_intents[-1] == burst


def test_casters_watching_for_burst_no_chain():
    p = _build_party()
    assert p.casters_watching_for_burst(now_seconds=0.0) == ()


def test_casters_watching_for_burst_in_window():
    p = _build_party()
    p.broadcast_chain_intent(
        leader_id="leader_1",
        skillchain_element=SkillchainElement.EARTH,
        weapon_skill_id="ground_strike",
        now_seconds=100.0,
    )
    # Chain lands at 106s; checking at 105s (diff = 1s) is within window
    casters = p.casters_watching_for_burst(now_seconds=105.0)
    assert len(casters) == 1
    assert casters[0].mob_id == "caster_1"


def test_casters_watching_for_burst_outside_window():
    p = _build_party()
    p.broadcast_chain_intent(
        leader_id="leader_1",
        skillchain_element=SkillchainElement.EARTH,
        weapon_skill_id="ground_strike",
        now_seconds=100.0,
    )
    # chain at 106s, ask at 200s -> way outside the watch_window
    assert p.casters_watching_for_burst(now_seconds=200.0) == ()


def test_melees_ready_to_chain_initial():
    p = _build_party()
    # No actions recorded yet -> all melees+leader are ready
    ready = p.melees_ready_to_chain(now_seconds=10.0)
    ids = {m.mob_id for m in ready}
    assert ids == {"leader_1", "melee_1", "melee_2"}


def test_melees_ready_to_chain_after_action():
    p = _build_party()
    p.record_action(mob_id="melee_1", now_seconds=10.0)
    # Just acted -> melee_1 is NOT ready, others still ready
    ready = p.melees_ready_to_chain(now_seconds=11.0)
    ids = {m.mob_id for m in ready}
    assert "melee_1" not in ids
    assert "melee_2" in ids
    assert "leader_1" in ids
    # 10 seconds later -> melee_1 ready again
    ready_later = p.melees_ready_to_chain(now_seconds=20.0)
    assert "melee_1" in {m.mob_id for m in ready_later}


def test_record_action_unknown_mob():
    p = _build_party()
    assert not p.record_action(mob_id="ghost", now_seconds=0.0)


def test_full_lifecycle_party_chains_and_bursts():
    """End-to-end: party assembles, locks target, leader broadcasts
    chain, melees ready, caster bursts on the window."""
    p = _build_party()
    p.set_focus_target(target_id="player_target")
    # Leader announces a Fusion-element WS
    p.broadcast_chain_intent(
        leader_id="leader_1",
        skillchain_element=SkillchainElement.FIRE,
        weapon_skill_id="evisceration",
        now_seconds=50.0,
    )
    # Melees should all be ready (no prior actions)
    melees = p.melees_ready_to_chain(now_seconds=50.0)
    assert len(melees) >= 2
    # Within the magic-burst watch window, the caster commits
    casters = p.casters_watching_for_burst(now_seconds=55.0)
    assert len(casters) == 1
    p.broadcast_burst_intent(
        caster_id=casters[0].mob_id,
        burst_element=SkillchainElement.FIRE,
        spell_id="fire_v",
        intended_at_seconds=57.0,
    )
    assert len(p.burst_intents) == 1
    # Leader and one melee both act, simulating the chain
    assert p.record_action(mob_id="leader_1", now_seconds=56.0)
    assert p.record_action(mob_id="melee_1", now_seconds=56.5)
    # Right after acting, only melee_2 is still ready
    ready_after = p.melees_ready_to_chain(now_seconds=57.0)
    ready_ids = {m.mob_id for m in ready_after}
    assert ready_ids == {"melee_2"}
