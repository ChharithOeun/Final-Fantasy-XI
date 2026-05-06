"""Tests for combat_stance_system."""
from __future__ import annotations

from server.combat_stance_system import (
    AbilityTag,
    CombatStanceSystem,
    SETTLING_SECONDS,
    SWITCH_COOLDOWN_SECONDS,
    Stance,
)


def test_default_balanced():
    s = CombatStanceSystem()
    assert s.current(player_id="alice") == Stance.BALANCED


def test_set_stance_happy():
    s = CombatStanceSystem()
    out = s.set_stance(
        player_id="alice", stance=Stance.OFFENSIVE, now_seconds=0,
    )
    assert out.accepted is True
    assert out.new_stance == Stance.OFFENSIVE
    assert s.current(player_id="alice") == Stance.OFFENSIVE


def test_blank_player_blocked():
    s = CombatStanceSystem()
    out = s.set_stance(
        player_id="", stance=Stance.OFFENSIVE, now_seconds=0,
    )
    assert out.accepted is False


def test_same_stance_blocked():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.OFFENSIVE, now_seconds=0,
    )
    out = s.set_stance(
        player_id="alice", stance=Stance.OFFENSIVE, now_seconds=20,
    )
    assert out.accepted is False


def test_switch_cooldown_blocks():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.OFFENSIVE, now_seconds=0,
    )
    out = s.set_stance(
        player_id="alice", stance=Stance.DEFENSIVE, now_seconds=3,
    )
    assert out.accepted is False
    after = s.set_stance(
        player_id="alice", stance=Stance.DEFENSIVE,
        now_seconds=SWITCH_COOLDOWN_SECONDS + 1,
    )
    assert after.accepted is True


def test_settling_period_neutralizes_modifiers():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.OFFENSIVE, now_seconds=0,
    )
    mid = s.modifiers(player_id="alice", now_seconds=0)
    # during settling
    assert mid.damage_out_pct == 100
    after = s.modifiers(
        player_id="alice", now_seconds=SETTLING_SECONDS + 1,
    )
    assert after.damage_out_pct == 130


def test_offensive_blocks_defensive_cooldowns():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.OFFENSIVE, now_seconds=0,
    )
    allowed = s.ability_allowed(
        player_id="alice", ability_tag=AbilityTag.DEFENSIVE_COOLDOWN,
        now_seconds=10,
    )
    assert allowed is False


def test_defensive_blocks_two_hour():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.DEFENSIVE, now_seconds=0,
    )
    allowed = s.ability_allowed(
        player_id="alice", ability_tag=AbilityTag.TWO_HOUR_SP,
        now_seconds=10,
    )
    assert allowed is False


def test_defensive_modifiers():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.DEFENSIVE, now_seconds=0,
    )
    m = s.modifiers(player_id="alice", now_seconds=10)
    assert m.damage_out_pct == 75
    assert m.damage_taken_pct == 70
    assert m.threat_pct == 120


def test_evasive_blocks_heavy():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.EVASIVE, now_seconds=0,
    )
    assert s.ability_allowed(
        player_id="alice", ability_tag=AbilityTag.HEAVY_WS,
        now_seconds=10,
    ) is False
    assert s.ability_allowed(
        player_id="alice", ability_tag=AbilityTag.LIGHT_WS,
        now_seconds=10,
    ) is True


def test_support_blocks_damage():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.SUPPORT, now_seconds=0,
    )
    assert s.ability_allowed(
        player_id="alice", ability_tag=AbilityTag.ATTACK_SPELL,
        now_seconds=10,
    ) is False
    assert s.ability_allowed(
        player_id="alice", ability_tag=AbilityTag.HEAL_SPELL,
        now_seconds=10,
    ) is True


def test_balanced_allows_everything():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.BALANCED, now_seconds=0,
    )
    for tag in AbilityTag:
        assert s.ability_allowed(
            player_id="alice", ability_tag=tag, now_seconds=10,
        ) is True


def test_settling_blocks_all_abilities():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.OFFENSIVE, now_seconds=10,
    )
    # within settling
    assert s.ability_allowed(
        player_id="alice", ability_tag=AbilityTag.LIGHT_WS,
        now_seconds=10,
    ) is False


def test_unknown_player_default_modifiers():
    s = CombatStanceSystem()
    m = s.modifiers(player_id="ghost", now_seconds=10)
    assert m.damage_out_pct == 100
    assert m.damage_taken_pct == 100


def test_unknown_player_default_allows_all():
    s = CombatStanceSystem()
    for tag in AbilityTag:
        assert s.ability_allowed(
            player_id="ghost", ability_tag=tag, now_seconds=10,
        ) is True


def test_time_to_next_switch():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.OFFENSIVE, now_seconds=0,
    )
    rem = s.time_to_next_switch(player_id="alice", now_seconds=3)
    assert rem == SWITCH_COOLDOWN_SECONDS - 3
    rem = s.time_to_next_switch(
        player_id="alice", now_seconds=SWITCH_COOLDOWN_SECONDS + 5,
    )
    assert rem == 0


def test_offensive_modifiers():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.OFFENSIVE, now_seconds=0,
    )
    m = s.modifiers(player_id="alice", now_seconds=10)
    assert m.damage_out_pct == 130
    assert m.tp_gain_pct == 110


def test_evasive_modifiers():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.EVASIVE, now_seconds=0,
    )
    m = s.modifiers(player_id="alice", now_seconds=10)
    assert m.evasion_pct == 125
    assert m.movement_pct == 110


def test_support_modifiers():
    s = CombatStanceSystem()
    s.set_stance(
        player_id="alice", stance=Stance.SUPPORT, now_seconds=0,
    )
    m = s.modifiers(player_id="alice", now_seconds=10)
    assert m.healing_pct == 120
    assert m.mp_regen_pct == 120
    assert m.damage_out_pct == 60


def test_full_5_stance_cycle():
    """Stance cycles work as long as cooldown respected."""
    s = CombatStanceSystem()
    seq = [
        Stance.OFFENSIVE, Stance.DEFENSIVE, Stance.EVASIVE,
        Stance.SUPPORT, Stance.BALANCED,
    ]
    t = 0
    for st in seq:
        out = s.set_stance(
            player_id="alice", stance=st, now_seconds=t,
        )
        assert out.accepted is True
        t += SWITCH_COOLDOWN_SECONDS + 1
