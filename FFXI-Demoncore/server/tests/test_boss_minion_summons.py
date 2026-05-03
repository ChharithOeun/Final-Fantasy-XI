"""Tests for boss minion summon registry."""
from __future__ import annotations

from server.boss_minion_summons import (
    AddArchetype,
    SummonRegistry,
    SummonRule,
    SummonTriggerKind,
)


def _hp_rule(
    rule_id: str = "r1", hp_pct: int = 75,
    archetype: AddArchetype = AddArchetype.HEAVY_GUARD,
    count: int = 2, cooldown: float = 60.0,
) -> SummonRule:
    return SummonRule(
        rule_id=rule_id,
        trigger_kind=SummonTriggerKind.HP_THRESHOLD,
        archetype=archetype, count=count,
        hp_pct=hp_pct, cooldown_seconds=cooldown,
    )


def _timer_rule(
    rule_id: str = "tick", period: float = 30.0,
    archetype: AddArchetype = AddArchetype.SUICIDAL_BOMBER,
    count: int = 1, cooldown: float = 25.0,
) -> SummonRule:
    return SummonRule(
        rule_id=rule_id,
        trigger_kind=SummonTriggerKind.TIMER,
        archetype=archetype, count=count,
        period_seconds=period, cooldown_seconds=cooldown,
    )


def test_hp_threshold_fires_at_crossing():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1", rules=[_hp_rule(hp_pct=75)],
    )
    # No spawn at 90%
    a = reg.on_hp_change(
        boss_id="boss_1", hp_pct=90, now_seconds=10.0,
    )
    assert a == ()
    # Spawn at 75% (crossing)
    b = reg.on_hp_change(
        boss_id="boss_1", hp_pct=75, now_seconds=20.0,
    )
    assert len(b) == 2
    for add in b:
        assert add.archetype == AddArchetype.HEAVY_GUARD


def test_hp_threshold_only_fires_once_per_crossing():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1",
        rules=[_hp_rule(hp_pct=75, cooldown=999)],
    )
    reg.on_hp_change(
        boss_id="boss_1", hp_pct=70, now_seconds=10.0,
    )
    # HP came back up then down again — but cooldown blocks re-fire
    reg.on_hp_change(
        boss_id="boss_1", hp_pct=85, now_seconds=20.0,
    )
    second = reg.on_hp_change(
        boss_id="boss_1", hp_pct=70, now_seconds=30.0,
    )
    assert second == ()


def test_hp_threshold_can_refire_after_cooldown():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1",
        rules=[_hp_rule(hp_pct=75, cooldown=10.0)],
    )
    reg.on_hp_change(
        boss_id="boss_1", hp_pct=70, now_seconds=10.0,
    )
    reg.on_hp_change(
        boss_id="boss_1", hp_pct=85, now_seconds=20.0,
    )
    # Cooldown elapsed
    second = reg.on_hp_change(
        boss_id="boss_1", hp_pct=70, now_seconds=30.0,
    )
    assert len(second) > 0


def test_multiple_hp_bands():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1",
        rules=[
            _hp_rule(rule_id="band_75", hp_pct=75,
                     archetype=AddArchetype.HEAVY_GUARD),
            _hp_rule(rule_id="band_50", hp_pct=50,
                     archetype=AddArchetype.HEALER),
            _hp_rule(rule_id="band_25", hp_pct=25,
                     archetype=AddArchetype.SUICIDAL_BOMBER),
        ],
    )
    reg.on_hp_change(
        boss_id="boss_1", hp_pct=80, now_seconds=10.0,
    )
    a = reg.on_hp_change(
        boss_id="boss_1", hp_pct=20, now_seconds=20.0,
    )
    # All three thresholds crossed simultaneously
    archetypes = {add.archetype for add in a}
    assert AddArchetype.HEAVY_GUARD in archetypes
    assert AddArchetype.HEALER in archetypes
    assert AddArchetype.SUICIDAL_BOMBER in archetypes


def test_timer_fires_at_period():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1",
        rules=[_timer_rule(period=30.0)],
        spawned_at_seconds=0.0,
    )
    # Before period, no spawn
    a = reg.on_timer_tick(boss_id="boss_1", now_seconds=10.0)
    assert a == ()
    # After period elapsed
    b = reg.on_timer_tick(boss_id="boss_1", now_seconds=35.0)
    assert len(b) == 1


def test_timer_repeats():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1",
        rules=[_timer_rule(period=10.0, cooldown=5.0)],
        spawned_at_seconds=0.0,
    )
    a = reg.on_timer_tick(boss_id="boss_1", now_seconds=15.0)
    b = reg.on_timer_tick(boss_id="boss_1", now_seconds=30.0)
    assert len(a) == 1
    assert len(b) == 1


def test_ability_cast_triggers_summon():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1", rules=[
            SummonRule(
                rule_id="rage_call",
                trigger_kind=SummonTriggerKind.ABILITY_CAST,
                archetype=AddArchetype.FAST_HARASSER,
                count=3, ability_id="rage_call",
            ),
        ],
    )
    a = reg.on_ability_cast(
        boss_id="boss_1", ability_id="rage_call",
        now_seconds=10.0,
    )
    assert len(a) == 3
    # Different ability — no spawn
    b = reg.on_ability_cast(
        boss_id="boss_1", ability_id="other",
        now_seconds=20.0,
    )
    assert b == ()


def test_player_response_triggers_summon():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1", rules=[
            SummonRule(
                rule_id="silence_punish",
                trigger_kind=SummonTriggerKind.PLAYER_RESPONSE,
                archetype=AddArchetype.ELEMENTALIST,
                count=2, response_id="boss_silenced",
            ),
        ],
    )
    a = reg.on_player_response(
        boss_id="boss_1", response_id="boss_silenced",
        now_seconds=10.0,
    )
    assert len(a) == 2


def test_boss_death_despawns_adds():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1", rules=[_hp_rule(hp_pct=75, count=3)],
    )
    reg.on_hp_change(
        boss_id="boss_1", hp_pct=70, now_seconds=10.0,
    )
    assert len(reg.live_adds_of("boss_1")) == 3
    despawned = reg.on_boss_death(boss_id="boss_1")
    assert len(despawned) == 3
    assert reg.live_adds_of("boss_1") == ()


def test_kill_add_removes_from_live_set():
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="boss_1", rules=[_hp_rule(hp_pct=75, count=2)],
    )
    spawned = reg.on_hp_change(
        boss_id="boss_1", hp_pct=70, now_seconds=10.0,
    )
    aid = spawned[0].add_id
    assert reg.kill_add(add_id=aid)
    live = reg.live_adds_of("boss_1")
    assert all(add.add_id != aid for add in live)
    assert len(live) == 1


def test_kill_unknown_add_returns_false():
    reg = SummonRegistry()
    assert not reg.kill_add(add_id="ghost")


def test_unknown_boss_returns_empty():
    reg = SummonRegistry()
    assert reg.on_hp_change(
        boss_id="ghost", hp_pct=10, now_seconds=0.0,
    ) == ()
    assert reg.on_timer_tick(
        boss_id="ghost", now_seconds=100.0,
    ) == ()
    assert reg.on_ability_cast(
        boss_id="ghost", ability_id="x", now_seconds=0.0,
    ) == ()
    assert reg.on_player_response(
        boss_id="ghost", response_id="y", now_seconds=0.0,
    ) == ()
    assert reg.on_boss_death(boss_id="ghost") == ()


def test_full_lifecycle_dragon_fight():
    """Dragon boss: HP-band guards at 75%, healer at 50%,
    suicide bombers via timer every 60s, fire breath summons
    elementalists. Player silences boss -> punisher elemental."""
    reg = SummonRegistry()
    reg.register_boss(
        boss_id="dragon", spawned_at_seconds=0.0,
        rules=[
            _hp_rule(rule_id="guards", hp_pct=75, count=2,
                     archetype=AddArchetype.HEAVY_GUARD),
            _hp_rule(rule_id="healer", hp_pct=50, count=1,
                     archetype=AddArchetype.HEALER),
            _timer_rule(rule_id="bomber", period=60.0,
                        cooldown=55.0,
                        archetype=AddArchetype.SUICIDAL_BOMBER),
            SummonRule(
                rule_id="fire_breath",
                trigger_kind=SummonTriggerKind.ABILITY_CAST,
                archetype=AddArchetype.ELEMENTALIST,
                count=2, ability_id="fire_breath",
            ),
            SummonRule(
                rule_id="silence_punish",
                trigger_kind=SummonTriggerKind.PLAYER_RESPONSE,
                archetype=AddArchetype.ELEMENTALIST,
                count=1, response_id="boss_silenced",
            ),
        ],
    )
    # HP drops to 75 -> 2 guards
    a1 = reg.on_hp_change(
        boss_id="dragon", hp_pct=75, now_seconds=10.0,
    )
    assert len(a1) == 2
    # Timer ticks -> bomber
    a2 = reg.on_timer_tick(
        boss_id="dragon", now_seconds=70.0,
    )
    assert len(a2) == 1
    # Fire breath -> 2 elementalists
    a3 = reg.on_ability_cast(
        boss_id="dragon", ability_id="fire_breath",
        now_seconds=80.0,
    )
    assert len(a3) == 2
    # Player silences boss -> 1 elemental
    a4 = reg.on_player_response(
        boss_id="dragon", response_id="boss_silenced",
        now_seconds=90.0,
    )
    assert len(a4) == 1
    # 2 + 1 + 2 + 1 = 6 adds live
    assert len(reg.live_adds_of("dragon")) == 6
    # Boss dies
    despawned = reg.on_boss_death(boss_id="dragon")
    assert len(despawned) == 6
