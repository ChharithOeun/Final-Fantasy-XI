"""Slow-action carve-outs — the things that intentionally DON'T speed up.

Per COMBAT_TEMPO.md the principle is:
    'action that's about reflex gets faster;
     action that's about commitment stays slow.'

Six action ids retain their OG weight even though everything around
them got halved:

    raise           weighty death recovery (especially with permadeath)
    tractor         same
    reraise         same
    teleport        long cast (8-10s), interruptable; travel still has
                       friction
    boss_enrage     boss fights have *length* on purpose; marathon
                       energy
    crafting_synth  meditative; explicitly not sped up

A 7th tier-2 carve-out — keystone spells — is implemented as a flag
on individual recasts (the recast-halver passes a `keystone=True`
hint to skip).
"""
from __future__ import annotations

import dataclasses
import enum


class SlowActionId(str, enum.Enum):
    """The six carve-outs the doc names."""
    RAISE = "raise"
    TRACTOR = "tractor"
    RERAISE = "reraise"
    TELEPORT = "teleport"
    BOSS_ENRAGE = "boss_enrage"
    CRAFTING_SYNTH = "crafting_synth"


@dataclasses.dataclass(frozen=True)
class SlowActionRule:
    """One slow-action carve-out."""
    action: SlowActionId
    cast_time_seconds: float        # 0 = no fixed cast time (e.g. enrage)
    interruptible: bool
    skip_recast_halve: bool         # True if global recast halve passes
                                       # this action by
    rationale: str


SLOW_ACTION_RULES: dict[SlowActionId, SlowActionRule] = {
    SlowActionId.RAISE: SlowActionRule(
        action=SlowActionId.RAISE,
        cast_time_seconds=8.0,
        interruptible=True,
        skip_recast_halve=True,
        rationale=("weighty death recovery; permadeath world makes "
                      "this commitment, not reflex"),
    ),
    SlowActionId.TRACTOR: SlowActionRule(
        action=SlowActionId.TRACTOR,
        cast_time_seconds=3.0,
        interruptible=True,
        skip_recast_halve=True,
        rationale="death-recovery class; same weight as Raise",
    ),
    SlowActionId.RERAISE: SlowActionRule(
        action=SlowActionId.RERAISE,
        cast_time_seconds=12.0,
        interruptible=True,
        skip_recast_halve=True,
        rationale="pre-death insurance; the cost stays heavy",
    ),
    SlowActionId.TELEPORT: SlowActionRule(
        action=SlowActionId.TELEPORT,
        cast_time_seconds=10.0,
        interruptible=True,
        skip_recast_halve=True,
        rationale="travel friction is part of the world",
    ),
    SlowActionId.BOSS_ENRAGE: SlowActionRule(
        action=SlowActionId.BOSS_ENRAGE,
        cast_time_seconds=0.0,           # no cast; this is a phase-fire
        interruptible=False,
        skip_recast_halve=True,
        rationale="boss fights have length on purpose; marathon energy",
    ),
    SlowActionId.CRAFTING_SYNTH: SlowActionRule(
        action=SlowActionId.CRAFTING_SYNTH,
        cast_time_seconds=4.0,
        interruptible=False,
        skip_recast_halve=True,
        rationale="crafting is meditative; we don't speed it up",
    ),
}


def is_slow_action(action_id: str) -> bool:
    """Does this action_id retain OG cadence?"""
    try:
        SlowActionId(action_id)
        return True
    except ValueError:
        return False


def get_rule(action_id: str) -> SlowActionRule:
    """Look up the rule. Raises ValueError if action_id isn't a
    slow-action carve-out."""
    return SLOW_ACTION_RULES[SlowActionId(action_id)]


def should_halve_recast(action_id: str, *, keystone: bool = False) -> bool:
    """Decision the recast-halver pipeline asks of every action.

    Slow actions and keystone spells skip the halve; everything else
    gets cut in half.
    """
    if keystone:
        return False
    if is_slow_action(action_id):
        return False
    return True
