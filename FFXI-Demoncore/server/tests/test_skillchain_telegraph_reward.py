"""Tests for skillchain_telegraph_reward."""
from __future__ import annotations

from server.skillchain_telegraph_reward import (
    SkillchainTelegraphReward,
    SkillchainTier,
    TIER_VISIBILITY_SECONDS,
)
from server.telegraph_visibility_gate import (
    TelegraphVisibilityGate, VisibilitySource,
)


def test_lv1_chain_grants_8s():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="ch1",
        participant_ids=["alice", "bob"],
        tier=SkillchainTier.LV1,
        gate=gate, now_seconds=10,
    )
    assert out.accepted is True
    assert out.visibility_seconds == 8
    assert "alice" in out.granted_player_ids


def test_light_grants_12s():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="ch1",
        participant_ids=["alice"],
        tier=SkillchainTier.LIGHT,
        gate=gate, now_seconds=10,
    )
    assert out.visibility_seconds == 12


def test_darkness_grants_12s():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice"],
        tier=SkillchainTier.DARKNESS,
        gate=gate, now_seconds=10,
    )
    assert out.visibility_seconds == 12


def test_chain_grants_visibility_in_gate():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice"],
        tier=SkillchainTier.LV1, gate=gate, now_seconds=10,
    )
    assert gate.is_visible(player_id="alice", now_seconds=15) is True


def test_visibility_expires():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice"],
        tier=SkillchainTier.LV1, gate=gate, now_seconds=0,
    )
    assert gate.is_visible(player_id="alice", now_seconds=20) is False


def test_visibility_source_is_skillchain_bonus():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice"],
        tier=SkillchainTier.LV1, gate=gate, now_seconds=10,
    )
    sources = gate.active_sources(player_id="alice", now_seconds=15)
    assert VisibilitySource.SKILLCHAIN_BONUS in sources


def test_double_chain_blocked():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice"],
        tier=SkillchainTier.LV1, gate=gate, now_seconds=10,
    )
    out = r.on_chain_closed(
        chain_id="ch1", participant_ids=["bob"],
        tier=SkillchainTier.LV1, gate=gate, now_seconds=20,
    )
    assert out.accepted is False


def test_blank_chain_id_blocked():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="", participant_ids=["alice"],
        tier=SkillchainTier.LV1, gate=gate, now_seconds=10,
    )
    assert out.accepted is False


def test_no_participants_blocked():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="ch1", participant_ids=[],
        tier=SkillchainTier.LV1, gate=gate, now_seconds=10,
    )
    assert out.accepted is False


def test_mb_casters_get_visibility():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice"],
        tier=SkillchainTier.LV2, gate=gate,
        mb_caster_ids=["mage_a", "mage_b"], now_seconds=10,
    )
    assert "mage_a" in out.granted_player_ids
    assert "mage_b" in out.granted_player_ids
    assert "alice" in out.granted_player_ids


def test_dedup_when_caster_is_also_chain_participant():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice", "bob"],
        tier=SkillchainTier.LV1, gate=gate,
        mb_caster_ids=["alice", "carol"], now_seconds=10,
    )
    granted = list(out.granted_player_ids)
    assert granted.count("alice") == 1
    assert "bob" in granted
    assert "carol" in granted


def test_blank_player_ids_filtered():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="ch1", participant_ids=["", "alice"],
        tier=SkillchainTier.LV1, gate=gate, now_seconds=10,
    )
    assert out.accepted is True
    assert "" not in out.granted_player_ids


def test_has_been_rewarded():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    assert r.has_been_rewarded(chain_id="ch1") is False
    r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice"],
        tier=SkillchainTier.LV1, gate=gate, now_seconds=10,
    )
    assert r.has_been_rewarded(chain_id="ch1") is True


def test_lv2_grants_9s():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice"],
        tier=SkillchainTier.LV2, gate=gate, now_seconds=10,
    )
    assert out.visibility_seconds == 9


def test_lv3_grants_10s():
    r = SkillchainTelegraphReward()
    gate = TelegraphVisibilityGate()
    out = r.on_chain_closed(
        chain_id="ch1", participant_ids=["alice"],
        tier=SkillchainTier.LV3, gate=gate, now_seconds=10,
    )
    assert out.visibility_seconds == 10


def test_5_tiers_each_have_visibility():
    """All 5 tiers must have a visibility window defined."""
    for tier in SkillchainTier:
        assert TIER_VISIBILITY_SECONDS[tier] > 0
