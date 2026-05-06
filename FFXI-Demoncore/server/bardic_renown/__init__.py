"""Bardic renown — songs composed about specific players' deeds.

A BRD doesn't just buff DPS. On Demoncore, bards keep the
oral tradition of the server. They compose ballads tied to
named historical events; when those ballads are sung, they
buff their subject the way a hero remembers his own legend.

It's the only buff system on the server that's narratively
locked to *who you are*. A song "Of Vorrak's Fall" only
buffs players who actually participated in killing Vorrak
that day — anyone else listening just hears a nice tune.

Renown tiers
------------
    UNSUNG       no songs about this player (default)
    NOTED        1-4 songs in the songbook
    CELEBRATED   5-9 songs
    LEGEND      10+ songs
    IMMORTAL    20+ songs AND at least one MYTHIC-source song

Public surface
--------------
    SongTier enum          (rarity of the source event)
    Ballad dataclass       (frozen) — id, title, composer,
                           composed_at, subject_player_ids,
                           source_entry_id, song_tier
    BardicSongbook
        .compose_ballad(title, composer, composed_at,
                        subject_player_ids, source_entry_id,
                        song_tier) -> ballad_id
        .perform(ballad_id, listening_player_id, performed_at)
            -> bool   (True = buff applies to this listener)
        .ballads_about(player_id) -> tuple[Ballad, ...]
        .ballads_by(composer_id) -> tuple[Ballad, ...]
        .renown_of(player_id) -> RenownTier
        .total_ballads() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SongTier(str, enum.Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class RenownTier(str, enum.Enum):
    UNSUNG = "unsung"
    NOTED = "noted"
    CELEBRATED = "celebrated"
    LEGEND = "legend"
    IMMORTAL = "immortal"


@dataclasses.dataclass(frozen=True)
class Ballad:
    ballad_id: str
    title: str
    composer_id: str
    composed_at: int
    subject_player_ids: tuple[str, ...]
    source_entry_id: t.Optional[str]
    song_tier: SongTier


@dataclasses.dataclass
class BardicSongbook:
    _ballads: list[Ballad] = dataclasses.field(default_factory=list)
    _next_id: int = 0
    _by_subject: dict[str, list[int]] = dataclasses.field(
        default_factory=dict,
    )
    _by_composer: dict[str, list[int]] = dataclasses.field(
        default_factory=dict,
    )

    def compose_ballad(
        self, *, title: str, composer_id: str,
        composed_at: int,
        subject_player_ids: t.Iterable[str],
        source_entry_id: t.Optional[str] = None,
        song_tier: SongTier = SongTier.COMMON,
    ) -> str:
        if not title or not composer_id:
            return ""
        subjects = tuple(s for s in subject_player_ids if s)
        if not subjects:
            return ""
        self._next_id += 1
        bid = f"ballad_{self._next_id}"
        b = Ballad(
            ballad_id=bid, title=title,
            composer_id=composer_id,
            composed_at=composed_at,
            subject_player_ids=subjects,
            source_entry_id=source_entry_id,
            song_tier=song_tier,
        )
        idx = len(self._ballads)
        self._ballads.append(b)
        for s in subjects:
            self._by_subject.setdefault(s, []).append(idx)
        self._by_composer.setdefault(composer_id, []).append(idx)
        return bid

    def get(self, *, ballad_id: str) -> t.Optional[Ballad]:
        for b in self._ballads:
            if b.ballad_id == ballad_id:
                return b
        return None

    def perform(
        self, *, ballad_id: str,
        listening_player_id: str,
        performed_at: int,
    ) -> bool:
        b = self.get(ballad_id=ballad_id)
        if b is None:
            return False
        if not listening_player_id:
            return False
        return listening_player_id in b.subject_player_ids

    def ballads_about(
        self, *, player_id: str,
    ) -> tuple[Ballad, ...]:
        idxs = self._by_subject.get(player_id, [])
        return tuple(self._ballads[i] for i in idxs)

    def ballads_by(
        self, *, composer_id: str,
    ) -> tuple[Ballad, ...]:
        idxs = self._by_composer.get(composer_id, [])
        return tuple(self._ballads[i] for i in idxs)

    def renown_of(self, *, player_id: str) -> RenownTier:
        ballads = self.ballads_about(player_id=player_id)
        n = len(ballads)
        if n == 0:
            return RenownTier.UNSUNG
        if n < 5:
            return RenownTier.NOTED
        if n < 10:
            return RenownTier.CELEBRATED
        # 10+
        has_mythic = any(b.song_tier == SongTier.MYTHIC for b in ballads)
        if n >= 20 and has_mythic:
            return RenownTier.IMMORTAL
        return RenownTier.LEGEND

    def total_ballads(self) -> int:
        return len(self._ballads)


__all__ = [
    "SongTier", "RenownTier", "Ballad", "BardicSongbook",
]
