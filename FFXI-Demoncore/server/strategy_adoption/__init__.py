"""Strategy adoption — players pin a guide to their HUD.

Mirrors gearswap_adopt: a player browsing the published
guides hits "Adopt", and the next time they engage the
matching encounter, the guide pins as a small overlay
checklist in the encounter UI.

Modes:
    PIN_DURING_FIGHT   guide is shown during the encounter
                       only; auto-hides on victory/defeat
    KEEP_ALWAYS_VISIBLE pinned in a small persistent panel
                       even out of combat — for studying

Per-encounter, ONE guide can be active. Adopting a new
guide for the same encounter replaces the previous (with
an explicit "you're switching from <Author>'s guide to
<NewAuthor>'s" prompt — that's UI not data).

Adoption is voluntary; players can have many guides
adopted across many encounters. The lookup queries
"what's pinned for THIS encounter right now" is the hot
path during fight prep.

Public surface
--------------
    PinMode enum
    AdoptionRecord dataclass (frozen)
    StrategyAdoption
        .adopt(player_id, guide_id, mode, adopted_at)
            -> Optional[AdoptionRecord]
        .un_adopt(player_id, guide_id) -> bool
        .pinned_for(player_id, encounter)
            -> Optional[AdoptionRecord]
        .adoptions_for(player_id) -> list[AdoptionRecord]
        .adopters_count(guide_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.strategy_publisher import (
    EncounterRef, GuideStatus, StrategyPublisher,
)


class PinMode(str, enum.Enum):
    PIN_DURING_FIGHT = "pin_during_fight"
    KEEP_ALWAYS_VISIBLE = "keep_always_visible"


@dataclasses.dataclass(frozen=True)
class AdoptionRecord:
    player_id: str
    guide_id: str
    encounter: EncounterRef
    mode: PinMode
    adopted_at: int


@dataclasses.dataclass
class StrategyAdoption:
    _publisher: StrategyPublisher
    # (player_id, encounter_kind, encounter_id) -> record
    _by_encounter: dict[
        tuple[str, str, str], AdoptionRecord,
    ] = dataclasses.field(default_factory=dict)

    def adopt(
        self, *, player_id: str, guide_id: str,
        mode: PinMode, adopted_at: int,
    ) -> t.Optional[AdoptionRecord]:
        if not player_id:
            return None
        guide = self._publisher.lookup(guide_id=guide_id)
        if guide is None:
            return None
        if guide.status != GuideStatus.PUBLISHED:
            return None
        # Replace any prior pin for this player+encounter
        key = (
            player_id,
            guide.encounter.kind.value,
            guide.encounter.encounter_id,
        )
        rec = AdoptionRecord(
            player_id=player_id, guide_id=guide_id,
            encounter=guide.encounter, mode=mode,
            adopted_at=adopted_at,
        )
        self._by_encounter[key] = rec
        return rec

    def un_adopt(
        self, *, player_id: str, guide_id: str,
    ) -> bool:
        for key, rec in list(self._by_encounter.items()):
            if (rec.player_id == player_id
                    and rec.guide_id == guide_id):
                del self._by_encounter[key]
                return True
        return False

    def pinned_for(
        self, *, player_id: str, encounter: EncounterRef,
    ) -> t.Optional[AdoptionRecord]:
        return self._by_encounter.get((
            player_id, encounter.kind.value,
            encounter.encounter_id,
        ))

    def adoptions_for(
        self, *, player_id: str,
    ) -> list[AdoptionRecord]:
        out = [
            r for (pid, _, _), r in self._by_encounter.items()
            if pid == player_id
        ]
        out.sort(key=lambda r: r.adopted_at)
        return out

    def adopters_count(self, *, guide_id: str) -> int:
        return sum(
            1 for r in self._by_encounter.values()
            if r.guide_id == guide_id
        )

    def total_adoptions(self) -> int:
        return len(self._by_encounter)


__all__ = [
    "PinMode", "AdoptionRecord", "StrategyAdoption",
]
