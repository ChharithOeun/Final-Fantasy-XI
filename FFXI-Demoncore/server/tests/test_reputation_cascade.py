"""Tests for reputation cascade."""
from __future__ import annotations

import pytest

from server.faction_reputation import PlayerFactionReputation
from server.reputation_cascade import (
    ReputationCascadeRegistry,
    seed_default_alignment,
)


def _rep(player_id: str = "alice") -> PlayerFactionReputation:
    return PlayerFactionReputation(player_id=player_id)


def test_coefficient_validation():
    reg = ReputationCascadeRegistry()
    with pytest.raises(ValueError):
        reg.add_alignment(src="a", dst="b", coefficient=2.0)


def test_add_alignment_basic():
    reg = ReputationCascadeRegistry()
    edge = reg.add_alignment(
        src="orc", dst="san_doria", coefficient=-0.5,
    )
    assert edge.coefficient == -0.5
    assert reg.total_edges() == 1


def test_neighbors_filters_by_src():
    reg = ReputationCascadeRegistry()
    reg.add_alignment(src="orc", dst="san_doria", coefficient=-0.5)
    reg.add_alignment(src="orc", dst="goblin", coefficient=-0.3)
    reg.add_alignment(src="san_doria", dst="orc", coefficient=-0.5)
    nbrs = reg.neighbors("orc")
    assert len(nbrs) == 2


def test_propagate_no_neighbors():
    reg = ReputationCascadeRegistry()
    rep = _rep()
    res = reg.propagate(
        player_id="alice", source_faction="bastok",
        source_delta=50, rep=rep,
    )
    assert res.propagated == {}
    assert rep.value("bastok") == 50


def test_propagate_negative_alignment():
    """Helping the orcs hurts San d'Oria standing."""
    reg = ReputationCascadeRegistry()
    reg.add_alignment(src="orc", dst="san_doria", coefficient=-0.5)
    rep = _rep()
    rep.set(faction_id="san_doria", value=100)
    res = reg.propagate(
        player_id="alice", source_faction="orc",
        source_delta=50, rep=rep,
    )
    assert res.propagated["san_doria"] == -25
    # Net: san_doria went from 100 -> 75
    assert rep.value("san_doria") == 75
    # Orc rep up by 50
    assert rep.value("orc") == 50


def test_propagate_positive_alignment():
    """Helping Bastok also lifts Jeuno (mediator)."""
    reg = ReputationCascadeRegistry()
    reg.add_alignment(src="bastok", dst="jeuno", coefficient=0.15)
    rep = _rep()
    res = reg.propagate(
        player_id="alice", source_faction="bastok",
        source_delta=100, rep=rep,
    )
    # 0.15 * 100 = 15
    assert res.propagated["jeuno"] == 15
    assert rep.value("jeuno") == 15
    assert rep.value("bastok") == 100


def test_zero_delta_propagation_skipped():
    reg = ReputationCascadeRegistry()
    reg.add_alignment(src="bastok", dst="jeuno", coefficient=0.15)
    rep = _rep()
    res = reg.propagate(
        player_id="alice", source_faction="bastok",
        source_delta=3, rep=rep,
    )
    # 3 * 0.15 = 0.45 -> rounds to 0 -> skipped
    assert res.propagated == {}


def test_cascade_change_aggregates_propagated():
    reg = ReputationCascadeRegistry()
    reg.add_alignment(
        src="orc", dst="san_doria", coefficient=-0.5,
    )
    reg.add_alignment(
        src="orc", dst="goblin", coefficient=-0.3,
    )
    rep = _rep()
    res = reg.propagate(
        player_id="alice", source_faction="orc",
        source_delta=100, rep=rep,
    )
    assert res.propagated["san_doria"] == -50
    assert res.propagated["goblin"] == -30


def test_seed_default_alignment_count():
    reg = seed_default_alignment(ReputationCascadeRegistry())
    # Should have many edges seeded
    assert reg.total_edges() >= 20


def test_default_seed_orc_san_doria_negative():
    reg = seed_default_alignment(ReputationCascadeRegistry())
    rep = _rep()
    res = reg.propagate(
        player_id="alice", source_faction="orc",
        source_delta=100, rep=rep,
    )
    assert res.propagated["san_doria"] == -50


def test_default_seed_bastok_jeuno_positive():
    reg = seed_default_alignment(ReputationCascadeRegistry())
    rep = _rep()
    res = reg.propagate(
        player_id="alice", source_faction="bastok",
        source_delta=100, rep=rep,
    )
    assert res.propagated["jeuno"] >= 1


def test_default_seed_tenshodo_hurts_nations():
    reg = seed_default_alignment(ReputationCascadeRegistry())
    rep = _rep()
    res = reg.propagate(
        player_id="alice", source_faction="tenshodo",
        source_delta=100, rep=rep,
    )
    assert res.propagated.get("bastok", 0) < 0
    assert res.propagated.get("san_doria", 0) < 0
    assert res.propagated.get("windurst", 0) < 0


def test_full_lifecycle_help_orcs_lose_sandy():
    """Alice helps the Orcs heavily; her San d'Oria rep
    collapses."""
    reg = seed_default_alignment(ReputationCascadeRegistry())
    rep = _rep()
    rep.set(faction_id="san_doria", value=200)  # Allied
    rep.set(faction_id="orc", value=-100)
    # Big swing toward the orcs
    reg.propagate(
        player_id="alice", source_faction="orc",
        source_delta=300, rep=rep,
    )
    # San d'Oria should drop by ~150
    assert rep.value("san_doria") == 50
    # Orc rep climbs
    assert rep.value("orc") == 200


def test_full_lifecycle_jeuno_neutral_friendship():
    """Alice walks the diplomatic line — earning rep with Jeuno
    bumps all three nations slightly."""
    reg = seed_default_alignment(ReputationCascadeRegistry())
    rep = _rep()
    res = reg.propagate(
        player_id="alice", source_faction="jeuno",
        source_delta=100, rep=rep,
    )
    # Each nation +15
    assert res.propagated["bastok"] == 15
    assert res.propagated["san_doria"] == 15
    assert res.propagated["windurst"] == 15
