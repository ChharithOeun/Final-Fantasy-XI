"""Jukebox — Mog House music selector + unlock catalog.

Players unlock BGM tracks via achievements, missions, item rewards,
or bonus events. The jukebox lets them pick which track plays in
their Mog House.

Public surface
--------------
    UnlockSource enum
    JukeboxRoll dataclass with track + unlock metadata
    BGM_CATALOG sample tracks
    PlayerJukebox per-character
        .unlock(track_id) / .has(track_id)
        .set_active(track_id)
        .available()
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class UnlockSource(str, enum.Enum):
    DEFAULT = "default"
    ACHIEVEMENT = "achievement"
    MISSION = "mission"
    ITEM_REWARD = "item_reward"
    EVENT = "event"
    PURCHASE = "purchase"


@dataclasses.dataclass(frozen=True)
class JukeboxRoll:
    track_id: str
    title: str
    composer: str = "Naoshi Mizuta"
    unlock_source: UnlockSource = UnlockSource.DEFAULT


# Sample catalog (real FFXI tracks)
BGM_CATALOG: tuple[JukeboxRoll, ...] = (
    JukeboxRoll("vana_diel_march", "Vana'diel March",
                composer="Nobuo Uematsu",
                unlock_source=UnlockSource.DEFAULT),
    JukeboxRoll("ronfaure", "Ronfaure",
                composer="Nobuo Uematsu",
                unlock_source=UnlockSource.DEFAULT),
    JukeboxRoll("gustaberg", "Gustaberg",
                composer="Nobuo Uematsu",
                unlock_source=UnlockSource.DEFAULT),
    JukeboxRoll("sarutabaruta", "Sarutabaruta",
                composer="Nobuo Uematsu",
                unlock_source=UnlockSource.DEFAULT),
    JukeboxRoll("the_grand_duchy_of_jeuno",
                "The Grand Duchy of Jeuno",
                composer="Nobuo Uematsu",
                unlock_source=UnlockSource.MISSION),
    JukeboxRoll("battle_theme",
                "Battle Theme",
                composer="Nobuo Uematsu",
                unlock_source=UnlockSource.DEFAULT),
    JukeboxRoll("repression",
                "Repression",
                unlock_source=UnlockSource.MISSION),
    JukeboxRoll("memoro_de_la_stono",
                "Memoro de la Stono",
                composer="Naoshi Mizuta",
                unlock_source=UnlockSource.MISSION),
    JukeboxRoll("eternal_oath",
                "Eternal Oath",
                composer="Naoshi Mizuta",
                unlock_source=UnlockSource.ACHIEVEMENT),
    JukeboxRoll("distant_worlds",
                "Distant Worlds",
                composer="Nobuo Uematsu",
                unlock_source=UnlockSource.EVENT),
)

BGM_BY_ID: dict[str, JukeboxRoll] = {
    r.track_id: r for r in BGM_CATALOG
}

DEFAULT_TRACKS: frozenset[str] = frozenset(
    r.track_id for r in BGM_CATALOG
    if r.unlock_source == UnlockSource.DEFAULT
)


@dataclasses.dataclass
class PlayerJukebox:
    player_id: str
    unlocked: set[str] = dataclasses.field(
        default_factory=lambda: set(DEFAULT_TRACKS),
    )
    active_track: t.Optional[str] = None

    def unlock(self, *, track_id: str) -> bool:
        if track_id not in BGM_BY_ID:
            return False
        if track_id in self.unlocked:
            return False
        self.unlocked.add(track_id)
        return True

    def has(self, track_id: str) -> bool:
        return track_id in self.unlocked

    def set_active(self, *, track_id: t.Optional[str]) -> bool:
        if track_id is None:
            self.active_track = None
            return True
        if track_id not in self.unlocked:
            return False
        self.active_track = track_id
        return True

    def available(self) -> tuple[JukeboxRoll, ...]:
        return tuple(
            BGM_BY_ID[tid] for tid in sorted(self.unlocked)
            if tid in BGM_BY_ID
        )

    @property
    def collection_size(self) -> int:
        return len(self.unlocked)


__all__ = [
    "UnlockSource", "JukeboxRoll",
    "BGM_CATALOG", "BGM_BY_ID", "DEFAULT_TRACKS",
    "PlayerJukebox",
]
