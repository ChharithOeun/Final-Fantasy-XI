"""Subtle dialogue inserts — runtime hint placement engine.

The actual moment a hint appears in front of a player —
a poster's text rendering on the wall, an NPC's
secondary line firing during a cutscene, an ambient bark
floating up from a passing fisherman — is governed by
this module. It watches three trigger streams:

    on_zone_enter(player_id, zone_id)
    on_npc_interact(player_id, npc_id, zone_id)
    on_cutscene_play(player_id, cutscene_id, zone_id)
    on_ambient_tick(player_id, zone_id, now_seconds)
    on_item_inspect(player_id, item_id, zone_id)

For each trigger, it looks up matching hints, asks the
attentiveness tracker if the player is allowed to see
them, and if so emits an `InsertEvent` and notifies the
puzzle assembly journal.

This decoupling means designers can author hints
declaratively (just register them in the lore registry)
and the runtime weaves them into the world without any
quest-engine bespoke wiring.

Public surface
--------------
    InsertEvent dataclass (frozen)
    SubtleDialogueInserts
        .__init__(hint_registry, attentiveness, journal,
                  hint_to_piece_map)
        .on_zone_enter(player_id, zone_id) -> tuple[InsertEvent, ...]
        .on_npc_interact(player_id, npc_id, zone_id)
            -> tuple[InsertEvent, ...]
        .on_cutscene_play(player_id, cutscene_id, zone_id)
            -> tuple[InsertEvent, ...]
        .on_ambient_tick(player_id, zone_id, now_seconds)
            -> tuple[InsertEvent, ...]
        .on_item_inspect(player_id, item_id, zone_id)
            -> tuple[InsertEvent, ...]

Note on cooldowns: ambient barks have a per-zone-per-
player cooldown so a player isn't drowned in chatter
when standing in one spot.
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.lore_hint_registry import (
    HintLocation, LoreHint, LoreHintRegistry,
)
from server.hint_attentiveness_tracker import (
    HintAttentivenessTracker,
)
from server.puzzle_assembly_journal import PuzzleAssemblyJournal


AMBIENT_COOLDOWN_SECONDS = 90


@dataclasses.dataclass(frozen=True)
class InsertEvent:
    hint_id: str
    text: str
    location: HintLocation
    zone_id: str
    puzzle_piece_id: str
    subtlety: int


@dataclasses.dataclass
class SubtleDialogueInserts:
    hint_registry: LoreHintRegistry
    attentiveness: HintAttentivenessTracker
    journal: PuzzleAssemblyJournal
    hint_to_piece: dict[str, str] = dataclasses.field(default_factory=dict)
    # (player_id, hint_id) -> last fire time
    _seen_at: dict[tuple[str, str], int] = dataclasses.field(
        default_factory=dict,
    )
    # (player_id, zone_id) -> last ambient fire time, for cooldown
    _last_ambient_at: dict[tuple[str, str], int] = dataclasses.field(
        default_factory=dict,
    )

    def register_mapping(
        self, *, hint_id: str, piece_id: str,
    ) -> bool:
        if not hint_id or not piece_id:
            return False
        if hint_id in self.hint_to_piece:
            return False
        self.hint_to_piece[hint_id] = piece_id
        return True

    def _emit(
        self, *, player_id: str, hint: LoreHint,
        now_seconds: int = 0,
    ) -> t.Optional[InsertEvent]:
        # check attentiveness gate
        if not self.attentiveness.can_see(
            player_id=player_id,
            subtlety=hint.subtlety,
            required_msq_chapter=hint.required_msq_chapter,
            required_side_quests=hint.required_side_quests,
        ):
            return None
        piece_id = self.hint_to_piece.get(hint.hint_id, hint.puzzle_piece_id)
        # record into journal (will return False if dup, which is fine)
        self.journal.observe_hint(
            player_id=player_id,
            hint_id=hint.hint_id,
            piece_id=piece_id,
        )
        self._seen_at[(player_id, hint.hint_id)] = now_seconds
        return InsertEvent(
            hint_id=hint.hint_id,
            text=hint.text,
            location=hint.location,
            zone_id=hint.zone_id,
            puzzle_piece_id=piece_id,
            subtlety=hint.subtlety,
        )

    def on_zone_enter(
        self, *, player_id: str, zone_id: str,
        now_seconds: int = 0,
    ) -> tuple[InsertEvent, ...]:
        """Player entered a zone — fire posters, scribbled
        notes, journal entries that live in this zone."""
        out: list[InsertEvent] = []
        for h in self.hint_registry.for_zone(zone_id=zone_id):
            if h.location not in (
                HintLocation.POSTER,
                HintLocation.SCRIBBLED_NOTE,
                HintLocation.JOURNAL_ENTRY,
                HintLocation.SONG_VERSE,
            ):
                continue
            ev = self._emit(
                player_id=player_id, hint=h, now_seconds=now_seconds,
            )
            if ev:
                out.append(ev)
        return tuple(out)

    def on_npc_interact(
        self, *, player_id: str, npc_id: str, zone_id: str,
        now_seconds: int = 0,
    ) -> tuple[InsertEvent, ...]:
        out: list[InsertEvent] = []
        for h in self.hint_registry.for_zone(zone_id=zone_id):
            if h.location != HintLocation.NPC_DIALOGUE:
                continue
            if h.npc_id != npc_id:
                continue
            ev = self._emit(
                player_id=player_id, hint=h, now_seconds=now_seconds,
            )
            if ev:
                out.append(ev)
        return tuple(out)

    def on_cutscene_play(
        self, *, player_id: str, cutscene_id: str, zone_id: str,
        now_seconds: int = 0,
    ) -> tuple[InsertEvent, ...]:
        out: list[InsertEvent] = []
        for h in self.hint_registry.all_hints():
            if h.location != HintLocation.CUTSCENE_BACKGROUND:
                continue
            if h.cutscene_id != cutscene_id:
                continue
            ev = self._emit(
                player_id=player_id, hint=h, now_seconds=now_seconds,
            )
            if ev:
                out.append(ev)
        return tuple(out)

    def on_ambient_tick(
        self, *, player_id: str, zone_id: str,
        now_seconds: int,
    ) -> tuple[InsertEvent, ...]:
        """Background NPC chatter — rate-limited to one bark
        per zone per AMBIENT_COOLDOWN_SECONDS per player."""
        cd_key = (player_id, zone_id)
        last = self._last_ambient_at.get(cd_key, -10_000_000)
        if (now_seconds - last) < AMBIENT_COOLDOWN_SECONDS:
            return ()
        out: list[InsertEvent] = []
        for h in self.hint_registry.for_zone(zone_id=zone_id):
            if h.location != HintLocation.AMBIENT_BARK:
                continue
            ev = self._emit(
                player_id=player_id, hint=h, now_seconds=now_seconds,
            )
            if ev:
                out.append(ev)
                # one ambient bark per tick — break and arm cooldown
                self._last_ambient_at[cd_key] = now_seconds
                break
        return tuple(out)

    def on_item_inspect(
        self, *, player_id: str, item_id: str, zone_id: str,
        now_seconds: int = 0,
    ) -> tuple[InsertEvent, ...]:
        out: list[InsertEvent] = []
        for h in self.hint_registry.all_hints():
            if h.location != HintLocation.ITEM_DESCRIPTION:
                continue
            if h.item_id != item_id:
                continue
            ev = self._emit(
                player_id=player_id, hint=h, now_seconds=now_seconds,
            )
            if ev:
                out.append(ev)
        return tuple(out)


__all__ = [
    "InsertEvent", "SubtleDialogueInserts",
    "AMBIENT_COOLDOWN_SECONDS",
]
