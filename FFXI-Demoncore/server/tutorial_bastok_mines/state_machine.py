"""Tutorial state machine — per-character progress through the 7 gates.

One TutorialSession per new character. The orchestrator pumps it
events; the session decides whether the current gate is now done,
whether to advance, and whether the whole tutorial has aged out.

Doc: 'These tags are inert except during the first 90 minutes of
a new character. After that they age out (or the player has
already moved past them).'
"""
from __future__ import annotations

import dataclasses
import typing as t

from .gates import (
    CHAIN_GATE_CLOSES_REQUIRED,
    GATE_TABLE,
    TUTORIAL_AGE_OUT_MINUTES,
    GateBeat,
    TutorialGate,
    first_gate,
    gate_after,
    get_beat,
)


class TutorialPhase(str):
    """String constants describing the session's outer state."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    AGED_OUT = "aged_out"
    ABANDONED = "abandoned"


@dataclasses.dataclass
class TutorialSession:
    """Per-character tutorial state.

    A session has one of four lifecycle states:
        NOT_STARTED  — created but the character hasn't entered
                          Bastok Mines yet
        IN_PROGRESS  — currently working through gates
        COMPLETED    — all 7 gates cleared
        AGED_OUT     — 90 minutes elapsed before completion
        ABANDONED    — explicitly left tutorial (relog after
                          90 min, switched to non-Bastok start, etc.)
    """
    actor_id: str
    job: str = "WAR"
    started_at_minutes: float = 0.0
    current_gate: t.Optional[TutorialGate] = None
    completed_gates: list[TutorialGate] = dataclasses.field(
        default_factory=list)
    completed_gate_minutes: dict[TutorialGate, float] = (
        dataclasses.field(default_factory=dict))
    chain_closes_logged: int = 0
    phase: str = TutorialPhase.NOT_STARTED

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, *, now_minutes: float) -> None:
        """Player has entered Bastok Mines for the first time."""
        if self.phase != TutorialPhase.NOT_STARTED:
            return
        self.started_at_minutes = now_minutes
        self.current_gate = first_gate()
        self.phase = TutorialPhase.IN_PROGRESS

    def abandon(self) -> None:
        """Player explicitly left or chose a non-Bastok start."""
        self.phase = TutorialPhase.ABANDONED
        self.current_gate = None

    # ------------------------------------------------------------------
    # Aging
    # ------------------------------------------------------------------

    def elapsed_minutes(self, *, now_minutes: float) -> float:
        if self.phase == TutorialPhase.NOT_STARTED:
            return 0.0
        return max(0.0, now_minutes - self.started_at_minutes)

    def is_aged_out(self, *, now_minutes: float) -> bool:
        if self.phase in (TutorialPhase.NOT_STARTED,
                              TutorialPhase.COMPLETED,
                              TutorialPhase.ABANDONED):
            return False
        return self.elapsed_minutes(now_minutes=now_minutes) > TUTORIAL_AGE_OUT_MINUTES

    def maybe_age_out(self, *, now_minutes: float) -> bool:
        """Mark the session aged out if the 90-min window passed.
        Returns True if a state change occurred."""
        if self.phase != TutorialPhase.IN_PROGRESS:
            return False
        if self.is_aged_out(now_minutes=now_minutes):
            self.phase = TutorialPhase.AGED_OUT
            self.current_gate = None
            return True
        return False

    # ------------------------------------------------------------------
    # Gate advancement
    # ------------------------------------------------------------------

    def has_completed(self, gate: TutorialGate) -> bool:
        return gate in self.completed_gates

    def current_beat(self) -> t.Optional[GateBeat]:
        if self.current_gate is None:
            return None
        return get_beat(self.current_gate)

    def log_chain_close(self) -> int:
        """Record a successful chain close inside the CHAIN gate.

        Returns the running total. Caller decides whether to
        complete the gate based on CHAIN_GATE_CLOSES_REQUIRED.
        """
        if self.current_gate != TutorialGate.CHAIN:
            return self.chain_closes_logged
        self.chain_closes_logged += 1
        return self.chain_closes_logged

    def chain_gate_satisfied(self) -> bool:
        return self.chain_closes_logged >= CHAIN_GATE_CLOSES_REQUIRED

    def complete_current_gate(self, *, now_minutes: float) -> bool:
        """Mark the current gate complete and advance.

        Returns True if a transition occurred. False if the session
        wasn't on a gate (already aged out / abandoned / completed)
        or if a precondition (e.g. CHAIN closes_required) wasn't met.
        """
        if self.phase != TutorialPhase.IN_PROGRESS:
            return False
        if self.current_gate is None:
            return False

        # Special case: CHAIN gate requires N closes before
        # complete is allowed.
        if (self.current_gate == TutorialGate.CHAIN
                and not self.chain_gate_satisfied()):
            return False

        gate = self.current_gate
        if gate not in self.completed_gates:
            self.completed_gates.append(gate)
            self.completed_gate_minutes[gate] = now_minutes

        nxt = gate_after(gate)
        if nxt is None:
            # Last gate cleared.
            self.current_gate = None
            self.phase = TutorialPhase.COMPLETED
        else:
            self.current_gate = nxt
        return True

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def remaining_gates(self) -> list[TutorialGate]:
        if self.phase != TutorialPhase.IN_PROGRESS:
            return []
        seq = [b.gate for b in GATE_TABLE]
        if self.current_gate is None:
            return []
        idx = seq.index(self.current_gate)
        return seq[idx:]

    def progress_summary(self) -> dict[str, t.Any]:
        return {
            "actor_id": self.actor_id,
            "job": self.job,
            "phase": self.phase,
            "current_gate": (self.current_gate.name
                                if self.current_gate else None),
            "completed_gates": [g.name for g in self.completed_gates],
            "completed_count": len(self.completed_gates),
            "remaining_count": len(self.remaining_gates()),
            "chain_closes_logged": self.chain_closes_logged,
        }
