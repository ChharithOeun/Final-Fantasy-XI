"""Bard song catalog + max-songs cap.

BRD plays songs that apply enhancing/enfeebling auras. Each
target has a slot pool; if the cap is exceeded, the oldest song
is overwritten. Default cap is 2 songs per target. Troubadour
SP raises it to 3 for the duration of the buff.

Song "strength" is determined by:
* base_strength (per-song)
* sing skill (BRD's singing skill cap by level)
* string/wind instrument bonus (for the mode it boosts)

Public surface
--------------
    SongFamily / Song dataclass / SONG_CATALOG
    SongTarget — accumulator (per-mob or per-player)
        .apply(song, troubadour=False) -> ApplyResult
        .has(song_id) -> bool
        .active_songs property
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


DEFAULT_SONG_CAP = 2
TROUBADOUR_SONG_CAP = 3


class SongFamily(str, enum.Enum):
    MARCH = "march"             # haste
    MADRIGAL = "madrigal"       # accuracy
    MINUET = "minuet"           # attack
    MINNE = "minne"             # defense
    BALLAD = "ballad"           # MP refresh
    PAEON = "paeon"             # HP regen
    HYMNUS = "hymnus"           # cure
    ETUDE = "etude"             # stat boost
    SCHERZO = "scherzo"         # crit eva
    PRELUDE = "prelude"         # ranged accuracy
    THRENODY = "threnody"       # mob magic def down (debuff)
    LULLABY = "lullaby"         # sleep (debuff)
    CARNAGE_ELEGY = "elegy"     # mob slow (debuff)
    REQUIEM = "requiem"         # mob HP drain (debuff)


@dataclasses.dataclass(frozen=True)
class Song:
    song_id: str
    family: SongFamily
    label: str
    tier: int
    base_strength: int
    instrument_pref: str = "wind"   # "wind" / "string"
    is_debuff: bool = False


SONG_CATALOG: dict[str, Song] = {
    "valor_minuet_1": Song(
        "valor_minuet_1", SongFamily.MINUET, "Valor Minuet I",
        tier=1, base_strength=12,
    ),
    "valor_minuet_2": Song(
        "valor_minuet_2", SongFamily.MINUET, "Valor Minuet II",
        tier=2, base_strength=20,
    ),
    "valor_minuet_3": Song(
        "valor_minuet_3", SongFamily.MINUET, "Valor Minuet III",
        tier=3, base_strength=28,
    ),
    "knights_minne_1": Song(
        "knights_minne_1", SongFamily.MINNE, "Knight's Minne I",
        tier=1, base_strength=10, instrument_pref="string",
    ),
    "knights_minne_2": Song(
        "knights_minne_2", SongFamily.MINNE, "Knight's Minne II",
        tier=2, base_strength=18, instrument_pref="string",
    ),
    "advancing_march": Song(
        "advancing_march", SongFamily.MARCH, "Advancing March",
        tier=1, base_strength=10,
    ),
    "victory_march": Song(
        "victory_march", SongFamily.MARCH, "Victory March",
        tier=2, base_strength=15,
    ),
    "armys_paeon_1": Song(
        "armys_paeon_1", SongFamily.PAEON, "Army's Paeon I",
        tier=1, base_strength=2, instrument_pref="string",
    ),
    "marchers_madrigal_1": Song(
        "marchers_madrigal_1", SongFamily.MADRIGAL,
        "Marcher's Madrigal I", tier=1, base_strength=10,
        instrument_pref="string",
    ),
    "ballad_1": Song(
        "ballad_1", SongFamily.BALLAD, "Mage's Ballad I",
        tier=1, base_strength=2, instrument_pref="string",
    ),
    "ballad_2": Song(
        "ballad_2", SongFamily.BALLAD, "Mage's Ballad II",
        tier=2, base_strength=4, instrument_pref="string",
    ),
    "horde_lullaby": Song(
        "horde_lullaby", SongFamily.LULLABY, "Horde Lullaby",
        tier=1, base_strength=0, is_debuff=True,
    ),
    "battlefield_elegy": Song(
        "battlefield_elegy", SongFamily.CARNAGE_ELEGY,
        "Battlefield Elegy", tier=1, base_strength=0,
        is_debuff=True,
    ),
    "magic_threnody_water": Song(
        "magic_threnody_water", SongFamily.THRENODY,
        "Water Threnody", tier=1, base_strength=15,
        is_debuff=True,
    ),
    "fire_carol": Song(
        "fire_carol", SongFamily.ETUDE, "Fire Carol",
        tier=1, base_strength=8,
    ),
}


@dataclasses.dataclass(frozen=True)
class ActiveSong:
    song_id: str
    family: SongFamily
    strength: int
    cast_at: float


@dataclasses.dataclass(frozen=True)
class ApplyResult:
    accepted: bool
    overwrote_song_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SongTarget:
    target_id: str
    _songs: list[ActiveSong] = dataclasses.field(default_factory=list)

    @property
    def active_songs(self) -> tuple[ActiveSong, ...]:
        return tuple(self._songs)

    def has(self, song_id: str) -> bool:
        return any(s.song_id == song_id for s in self._songs)

    def has_family(self, family: SongFamily) -> bool:
        return any(s.family == family for s in self._songs)

    def apply(self, *, song: Song, sing_skill: int = 240,
              instrument_bonus: int = 0,
              troubadour: bool = False,
              now: float = 0.0) -> ApplyResult:
        cap = TROUBADOUR_SONG_CAP if troubadour else DEFAULT_SONG_CAP

        # Replacing same family => overwrites in place (canonical
        # behavior: a higher-tier song of the same family kicks the
        # weaker one out without taking up a fresh slot).
        for existing in list(self._songs):
            if existing.family == song.family:
                if existing.song_id == song.song_id:
                    # Refreshing the exact same song
                    self._songs.remove(existing)
                    overwrote = existing.song_id
                else:
                    # Higher-tier replaces lower-tier same family
                    self._songs.remove(existing)
                    overwrote = existing.song_id
                self._songs.append(ActiveSong(
                    song_id=song.song_id, family=song.family,
                    strength=song.base_strength + sing_skill // 20
                              + instrument_bonus,
                    cast_at=now,
                ))
                return ApplyResult(True, overwrote_song_id=overwrote)

        # New family — does it fit under the cap?
        if len(self._songs) < cap:
            self._songs.append(ActiveSong(
                song_id=song.song_id, family=song.family,
                strength=song.base_strength + sing_skill // 20
                          + instrument_bonus,
                cast_at=now,
            ))
            return ApplyResult(True)

        # Cap reached: kick the OLDEST song
        oldest = min(self._songs, key=lambda s: s.cast_at)
        self._songs.remove(oldest)
        self._songs.append(ActiveSong(
            song_id=song.song_id, family=song.family,
            strength=song.base_strength + sing_skill // 20
                      + instrument_bonus,
            cast_at=now,
        ))
        return ApplyResult(True, overwrote_song_id=oldest.song_id)


__all__ = [
    "DEFAULT_SONG_CAP", "TROUBADOUR_SONG_CAP",
    "SongFamily", "Song", "SONG_CATALOG",
    "ActiveSong", "ApplyResult", "SongTarget",
]
