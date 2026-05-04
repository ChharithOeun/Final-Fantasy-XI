"""Audio listener config — per-player volume + channel mix.

Each player has independent control of:
* MASTER volume (0..100)
* SFX / VOICE / MUSIC / AMBIENT / UI sub-bus volumes
* Surround layout (STEREO, 5_1, 7_1, HEADPHONE_VIRTUAL)
* Voice ducking — auto-attenuate music/sfx when a voice line plays
* Mute (master)

The mixer (surround_audio_mixer) reads the listener's effective
per-bus gain via effective_gain_db() to compose the final output.

Public surface
--------------
    SurroundLayout enum
    BusKind enum
    AudioListenerConfig dataclass
    AudioListenerConfigs
        .config_for(player_id)
        .set_master(player_id, vol_pct)
        .set_bus(player_id, bus, vol_pct)
        .set_layout(player_id, layout)
        .set_voice_ducking(player_id, enabled, duck_db)
        .set_muted(player_id, muted)
        .effective_gain_db(player_id, bus, voice_active)
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Bounds.
MIN_VOL = 0
MAX_VOL = 100
DEFAULT_MASTER = 80
DEFAULT_SFX = 100
DEFAULT_VOICE = 100
DEFAULT_MUSIC = 70
DEFAULT_AMBIENT = 60
DEFAULT_UI = 100
DEFAULT_DUCK_DB = -8.0


class SurroundLayout(str, enum.Enum):
    STEREO = "stereo"
    HEADPHONE_VIRTUAL = "headphone_virtual"
    SURROUND_5_1 = "surround_5_1"
    SURROUND_7_1 = "surround_7_1"


class BusKind(str, enum.Enum):
    SFX = "sfx"
    VOICE = "voice"
    MUSIC = "music"
    AMBIENT = "ambient"
    UI = "ui"


@dataclasses.dataclass
class AudioListenerConfig:
    player_id: str
    master_vol: int = DEFAULT_MASTER
    sfx_vol: int = DEFAULT_SFX
    voice_vol: int = DEFAULT_VOICE
    music_vol: int = DEFAULT_MUSIC
    ambient_vol: int = DEFAULT_AMBIENT
    ui_vol: int = DEFAULT_UI
    layout: SurroundLayout = SurroundLayout.SURROUND_7_1
    voice_ducking_enabled: bool = True
    duck_db: float = DEFAULT_DUCK_DB
    muted: bool = False


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _vol_pct_to_db(vol_pct: int) -> float:
    if vol_pct <= 0:
        return -120.0       # effectively silent
    # Map 100 -> 0 dB, 50 -> -6 dB roughly, 0 -> -60 dB
    return 20.0 * math.log10(vol_pct / 100.0)


@dataclasses.dataclass
class AudioListenerConfigs:
    _configs: dict[str, AudioListenerConfig] = dataclasses.field(
        default_factory=dict,
    )

    def config_for(
        self, *, player_id: str,
    ) -> AudioListenerConfig:
        c = self._configs.get(player_id)
        if c is None:
            c = AudioListenerConfig(player_id=player_id)
            self._configs[player_id] = c
        return c

    def set_master(
        self, *, player_id: str, vol_pct: int,
    ) -> int:
        c = self.config_for(player_id=player_id)
        c.master_vol = _clamp(vol_pct, MIN_VOL, MAX_VOL)
        return c.master_vol

    def set_bus(
        self, *, player_id: str,
        bus: BusKind, vol_pct: int,
    ) -> int:
        c = self.config_for(player_id=player_id)
        v = _clamp(vol_pct, MIN_VOL, MAX_VOL)
        if bus == BusKind.SFX:
            c.sfx_vol = v
        elif bus == BusKind.VOICE:
            c.voice_vol = v
        elif bus == BusKind.MUSIC:
            c.music_vol = v
        elif bus == BusKind.AMBIENT:
            c.ambient_vol = v
        elif bus == BusKind.UI:
            c.ui_vol = v
        return v

    def set_layout(
        self, *, player_id: str,
        layout: SurroundLayout,
    ) -> SurroundLayout:
        c = self.config_for(player_id=player_id)
        c.layout = layout
        return layout

    def set_voice_ducking(
        self, *, player_id: str,
        enabled: bool,
        duck_db: t.Optional[float] = None,
    ) -> AudioListenerConfig:
        c = self.config_for(player_id=player_id)
        c.voice_ducking_enabled = enabled
        if duck_db is not None:
            c.duck_db = duck_db
        return c

    def set_muted(
        self, *, player_id: str, muted: bool,
    ) -> AudioListenerConfig:
        c = self.config_for(player_id=player_id)
        c.muted = muted
        return c

    def effective_gain_db(
        self, *, player_id: str,
        bus: BusKind,
        voice_active: bool = False,
    ) -> float:
        c = self.config_for(player_id=player_id)
        if c.muted:
            return -120.0
        master_db = _vol_pct_to_db(c.master_vol)
        if bus == BusKind.SFX:
            bus_db = _vol_pct_to_db(c.sfx_vol)
        elif bus == BusKind.VOICE:
            bus_db = _vol_pct_to_db(c.voice_vol)
        elif bus == BusKind.MUSIC:
            bus_db = _vol_pct_to_db(c.music_vol)
        elif bus == BusKind.AMBIENT:
            bus_db = _vol_pct_to_db(c.ambient_vol)
        else:
            bus_db = _vol_pct_to_db(c.ui_vol)
        result = master_db + bus_db
        # Voice ducking: when a voice line is active, attenuate
        # music & ambient (not voice itself, not UI).
        if (
            voice_active
            and c.voice_ducking_enabled
            and bus in (BusKind.MUSIC, BusKind.AMBIENT)
        ):
            result += c.duck_db
        return result

    def total_configs(self) -> int:
        return len(self._configs)


__all__ = [
    "MIN_VOL", "MAX_VOL",
    "DEFAULT_MASTER", "DEFAULT_SFX", "DEFAULT_VOICE",
    "DEFAULT_MUSIC", "DEFAULT_AMBIENT", "DEFAULT_UI",
    "DEFAULT_DUCK_DB",
    "SurroundLayout", "BusKind",
    "AudioListenerConfig", "AudioListenerConfigs",
]
