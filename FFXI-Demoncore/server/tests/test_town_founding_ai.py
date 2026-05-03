"""Tests for town founding AI."""
from __future__ import annotations

from server.town_founding_ai import (
    HAMLET_POP,
    SettlementStage,
    TOWN_POP,
    TownFoundingAI,
    VILLAGE_POP,
)


def _good_site(ai: TownFoundingAI, name="Newhope"):
    return ai.scout_site(
        zone_id="batallia", name=name,
        water_access=8, defensibility=7,
        trade_proximity=8, arable_land=6,
        beastman_threat=2,
    )


def test_scout_site_returns_score():
    ai = TownFoundingAI()
    s = _good_site(ai)
    assert s.composite_score > 0


def test_viable_above_threshold():
    ai = TownFoundingAI()
    s = _good_site(ai)
    assert ai.viable(s.site_id)


def test_unviable_below_threshold():
    ai = TownFoundingAI()
    s = ai.scout_site(
        zone_id="z", name="bad",
        water_access=1, defensibility=1,
        trade_proximity=1, arable_land=1,
        beastman_threat=10,
    )
    assert not ai.viable(s.site_id)


def test_threat_penalty_kills_score():
    ai = TownFoundingAI()
    high_threat = ai.scout_site(
        zone_id="z", name="risky",
        water_access=10, defensibility=10,
        trade_proximity=10, arable_land=10,
        beastman_threat=10,
    )
    low_threat = ai.scout_site(
        zone_id="z", name="safe",
        water_access=10, defensibility=10,
        trade_proximity=10, arable_land=10,
        beastman_threat=0,
    )
    assert high_threat.composite_score < low_threat.composite_score


def test_charter_succeeds_on_viable_site():
    ai = TownFoundingAI()
    s = _good_site(ai)
    settlement = ai.charter(
        site_id=s.site_id, founder_npc_id="aldric",
    )
    assert settlement is not None
    assert settlement.stage == SettlementStage.CAMP
    assert settlement.population == 1


def test_charter_fails_unviable():
    ai = TownFoundingAI()
    s = ai.scout_site(
        zone_id="z", name="bad",
        water_access=1, defensibility=1,
        trade_proximity=1, arable_land=1,
        beastman_threat=10,
    )
    assert ai.charter(
        site_id=s.site_id, founder_npc_id="x",
    ) is None


def test_charter_unknown_site():
    ai = TownFoundingAI()
    assert ai.charter(
        site_id="ghost", founder_npc_id="x",
    ) is None


def test_double_charter_rejected():
    ai = TownFoundingAI()
    s = _good_site(ai)
    ai.charter(site_id=s.site_id, founder_npc_id="a")
    second = ai.charter(
        site_id=s.site_id, founder_npc_id="b",
    )
    assert second is None


def test_grow_to_hamlet():
    ai = TownFoundingAI()
    s = _good_site(ai)
    ai.charter(site_id=s.site_id, founder_npc_id="a")
    change = ai.grow(
        site_id=s.site_id, new_pop=HAMLET_POP,
    )
    assert change is not None
    assert change.new_stage == SettlementStage.HAMLET


def test_grow_to_village():
    ai = TownFoundingAI()
    s = _good_site(ai)
    ai.charter(site_id=s.site_id, founder_npc_id="a")
    change = ai.grow(
        site_id=s.site_id, new_pop=VILLAGE_POP,
    )
    assert change.new_stage == SettlementStage.VILLAGE


def test_grow_to_town():
    ai = TownFoundingAI()
    s = _good_site(ai)
    ai.charter(site_id=s.site_id, founder_npc_id="a")
    change = ai.grow(
        site_id=s.site_id, new_pop=TOWN_POP,
    )
    assert change.new_stage == SettlementStage.TOWN


def test_grow_no_stage_change_returns_none():
    ai = TownFoundingAI()
    s = _good_site(ai)
    ai.charter(site_id=s.site_id, founder_npc_id="a")
    change = ai.grow(
        site_id=s.site_id, new_pop=5,
    )
    assert change is None


def test_grow_unknown_returns_none():
    ai = TownFoundingAI()
    assert ai.grow(site_id="ghost", new_pop=10) is None


def test_grow_negative_pop_rejected():
    ai = TownFoundingAI()
    s = _good_site(ai)
    ai.charter(site_id=s.site_id, founder_npc_id="a")
    assert ai.grow(
        site_id=s.site_id, new_pop=-1,
    ) is None


def test_abandon_marks_state():
    ai = TownFoundingAI()
    s = _good_site(ai)
    ai.charter(site_id=s.site_id, founder_npc_id="a")
    assert ai.abandon(site_id=s.site_id)
    assert ai.settlement(s.site_id).stage == SettlementStage.ABANDONED


def test_abandon_twice_returns_false():
    ai = TownFoundingAI()
    s = _good_site(ai)
    ai.charter(site_id=s.site_id, founder_npc_id="a")
    ai.abandon(site_id=s.site_id)
    assert not ai.abandon(site_id=s.site_id)


def test_grow_abandoned_no_op():
    ai = TownFoundingAI()
    s = _good_site(ai)
    ai.charter(site_id=s.site_id, founder_npc_id="a")
    ai.abandon(site_id=s.site_id)
    assert ai.grow(
        site_id=s.site_id, new_pop=500,
    ) is None


def test_total_counts():
    ai = TownFoundingAI()
    _good_site(ai)
    _good_site(ai, name="Other")
    assert ai.total_sites() == 2
    assert ai.total_settlements() == 0
