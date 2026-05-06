"""Tests for turn_command_resolver."""
from __future__ import annotations

from server.turn_command_resolver import (
    CommandKind, RejectReason, TurnCommandResolver,
)


def _setup():
    r = TurnCommandResolver()
    r.register_command(
        cmd_id="fire_iii", kind=CommandKind.SPELL,
        mp_cost=49, requires_target=True,
        range_yalms=21.0, cooldown_seconds=10,
    )
    r.register_command(
        cmd_id="provoke", kind=CommandKind.JOB_ABILITY,
        requires_target=True, range_yalms=21.0,
        cooldown_seconds=30,
    )
    r.register_command(
        cmd_id="vorpal_blade", kind=CommandKind.WEAPON_SKILL,
        tp_cost=1000, requires_target=True, range_yalms=5.0,
    )
    r.register_command(
        cmd_id="potion", kind=CommandKind.ITEM,
        requires_target=False,
    )
    return r


def test_register_happy():
    r = _setup()
    assert r.total_commands() == 4


def test_register_blank_id_blocked():
    r = TurnCommandResolver()
    out = r.register_command(
        cmd_id="", kind=CommandKind.SPELL,
    )
    assert out is False


def test_register_negative_cost_blocked():
    r = TurnCommandResolver()
    out = r.register_command(
        cmd_id="x", kind=CommandKind.SPELL, mp_cost=-1,
    )
    assert out is False


def test_register_duplicate_blocked():
    r = _setup()
    out = r.register_command(
        cmd_id="fire_iii", kind=CommandKind.SPELL,
    )
    assert out is False


def test_can_use_happy():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="fire_iii",
        actor_mp=100, actor_tp=0,
        actor_action_gated=False,
        target_id="goblin", target_alive=True,
        distance_yalms=10.0, now=1000,
    )
    assert out.success is True
    assert out.command.mp_paid == 49


def test_unknown_command_rejected():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="ghost",
        actor_mp=100, actor_tp=0,
        actor_action_gated=False,
        target_id="goblin", target_alive=True,
    )
    assert out.success is False
    assert out.reason == RejectReason.UNKNOWN_COMMAND


def test_action_gated_rejected():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="fire_iii",
        actor_mp=100, actor_tp=0,
        actor_action_gated=True,   # silenced
        target_id="goblin", target_alive=True,
    )
    assert out.success is False
    assert out.reason == RejectReason.ACTION_GATED


def test_no_target_when_required():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="fire_iii",
        actor_mp=100, actor_tp=0,
        actor_action_gated=False,
        target_id="",
    )
    assert out.success is False
    assert out.reason == RejectReason.NO_TARGET


def test_target_dead_rejected():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="fire_iii",
        actor_mp=100, actor_tp=0,
        actor_action_gated=False,
        target_id="goblin", target_alive=False,
    )
    assert out.success is False
    assert out.reason == RejectReason.TARGET_DEAD


def test_out_of_range_rejected():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="vorpal_blade",
        actor_mp=0, actor_tp=1500,
        actor_action_gated=False,
        target_id="goblin", target_alive=True,
        distance_yalms=10.0,   # melee range 5.0
    )
    assert out.success is False
    assert out.reason == RejectReason.OUT_OF_RANGE


def test_insufficient_mp():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="fire_iii",
        actor_mp=20, actor_tp=0,   # need 49
        actor_action_gated=False,
        target_id="goblin", target_alive=True,
    )
    assert out.success is False
    assert out.reason == RejectReason.INSUFFICIENT_MP


def test_insufficient_tp():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="vorpal_blade",
        actor_mp=0, actor_tp=500,   # need 1000
        actor_action_gated=False,
        target_id="goblin", target_alive=True,
        distance_yalms=2.0,
    )
    assert out.success is False
    assert out.reason == RejectReason.INSUFFICIENT_TP


def test_cooldown_blocks_reuse():
    r = _setup()
    r.mark_used(
        actor_id="alice", cmd_id="fire_iii", used_at=100,
    )
    out = r.can_use(
        actor_id="alice", cmd_id="fire_iii",
        actor_mp=100, actor_tp=0,
        actor_action_gated=False,
        target_id="goblin", target_alive=True,
        now=105,   # only 5s after, cooldown is 10
    )
    assert out.success is False
    assert out.reason == RejectReason.ON_COOLDOWN


def test_cooldown_expired_allows_reuse():
    r = _setup()
    r.mark_used(
        actor_id="alice", cmd_id="fire_iii", used_at=100,
    )
    out = r.can_use(
        actor_id="alice", cmd_id="fire_iii",
        actor_mp=100, actor_tp=0,
        actor_action_gated=False,
        target_id="goblin", target_alive=True,
        now=115,
    )
    assert out.success is True


def test_cooldown_per_actor_independent():
    r = _setup()
    r.mark_used(
        actor_id="alice", cmd_id="provoke", used_at=100,
    )
    out = r.can_use(
        actor_id="bob", cmd_id="provoke",
        actor_mp=0, actor_tp=0,
        actor_action_gated=False,
        target_id="goblin", target_alive=True,
        now=105,
    )
    # bob never used it; should be available
    assert out.success is True


def test_no_target_command_skips_target_checks():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="potion",
        actor_mp=0, actor_tp=0,
        actor_action_gated=False,
        target_id="",  # potion is self-use
    )
    assert out.success is True


def test_resolved_carries_actor_and_target():
    r = _setup()
    out = r.can_use(
        actor_id="alice", cmd_id="fire_iii",
        actor_mp=100, actor_tp=0,
        actor_action_gated=False,
        target_id="goblin", target_alive=True,
    )
    assert out.command.actor_id == "alice"
    assert out.command.target_id == "goblin"


def test_clear_cooldowns():
    r = _setup()
    r.mark_used(actor_id="alice", cmd_id="fire_iii", used_at=100)
    r.mark_used(actor_id="alice", cmd_id="provoke", used_at=100)
    out = r.clear_cooldowns(actor_id="alice")
    assert out == 2


def test_mark_unknown_command_blocked():
    r = TurnCommandResolver()
    out = r.mark_used(
        actor_id="alice", cmd_id="ghost", used_at=100,
    )
    assert out is False


def test_five_command_kinds():
    assert len(list(CommandKind)) == 5


def test_rejection_reasons():
    # NONE + 8 reject reasons
    assert len(list(RejectReason)) == 9
