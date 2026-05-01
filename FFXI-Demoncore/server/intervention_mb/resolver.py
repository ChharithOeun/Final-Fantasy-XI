"""Intervention resolver — the heart of the save-the-wipe pipeline.

Per INTERVENTION_MB.md (the damage formula section):

    if friendly_intervention_spell_lands_in_window:
        enemy_mb_damage *= 0.0   # cancelled entirely
        amplify_effect(spell, 3.0 or 5.0)
        if cure family:
            apply Regen V 30s (twice on Light)
        elif na/erase:
            apply Immunity 30s (60s + party cleanse on Light)
        unlock dual_cast for spell family

This module composes window + amplification + dual_cast + callouts
into one deterministic resolve_intervention call. The combat
pipeline calls this when a friendly spell LANDS during an open
window.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .amplification import (
    SpellFamily,
    amplification_for,
    apply_amplification,
    is_eligible,
)
from .callouts import Callout, callout_for, failure_grunt
from .dual_cast import (
    DUAL_CAST_DURATION_SECONDS,
    DualCastBuff,
    DualCastBuffId,
    DualCastManager,
    FAMILY_TO_BUFF,
)
from .window import InterventionWindow, lands_in_window


# Doc: 'apply_status(target, "Regen V", duration=30s)'.
INTERVENTION_REGEN_DURATION_S: float = 30.0
INTERVENTION_IMMUNITY_DURATION_S: float = 30.0
LIGHT_IMMUNITY_DURATION_S: float = 60.0


@dataclasses.dataclass(frozen=True)
class InterventionResult:
    """The pipeline's output."""
    succeeded: bool
    mb_damage_cancelled: int          # 0 if not succeeded, otherwise
                                          # = window.predicted_mb_damage
    amplified_effect: float           # base * 3 or base * 5 (or 0)
    regen_applied_seconds: float      # 0 if not cure family
    immunity_applied_seconds: float   # 0 if not na/erase
    party_cleanse_applied: bool       # only on Light + na/erase
    dual_cast_unlocked: t.Optional[DualCastBuffId]
    dual_cast_duration: float
    callout: Callout
    reason: str = ""


def _spell_label(family: SpellFamily, *, label_hint: str = "") -> str:
    if label_hint:
        return label_hint
    return family.value.title()


def resolve_intervention(*,
                              window: InterventionWindow,
                              family: SpellFamily,
                              base_effect: float,
                              caster_id: str,
                              land_time: float,
                              dual_cast_manager: DualCastManager,
                              spell_label: str = "",
                              ) -> InterventionResult:
    """Run the complete intervention path.

    Returns an InterventionResult. The caller is responsible for
    actually pushing the damage cancellation + status effects to
    the combat pipeline; this function decides what happens.
    """
    # Eligibility gate: direct-damage spells use the offensive MB
    # path, not the intervention path. Reject early so the call
    # site isn't ambiguous.
    if not is_eligible(family):
        return InterventionResult(
            succeeded=False,
            mb_damage_cancelled=0,
            amplified_effect=base_effect,
            regen_applied_seconds=0.0,
            immunity_applied_seconds=0.0,
            party_cleanse_applied=False,
            dual_cast_unlocked=None,
            dual_cast_duration=0.0,
            callout=failure_grunt(family),
            reason="direct-damage spells use offensive MB pipeline",
        )

    # Window gate: did the spell land inside the 3-second window?
    if not lands_in_window(window, land_time=land_time):
        return InterventionResult(
            succeeded=False,
            mb_damage_cancelled=0,
            amplified_effect=base_effect,
            regen_applied_seconds=0.0,
            immunity_applied_seconds=0.0,
            party_cleanse_applied=False,
            dual_cast_unlocked=None,
            dual_cast_duration=0.0,
            callout=failure_grunt(family),
            reason=("spell landed outside the 3-second intervention "
                      "window"),
        )

    light = window.is_light()
    amp_effect = apply_amplification(
        family=family, base_effect=base_effect,
        light_bonus=light,
    )

    # Per-family follow-on effects.
    regen_seconds = 0.0
    immunity_seconds = 0.0
    party_cleanse = False
    if family in (SpellFamily.CURE, SpellFamily.CURAGA):
        regen_seconds = INTERVENTION_REGEN_DURATION_S
        if light:
            # Doc: 'apply Regen V 30s' twice on Light => effective
            # 60s sustain. We model as a single 60s entry since
            # dispel rules don't differentiate stacks of the same
            # buff.
            regen_seconds = INTERVENTION_REGEN_DURATION_S * 2
    elif family in (SpellFamily.NA_SPELL, SpellFamily.ERASE):
        immunity_seconds = INTERVENTION_IMMUNITY_DURATION_S
        if light:
            immunity_seconds = LIGHT_IMMUNITY_DURATION_S
            party_cleanse = True

    # Unlock dual-cast / luopan-radius / enmity-spike for 30s.
    buff: t.Optional[DualCastBuff] = None
    if family in FAMILY_TO_BUFF:
        buff = dual_cast_manager.grant(
            caster_id=caster_id, family=family, now=land_time,
        )

    callout = callout_for(
        family=family, light_bonus=light,
        spell_label=_spell_label(family, label_hint=spell_label),
    )

    return InterventionResult(
        succeeded=True,
        mb_damage_cancelled=window.predicted_mb_damage,
        amplified_effect=amp_effect,
        regen_applied_seconds=regen_seconds,
        immunity_applied_seconds=immunity_seconds,
        party_cleanse_applied=party_cleanse,
        dual_cast_unlocked=buff.buff_id if buff else None,
        dual_cast_duration=DUAL_CAST_DURATION_SECONDS if buff else 0.0,
        callout=callout,
        reason=("intervention succeeded; "
                  f"{'light bonus 5x' if light else 'base 3x'}"),
    )
