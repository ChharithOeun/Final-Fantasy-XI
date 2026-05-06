"""Lore hint registry — subtle clues scattered across the undersea.

The Undersea Endgame (Sahagin Royal Conquest) is brutal —
3 alliances, randomized zone assignment, NM kill order
with chain revives, double-MB oxygen tank rotation. The
correct strategy is genuinely hard to figure out. So we
*do* publish it, but we publish it the way old games
hid their best lore: scattered, tiny, off-handed,
overlapping. A poster on the back wall of a mermaid bar.
A throwaway line a shark NPC mutters during the second
half of an unrelated cutscene. A graffiti scrawl in a
flooded crypt. A song verse in the bardic library.

A player who reads everything, talks to everyone, watches
every cutscene to the end, and explores every zone will
collect enough fragments to piece the strategy together.
A player who skips MSQ and races to endgame will arrive
unprepared — which is by design.

Hint locations
--------------
    NPC_DIALOGUE        - in an NPC's secondary chatter
    CUTSCENE_BACKGROUND - a non-focal NPC speaking behind
                          the focused action
    POSTER              - a wall poster, painting,
                          framed letter, etc.
    SCRIBBLED_NOTE      - a note dropped in a chest, on
                          a corpse, in a barrel
    AMBIENT_BARK        - random idle utterance from a
                          passerby
    SONG_VERSE          - a verse in a bard or jukebox
                          song
    JOURNAL_ENTRY       - a found journal in a dungeon
    ITEM_DESCRIPTION    - flavor text on a gear/key item

Each hint targets a `puzzle_piece_id` — multiple hints
can speak to the same puzzle piece (redundancy means
players who miss one entrance still have a path). Hints
also declare the prerequisite MSQ chapter and minimum
side-quest count required to even *see* them — the world
won't dump endgame strategy on a player who isn't ready
to absorb it.

Public surface
--------------
    HintLocation enum
    LoreHint dataclass (frozen)
    LoreHintRegistry
        .register(hint) -> bool
        .get(hint_id) -> Optional[LoreHint]
        .for_puzzle_piece(piece_id) -> tuple[LoreHint, ...]
        .for_zone(zone_id) -> tuple[LoreHint, ...]
        .all_hints() -> tuple[LoreHint, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class HintLocation(str, enum.Enum):
    NPC_DIALOGUE = "npc_dialogue"
    CUTSCENE_BACKGROUND = "cutscene_background"
    POSTER = "poster"
    SCRIBBLED_NOTE = "scribbled_note"
    AMBIENT_BARK = "ambient_bark"
    SONG_VERSE = "song_verse"
    JOURNAL_ENTRY = "journal_entry"
    ITEM_DESCRIPTION = "item_description"


@dataclasses.dataclass(frozen=True)
class LoreHint:
    hint_id: str
    puzzle_piece_id: str
    location: HintLocation
    zone_id: str
    text: str
    # gating
    required_msq_chapter: int = 0       # 0 = no MSQ gate
    required_side_quests: int = 0       # min completed sidequests to see it
    npc_id: t.Optional[str] = None      # for NPC_DIALOGUE / AMBIENT_BARK
    cutscene_id: t.Optional[str] = None # for CUTSCENE_BACKGROUND
    item_id: t.Optional[str] = None     # for ITEM_DESCRIPTION
    # subtlety knob: lower = more obvious, higher = needs sharp eyes
    subtlety: int = 5                   # 1..10


@dataclasses.dataclass
class LoreHintRegistry:
    _hints: dict[str, LoreHint] = dataclasses.field(default_factory=dict)

    def register(self, hint: LoreHint) -> bool:
        if not hint.hint_id or hint.hint_id in self._hints:
            return False
        if not hint.puzzle_piece_id or not hint.zone_id or not hint.text:
            return False
        if hint.subtlety < 1 or hint.subtlety > 10:
            return False
        # location-specific required fields
        if hint.location in (HintLocation.NPC_DIALOGUE,
                             HintLocation.AMBIENT_BARK):
            if not hint.npc_id:
                return False
        elif hint.location == HintLocation.CUTSCENE_BACKGROUND:
            if not hint.cutscene_id:
                return False
        elif hint.location == HintLocation.ITEM_DESCRIPTION:
            if not hint.item_id:
                return False
        self._hints[hint.hint_id] = hint
        return True

    def get(self, *, hint_id: str) -> t.Optional[LoreHint]:
        return self._hints.get(hint_id)

    def for_puzzle_piece(
        self, *, puzzle_piece_id: str,
    ) -> tuple[LoreHint, ...]:
        return tuple(
            h for h in self._hints.values()
            if h.puzzle_piece_id == puzzle_piece_id
        )

    def for_zone(self, *, zone_id: str) -> tuple[LoreHint, ...]:
        return tuple(
            h for h in self._hints.values() if h.zone_id == zone_id
        )

    def all_hints(self) -> tuple[LoreHint, ...]:
        return tuple(self._hints.values())

    def hint_count(self) -> int:
        return len(self._hints)


__all__ = [
    "HintLocation", "LoreHint", "LoreHintRegistry",
]
