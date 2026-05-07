"""Strategy step DSL — structured fight-plan steps.

The published guide body is freeform prose, but for the
in-encounter UI overlay we need structured steps the
client can render as a checklist. This module defines
the step grammar and validates step lists for correctness
before they're stored.

Step kinds:
    PHASE       a labelled section ("Phase 1: 100% to 75%")
    CALLOUT     "When boss casts Aerial Blast, hide
                behind pillar"
    POSITION    "stand 14 yalms behind boss"
    REQUIRED    a required gear/spell/buff/JA/SP listed
                up front (e.g., "Reraise scroll")
    COOLDOWN    "Pop Hundred Fists at 50%"
    INTERRUPT   "Stun Bind every cast"
    EMERGENCY   "If healer dies, /panic with Reraise"

Each step has:
    kind          one of the above
    order         monotonic int starting at 1
    text          the displayed line, ≤ 140 chars
    trigger_pct   optional HP% trigger (0-100); used for
                  PHASE/COOLDOWN/EMERGENCY when relevant
    required_at   optional "before-pull" flag for REQUIRED

A valid step list:
    - has order monotonically ascending starting at 1
    - has at least one PHASE step
    - has at most 100 steps total (UI sanity)
    - has trigger_pct in [0,100] when present
    - has text non-empty and ≤ 140 chars

Public surface
--------------
    StepKind enum
    StrategyStep dataclass (frozen)
    ValidationResult dataclass (frozen)
    StrategyStepDsl
        .build(steps) -> ValidationResult
        .filter_kind(steps, kind) -> list[StrategyStep]
        .next_step(steps, current_hp_pct) -> Optional[StrategyStep]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MAX_STEPS = 100
_MAX_TEXT_LEN = 140


class StepKind(str, enum.Enum):
    PHASE = "phase"
    CALLOUT = "callout"
    POSITION = "position"
    REQUIRED = "required"
    COOLDOWN = "cooldown"
    INTERRUPT = "interrupt"
    EMERGENCY = "emergency"


@dataclasses.dataclass(frozen=True)
class StrategyStep:
    kind: StepKind
    order: int
    text: str
    trigger_pct: int = -1     # -1 means no trigger
    required_at: bool = False


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str
    error_at_step: int   # 0 if global error, else step.order


@dataclasses.dataclass
class StrategyStepDsl:

    def build(
        self, *, steps: list[StrategyStep],
    ) -> ValidationResult:
        if not steps:
            return ValidationResult(
                valid=False, reason="empty_steps",
                error_at_step=0,
            )
        if len(steps) > _MAX_STEPS:
            return ValidationResult(
                valid=False, reason="too_many_steps",
                error_at_step=0,
            )
        # Order must be monotonic from 1
        expected = 1
        seen_phase = False
        for st in steps:
            if st.order != expected:
                return ValidationResult(
                    valid=False,
                    reason="order_must_be_monotonic_from_1",
                    error_at_step=st.order,
                )
            expected += 1
            text = st.text.strip()
            if not text:
                return ValidationResult(
                    valid=False, reason="text_required",
                    error_at_step=st.order,
                )
            if len(text) > _MAX_TEXT_LEN:
                return ValidationResult(
                    valid=False, reason="text_too_long",
                    error_at_step=st.order,
                )
            if st.trigger_pct != -1:
                if st.trigger_pct < 0 or st.trigger_pct > 100:
                    return ValidationResult(
                        valid=False,
                        reason="trigger_pct_out_of_range",
                        error_at_step=st.order,
                    )
            if st.kind == StepKind.PHASE:
                seen_phase = True
        if not seen_phase:
            return ValidationResult(
                valid=False, reason="no_phase_step",
                error_at_step=0,
            )
        return ValidationResult(
            valid=True, reason="", error_at_step=0,
        )

    @staticmethod
    def filter_kind(
        *, steps: list[StrategyStep], kind: StepKind,
    ) -> list[StrategyStep]:
        return [s for s in steps if s.kind == kind]

    @staticmethod
    def next_step(
        *, steps: list[StrategyStep],
        current_hp_pct: int,
    ) -> t.Optional[StrategyStep]:
        """Return the next CALLOUT/COOLDOWN/EMERGENCY/
        INTERRUPT step whose trigger_pct >= current_hp_pct
        (boss is at this HP or higher, the step's pending).
        Steps without trigger_pct are skipped — they're
        always-on, the UI shows them statically.

        Skips PHASE/POSITION/REQUIRED steps — those are
        rendered separately in the overlay header."""
        skip_kinds = {
            StepKind.PHASE, StepKind.POSITION,
            StepKind.REQUIRED,
        }
        candidates = [
            s for s in steps
            if s.kind not in skip_kinds
            and s.trigger_pct != -1
            and s.trigger_pct >= current_hp_pct
        ]
        if not candidates:
            return None
        # Lowest trigger_pct first (closest to current HP)
        candidates.sort(key=lambda s: s.trigger_pct)
        return candidates[0]


__all__ = [
    "StepKind", "StrategyStep", "ValidationResult",
    "StrategyStepDsl",
]
