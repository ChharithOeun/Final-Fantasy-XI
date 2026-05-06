"""Hint attentiveness tracker — gates hint visibility per player.

The world is full of hints, but only attentive players
can see them. This module measures how attentive a player
has been by tallying:

    - MSQ chapters completed
    - side quests completed
    - cutscenes watched to the end (not skipped)
    - zones discovered (map_discovery)
    - NPCs talked to at least once
    - bestiary species researched

These signals roll up into an `attentiveness_score`
which puts the player into one of 5 bands:

    OBLIVIOUS   (0..49)    - sees nothing subtle
    OBSERVANT   (50..119)  - sees subtlety<=4 hints
    PERCEPTIVE  (120..199) - sees subtlety<=6 hints
    ATTUNED     (200..299) - sees subtlety<=8 hints
    ENLIGHTENED (300+)     - sees ALL hints

A player at OBLIVIOUS will literally walk past the
poster on the bar wall and not register that the text
relates to anything. A player at ENLIGHTENED will catch
the half-second background line in cutscene #47.

Scoring weights are tuned so a player who *does the
content* — not who grinds — naturally arrives at
ATTUNED by mid-game and ENLIGHTENED by the time they're
ready to attempt the Sahagin Royal Conquest.

Public surface
--------------
    AttentivenessLevel enum
    HintAttentivenessTracker
        .award_msq_chapter(player_id, chapter)
        .award_side_quest(player_id, quest_id)
        .award_cutscene_watched(player_id, cutscene_id)
        .award_zone_discovered(player_id, zone_id)
        .award_npc_talked(player_id, npc_id)
        .award_bestiary(player_id, species_id)
        .score(player_id) -> int
        .level(player_id) -> AttentivenessLevel
        .can_see(player_id, subtlety, required_msq_chapter,
                 required_side_quests) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AttentivenessLevel(str, enum.Enum):
    OBLIVIOUS = "oblivious"
    OBSERVANT = "observant"
    PERCEPTIVE = "perceptive"
    ATTUNED = "attuned"
    ENLIGHTENED = "enlightened"


# Score weights per signal
WEIGHT_MSQ_CHAPTER = 10
WEIGHT_SIDE_QUEST = 3
WEIGHT_CUTSCENE = 2
WEIGHT_ZONE = 2
WEIGHT_NPC = 1
WEIGHT_BESTIARY = 1

# Score thresholds for each level
LEVEL_BANDS: tuple[tuple[int, AttentivenessLevel], ...] = (
    (300, AttentivenessLevel.ENLIGHTENED),
    (200, AttentivenessLevel.ATTUNED),
    (120, AttentivenessLevel.PERCEPTIVE),
    (50, AttentivenessLevel.OBSERVANT),
    (0, AttentivenessLevel.OBLIVIOUS),
)

# Max subtlety visible per level
MAX_SUBTLETY_BY_LEVEL: dict[AttentivenessLevel, int] = {
    AttentivenessLevel.OBLIVIOUS: 0,
    AttentivenessLevel.OBSERVANT: 4,
    AttentivenessLevel.PERCEPTIVE: 6,
    AttentivenessLevel.ATTUNED: 8,
    AttentivenessLevel.ENLIGHTENED: 10,
}


@dataclasses.dataclass
class _PlayerProgress:
    msq_chapters: set[int] = dataclasses.field(default_factory=set)
    side_quests: set[str] = dataclasses.field(default_factory=set)
    cutscenes: set[str] = dataclasses.field(default_factory=set)
    zones: set[str] = dataclasses.field(default_factory=set)
    npcs: set[str] = dataclasses.field(default_factory=set)
    bestiary: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class HintAttentivenessTracker:
    _progress: dict[str, _PlayerProgress] = dataclasses.field(
        default_factory=dict,
    )

    def _get(self, player_id: str) -> _PlayerProgress:
        if player_id not in self._progress:
            self._progress[player_id] = _PlayerProgress()
        return self._progress[player_id]

    def award_msq_chapter(
        self, *, player_id: str, chapter: int,
    ) -> bool:
        if not player_id or chapter < 1:
            return False
        p = self._get(player_id)
        if chapter in p.msq_chapters:
            return False
        p.msq_chapters.add(chapter)
        return True

    def award_side_quest(
        self, *, player_id: str, quest_id: str,
    ) -> bool:
        if not player_id or not quest_id:
            return False
        p = self._get(player_id)
        if quest_id in p.side_quests:
            return False
        p.side_quests.add(quest_id)
        return True

    def award_cutscene_watched(
        self, *, player_id: str, cutscene_id: str,
    ) -> bool:
        if not player_id or not cutscene_id:
            return False
        p = self._get(player_id)
        if cutscene_id in p.cutscenes:
            return False
        p.cutscenes.add(cutscene_id)
        return True

    def award_zone_discovered(
        self, *, player_id: str, zone_id: str,
    ) -> bool:
        if not player_id or not zone_id:
            return False
        p = self._get(player_id)
        if zone_id in p.zones:
            return False
        p.zones.add(zone_id)
        return True

    def award_npc_talked(
        self, *, player_id: str, npc_id: str,
    ) -> bool:
        if not player_id or not npc_id:
            return False
        p = self._get(player_id)
        if npc_id in p.npcs:
            return False
        p.npcs.add(npc_id)
        return True

    def award_bestiary(
        self, *, player_id: str, species_id: str,
    ) -> bool:
        if not player_id or not species_id:
            return False
        p = self._get(player_id)
        if species_id in p.bestiary:
            return False
        p.bestiary.add(species_id)
        return True

    def score(self, *, player_id: str) -> int:
        p = self._progress.get(player_id)
        if p is None:
            return 0
        return (
            len(p.msq_chapters) * WEIGHT_MSQ_CHAPTER
            + len(p.side_quests) * WEIGHT_SIDE_QUEST
            + len(p.cutscenes) * WEIGHT_CUTSCENE
            + len(p.zones) * WEIGHT_ZONE
            + len(p.npcs) * WEIGHT_NPC
            + len(p.bestiary) * WEIGHT_BESTIARY
        )

    def level(self, *, player_id: str) -> AttentivenessLevel:
        s = self.score(player_id=player_id)
        for threshold, lvl in LEVEL_BANDS:
            if s >= threshold:
                return lvl
        return AttentivenessLevel.OBLIVIOUS

    def can_see(
        self, *, player_id: str,
        subtlety: int,
        required_msq_chapter: int = 0,
        required_side_quests: int = 0,
    ) -> bool:
        """A hint is visible only if the player has unlocked it.

        Three independent gates:
            (1) attentiveness level vs hint subtlety
            (2) MSQ chapter prerequisite
            (3) side-quest count floor
        """
        p = self._progress.get(player_id)
        if p is None:
            return subtlety <= 0  # ungated only
        # subtlety gate
        cap = MAX_SUBTLETY_BY_LEVEL[self.level(player_id=player_id)]
        if subtlety > cap:
            return False
        # MSQ gate — must have completed AT LEAST that chapter
        if required_msq_chapter > 0:
            if not any(
                ch >= required_msq_chapter for ch in p.msq_chapters
            ):
                return False
        # side quest count gate
        if len(p.side_quests) < required_side_quests:
            return False
        return True

    def msq_chapters_completed(self, *, player_id: str) -> int:
        p = self._progress.get(player_id)
        return len(p.msq_chapters) if p else 0

    def side_quests_completed(self, *, player_id: str) -> int:
        p = self._progress.get(player_id)
        return len(p.side_quests) if p else 0


__all__ = [
    "AttentivenessLevel", "HintAttentivenessTracker",
    "WEIGHT_MSQ_CHAPTER", "WEIGHT_SIDE_QUEST",
    "WEIGHT_CUTSCENE", "WEIGHT_ZONE",
    "WEIGHT_NPC", "WEIGHT_BESTIARY",
    "LEVEL_BANDS", "MAX_SUBTLETY_BY_LEVEL",
]
