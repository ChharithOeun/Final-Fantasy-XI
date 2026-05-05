"""Blue Chocobo mount quest — underwater mount unlock.

Underwater combat/travel uses ONLY the LIGHT_BLUE chocobo (the
water-elemental "blue chocobo" — the only color that can swim
and dive). Even owning a Light Blue chocobo doesn't grant the
underwater mount permission until the player completes the
BLUE CHOCOBO MOUNT QUEST chain:

  STAGE_GROOM       - prove the chocobo can hold its breath
                      (consume 5 brine_lozenges, demonstrate dive)
  STAGE_BREATH_BOND - establish player↔chocobo breath sharing
                      (R/EX item: bonded_seapearl)
  STAGE_DEEP_TRIAL  - dive to depth 200 yalms with the chocobo
                      and survive the journey back

Each stage is gated and produces a key item that unlocks the
next. On completion, an UNDERWATER_MOUNT permission is granted
for that specific chocobo (per-mount, not per-player).

Public surface
--------------
    QuestStage enum       NOT_STARTED / GROOM / BREATH_BOND /
                          DEEP_TRIAL / COMPLETED
    BlueChocoboMountQuest
        .start_quest(player_id, chocobo_id, color_name)
        .advance(player_id, chocobo_id, evidence)
        .can_mount_underwater(player_id, chocobo_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class QuestStage(str, enum.Enum):
    NOT_STARTED = "not_started"
    GROOM = "groom"
    BREATH_BOND = "breath_bond"
    DEEP_TRIAL = "deep_trial"
    COMPLETED = "completed"


_STAGE_ORDER: list[QuestStage] = [
    QuestStage.GROOM,
    QuestStage.BREATH_BOND,
    QuestStage.DEEP_TRIAL,
    QuestStage.COMPLETED,
]


_REQUIRED_EVIDENCE: dict[QuestStage, frozenset[str]] = {
    QuestStage.GROOM: frozenset({"brine_lozenge_x5", "dive_demo"}),
    QuestStage.BREATH_BOND: frozenset({"bonded_seapearl"}),
    QuestStage.DEEP_TRIAL: frozenset({"depth_200_survived"}),
}


@dataclasses.dataclass
class _Progress:
    chocobo_id: str
    color_name: str
    stage: QuestStage = QuestStage.NOT_STARTED


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    chocobo_id: str
    stage: QuestStage
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class AdvanceResult:
    accepted: bool
    chocobo_id: str
    stage: QuestStage
    reason: t.Optional[str] = None


def _key(player_id: str, chocobo_id: str) -> tuple[str, str]:
    return (player_id, chocobo_id)


@dataclasses.dataclass
class BlueChocoboMountQuest:
    _progress: dict[
        tuple[str, str], _Progress,
    ] = dataclasses.field(default_factory=dict)

    def start_quest(
        self, *, player_id: str,
        chocobo_id: str,
        color_name: str,
    ) -> StartResult:
        if color_name != "light_blue":
            return StartResult(
                False, chocobo_id, QuestStage.NOT_STARTED,
                reason="only light_blue chocobos qualify",
            )
        k = _key(player_id, chocobo_id)
        if k in self._progress:
            return StartResult(
                False, chocobo_id, self._progress[k].stage,
                reason="already started",
            )
        self._progress[k] = _Progress(
            chocobo_id=chocobo_id,
            color_name=color_name,
            stage=QuestStage.GROOM,
        )
        return StartResult(
            accepted=True,
            chocobo_id=chocobo_id,
            stage=QuestStage.GROOM,
        )

    def advance(
        self, *, player_id: str,
        chocobo_id: str,
        evidence: frozenset[str],
    ) -> AdvanceResult:
        prog = self._progress.get(_key(player_id, chocobo_id))
        if prog is None:
            return AdvanceResult(
                False, chocobo_id, QuestStage.NOT_STARTED,
                reason="quest not started",
            )
        if prog.stage == QuestStage.COMPLETED:
            return AdvanceResult(
                False, chocobo_id, prog.stage,
                reason="already completed",
            )
        required = _REQUIRED_EVIDENCE.get(prog.stage)
        if required is None or not required.issubset(evidence):
            return AdvanceResult(
                False, chocobo_id, prog.stage,
                reason="missing required evidence",
            )
        idx = _STAGE_ORDER.index(prog.stage)
        prog.stage = _STAGE_ORDER[idx + 1]
        return AdvanceResult(
            accepted=True,
            chocobo_id=chocobo_id,
            stage=prog.stage,
        )

    def can_mount_underwater(
        self, *, player_id: str, chocobo_id: str,
    ) -> bool:
        prog = self._progress.get(_key(player_id, chocobo_id))
        if prog is None:
            return False
        return prog.stage == QuestStage.COMPLETED

    def stage_for(
        self, *, player_id: str, chocobo_id: str,
    ) -> QuestStage:
        prog = self._progress.get(_key(player_id, chocobo_id))
        if prog is None:
            return QuestStage.NOT_STARTED
        return prog.stage

    def total_quests(self) -> int:
        return len(self._progress)


__all__ = [
    "QuestStage",
    "StartResult", "AdvanceResult",
    "BlueChocoboMountQuest",
]
