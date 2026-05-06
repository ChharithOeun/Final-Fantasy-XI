"""Turn command resolver — menu pick → resolved action.

The bridge between "player clicked Magic > Black Magic > Fire III"
in the menu and the action_queue that actually fires the spell
on their next turn slot. This module validates everything that
*could* stop the command from being valid right now:

    - target alive and in range?
    - enough MP / TP / ammo?
    - command on cooldown?
    - action gate (silenced for spells, amnesia for JAs)?

If all checks pass, returns a ResolvedCommand the action_queue
can consume. If any fail, returns the specific reason — the
menu UI surfaces this as a chat-bar message ("Out of MP." /
"Target out of range." / "You cannot cast at this time.").

The resolver is deliberately deterministic — no random rolls —
so the player's menu always tells the truth about whether
the action will go through. That predictability is the heart
of menu-driven combat.

Public surface
--------------
    CommandKind enum (SPELL/JOB_ABILITY/WEAPON_SKILL/ITEM/ATTACK)
    ResolvedCommand dataclass (frozen)
    RejectReason enum
    ResolveResult dataclass (frozen)
    TurnCommandResolver
        .register_command(cmd_id, kind, mp_cost, tp_cost,
                          requires_target, range_yalms,
                          cooldown_seconds) -> bool
        .can_use(actor_id, cmd_id, ...) -> ResolveResult
        .mark_used(actor_id, cmd_id, used_at) -> bool
        .clear_cooldowns(actor_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CommandKind(str, enum.Enum):
    SPELL = "spell"
    JOB_ABILITY = "job_ability"
    WEAPON_SKILL = "weapon_skill"
    ITEM = "item"
    ATTACK = "attack"


class RejectReason(str, enum.Enum):
    NONE = "none"
    UNKNOWN_COMMAND = "unknown_command"
    NO_TARGET = "no_target"
    TARGET_DEAD = "target_dead"
    OUT_OF_RANGE = "out_of_range"
    INSUFFICIENT_MP = "insufficient_mp"
    INSUFFICIENT_TP = "insufficient_tp"
    ON_COOLDOWN = "on_cooldown"
    ACTION_GATED = "action_gated"   # silenced/amnesia/etc


@dataclasses.dataclass(frozen=True)
class CommandSpec:
    cmd_id: str
    kind: CommandKind
    mp_cost: int
    tp_cost: int
    requires_target: bool
    range_yalms: float
    cooldown_seconds: int


@dataclasses.dataclass(frozen=True)
class ResolvedCommand:
    cmd_id: str
    kind: CommandKind
    actor_id: str
    target_id: str       # "" if no target
    mp_paid: int
    tp_paid: int


@dataclasses.dataclass(frozen=True)
class ResolveResult:
    success: bool
    reason: RejectReason
    command: t.Optional[ResolvedCommand]


# Per-actor per-command last-used timestamp (for cooldowns).
# Cooldowns are global per command for simplicity here;
# more elaborate spell recast vs JA timer logic lives in
# spell_casting / job_abilities modules.


@dataclasses.dataclass
class TurnCommandResolver:
    _commands: dict[str, CommandSpec] = dataclasses.field(
        default_factory=dict,
    )
    _last_used: dict[tuple[str, str], int] = dataclasses.field(
        default_factory=dict,
    )

    def register_command(
        self, *, cmd_id: str, kind: CommandKind,
        mp_cost: int = 0, tp_cost: int = 0,
        requires_target: bool = True,
        range_yalms: float = 21.0,
        cooldown_seconds: int = 0,
    ) -> bool:
        if not cmd_id:
            return False
        if cmd_id in self._commands:
            return False
        if mp_cost < 0 or tp_cost < 0 or cooldown_seconds < 0:
            return False
        self._commands[cmd_id] = CommandSpec(
            cmd_id=cmd_id, kind=kind,
            mp_cost=mp_cost, tp_cost=tp_cost,
            requires_target=requires_target,
            range_yalms=range_yalms,
            cooldown_seconds=cooldown_seconds,
        )
        return True

    def can_use(
        self, *, actor_id: str, cmd_id: str,
        actor_mp: int, actor_tp: int,
        actor_action_gated: bool,
        target_id: str = "",
        target_alive: bool = True,
        distance_yalms: float = 0.0,
        now: int = 0,
    ) -> ResolveResult:
        spec = self._commands.get(cmd_id)
        if spec is None:
            return ResolveResult(
                success=False,
                reason=RejectReason.UNKNOWN_COMMAND,
                command=None,
            )
        if actor_action_gated:
            return ResolveResult(
                success=False,
                reason=RejectReason.ACTION_GATED,
                command=None,
            )
        if spec.requires_target:
            if not target_id:
                return ResolveResult(
                    success=False,
                    reason=RejectReason.NO_TARGET,
                    command=None,
                )
            if not target_alive:
                return ResolveResult(
                    success=False,
                    reason=RejectReason.TARGET_DEAD,
                    command=None,
                )
            if distance_yalms > spec.range_yalms:
                return ResolveResult(
                    success=False,
                    reason=RejectReason.OUT_OF_RANGE,
                    command=None,
                )
        if actor_mp < spec.mp_cost:
            return ResolveResult(
                success=False,
                reason=RejectReason.INSUFFICIENT_MP,
                command=None,
            )
        if actor_tp < spec.tp_cost:
            return ResolveResult(
                success=False,
                reason=RejectReason.INSUFFICIENT_TP,
                command=None,
            )
        if spec.cooldown_seconds > 0:
            last = self._last_used.get((actor_id, cmd_id), -1)
            if last >= 0 and now - last < spec.cooldown_seconds:
                return ResolveResult(
                    success=False,
                    reason=RejectReason.ON_COOLDOWN,
                    command=None,
                )
        return ResolveResult(
            success=True, reason=RejectReason.NONE,
            command=ResolvedCommand(
                cmd_id=cmd_id, kind=spec.kind,
                actor_id=actor_id,
                target_id=target_id if spec.requires_target else "",
                mp_paid=spec.mp_cost,
                tp_paid=spec.tp_cost,
            ),
        )

    def mark_used(
        self, *, actor_id: str, cmd_id: str, used_at: int,
    ) -> bool:
        if cmd_id not in self._commands:
            return False
        self._last_used[(actor_id, cmd_id)] = used_at
        return True

    def clear_cooldowns(self, *, actor_id: str) -> int:
        keys = [k for k in self._last_used if k[0] == actor_id]
        for k in keys:
            del self._last_used[k]
        return len(keys)

    def total_commands(self) -> int:
        return len(self._commands)


__all__ = [
    "CommandKind", "RejectReason", "CommandSpec",
    "ResolvedCommand", "ResolveResult",
    "TurnCommandResolver",
]
