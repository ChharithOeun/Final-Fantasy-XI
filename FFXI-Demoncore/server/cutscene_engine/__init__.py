"""Cutscene engine — triggers + queue + replay log.

Cutscenes are gated by prerequisites (mission state, item ownership,
zone entry). The engine queues a cutscene, marks it as viewed when
played, and supports replay from the research log.

Public surface
--------------
    Cutscene immutable spec
    CUTSCENE_CATALOG
    CutsceneQueue per player
        .try_trigger(cutscene_id)
        .play(cutscene_id, now_tick) -> PlayResult
        .replay(cutscene_id) -> PlayResult
        .viewed(cutscene_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CutsceneCategory(str, enum.Enum):
    OPENING = "opening"
    MISSION = "mission"
    QUEST = "quest"
    BOSS_INTRO = "boss_intro"
    AVATAR_FIGHT = "avatar_fight"
    EVENT = "event"
    MEMORY = "memory"


@dataclasses.dataclass(frozen=True)
class CutsceneSpec:
    cutscene_id: str
    label: str
    category: CutsceneCategory
    required_quests_complete: tuple[str, ...] = ()
    required_zone_entered: t.Optional[str] = None
    required_items_held: tuple[str, ...] = ()
    skippable: bool = True
    duration_seconds: int = 60


CUTSCENE_CATALOG: tuple[CutsceneSpec, ...] = (
    CutsceneSpec("opening_movie", "Vana'diel Awaits",
                 category=CutsceneCategory.OPENING,
                 skippable=True, duration_seconds=180),
    CutsceneSpec("bastok_intro_naji", "Naji's Welcome",
                 category=CutsceneCategory.MISSION,
                 required_zone_entered="bastok_markets",
                 duration_seconds=45),
    CutsceneSpec("zeruhn_report_pickup", "Zeruhn Report Briefing",
                 category=CutsceneCategory.MISSION,
                 required_quests_complete=("bastok_intro",),
                 duration_seconds=60),
    CutsceneSpec("shadow_lord_appears", "Shadow Lord Awakens",
                 category=CutsceneCategory.BOSS_INTRO,
                 required_zone_entered="castle_zvahl_keep",
                 skippable=False, duration_seconds=120),
    CutsceneSpec("ifrit_pact", "The Pact of Ifrit",
                 category=CutsceneCategory.AVATAR_FIGHT,
                 required_zone_entered="ifrits_cauldron",
                 duration_seconds=90),
    CutsceneSpec("save_my_son", "Save My Son",
                 category=CutsceneCategory.QUEST,
                 duration_seconds=60),
    CutsceneSpec("memoro_lufaise", "Memories of Lufaise",
                 category=CutsceneCategory.MEMORY,
                 required_quests_complete=("cop_chapter_1",),
                 duration_seconds=240),
)

CUTSCENE_BY_ID: dict[str, CutsceneSpec] = {
    c.cutscene_id: c for c in CUTSCENE_CATALOG
}


@dataclasses.dataclass(frozen=True)
class TriggerContext:
    completed_quests: frozenset[str] = frozenset()
    zones_entered: frozenset[str] = frozenset()
    items_held: frozenset[str] = frozenset()


def can_trigger(
    cs: CutsceneSpec, ctx: TriggerContext,
) -> bool:
    for qid in cs.required_quests_complete:
        if qid not in ctx.completed_quests:
            return False
    if cs.required_zone_entered is not None:
        if cs.required_zone_entered not in ctx.zones_entered:
            return False
    for item in cs.required_items_held:
        if item not in ctx.items_held:
            return False
    return True


@dataclasses.dataclass(frozen=True)
class PlayResult:
    accepted: bool
    cutscene_id: str
    duration_seconds: int = 0
    skipped: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class CutsceneQueue:
    player_id: str
    viewed_set: set[str] = dataclasses.field(default_factory=set)
    pending: list[str] = dataclasses.field(default_factory=list)

    def try_trigger(
        self, *,
        cutscene_id: str, ctx: TriggerContext,
    ) -> bool:
        cs = CUTSCENE_BY_ID.get(cutscene_id)
        if cs is None:
            return False
        if not can_trigger(cs, ctx):
            return False
        if cutscene_id in self.viewed_set:
            return False    # don't re-queue if already seen
        if cutscene_id in self.pending:
            return False
        self.pending.append(cutscene_id)
        return True

    def play(
        self, *, cutscene_id: str, skip: bool = False,
    ) -> PlayResult:
        cs = CUTSCENE_BY_ID.get(cutscene_id)
        if cs is None:
            return PlayResult(False, cutscene_id, reason="unknown")
        if cutscene_id not in self.pending:
            return PlayResult(False, cutscene_id,
                              reason="not queued")
        if skip and not cs.skippable:
            return PlayResult(False, cutscene_id,
                              reason="not skippable")
        self.pending.remove(cutscene_id)
        self.viewed_set.add(cutscene_id)
        duration = 0 if skip else cs.duration_seconds
        return PlayResult(
            accepted=True, cutscene_id=cutscene_id,
            duration_seconds=duration, skipped=skip,
        )

    def replay(self, *, cutscene_id: str) -> PlayResult:
        """Replay a previously viewed cutscene from research log."""
        cs = CUTSCENE_BY_ID.get(cutscene_id)
        if cs is None:
            return PlayResult(False, cutscene_id, reason="unknown")
        if cutscene_id not in self.viewed_set:
            return PlayResult(False, cutscene_id,
                              reason="never viewed")
        return PlayResult(
            accepted=True, cutscene_id=cutscene_id,
            duration_seconds=cs.duration_seconds,
            skipped=False,
        )

    def viewed(self, cutscene_id: str) -> bool:
        return cutscene_id in self.viewed_set

    def pending_count(self) -> int:
        return len(self.pending)


__all__ = [
    "CutsceneCategory", "CutsceneSpec",
    "CUTSCENE_CATALOG", "CUTSCENE_BY_ID",
    "TriggerContext", "can_trigger",
    "PlayResult", "CutsceneQueue",
]
