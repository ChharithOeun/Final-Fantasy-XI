"""Beastman starter zones — race-specific opening tutorial.

Each playable beastman race lands in a tutorial zone that
teaches the race's hooks. Per the canon vibe each race lives
in:

  Yagudo  -> Oztroja Seminary             (clergy + pilgrim
                                           training)
  Quadav  -> Palborough Foundry           (stoneshell + battle
                                           drills)
  Lamia   -> Aydeewa Tidehold             (predator stalks +
                                           charm rites)
  Orc     -> Davoi Iron Cradle            (war-frenzy +
                                           battlefield triage)

Each tutorial is a fixed sequence of CHAPTERS. Steps inside a
chapter are optional in order; chapters themselves run in
sequence. Completion hands the player off to their first
city's mission giver.

Public surface
--------------
    StarterChapterKind enum
    StarterChapter dataclass
    StarterTutorial dataclass
    BeastmanStarterZones
        .seed_default_tutorials()
        .tutorial_for(race)
        .start(player_id, race)
        .complete_chapter(player_id, race, chapter_kind)
        .progress_for(player_id)
        .is_complete(player_id, race)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class StarterChapterKind(str, enum.Enum):
    AWAKENING = "awakening"          # name selection / character set
    LANGUAGE_INITIATION = "language_initiation"
    COMBAT_BASICS = "combat_basics"
    RACIAL_RITE = "racial_rite"
    HANDOFF_TO_CITY = "handoff_to_city"


_CHAPTER_ORDER: tuple[StarterChapterKind, ...] = tuple(
    StarterChapterKind,
)


@dataclasses.dataclass(frozen=True)
class StarterChapter:
    kind: StarterChapterKind
    label: str
    detail: str = ""


@dataclasses.dataclass(frozen=True)
class StarterTutorial:
    race: BeastmanRace
    zone_id: str
    label: str
    chapters: tuple[StarterChapter, ...]


@dataclasses.dataclass
class _Progress:
    player_id: str
    race: BeastmanRace
    completed_chapters: list[StarterChapterKind] = (
        dataclasses.field(default_factory=list)
    )


_DEFAULT_TUTORIALS: dict[
    BeastmanRace, StarterTutorial,
] = {
    BeastmanRace.YAGUDO: StarterTutorial(
        race=BeastmanRace.YAGUDO,
        zone_id="oztroja_seminary",
        label="Oztroja Seminary",
        chapters=(
            StarterChapter(
                StarterChapterKind.AWAKENING,
                "First Sermon",
                "wake among the bishops; receive a pilgrim's robe",
            ),
            StarterChapter(
                StarterChapterKind.LANGUAGE_INITIATION,
                "Vows of the Beak",
                "speak the rite-tongue, recite the open hymn",
            ),
            StarterChapter(
                StarterChapterKind.COMBAT_BASICS,
                "Talon and Staff",
                "drill with a beak-strike trainer; basic ws",
            ),
            StarterChapter(
                StarterChapterKind.RACIAL_RITE,
                "Honor Bond",
                "kneel before a relic; bond is woven",
            ),
            StarterChapter(
                StarterChapterKind.HANDOFF_TO_CITY,
                "To the Bishop Supreme",
                "depart for the Oztroja temple proper",
            ),
        ),
    ),
    BeastmanRace.QUADAV: StarterTutorial(
        race=BeastmanRace.QUADAV,
        zone_id="palborough_foundry",
        label="Palborough Foundry",
        chapters=(
            StarterChapter(
                StarterChapterKind.AWAKENING,
                "Forge Awakening",
                "rise from the mineral cradle",
            ),
            StarterChapter(
                StarterChapterKind.LANGUAGE_INITIATION,
                "Stone Speech",
                "the foundry teaches your tongue",
            ),
            StarterChapter(
                StarterChapterKind.COMBAT_BASICS,
                "Hammer and Shell",
                "shield drill, opening salvo",
            ),
            StarterChapter(
                StarterChapterKind.RACIAL_RITE,
                "Hard-Shell Rite",
                "endure the strike-test; the shell hardens",
            ),
            StarterChapter(
                StarterChapterKind.HANDOFF_TO_CITY,
                "To the Underforge",
                "head into the city proper",
            ),
        ),
    ),
    BeastmanRace.LAMIA: StarterTutorial(
        race=BeastmanRace.LAMIA,
        zone_id="aydeewa_tidehold",
        label="Aydeewa Tidehold",
        chapters=(
            StarterChapter(
                StarterChapterKind.AWAKENING,
                "Tide Coming",
                "the salt receives you",
            ),
            StarterChapter(
                StarterChapterKind.LANGUAGE_INITIATION,
                "Tongue of Coils",
                "rolled-r practice and hiss-cadence",
            ),
            StarterChapter(
                StarterChapterKind.COMBAT_BASICS,
                "Strike, Charm, Vanish",
                "predator triplet drill",
            ),
            StarterChapter(
                StarterChapterKind.RACIAL_RITE,
                "Serpent Gaze",
                "lock eyes with an elder; her gaze becomes yours",
            ),
            StarterChapter(
                StarterChapterKind.HANDOFF_TO_CITY,
                "To the Subhold",
                "ride a coiler down to the Aydeewa core",
            ),
        ),
    ),
    BeastmanRace.ORC: StarterTutorial(
        race=BeastmanRace.ORC,
        zone_id="davoi_iron_cradle",
        label="Davoi Iron Cradle",
        chapters=(
            StarterChapter(
                StarterChapterKind.AWAKENING,
                "Iron Awakening",
                "born in the foundry roar",
            ),
            StarterChapter(
                StarterChapterKind.LANGUAGE_INITIATION,
                "Roar Speech",
                "throat practice; basic war cries",
            ),
            StarterChapter(
                StarterChapterKind.COMBAT_BASICS,
                "Axe and Frenzy",
                "mid-line drill with a war captain",
            ),
            StarterChapter(
                StarterChapterKind.RACIAL_RITE,
                "Savage Roar Rite",
                "scream to the four winds; the war note unlocks",
            ),
            StarterChapter(
                StarterChapterKind.HANDOFF_TO_CITY,
                "To the Mead Hall",
                "fall in with the warlord's column",
            ),
        ),
    ),
}


@dataclasses.dataclass
class BeastmanStarterZones:
    _tutorials: dict[
        BeastmanRace, StarterTutorial,
    ] = dataclasses.field(default_factory=dict)
    _progress: dict[
        tuple[str, BeastmanRace], _Progress,
    ] = dataclasses.field(default_factory=dict)

    def seed_default_tutorials(self) -> int:
        added = 0
        for race, tut in _DEFAULT_TUTORIALS.items():
            if race not in self._tutorials:
                self._tutorials[race] = tut
                added += 1
        return added

    def register_tutorial(
        self, *, tutorial: StarterTutorial,
    ) -> bool:
        if tutorial.race in self._tutorials:
            return False
        if not tutorial.chapters:
            return False
        # Chapters must be in canonical order.
        for i, ch in enumerate(tutorial.chapters):
            if ch.kind != _CHAPTER_ORDER[i]:
                return False
        self._tutorials[tutorial.race] = tutorial
        return True

    def tutorial_for(
        self, *, race: BeastmanRace,
    ) -> t.Optional[StarterTutorial]:
        return self._tutorials.get(race)

    def start(
        self, *, player_id: str, race: BeastmanRace,
    ) -> bool:
        if race not in self._tutorials:
            return False
        key = (player_id, race)
        if key in self._progress:
            return False
        self._progress[key] = _Progress(
            player_id=player_id, race=race,
        )
        return True

    def complete_chapter(
        self, *, player_id: str,
        race: BeastmanRace,
        chapter_kind: StarterChapterKind,
    ) -> bool:
        prog = self._progress.get((player_id, race))
        if prog is None:
            return False
        next_idx = len(prog.completed_chapters)
        if next_idx >= len(_CHAPTER_ORDER):
            return False
        if chapter_kind != _CHAPTER_ORDER[next_idx]:
            return False
        prog.completed_chapters.append(chapter_kind)
        return True

    def is_complete(
        self, *, player_id: str, race: BeastmanRace,
    ) -> bool:
        prog = self._progress.get((player_id, race))
        if prog is None:
            return False
        return (
            len(prog.completed_chapters)
            == len(_CHAPTER_ORDER)
        )

    def progress_for(
        self, *, player_id: str, race: BeastmanRace,
    ) -> t.Optional[_Progress]:
        return self._progress.get((player_id, race))

    def total_tutorials(self) -> int:
        return len(self._tutorials)

    def total_progress_records(self) -> int:
        return len(self._progress)


__all__ = [
    "StarterChapterKind", "StarterChapter",
    "StarterTutorial",
    "BeastmanStarterZones",
]
