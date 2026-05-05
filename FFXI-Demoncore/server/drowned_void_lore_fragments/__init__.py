"""Drowned Void lore fragments — ghost-city navigation.

DROWNED_VOID is the ABYSSAL_BLACK ghost-city at 400 yalms.
You don't fight there. You navigate it. The fomor underwater
echoes wander it endlessly, and scattered through their
patrols are LORE FRAGMENTS — fragments of the city's last
days before it drowned. Collecting fragments unlocks
journal entries that reveal what really happened to the
DROWNED_PRINCES (the SUNKEN_CROWN cult's flagship line).

Fragments are collected NOT killed. Each fragment has a
WHISPER_DURATION — when a player approaches, the echo
"speaks" for a few seconds, then fades. If you walk away
during the whisper you miss the fragment. If you stay
through the whole whisper, you collect it.

We model this as a per-player COLLECTION SET keyed on
fragment_id. The fragment world-spawner publishes a roster
of fragment IDs and their order in the canonical lore
sequence. Once a player has collected fragments [1..N]
contiguously, they unlock the corresponding chapter of
the journal.

Public surface
--------------
    Chapter enum
    FragmentProfile dataclass
    EncounterResult dataclass
    DrownedVoidLore
        .register_fragment(fragment_id, chapter, order)
        .approach(player_id, fragment_id, now_seconds)
        .leave(player_id, now_seconds)
        .chapters_unlocked(player_id) -> tuple[Chapter, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Chapter(str, enum.Enum):
    DAYS_BEFORE = "days_before"
    THE_SONG_BEGINS = "the_song_begins"
    PRINCES_BARGAIN = "princes_bargain"
    THE_DROWNING = "the_drowning"
    AFTER_SILENCE = "after_silence"


# Whispering takes this long; player must remain near for
# the duration to collect the fragment.
WHISPER_DURATION_SECONDS = 12


@dataclasses.dataclass(frozen=True)
class FragmentProfile:
    fragment_id: str
    chapter: Chapter
    order_in_chapter: int


@dataclasses.dataclass
class _Approach:
    player_id: str
    fragment_id: str
    started_at: int


@dataclasses.dataclass(frozen=True)
class EncounterResult:
    accepted: bool
    fragment_id: str
    chapter: t.Optional[Chapter] = None
    chapter_unlocked: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class DrownedVoidLore:
    _fragments: dict[str, FragmentProfile] = dataclasses.field(
        default_factory=dict,
    )
    _by_chapter: dict[Chapter, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    _approaches: dict[str, _Approach] = dataclasses.field(
        default_factory=dict,
    )
    # player -> set of fragment_ids collected
    _collected: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )

    def register_fragment(
        self, *, fragment_id: str,
        chapter: Chapter,
        order_in_chapter: int,
    ) -> bool:
        if not fragment_id or order_in_chapter <= 0:
            return False
        if fragment_id in self._fragments:
            return False
        prof = FragmentProfile(
            fragment_id=fragment_id,
            chapter=chapter,
            order_in_chapter=order_in_chapter,
        )
        self._fragments[fragment_id] = prof
        self._by_chapter.setdefault(chapter, set()).add(fragment_id)
        return True

    def approach(
        self, *, player_id: str,
        fragment_id: str,
        now_seconds: int,
    ) -> bool:
        if not player_id or fragment_id not in self._fragments:
            return False
        # already collected -> still allow but harmless
        self._approaches[player_id] = _Approach(
            player_id=player_id,
            fragment_id=fragment_id,
            started_at=now_seconds,
        )
        return True

    def leave(
        self, *, player_id: str,
        now_seconds: int,
    ) -> EncounterResult:
        approach = self._approaches.pop(player_id, None)
        if approach is None:
            return EncounterResult(
                False, fragment_id="", reason="no approach",
            )
        elapsed = now_seconds - approach.started_at
        prof = self._fragments[approach.fragment_id]
        if elapsed < WHISPER_DURATION_SECONDS:
            return EncounterResult(
                accepted=True,
                fragment_id=approach.fragment_id,
                chapter=prof.chapter,
                reason="left too soon",
            )
        already = approach.fragment_id in self._collected.get(
            player_id, set(),
        )
        # collect
        self._collected.setdefault(player_id, set()).add(
            approach.fragment_id,
        )
        unlocked = (
            not already
            and self._chapter_complete_now(
                player_id=player_id, chapter=prof.chapter,
            )
        )
        return EncounterResult(
            accepted=True,
            fragment_id=approach.fragment_id,
            chapter=prof.chapter,
            chapter_unlocked=unlocked,
        )

    def _chapter_complete_now(
        self, *, player_id: str, chapter: Chapter,
    ) -> bool:
        needed = self._by_chapter.get(chapter, set())
        if not needed:
            return False
        have = self._collected.get(player_id, set())
        return needed.issubset(have)

    def chapters_unlocked(
        self, *, player_id: str,
    ) -> tuple[Chapter, ...]:
        return tuple(
            ch for ch in Chapter
            if self._chapter_complete_now(
                player_id=player_id, chapter=ch,
            )
        )

    def collected_count(self, *, player_id: str) -> int:
        return len(self._collected.get(player_id, set()))


__all__ = [
    "Chapter", "FragmentProfile", "EncounterResult",
    "DrownedVoidLore", "WHISPER_DURATION_SECONDS",
]
