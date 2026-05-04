"""Shadowlands endgame quests — three-stage proof chain.

The three quests a player must complete (on the hume side)
before the beastman race option opens. They're framed as the
PROOF a Vana'diel adventurer offers the beastman elders that
they're worthy to wear the other side's skin:

  1. THE_FIRST_PROOF / Mercy Without Eyes
     Spare a beastman whose death you've been asked to deliver.
     The beastman_unlock_gate notes the completion.

  2. THE_SECOND_PROOF / The Empty Crown
     Refuse a king's sanction; walk away from the gold and
     the title.

  3. THE_THIRD_PROOF / Crossing the Veil
     Survive a vigil at one of the four beastman shrines and
     return without word from any nation NPC.

Each quest can be ACCEPTED, then advanced through STEPS, then
COMPLETED. Completion triggers a callback into the
beastman_unlock_gate so the gate marks the account.

Public surface
--------------
    QuestId enum (string values lock the canon ids)
    StepKind enum
    QuestStep dataclass
    QuestProgress dataclass
    AcceptResult / StepResult / CompleteResult dataclasses
    ShadowlandsEndgameQuests
        .accept(player_id, quest_id, account_id)
        .advance_step(player_id, quest_id, step_kind)
        .can_complete(player_id, quest_id) -> bool
        .complete(player_id, quest_id, gate_callback)
        .progress_for(player_id, quest_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class QuestId(str, enum.Enum):
    THE_FIRST_PROOF = "shadowlands_proof_1"
    THE_SECOND_PROOF = "shadowlands_proof_2"
    THE_THIRD_PROOF = "shadowlands_proof_3"


class StepKind(str, enum.Enum):
    ACCEPT_TARGET = "accept_target"
    LOCATE_TARGET = "locate_target"
    SPARE_TARGET = "spare_target"
    REFUSE_REWARD = "refuse_reward"
    WALK_AWAY = "walk_away"
    REACH_SHRINE = "reach_shrine"
    HOLD_VIGIL = "hold_vigil"
    RETURN_QUIETLY = "return_quietly"


_REQUIRED_STEPS: dict[QuestId, tuple[StepKind, ...]] = {
    QuestId.THE_FIRST_PROOF: (
        StepKind.ACCEPT_TARGET,
        StepKind.LOCATE_TARGET,
        StepKind.SPARE_TARGET,
    ),
    QuestId.THE_SECOND_PROOF: (
        StepKind.REFUSE_REWARD,
        StepKind.WALK_AWAY,
    ),
    QuestId.THE_THIRD_PROOF: (
        StepKind.REACH_SHRINE,
        StepKind.HOLD_VIGIL,
        StepKind.RETURN_QUIETLY,
    ),
}


class QuestStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclasses.dataclass
class QuestProgress:
    player_id: str
    account_id: str
    quest_id: QuestId
    status: QuestStatus = QuestStatus.IN_PROGRESS
    completed_steps: list[StepKind] = dataclasses.field(
        default_factory=list,
    )
    accepted_at_seconds: float = 0.0
    completed_at_seconds: t.Optional[float] = None


@dataclasses.dataclass(frozen=True)
class AcceptResult:
    accepted: bool
    quest_id: QuestId
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class StepResult:
    accepted: bool
    quest_id: QuestId
    step: StepKind
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    quest_id: QuestId
    reason: t.Optional[str] = None


# Type alias for the gate callback so we don't import the
# real type (avoids a circular import; the gate calls into
# this module by id strings, and this module passes the
# completed quest_id back via callback for the account).
GateCallback = t.Callable[[str, str], bool]


@dataclasses.dataclass
class ShadowlandsEndgameQuests:
    _progress: dict[
        tuple[str, QuestId], QuestProgress,
    ] = dataclasses.field(default_factory=dict)

    def accept(
        self, *, player_id: str,
        account_id: str,
        quest_id: QuestId,
        now_seconds: float = 0.0,
    ) -> AcceptResult:
        key = (player_id, quest_id)
        if key in self._progress:
            return AcceptResult(
                False, quest_id=quest_id,
                reason="already accepted",
            )
        # Sequencing: must complete proofs in order.
        order = (
            QuestId.THE_FIRST_PROOF,
            QuestId.THE_SECOND_PROOF,
            QuestId.THE_THIRD_PROOF,
        )
        idx = order.index(quest_id)
        for prior in order[:idx]:
            prior_key = (player_id, prior)
            prior_prog = self._progress.get(prior_key)
            if (
                prior_prog is None
                or prior_prog.status != QuestStatus.COMPLETE
            ):
                return AcceptResult(
                    False, quest_id=quest_id,
                    reason=(
                        f"prior proof {prior.value}"
                        " not complete"
                    ),
                )
        self._progress[key] = QuestProgress(
            player_id=player_id,
            account_id=account_id,
            quest_id=quest_id,
            status=QuestStatus.IN_PROGRESS,
            accepted_at_seconds=now_seconds,
        )
        return AcceptResult(
            accepted=True, quest_id=quest_id,
        )

    def advance_step(
        self, *, player_id: str,
        quest_id: QuestId,
        step: StepKind,
    ) -> StepResult:
        key = (player_id, quest_id)
        prog = self._progress.get(key)
        if prog is None:
            return StepResult(
                False, quest_id=quest_id, step=step,
                reason="quest not accepted",
            )
        if prog.status != QuestStatus.IN_PROGRESS:
            return StepResult(
                False, quest_id=quest_id, step=step,
                reason="quest not in progress",
            )
        required = _REQUIRED_STEPS[quest_id]
        if step not in required:
            return StepResult(
                False, quest_id=quest_id, step=step,
                reason="step not part of this proof",
            )
        # Steps must be done in the canonical order.
        next_idx = len(prog.completed_steps)
        expected = required[next_idx]
        if step != expected:
            return StepResult(
                False, quest_id=quest_id, step=step,
                reason=(
                    f"out of order; expected "
                    f"{expected.value}"
                ),
            )
        if step in prog.completed_steps:
            return StepResult(
                False, quest_id=quest_id, step=step,
                reason="step already done",
            )
        prog.completed_steps.append(step)
        return StepResult(
            accepted=True, quest_id=quest_id, step=step,
        )

    def can_complete(
        self, *, player_id: str,
        quest_id: QuestId,
    ) -> bool:
        prog = self._progress.get((player_id, quest_id))
        if prog is None:
            return False
        if prog.status != QuestStatus.IN_PROGRESS:
            return False
        return (
            tuple(prog.completed_steps)
            == _REQUIRED_STEPS[quest_id]
        )

    def complete(
        self, *, player_id: str,
        quest_id: QuestId,
        gate_callback: t.Optional[GateCallback] = None,
        now_seconds: float = 0.0,
    ) -> CompleteResult:
        prog = self._progress.get((player_id, quest_id))
        if prog is None:
            return CompleteResult(
                False, quest_id=quest_id,
                reason="quest not accepted",
            )
        if not self.can_complete(
            player_id=player_id, quest_id=quest_id,
        ):
            return CompleteResult(
                False, quest_id=quest_id,
                reason="steps incomplete",
            )
        prog.status = QuestStatus.COMPLETE
        prog.completed_at_seconds = now_seconds
        if gate_callback is not None:
            gate_callback(prog.account_id, quest_id.value)
        return CompleteResult(
            accepted=True, quest_id=quest_id,
        )

    def progress_for(
        self, *, player_id: str,
        quest_id: QuestId,
    ) -> t.Optional[QuestProgress]:
        return self._progress.get((player_id, quest_id))

    def total_progress(self) -> int:
        return len(self._progress)


__all__ = [
    "QuestId", "StepKind", "QuestStatus",
    "QuestProgress",
    "AcceptResult", "StepResult", "CompleteResult",
    "GateCallback",
    "ShadowlandsEndgameQuests",
]
