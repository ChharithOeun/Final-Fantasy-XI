"""Animation cancellation — the modern-action-RPG signature feature.

Per COMBAT_TEMPO.md three cancel rules:
    - Cancel auto-attack startup by initiating a Weapon Skill or
      moving (commits to whatever you canceled into).
    - Cancel WS recovery by moving (lose the WS bonus damage but
      you're not stuck mid-pose).
    - Cancel spell mid-cast by moving (interrupts the spell, like
      always - but you regain control instantly, no recovery
      animation).

'This single feature is what makes combat feel good. Player input
has agency.'

The combat pipeline calls resolve_cancel(...) when the player
issues an intent during an action's animation. The returned
CancelResult tells the pipeline whether the cancel landed, what
the new committed state is, and what (if anything) was lost.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ActionPhase(str, enum.Enum):
    """Where in an action's lifecycle we are when intent arrives."""
    AUTO_ATTACK_STARTUP = "auto_attack_startup"
    AUTO_ATTACK_ACTIVE = "auto_attack_active"
    WS_STARTUP = "ws_startup"
    WS_ACTIVE = "ws_active"             # dealing damage; can't cancel
    WS_RECOVERY = "ws_recovery"
    SPELL_CAST = "spell_cast"
    SPELL_RESOLVE = "spell_resolve"     # spell fired; can't unfire


class CancelIntent(str, enum.Enum):
    """What the player asked to do mid-action."""
    INITIATE_WS = "initiate_ws"
    MOVE = "move"
    INITIATE_SPELL = "initiate_spell"


class CancelOutcome(str, enum.Enum):
    """What happened to the player's input."""
    COMMITTED_TO_NEW = "committed_to_new"   # canceled current,
                                                # started new action
    LOST_BONUS = "lost_bonus"               # canceled but paid a tax
    INTERRUPTED = "interrupted"             # canceled, nothing replaced
    REJECTED = "rejected"                   # cancel not legal here


@dataclasses.dataclass(frozen=True)
class CancelResult:
    """Pipeline output after one cancel resolution."""
    outcome: CancelOutcome
    new_phase: t.Optional[ActionPhase]
    bonus_lost: bool
    reason: str


def resolve_cancel(*,
                      phase: ActionPhase,
                      intent: CancelIntent) -> CancelResult:
    """Resolve a cancel intent against the action's current phase.

    The doc allows three specific paths; everything else is rejected
    so the player doesn't accidentally drop a high-commit action
    they meant to keep.
    """
    # Rule 1: auto-attack startup -> WS or move.
    if phase == ActionPhase.AUTO_ATTACK_STARTUP:
        if intent == CancelIntent.INITIATE_WS:
            return CancelResult(
                outcome=CancelOutcome.COMMITTED_TO_NEW,
                new_phase=ActionPhase.WS_STARTUP,
                bonus_lost=False,
                reason=("auto-attack startup canceled into WS; "
                          "swing wasted"),
            )
        if intent == CancelIntent.MOVE:
            return CancelResult(
                outcome=CancelOutcome.COMMITTED_TO_NEW,
                new_phase=None,
                bonus_lost=False,
                reason="auto-attack startup canceled by movement",
            )
        if intent == CancelIntent.INITIATE_SPELL:
            return CancelResult(
                outcome=CancelOutcome.COMMITTED_TO_NEW,
                new_phase=ActionPhase.SPELL_CAST,
                bonus_lost=False,
                reason="auto-attack startup canceled into spell cast",
            )

    # Rule 2: WS recovery -> move (lose the bonus).
    if phase == ActionPhase.WS_RECOVERY and intent == CancelIntent.MOVE:
        return CancelResult(
            outcome=CancelOutcome.LOST_BONUS,
            new_phase=None,
            bonus_lost=True,
            reason="WS recovery canceled by movement; bonus lost",
        )

    # Rule 3: spell mid-cast -> move (interrupted).
    if phase == ActionPhase.SPELL_CAST and intent == CancelIntent.MOVE:
        return CancelResult(
            outcome=CancelOutcome.INTERRUPTED,
            new_phase=None,
            bonus_lost=False,
            reason=("spell cast canceled by movement; instant control "
                      "regained, no recovery animation"),
        )

    # Unrecognized phase/intent pair — reject. Conservative default
    # protects high-commit phases (WS_ACTIVE, SPELL_RESOLVE).
    return CancelResult(
        outcome=CancelOutcome.REJECTED,
        new_phase=phase,
        bonus_lost=False,
        reason=f"cancel of {phase.value} via {intent.value} not allowed",
    )


def can_cancel(phase: ActionPhase) -> bool:
    """Is this phase cancelable by ANY of the doc's rules?"""
    return phase in (ActionPhase.AUTO_ATTACK_STARTUP,
                       ActionPhase.WS_RECOVERY,
                       ActionPhase.SPELL_CAST)
