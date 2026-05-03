"""Tests for rumor propagation across the NPC gossip graph."""
from __future__ import annotations

import random

import pytest

from server.rumor_propagation import (
    NodeKind,
    Rumor,
    RumorKind,
    RumorPropagationEngine,
    SocialEdge,
    SocialGraph,
)


def _rumor(rid: str = "r1", **kwargs) -> Rumor:
    base = dict(
        rumor_id=rid, kind=RumorKind.PLAYER_KILLED_NM,
        subject_id="alice", origin_npc_id="npc_a",
        salience=80, fidelity=100, created_at_seconds=0.0,
        summary="Alice slew the Dragon",
    )
    base.update(kwargs)
    return Rumor(**base)


def _line_graph(*nodes: str) -> SocialGraph:
    """Build a chain a -> b -> c -> ... with strength 1.0."""
    g = SocialGraph()
    for n in nodes:
        g.add_node(node_id=n, kind=NodeKind.NPC)
    for i in range(len(nodes) - 1):
        g.add_edge(
            src=nodes[i], dst=nodes[i + 1], strength=1.0,
            bidirectional=False,
        )
    return g


def test_graph_add_node():
    g = SocialGraph()
    g.add_node(node_id="npc_a", kind=NodeKind.NPC)
    assert g.has_node("npc_a")


def test_graph_add_edge_strength_validated():
    g = SocialGraph()
    with pytest.raises(ValueError):
        g.add_edge(src="a", dst="b", strength=2.0)


def test_graph_neighbors_returns_outgoing_edges():
    g = SocialGraph()
    g.add_edge(src="a", dst="b", strength=0.7,
                 bidirectional=False)
    g.add_edge(src="a", dst="c", strength=0.4,
                 bidirectional=False)
    nbrs = g.neighbors("a")
    assert len(nbrs) == 2
    dst_ids = {e.dst_node_id for e in nbrs}
    assert dst_ids == {"b", "c"}


def test_graph_bidirectional_creates_two_edges():
    g = SocialGraph()
    g.add_edge(src="a", dst="b", strength=0.5,
                 bidirectional=True)
    a_out = g.neighbors("a")
    b_out = g.neighbors("b")
    assert len(a_out) == 1
    assert len(b_out) == 1


def test_seed_plants_rumor_at_origin():
    eng = RumorPropagationEngine(graph=_line_graph("a", "b"))
    r = _rumor("r1", origin_npc_id="a")
    eng.seed(rumor=r, origin_node_id="a")
    assert eng.reach_of("r1") == frozenset({"a"})


def test_tick_propagates_along_strength_one_edges():
    eng = RumorPropagationEngine(
        graph=_line_graph("a", "b", "c"),
    )
    eng.seed(rumor=_rumor("r1"), origin_node_id="a")
    rng = random.Random(0)
    eng.tick(rng=rng)
    eng.tick(rng=rng)
    reach = eng.reach_of("r1")
    assert "a" in reach
    assert "b" in reach
    assert "c" in reach


def test_fidelity_decays_along_chain():
    g = SocialGraph()
    g.add_edge(src="a", dst="b", strength=0.5,
                 bidirectional=False)
    g.add_edge(src="b", dst="c", strength=0.5,
                 bidirectional=False)
    eng = RumorPropagationEngine(graph=g)
    eng.seed(rumor=_rumor("r1", fidelity=100), origin_node_id="a")
    rng = random.Random(42)
    eng.settle(max_ticks=10, rng=rng)
    rumors_at_b = eng.rumors_at("b")
    rumors_at_c = eng.rumors_at("c")
    if rumors_at_b and rumors_at_c:
        # b should have higher fidelity than c (one step further)
        b_fid = rumors_at_b[0][1]
        c_fid = rumors_at_c[0][1]
        assert b_fid > c_fid


def test_fidelity_floor_blocks_propagation():
    """Very low strength dies before reaching the third node."""
    g = SocialGraph()
    g.add_edge(src="a", dst="b", strength=0.05,
                 bidirectional=False)
    g.add_edge(src="b", dst="c", strength=0.05,
                 bidirectional=False)
    eng = RumorPropagationEngine(
        graph=g, fidelity_floor=10,
    )
    eng.seed(rumor=_rumor("r1", fidelity=80), origin_node_id="a")
    rng = random.Random(0)
    eng.settle(max_ticks=20, rng=rng)
    # 80 * 0.05 = 4 (below floor 10), so b shouldn't even pick it up
    reach = eng.reach_of("r1")
    assert "c" not in reach


def test_rumor_does_not_re_visit_node():
    """Once a node has the rumor, it shouldn't get a second copy
    even on a bidirectional graph."""
    g = SocialGraph()
    g.add_edge(src="a", dst="b", strength=1.0,
                 bidirectional=True)
    eng = RumorPropagationEngine(graph=g)
    eng.seed(rumor=_rumor("r1"), origin_node_id="a")
    rng = random.Random(0)
    for _ in range(5):
        eng.tick(rng=rng)
    rumors_a = eng.rumors_at("a")
    rumors_b = eng.rumors_at("b")
    # Both nodes have ONE copy of the rumor (no duplicates)
    assert len(rumors_a) == 1
    assert len(rumors_b) == 1


def test_salience_decays_per_tick():
    eng = RumorPropagationEngine(
        graph=_line_graph("a", "b"),
    )
    r = _rumor("r1", salience=80)
    eng.seed(rumor=r, origin_node_id="a")
    eng.tick(rng=random.Random(0))
    eng.tick(rng=random.Random(0))
    rumors_at_a = eng.rumors_at("a")
    # 80 - 2*2 = 76
    assert rumors_at_a[0][0].salience <= 76


def test_total_active_rumors():
    eng = RumorPropagationEngine(
        graph=_line_graph("a", "b"),
    )
    eng.seed(rumor=_rumor("r1"), origin_node_id="a")
    eng.seed(rumor=_rumor("r2"), origin_node_id="a")
    assert eng.total_active_rumors() == 2


def test_compact_old_drops_aged_rumors():
    eng = RumorPropagationEngine(
        graph=_line_graph("a", "b"),
    )
    old = _rumor("r1", created_at_seconds=0.0)
    eng.seed(rumor=old, origin_node_id="a")
    fresh = _rumor("r2", created_at_seconds=1800.0)
    eng.seed(rumor=fresh, origin_node_id="a")
    # cutoff = 2000 - 500 = 1500
    # r1.created_at = 0 < 1500 -> dropped
    # r2.created_at = 1800 > 1500 -> kept
    dropped = eng.compact_old(
        now_seconds=2000.0, max_age_seconds=500.0,
    )
    assert dropped >= 1
    rumors_a = eng.rumors_at("a")
    rids = {r.rumor_id for r, _ in rumors_a}
    assert "r2" in rids
    assert "r1" not in rids


def test_settle_returns_total_spread():
    eng = RumorPropagationEngine(
        graph=_line_graph("a", "b", "c", "d"),
    )
    eng.seed(rumor=_rumor("r1"), origin_node_id="a")
    total = eng.settle(rng=random.Random(0))
    # Should reach 3 new nodes (b, c, d)
    assert total == 3


def test_full_lifecycle_news_reaches_distant_settlement():
    """Build a 3-town gossip network: tavern_npc -> caravan_master
    -> distant_npc. Player slays the dragon at town A; news
    reaches town C after a few ticks."""
    g = SocialGraph()
    # Node kinds spelled out
    g.add_node(node_id="tavern_npc_a", kind=NodeKind.NPC)
    g.add_node(node_id="caravan_master", kind=NodeKind.NPC)
    g.add_node(node_id="distant_npc", kind=NodeKind.NPC)
    g.add_node(node_id="town_a", kind=NodeKind.SETTLEMENT)
    g.add_node(node_id="town_c", kind=NodeKind.SETTLEMENT)
    g.add_edge(
        src="tavern_npc_a", dst="caravan_master", strength=0.8,
    )
    g.add_edge(
        src="caravan_master", dst="distant_npc", strength=0.7,
    )
    g.add_edge(
        src="tavern_npc_a", dst="town_a", strength=0.95,
    )
    g.add_edge(
        src="distant_npc", dst="town_c", strength=0.95,
    )
    eng = RumorPropagationEngine(graph=g)
    eng.seed(
        rumor=_rumor(
            "rdragon", kind=RumorKind.PLAYER_KILLED_BOSS,
            subject_id="alice", origin_npc_id="tavern_npc_a",
            summary="Alice slew the Adamantoise",
        ),
        origin_node_id="tavern_npc_a",
    )
    eng.settle(rng=random.Random(7))
    reach = eng.reach_of("rdragon")
    # News reached the far town
    assert "distant_npc" in reach
    assert "town_c" in reach
