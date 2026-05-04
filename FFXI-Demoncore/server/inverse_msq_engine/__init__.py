"""Inverse MSQ engine — beastman POV that mirrors canon MSQ.

When a Hume / Elvaan / Mithra / Tarutaru player completes a
canon MSQ chapter that affected the beastmen — slew an Orc
warlord, broke a Quadav barricade, killed the Yagudo high
priest, freed a slave from Lamia — the WORLD remembers it.
A beastman player's MSQ is the OTHER SIDE of those events.

Each canon chapter has a MIRROR chapter on each affected
beastman race. Mirrors range over reactions:
  GRIEVE — a fallen leader
  AVENGE — track the hume invader
  REBUILD — patch the destroyed thing
  RECRUIT — find a new champion
  SCATTER — flee, regroup, hide
  PROPHESY — the elders prophesy

Mirror chapters consume the canon chapter as a TRIGGER and stay
DORMANT until the trigger fires. Then they OPEN for affected
race players.

Public surface
--------------
    MirrorReactionKind enum
    MirrorChapter dataclass
    MirrorTriggerEvent dataclass
    InverseMsqEngine
        .register_mirror(canon_chapter_id, race, kind, label)
        .ingest_canon_completion(canon_chapter_id, completed_at)
        .open_chapters_for(player_id, race)
        .start_chapter(player_id, mirror_id)
        .complete_chapter(player_id, mirror_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class MirrorReactionKind(str, enum.Enum):
    GRIEVE = "grieve"
    AVENGE = "avenge"
    REBUILD = "rebuild"
    RECRUIT = "recruit"
    SCATTER = "scatter"
    PROPHESY = "prophesy"


class MirrorStatus(str, enum.Enum):
    DORMANT = "dormant"           # canon trigger not yet fired
    OPEN = "open"                 # available to start
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclasses.dataclass
class MirrorChapter:
    mirror_id: str
    canon_chapter_id: str
    race: BeastmanRace
    reaction_kind: MirrorReactionKind
    label: str
    status: MirrorStatus = MirrorStatus.DORMANT
    triggered_at_seconds: t.Optional[float] = None


@dataclasses.dataclass
class _PlayerProgress:
    player_id: str
    mirror_id: str
    started_at_seconds: float = 0.0
    completed_at_seconds: t.Optional[float] = None
    status: MirrorStatus = MirrorStatus.IN_PROGRESS


@dataclasses.dataclass
class InverseMsqEngine:
    _mirrors: dict[str, MirrorChapter] = dataclasses.field(
        default_factory=dict,
    )
    # canon chapter id -> set of mirror ids that wait on it
    _canon_waiting: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)
    # (player_id, mirror_id) -> progress
    _progress: dict[
        tuple[str, str], _PlayerProgress,
    ] = dataclasses.field(default_factory=dict)
    _next_id: int = 0

    def register_mirror(
        self, *, canon_chapter_id: str,
        race: BeastmanRace,
        reaction_kind: MirrorReactionKind,
        label: str,
        mirror_id: t.Optional[str] = None,
    ) -> t.Optional[MirrorChapter]:
        if not canon_chapter_id or not label:
            return None
        if mirror_id is None:
            mirror_id = f"mirror_{self._next_id}"
            self._next_id += 1
        if mirror_id in self._mirrors:
            return None
        m = MirrorChapter(
            mirror_id=mirror_id,
            canon_chapter_id=canon_chapter_id,
            race=race,
            reaction_kind=reaction_kind,
            label=label,
        )
        self._mirrors[mirror_id] = m
        self._canon_waiting.setdefault(
            canon_chapter_id, set(),
        ).add(mirror_id)
        return m

    def ingest_canon_completion(
        self, *, canon_chapter_id: str,
        completed_at_seconds: float = 0.0,
    ) -> tuple[str, ...]:
        """Mark canon chapter complete; flips dependent
        mirrors from DORMANT to OPEN. Returns mirror_ids that
        flipped status this call."""
        waiting = self._canon_waiting.get(
            canon_chapter_id, set(),
        )
        flipped: list[str] = []
        for mid in waiting:
            m = self._mirrors.get(mid)
            if m is None:
                continue
            if m.status != MirrorStatus.DORMANT:
                continue
            m.status = MirrorStatus.OPEN
            m.triggered_at_seconds = completed_at_seconds
            flipped.append(mid)
        return tuple(flipped)

    def mirror(
        self, mirror_id: str,
    ) -> t.Optional[MirrorChapter]:
        return self._mirrors.get(mirror_id)

    def open_chapters_for(
        self, *, race: BeastmanRace,
    ) -> tuple[MirrorChapter, ...]:
        return tuple(
            m for m in self._mirrors.values()
            if m.race == race
            and m.status == MirrorStatus.OPEN
        )

    def start_chapter(
        self, *, player_id: str, mirror_id: str,
        race: BeastmanRace,
        now_seconds: float = 0.0,
    ) -> t.Optional[_PlayerProgress]:
        m = self._mirrors.get(mirror_id)
        if m is None:
            return None
        if m.status != MirrorStatus.OPEN:
            return None
        if m.race != race:
            return None
        key = (player_id, mirror_id)
        if key in self._progress:
            return None
        prog = _PlayerProgress(
            player_id=player_id, mirror_id=mirror_id,
            started_at_seconds=now_seconds,
            status=MirrorStatus.IN_PROGRESS,
        )
        self._progress[key] = prog
        return prog

    def complete_chapter(
        self, *, player_id: str, mirror_id: str,
        now_seconds: float = 0.0,
    ) -> bool:
        key = (player_id, mirror_id)
        prog = self._progress.get(key)
        if prog is None:
            return False
        if prog.status != MirrorStatus.IN_PROGRESS:
            return False
        prog.status = MirrorStatus.COMPLETE
        prog.completed_at_seconds = now_seconds
        return True

    def progress_for(
        self, *, player_id: str, mirror_id: str,
    ) -> t.Optional[_PlayerProgress]:
        return self._progress.get((player_id, mirror_id))

    def total_mirrors(self) -> int:
        return len(self._mirrors)

    def total_progress_records(self) -> int:
        return len(self._progress)


__all__ = [
    "MirrorReactionKind", "MirrorStatus",
    "MirrorChapter",
    "InverseMsqEngine",
]
