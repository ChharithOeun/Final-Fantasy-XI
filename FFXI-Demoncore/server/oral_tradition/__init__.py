"""Oral tradition — NPCs in taverns retell player exploits.

A bard at the Steaming Sheep tells a story about Iron Wing
felling Vorrak. A drunk at the Razor Edge brags he was
there. A child in San d'Oria dreams of Alice the Bold.
This is how legends *spread*.

A LegendStory is seeded from a server_history_log entry
and propagates through NPCs over time. Each tick, a
fraction of NPCs who don't yet know the story may hear
it — modeled by a propagation_rate per zone.

A story has a confidence_score that decays away from its
origin (NPCs in distant zones know it but get details
wrong). When asked, an NPC retells the story with the
current accuracy level.

Public surface
--------------
    StoryAccuracy enum (FIRSTHAND/CLEAR/EMBELLISHED/GARBLED)
    LegendStory dataclass (frozen seed) - origin + topic
    NpcKnowledge dataclass (mutable) - what one NPC knows
    OralTradition
        .seed_story(story_id, source_entry_id, summary,
                    origin_zone_id, started_at) -> bool
        .npc_hears(npc_id, zone_id, story_id, accuracy)
            -> bool
        .what_does_npc_know(npc_id, story_id)
            -> Optional[NpcKnowledge]
        .npcs_who_know(story_id) -> tuple[str, ...]
        .retell(npc_id, story_id) -> Optional[str]
        .total_stories() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class StoryAccuracy(str, enum.Enum):
    FIRSTHAND = "firsthand"      # the player who lived it
    CLEAR = "clear"              # heard from a witness
    EMBELLISHED = "embellished"  # heard from a friend of a witness
    GARBLED = "garbled"          # heard fourth-hand


_RETELL_PHRASING = {
    StoryAccuracy.FIRSTHAND:
        "I was there. {summary}",
    StoryAccuracy.CLEAR:
        "I heard from those who were there: {summary}",
    StoryAccuracy.EMBELLISHED:
        "They say in the taverns: {summary}, "
        "or so the bards sing.",
    StoryAccuracy.GARBLED:
        "Word reached me through many mouths — "
        "something about: {summary}. Could be true.",
}


@dataclasses.dataclass(frozen=True)
class LegendStory:
    story_id: str
    source_entry_id: t.Optional[str]
    summary: str
    origin_zone_id: str
    started_at: int


@dataclasses.dataclass
class NpcKnowledge:
    npc_id: str
    story_id: str
    accuracy: StoryAccuracy
    heard_at: int


@dataclasses.dataclass
class OralTradition:
    _stories: dict[str, LegendStory] = dataclasses.field(
        default_factory=dict,
    )
    # (npc_id, story_id) -> NpcKnowledge
    _knowledge: dict[
        tuple[str, str], NpcKnowledge,
    ] = dataclasses.field(default_factory=dict)
    _by_story: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )

    def seed_story(
        self, *, story_id: str,
        source_entry_id: t.Optional[str],
        summary: str, origin_zone_id: str,
        started_at: int,
    ) -> bool:
        if not story_id or not summary or not origin_zone_id:
            return False
        if story_id in self._stories:
            return False
        self._stories[story_id] = LegendStory(
            story_id=story_id,
            source_entry_id=source_entry_id,
            summary=summary, origin_zone_id=origin_zone_id,
            started_at=started_at,
        )
        return True

    def get_story(
        self, *, story_id: str,
    ) -> t.Optional[LegendStory]:
        return self._stories.get(story_id)

    def npc_hears(
        self, *, npc_id: str, story_id: str,
        accuracy: StoryAccuracy, heard_at: int,
    ) -> bool:
        if not npc_id:
            return False
        if story_id not in self._stories:
            return False
        key = (npc_id, story_id)
        existing = self._knowledge.get(key)
        if existing is not None:
            # only upgrade accuracy if better
            order = list(StoryAccuracy)
            if order.index(accuracy) < order.index(existing.accuracy):
                existing.accuracy = accuracy
                existing.heard_at = heard_at
            return False  # not a new hearing
        self._knowledge[key] = NpcKnowledge(
            npc_id=npc_id, story_id=story_id,
            accuracy=accuracy, heard_at=heard_at,
        )
        self._by_story.setdefault(story_id, []).append(npc_id)
        return True

    def what_does_npc_know(
        self, *, npc_id: str, story_id: str,
    ) -> t.Optional[NpcKnowledge]:
        return self._knowledge.get((npc_id, story_id))

    def npcs_who_know(
        self, *, story_id: str,
    ) -> tuple[str, ...]:
        return tuple(self._by_story.get(story_id, []))

    def retell(
        self, *, npc_id: str, story_id: str,
    ) -> t.Optional[str]:
        kn = self._knowledge.get((npc_id, story_id))
        if kn is None:
            return None
        story = self._stories.get(story_id)
        if story is None:
            return None
        template = _RETELL_PHRASING[kn.accuracy]
        return template.format(summary=story.summary)

    def total_stories(self) -> int:
        return len(self._stories)


__all__ = [
    "StoryAccuracy", "LegendStory", "NpcKnowledge",
    "OralTradition",
]
