"""Tests for the AI plot generator."""
from __future__ import annotations

from server.ai_plot_generator import (
    AIPlotGenerator,
    DEFAULT_MAX_HOOKS_PER_TICK,
    FactionTension,
    PlotHookKind,
    Urgency,
    WorldStateSnapshot,
)


def test_default_max_hooks_constant():
    assert DEFAULT_MAX_HOOKS_PER_TICK == 5


def test_empty_snapshot_yields_no_hooks():
    gen = AIPlotGenerator()
    res = gen.generate(snapshot=WorldStateSnapshot())
    assert res.hooks == ()
    assert res.skipped_low_urgency == 0


def test_revenge_arc_urgent_when_recent():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        recent_boss_kills=(("alice", "fafnir", 1),),
    )
    res = gen.generate(snapshot=snap)
    assert len(res.hooks) == 1
    h = res.hooks[0]
    assert h.kind == PlotHookKind.REVENGE_ARC
    assert h.urgency == Urgency.URGENT
    assert h.target_actor_id == "alice"


def test_revenge_arc_high_when_older():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        recent_boss_kills=(("bob", "kingbehemoth", 7),),
    )
    res = gen.generate(snapshot=snap)
    assert res.hooks[0].urgency == Urgency.HIGH


def test_revenge_arc_skipped_when_too_old():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        recent_boss_kills=(("bob", "x", 30),),
    )
    res = gen.generate(snapshot=snap)
    assert res.hooks == ()


def test_succession_crisis_on_permadeath():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        recent_permadeaths=(
            ("Cid", "Bastok", "assassinated"),
        ),
    )
    res = gen.generate(snapshot=snap)
    assert len(res.hooks) == 1
    assert res.hooks[0].kind == PlotHookKind.SUCCESSION_CRISIS


def test_grieving_arc():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        npc_grief_signals=(("widow_npc", "fallen_npc"),),
    )
    res = gen.generate(snapshot=snap)
    assert len(res.hooks) == 1
    assert res.hooks[0].kind == PlotHookKind.GRIEVING_ARC
    assert res.hooks[0].urgency == Urgency.NORMAL


def test_border_incident_above_threshold():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        factions_in_tension=(
            FactionTension(
                faction_a="orcs", faction_b="san_doria",
                tension_pct=80,
            ),
        ),
    )
    res = gen.generate(snapshot=snap)
    assert len(res.hooks) == 1
    assert res.hooks[0].kind == PlotHookKind.BORDER_INCIDENT
    assert res.hooks[0].urgency == Urgency.HIGH


def test_border_incident_urgent_when_extreme():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        factions_in_tension=(
            FactionTension(
                faction_a="quadav", faction_b="bastok",
                tension_pct=95,
            ),
        ),
    )
    res = gen.generate(snapshot=snap)
    assert res.hooks[0].urgency == Urgency.URGENT


def test_border_incident_skipped_below_threshold():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        factions_in_tension=(
            FactionTension(
                faction_a="orcs", faction_b="san_doria",
                tension_pct=40,
            ),
        ),
    )
    res = gen.generate(snapshot=snap)
    assert res.hooks == ()


def test_scandal_fires_at_high_rumor_density():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        outstanding_high_salience_rumors=6,
    )
    res = gen.generate(snapshot=snap)
    assert len(res.hooks) == 1
    assert res.hooks[0].kind == PlotHookKind.SCANDAL


def test_scandal_skipped_when_quiet():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        outstanding_high_salience_rumors=2,
    )
    res = gen.generate(snapshot=snap)
    assert res.hooks == ()


def test_plague_outbreak_high_urgency():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        plague_rumors_in_zone=(("jeuno", 5),),
    )
    res = gen.generate(snapshot=snap)
    assert len(res.hooks) == 1
    assert res.hooks[0].kind == PlotHookKind.PLAGUE_OUTBREAK
    assert res.hooks[0].urgency == Urgency.HIGH


def test_plague_outbreak_urgent_when_severe():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        plague_rumors_in_zone=(("bastok", 10),),
    )
    res = gen.generate(snapshot=snap)
    assert res.hooks[0].urgency == Urgency.URGENT


def test_wandering_hero_above_fame_threshold():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        famous_player_id="alice",
        famous_player_fame_score=750,
    )
    res = gen.generate(snapshot=snap)
    assert len(res.hooks) == 1
    assert res.hooks[0].kind == PlotHookKind.WANDERING_HERO
    assert res.hooks[0].target_actor_id == "alice"


def test_wandering_hero_skipped_below_threshold():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        famous_player_id="alice",
        famous_player_fame_score=200,
    )
    res = gen.generate(snapshot=snap)
    assert res.hooks == ()


def test_urgency_sort_order():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        # NORMAL urgency
        npc_grief_signals=(("a", "b"),),
        # URGENT urgency
        recent_boss_kills=(("p", "boss1", 1),),
        # HIGH urgency
        factions_in_tension=(
            FactionTension(
                faction_a="x", faction_b="y", tension_pct=80,
            ),
        ),
    )
    res = gen.generate(snapshot=snap)
    # URGENT first, then HIGH, then NORMAL
    assert res.hooks[0].urgency == Urgency.URGENT
    assert res.hooks[1].urgency == Urgency.HIGH
    assert res.hooks[2].urgency == Urgency.NORMAL


def test_cap_at_max_hooks_per_tick():
    gen = AIPlotGenerator(max_hooks_per_tick=2)
    snap = WorldStateSnapshot(
        recent_boss_kills=(
            ("p1", "b1", 1),
            ("p2", "b2", 1),
            ("p3", "b3", 1),
            ("p4", "b4", 1),
        ),
    )
    res = gen.generate(snapshot=snap)
    assert len(res.hooks) == 2
    assert res.skipped_low_urgency == 2


def test_acknowledge_then_double_ack_rejected():
    gen = AIPlotGenerator()
    snap = WorldStateSnapshot(
        recent_boss_kills=(("p", "b", 1),),
    )
    res = gen.generate(snapshot=snap)
    hid = res.hooks[0].hook_id
    assert gen.acknowledge(hook_id=hid)
    assert not gen.acknowledge(hook_id=hid)
    assert gen.is_acknowledged(hid)


def test_acknowledge_unknown_hook():
    gen = AIPlotGenerator()
    assert not gen.acknowledge(hook_id="ghost")


def test_total_proposed_increments():
    gen = AIPlotGenerator()
    assert gen.total_proposed() == 0
    snap = WorldStateSnapshot(
        recent_boss_kills=(("p", "b", 1),),
    )
    gen.generate(snapshot=snap)
    assert gen.total_proposed() == 1


def test_full_world_state_produces_diverse_hooks():
    """Smoke test of a full snapshot with many signals."""
    gen = AIPlotGenerator(max_hooks_per_tick=20)
    snap = WorldStateSnapshot(
        now_seconds=1000.0,
        factions_in_tension=(
            FactionTension(
                faction_a="orcs", faction_b="san_doria",
                tension_pct=85,
            ),
        ),
        recent_boss_kills=(("alice", "fafnir", 2),),
        outstanding_high_salience_rumors=7,
        recent_permadeaths=(("Naji", "Bastok", "ambush"),),
        npc_grief_signals=(("kin_npc", "Naji"),),
        famous_player_fame_score=900,
        famous_player_id="alice",
        plague_rumors_in_zone=(("jeuno", 6),),
    )
    res = gen.generate(snapshot=snap)
    kinds = {h.kind for h in res.hooks}
    # All 7 signal-producing kinds should appear
    assert PlotHookKind.REVENGE_ARC in kinds
    assert PlotHookKind.BORDER_INCIDENT in kinds
    assert PlotHookKind.SUCCESSION_CRISIS in kinds
    assert PlotHookKind.GRIEVING_ARC in kinds
    assert PlotHookKind.SCANDAL in kinds
    assert PlotHookKind.PLAGUE_OUTBREAK in kinds
    assert PlotHookKind.WANDERING_HERO in kinds
