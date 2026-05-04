"""Tests for the beastman fellowship NPC."""
from __future__ import annotations

from server.beastman_fellowship_npc import (
    BeastmanFellowshipNpc,
    FellowshipTier,
    PersonalityArchetype,
)


def test_summon_basic():
    f = BeastmanFellowshipNpc()
    res = f.summon_fellow(
        player_id="kraw",
        name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    assert res.accepted
    assert res.archetype == PersonalityArchetype.HEALER


def test_summon_empty_name():
    f = BeastmanFellowshipNpc()
    res = f.summon_fellow(
        player_id="kraw",
        name="",
        archetype=PersonalityArchetype.HEALER,
    )
    assert not res.accepted


def test_summon_double_blocked():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="A",
        archetype=PersonalityArchetype.HEALER,
    )
    res = f.summon_fellow(
        player_id="kraw", name="B",
        archetype=PersonalityArchetype.SCHOLAR,
    )
    assert not res.accepted


def test_grant_bond_basic():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    res = f.grant_bond(player_id="kraw", points=200)
    assert res.accepted
    assert res.bond_points == 200
    assert res.new_tier == FellowshipTier.FAITHFUL


def test_grant_bond_no_fellow():
    f = BeastmanFellowshipNpc()
    res = f.grant_bond(player_id="ghost", points=100)
    assert not res.accepted


def test_grant_bond_zero_points():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    res = f.grant_bond(player_id="kraw", points=0)
    assert not res.accepted


def test_grant_bond_negative_points():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    res = f.grant_bond(player_id="kraw", points=-10)
    assert not res.accepted


def test_promote_to_trusted():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    f.grant_bond(player_id="kraw", points=600)
    res = f.promote_if_eligible(player_id="kraw")
    assert res.accepted
    assert res.promoted
    assert res.new_tier == FellowshipTier.TRUSTED


def test_promote_to_sworn_at_8000():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    f.grant_bond(player_id="kraw", points=10_000)
    res = f.promote_if_eligible(player_id="kraw")
    assert res.new_tier == FellowshipTier.SWORN


def test_promote_no_jump_below_threshold():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    f.grant_bond(player_id="kraw", points=100)
    res = f.promote_if_eligible(player_id="kraw")
    assert not res.promoted
    assert res.new_tier == FellowshipTier.FAITHFUL


def test_promote_no_fellow():
    f = BeastmanFellowshipNpc()
    res = f.promote_if_eligible(player_id="ghost")
    assert not res.accepted


def test_dismiss():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    assert f.dismiss(player_id="kraw")
    # Can re-summon after dismiss
    res = f.summon_fellow(
        player_id="kraw", name="Other",
        archetype=PersonalityArchetype.SCHOLAR,
    )
    assert res.accepted


def test_dismiss_no_fellow():
    f = BeastmanFellowshipNpc()
    assert not f.dismiss(player_id="ghost")


def test_fellow_for_basic():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    fl = f.fellow_for(player_id="kraw")
    assert fl is not None
    assert fl.name == "Sirah"


def test_fellow_for_none():
    f = BeastmanFellowshipNpc()
    assert f.fellow_for(player_id="ghost") is None


def test_total_fellows():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="alice", name="A",
        archetype=PersonalityArchetype.HEALER,
    )
    f.summon_fellow(
        player_id="bob", name="B",
        archetype=PersonalityArchetype.BERSERKER,
    )
    assert f.total_fellows() == 2


def test_archetype_pulls_through():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Trickster",
        archetype=PersonalityArchetype.TRICKSTER,
    )
    fl = f.fellow_for(player_id="kraw")
    assert fl.archetype == PersonalityArchetype.TRICKSTER


def test_per_player_isolation():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="alice", name="A",
        archetype=PersonalityArchetype.HEALER,
    )
    res = f.summon_fellow(
        player_id="bob", name="B",
        archetype=PersonalityArchetype.SCHOLAR,
    )
    assert res.accepted


def test_promote_walks_multiple_tiers():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    f.grant_bond(player_id="kraw", points=2_500)
    res = f.promote_if_eligible(player_id="kraw")
    assert res.new_tier == FellowshipTier.STAUNCH


def test_promote_already_max_no_op():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    f.grant_bond(player_id="kraw", points=10_000)
    f.promote_if_eligible(player_id="kraw")
    res = f.promote_if_eligible(player_id="kraw")
    assert not res.promoted


def test_bond_accumulates():
    f = BeastmanFellowshipNpc()
    f.summon_fellow(
        player_id="kraw", name="Sirah",
        archetype=PersonalityArchetype.HEALER,
    )
    f.grant_bond(player_id="kraw", points=100)
    f.grant_bond(player_id="kraw", points=300)
    fl = f.fellow_for(player_id="kraw")
    assert fl.bond_points == 400
