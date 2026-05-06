"""Legendary quest unlocks — title-gated quest visibility.

Some quests in Vana'diel are not for everyone. They open
only when a player has earned the right titles. This is
how the world rewards legendary players: with quests
nobody else can see.

A QuestGate has:
    - quest_id (the underlying quest in quest_engine)
    - any of N required titles, OR all of N required titles
    - optional minimum_recognition tier (uses
      npc_legend_awareness)
    - optional excluded_titles (e.g. an outlaw-flagged
      title bars certain knightly quests)

Public surface
--------------
    UnlockMode enum (ANY_OF / ALL_OF)
    QuestGate dataclass (frozen)
    UnlockResult dataclass (frozen)
    LegendaryQuestUnlocks
        .register_gate(quest_id, required_title_ids, mode,
                       min_recognition, excluded_title_ids)
        .can_see(quest_id, player_id, title_registry,
                 recognition) -> UnlockResult
        .visible_quests(player_id, title_registry,
                        recognition) -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.hero_titles import HeroTitleRegistry
from server.npc_legend_awareness import (
    RecognitionResult,
    RecognitionTier,
)


class UnlockMode(str, enum.Enum):
    ANY_OF = "any_of"
    ALL_OF = "all_of"


_TIER_ORDER = {
    RecognitionTier.UNKNOWN: 0,
    RecognitionTier.NOTED: 1,
    RecognitionTier.HONORED: 2,
    RecognitionTier.REVERED: 3,
    RecognitionTier.MYTHICAL: 4,
}


@dataclasses.dataclass(frozen=True)
class QuestGate:
    quest_id: str
    required_title_ids: tuple[str, ...]
    mode: UnlockMode = UnlockMode.ANY_OF
    min_recognition: RecognitionTier = RecognitionTier.UNKNOWN
    excluded_title_ids: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class UnlockResult:
    visible: bool
    reason: str = ""


@dataclasses.dataclass
class LegendaryQuestUnlocks:
    _gates: dict[str, QuestGate] = dataclasses.field(
        default_factory=dict,
    )

    def register_gate(
        self, *, quest_id: str,
        required_title_ids: t.Iterable[str],
        mode: UnlockMode = UnlockMode.ANY_OF,
        min_recognition: RecognitionTier = RecognitionTier.UNKNOWN,
        excluded_title_ids: t.Iterable[str] = (),
    ) -> bool:
        if not quest_id:
            return False
        req = tuple(t for t in required_title_ids if t)
        excl = tuple(t for t in excluded_title_ids if t)
        # ALL_OF with no required titles is meaningless
        if mode == UnlockMode.ALL_OF and not req:
            return False
        if quest_id in self._gates:
            return False
        self._gates[quest_id] = QuestGate(
            quest_id=quest_id,
            required_title_ids=req, mode=mode,
            min_recognition=min_recognition,
            excluded_title_ids=excl,
        )
        return True

    def get_gate(
        self, *, quest_id: str,
    ) -> t.Optional[QuestGate]:
        return self._gates.get(quest_id)

    def can_see(
        self, *, quest_id: str, player_id: str,
        title_registry: HeroTitleRegistry,
        recognition: RecognitionResult,
    ) -> UnlockResult:
        gate = self._gates.get(quest_id)
        if gate is None:
            # no gate registered → quest is not legendary;
            # default to visible
            return UnlockResult(visible=True, reason="no gate")
        if not player_id:
            return UnlockResult(visible=False, reason="no player")

        # check excluded first
        held = {
            g.title_id for g in
            title_registry.titles_for_player(player_id=player_id)
        }
        for excl in gate.excluded_title_ids:
            if excl in held:
                return UnlockResult(
                    visible=False,
                    reason=f"excluded by {excl}",
                )

        # check recognition tier floor
        if (_TIER_ORDER[recognition.tier]
                < _TIER_ORDER[gate.min_recognition]):
            return UnlockResult(
                visible=False, reason="below recognition floor",
            )

        # check required titles
        if not gate.required_title_ids:
            # only recognition floor; that's already checked
            return UnlockResult(visible=True)

        if gate.mode == UnlockMode.ANY_OF:
            for req in gate.required_title_ids:
                if req in held:
                    return UnlockResult(visible=True)
            return UnlockResult(
                visible=False,
                reason="missing any required title",
            )
        # ALL_OF
        for req in gate.required_title_ids:
            if req not in held:
                return UnlockResult(
                    visible=False,
                    reason=f"missing {req}",
                )
        return UnlockResult(visible=True)

    def visible_quests(
        self, *, player_id: str,
        title_registry: HeroTitleRegistry,
        recognition: RecognitionResult,
    ) -> tuple[str, ...]:
        out: list[str] = []
        for qid in sorted(self._gates):
            r = self.can_see(
                quest_id=qid, player_id=player_id,
                title_registry=title_registry,
                recognition=recognition,
            )
            if r.visible:
                out.append(qid)
        return tuple(out)

    def total_gates(self) -> int:
        return len(self._gates)


__all__ = [
    "UnlockMode", "QuestGate", "UnlockResult",
    "LegendaryQuestUnlocks",
]
