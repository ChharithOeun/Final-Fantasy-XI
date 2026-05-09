"""Tests for entity_gossip_propagation."""
from __future__ import annotations

from server.entity_gossip_propagation import (
    EntityGossipPropagationSystem, GossipTier,
)
from server.entity_hobbies import HobbyKind


def test_register_hub_happy():
    s = EntityGossipPropagationSystem()
    assert s.register_gossip_hub(
        npc_id="bastok_innkeeper",
    ) is True


def test_register_hub_dup_blocked():
    s = EntityGossipPropagationSystem()
    s.register_gossip_hub(npc_id="x")
    assert s.register_gossip_hub(npc_id="x") is False


def test_record_observation_happy():
    s = EntityGossipPropagationSystem()
    assert s.record_observation(
        entity_id="volker", hobby=HobbyKind.FISHING,
        witness_id="naji",
    ) is True


def test_record_empty_entity_blocked():
    s = EntityGossipPropagationSystem()
    assert s.record_observation(
        entity_id="", hobby=HobbyKind.FISHING,
        witness_id="naji",
    ) is False


def test_record_empty_witness_blocked():
    s = EntityGossipPropagationSystem()
    assert s.record_observation(
        entity_id="x", hobby=HobbyKind.FISHING,
        witness_id="",
    ) is False


def test_starting_tier_private():
    s = EntityGossipPropagationSystem()
    s.record_observation(
        entity_id="volker", hobby=HobbyKind.FISHING,
        witness_id="naji",
    )
    # 1 < 5, still PRIVATE
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == GossipTier.PRIVATE


def test_neighborhood_tier_at_5():
    s = EntityGossipPropagationSystem()
    for i in range(5):
        s.record_observation(
            entity_id="volker",
            hobby=HobbyKind.FISHING,
            witness_id=f"w{i}",
        )
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == GossipTier.NEIGHBORHOOD


def test_town_tier_at_20():
    s = EntityGossipPropagationSystem()
    for i in range(20):
        s.record_observation(
            entity_id="volker",
            hobby=HobbyKind.FISHING,
            witness_id=f"w{i}",
        )
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == GossipTier.TOWN


def test_regional_at_50():
    s = EntityGossipPropagationSystem()
    for i in range(50):
        s.record_observation(
            entity_id="volker",
            hobby=HobbyKind.FISHING,
            witness_id=f"w{i}",
        )
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == GossipTier.REGIONAL


def test_famous_at_150():
    s = EntityGossipPropagationSystem()
    for i in range(150):
        s.record_observation(
            entity_id="volker",
            hobby=HobbyKind.FISHING,
            witness_id=f"w{i}",
        )
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == GossipTier.FAMOUS


def test_hub_boost_accelerates():
    s = EntityGossipPropagationSystem()
    s.register_gossip_hub(npc_id="innkeeper")
    # 1 obs through hub = 6 score (1 base + 5 boost)
    s.record_observation(
        entity_id="volker", hobby=HobbyKind.FISHING,
        witness_id="naji",
        propagator_npc_id="innkeeper",
    )
    assert s.fact(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ).spread_score == 6


def test_non_hub_no_boost():
    s = EntityGossipPropagationSystem()
    s.record_observation(
        entity_id="volker", hobby=HobbyKind.FISHING,
        witness_id="naji",
        propagator_npc_id="random_npc",
    )
    # No hub registered, no boost
    assert s.fact(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ).spread_score == 1


def test_distinct_witnesses_tracked():
    s = EntityGossipPropagationSystem()
    s.record_observation(
        entity_id="volker", hobby=HobbyKind.FISHING,
        witness_id="naji",
    )
    s.record_observation(
        entity_id="volker", hobby=HobbyKind.FISHING,
        witness_id="bob",
    )
    s.record_observation(
        entity_id="volker", hobby=HobbyKind.FISHING,
        witness_id="naji",   # repeat
    )
    f = s.fact(
        entity_id="volker", hobby=HobbyKind.FISHING,
    )
    assert f.distinct_witnesses == 2
    assert f.spread_score == 3


def test_is_public_knowledge_at_town():
    s = EntityGossipPropagationSystem()
    for i in range(20):
        s.record_observation(
            entity_id="volker",
            hobby=HobbyKind.FISHING,
            witness_id=f"w{i}",
        )
    assert s.is_public_knowledge(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) is True


def test_not_public_at_neighborhood():
    s = EntityGossipPropagationSystem()
    for i in range(10):
        s.record_observation(
            entity_id="volker",
            hobby=HobbyKind.FISHING,
            witness_id=f"w{i}",
        )
    assert s.is_public_knowledge(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) is False


def test_per_hobby_isolation():
    s = EntityGossipPropagationSystem()
    for i in range(20):
        s.record_observation(
            entity_id="volker",
            hobby=HobbyKind.FISHING,
            witness_id=f"w{i}",
        )
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == GossipTier.TOWN
    # Drinking unobserved → still PRIVATE
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.DRINKING,
    ) == GossipTier.PRIVATE


def test_known_facts_about_lookup():
    s = EntityGossipPropagationSystem()
    s.record_observation(
        entity_id="volker", hobby=HobbyKind.FISHING,
        witness_id="naji",
    )
    s.record_observation(
        entity_id="volker", hobby=HobbyKind.DRINKING,
        witness_id="naji",
    )
    facts = s.known_facts_about(entity_id="volker")
    assert len(facts) == 2


def test_tier_unknown_private():
    s = EntityGossipPropagationSystem()
    assert s.tier(
        entity_id="ghost", hobby=HobbyKind.FISHING,
    ) == GossipTier.PRIVATE


def test_fact_unknown_none():
    s = EntityGossipPropagationSystem()
    assert s.fact(
        entity_id="ghost", hobby=HobbyKind.FISHING,
    ) is None


def test_is_gossip_hub_query():
    s = EntityGossipPropagationSystem()
    s.register_gossip_hub(npc_id="x")
    assert s.is_gossip_hub(npc_id="x") is True
    assert s.is_gossip_hub(npc_id="y") is False


def test_register_empty_hub_blocked():
    s = EntityGossipPropagationSystem()
    assert s.register_gossip_hub(npc_id="") is False


def test_enum_count():
    assert len(list(GossipTier)) == 5
