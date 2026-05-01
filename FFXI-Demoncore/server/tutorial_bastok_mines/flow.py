"""TutorialFlow — orchestrator hook that dispatches events to gates.

The orchestrator pumps player events into TutorialFlow.on_event(...).
The flow looks up the current gate, decides whether the event
satisfies the gate's completion_event, and advances the session
when it does.

For the CHAIN gate (which needs N closes before completion), the
flow accumulates closes via session.log_chain_close() and only
calls complete_current_gate() once the threshold is met.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .gates import (
    GATE_TABLE,
    GateBeat,
    TutorialGate,
    all_layered_scene_tags,
    get_beat,
)
from .reveal_skill_pick import RevealSkill, pick_reveal_skill
from .state_machine import TutorialPhase, TutorialSession


@dataclasses.dataclass(frozen=True)
class FlowEvent:
    """One event emitted by the orchestrator into the tutorial flow."""
    event_kind: str          # matches GateBeat.completion_event ideally
    actor_id: str
    at_minutes: float
    payload: dict[str, t.Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class FlowResult:
    """The flow's response to an event."""
    advanced: bool                     # gate_completed_this_event
    aged_out: bool                     # tutorial expired this tick
    new_gate: t.Optional[TutorialGate]
    new_phase: str
    note: str = ""


class TutorialFlow:
    """Glue layer between the orchestrator and the tutorial state."""

    def __init__(self, session: TutorialSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def reveal_skill_for_player(self) -> RevealSkill:
        """Resolve which reveal skill the player uses at gate 4."""
        return pick_reveal_skill(self.session.job)

    def begin(self, *, now_minutes: float) -> None:
        """Start the tutorial. Idempotent if already started."""
        self.session.start(now_minutes=now_minutes)

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def on_event(self, event: FlowEvent) -> FlowResult:
        """Dispatch a player-event into the gate machinery."""
        # Always tick the age-out check first.
        aged = self.session.maybe_age_out(now_minutes=event.at_minutes)
        if aged:
            return FlowResult(
                advanced=False, aged_out=True,
                new_gate=None,
                new_phase=self.session.phase,
                note="aged out before event",
            )
        if self.session.phase != TutorialPhase.IN_PROGRESS:
            return FlowResult(
                advanced=False, aged_out=False,
                new_gate=None,
                new_phase=self.session.phase,
                note="session not in progress",
            )

        beat = self.session.current_beat()
        if beat is None:
            return FlowResult(
                advanced=False, aged_out=False, new_gate=None,
                new_phase=self.session.phase,
                note="no current gate",
            )

        # CHAIN gate: count closes; only advance once threshold met.
        if beat.gate == TutorialGate.CHAIN:
            if event.event_kind == "chain_closed":
                self.session.log_chain_close()
                if self.session.chain_gate_satisfied():
                    advanced = self.session.complete_current_gate(
                        now_minutes=event.at_minutes)
                    return FlowResult(
                        advanced=advanced, aged_out=False,
                        new_gate=self.session.current_gate,
                        new_phase=self.session.phase,
                        note=("chain gate satisfied; "
                              f"closes_logged="
                              f"{self.session.chain_closes_logged}"),
                    )
                return FlowResult(
                    advanced=False, aged_out=False,
                    new_gate=beat.gate,
                    new_phase=self.session.phase,
                    note=("chain close logged; "
                          f"need more "
                          f"({self.session.chain_closes_logged} so far)"),
                )
            # Some other event arriving inside CHAIN gate is ignored.
            return FlowResult(
                advanced=False, aged_out=False,
                new_gate=beat.gate,
                new_phase=self.session.phase,
                note=f"ignored {event.event_kind} in CHAIN gate",
            )

        # Non-chain gates: direct match advance.
        if event.event_kind == beat.completion_event:
            advanced = self.session.complete_current_gate(
                now_minutes=event.at_minutes)
            return FlowResult(
                advanced=advanced, aged_out=False,
                new_gate=self.session.current_gate,
                new_phase=self.session.phase,
                note=f"completed {beat.gate.name}",
            )

        return FlowResult(
            advanced=False, aged_out=False,
            new_gate=beat.gate,
            new_phase=self.session.phase,
            note=f"event {event.event_kind} not for current gate",
        )

    # ------------------------------------------------------------------
    # Layered-scene hooks
    # ------------------------------------------------------------------

    def active_layered_scene_tags(self) -> tuple[str, ...]:
        """Return the gate tags that should be present on tutorial NPCs.

        While IN_PROGRESS we emit only the current gate's tag (the
        layered-scene composer attaches it to the gate's NPC). When
        the session is COMPLETED / AGED_OUT / ABANDONED we emit no
        tags — per the doc 'these tags are inert except during the
        first 90 minutes'.
        """
        if (self.session.phase != TutorialPhase.IN_PROGRESS
                or self.session.current_gate is None):
            return ()
        return (get_beat(self.session.current_gate).layered_scene_tag,)

    @staticmethod
    def all_possible_tags() -> tuple[str, ...]:
        """For documentation / scene-composer manifest."""
        return all_layered_scene_tags()

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def is_completed(self) -> bool:
        return self.session.phase == TutorialPhase.COMPLETED

    def is_aged_out(self) -> bool:
        return self.session.phase == TutorialPhase.AGED_OUT

    def progress_summary(self) -> dict[str, t.Any]:
        return self.session.progress_summary()
