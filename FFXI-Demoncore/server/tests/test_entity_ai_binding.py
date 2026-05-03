"""Tests for entity-to-AI-agent binding registry."""
from __future__ import annotations

from server.entity_ai_binding import (
    DEMOTION_LADDER,
    AgentProfile,
    AITier,
    EntityAIRegistry,
    EntityKind,
    doctrine_audit,
)


def _profile() -> AgentProfile:
    return AgentProfile(
        agent_id="agent_1",
        model_name="claude-haiku-4-5",
        persona_path="agents/test.yaml",
    )


def test_demotion_ladder_top_to_bottom():
    assert DEMOTION_LADDER[0] == AITier.FLAGSHIP
    assert DEMOTION_LADDER[-1] == AITier.INERT


def test_bind_basic():
    reg = EntityAIRegistry()
    res = reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
        tier=AITier.LITE, now_seconds=0.0,
    )
    assert res.accepted
    assert res.binding.entity_id == "mob_1"
    assert reg.total == 1


def test_bind_duplicate_rejected():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
    )
    res = reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
    )
    assert not res.accepted


def test_static_must_be_inert():
    """Doctrine: STATIC kind only ever binds at INERT tier."""
    reg = EntityAIRegistry()
    res = reg.bind(
        entity_id="signpost_1", kind=EntityKind.STATIC,
        profile=_profile(), tier=AITier.LITE,
    )
    assert not res.accepted
    ok = reg.bind(
        entity_id="signpost_1", kind=EntityKind.STATIC,
        profile=_profile(), tier=AITier.INERT,
    )
    assert ok.accepted


def test_unbind():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
    )
    assert reg.unbind(entity_id="mob_1")
    assert not reg.unbind(entity_id="mob_1")


def test_by_kind_filters():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="boss_1", kind=EntityKind.BOSS, profile=_profile(),
    )
    reg.bind(
        entity_id="npc_1", kind=EntityKind.NPC, profile=_profile(),
    )
    reg.bind(
        entity_id="npc_2", kind=EntityKind.NPC, profile=_profile(),
    )
    npcs = reg.by_kind(EntityKind.NPC)
    assert len(npcs) == 2
    assert {b.entity_id for b in npcs} == {"npc_1", "npc_2"}


def test_by_tier_filters():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="boss_1", kind=EntityKind.BOSS, profile=_profile(),
        tier=AITier.FLAGSHIP,
    )
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
        tier=AITier.LITE,
    )
    flag = reg.by_tier(AITier.FLAGSHIP)
    assert len(flag) == 1
    assert flag[0].entity_id == "boss_1"


def test_all_live_excludes_inert():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
        tier=AITier.LITE,
    )
    reg.bind(
        entity_id="signpost_1", kind=EntityKind.STATIC,
        profile=_profile(), tier=AITier.INERT,
    )
    live = reg.all_live()
    assert len(live) == 1
    assert live[0].entity_id == "mob_1"


def test_touch_updates_last_active():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
        now_seconds=0.0,
    )
    assert reg.touch(entity_id="mob_1", now_seconds=42.0)
    b = reg.get("mob_1")
    assert b.last_active_at_seconds == 42.0


def test_touch_unknown_returns_false():
    reg = EntityAIRegistry()
    assert not reg.touch(entity_id="ghost", now_seconds=0.0)


def test_promote_climbs_tier():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
        tier=AITier.LITE,
    )
    res = reg.promote(entity_id="mob_1", target_tier=AITier.FULL)
    assert res.accepted
    assert reg.get("mob_1").tier == AITier.FULL


def test_promote_to_lower_tier_rejected():
    """Can't 'promote' to a cheaper tier — that's a demotion."""
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="boss_1", kind=EntityKind.BOSS, profile=_profile(),
        tier=AITier.FLAGSHIP,
    )
    res = reg.promote(entity_id="boss_1", target_tier=AITier.LITE)
    assert not res.accepted


def test_demote_drops_tier():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="boss_1", kind=EntityKind.BOSS, profile=_profile(),
        tier=AITier.FLAGSHIP,
    )
    res = reg.demote(entity_id="boss_1", target_tier=AITier.LITE)
    assert res.accepted
    assert reg.get("boss_1").tier == AITier.LITE


def test_demote_to_higher_tier_rejected():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
        tier=AITier.LITE,
    )
    res = reg.demote(entity_id="mob_1", target_tier=AITier.FLAGSHIP)
    assert not res.accepted


def test_stale_bindings():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
        now_seconds=0.0,
    )
    reg.bind(
        entity_id="mob_2", kind=EntityKind.MOB, profile=_profile(),
        now_seconds=100.0,
    )
    stale = reg.stale_bindings(now_seconds=120.0, max_age_seconds=60.0)
    ids = {b.entity_id for b in stale}
    assert "mob_1" in ids
    assert "mob_2" not in ids


def test_summary_buckets_by_tier():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="boss_1", kind=EntityKind.BOSS, profile=_profile(),
        tier=AITier.FLAGSHIP,
    )
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
        tier=AITier.LITE,
    )
    reg.bind(
        entity_id="mob_2", kind=EntityKind.MOB, profile=_profile(),
        tier=AITier.LITE,
    )
    summary = reg.summary()
    assert summary[AITier.FLAGSHIP] == 1
    assert summary[AITier.LITE] == 2
    assert summary[AITier.FULL] == 0


def test_doctrine_audit_finds_unbound():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
    )
    missing = doctrine_audit(reg, ["mob_1", "mob_2", "npc_1"])
    assert "mob_2" in missing
    assert "npc_1" in missing
    assert "mob_1" not in missing


def test_doctrine_audit_all_present():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="mob_1", kind=EntityKind.MOB, profile=_profile(),
    )
    reg.bind(
        entity_id="mob_2", kind=EntityKind.MOB, profile=_profile(),
    )
    missing = doctrine_audit(reg, ["mob_1", "mob_2"])
    assert missing == ()


def test_full_lifecycle_npc_bind_promote_demote_unbind():
    reg = EntityAIRegistry()
    reg.bind(
        entity_id="curilla", kind=EntityKind.NPC, profile=_profile(),
        tier=AITier.LITE, now_seconds=0.0,
    )
    # Player approached -> promote to FLAGSHIP
    reg.promote(entity_id="curilla", target_tier=AITier.FLAGSHIP)
    assert reg.get("curilla").tier == AITier.FLAGSHIP
    # Player left -> demote
    reg.demote(entity_id="curilla", target_tier=AITier.LITE)
    assert reg.get("curilla").tier == AITier.LITE
    # Done -> unbind
    assert reg.unbind(entity_id="curilla")
    assert reg.get("curilla") is None
