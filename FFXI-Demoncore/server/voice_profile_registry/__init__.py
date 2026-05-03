"""Voice profile registry — per-NPC TTS preset.

Each entity in the AI-driven world has a consistent VOICE.
The orchestrator's voice pipeline (Higgs Audio v2) uses this
preset every time the entity speaks. The same shopkeeper sounds
the same on day 1 and on game-day 100.

A `VoiceProfile` carries:
* pitch_hz_low + pitch_hz_high (range)
* speech_speed_wpm (words per minute baseline)
* accent (one of an enum)
* gender (one of an enum; affects pitch)
* timbre (warm / nasal / breathy / gravelly / robotic / monstrous)
* emotional_default (calm / cheerful / surly / anxious)
* per-faction defaults — used when an NPC has no override

Public surface
--------------
    VoiceAccent / VoiceGender / VoiceTimbre / VoiceEmotion enums
    VoiceProfile dataclass
    FactionDefault dataclass
    VoiceProfileRegistry
        .register_faction_default(...)
        .register_npc(npc_id, profile)
        .voice_for(npc_id, faction_id) -> VoiceProfile
        .resolve_for_speech(npc_id, faction_id, override_emotion)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class VoiceAccent(str, enum.Enum):
    NEUTRAL = "neutral"
    BASTOKAN = "bastokan"           # working-class, gravelly
    SANDORIAN = "sandorian"         # formal, lilting
    WINDURSTIAN = "windurstian"     # high-pitched, sing-song
    JEUNOAN = "jeunoan"             # crisp, mannered
    KAZHAMI = "kazhami"             # warm, fluid
    NORG = "norg"                   # rough, sailor-cadence
    BEASTMEN = "beastmen"           # broken-common
    DRAGONIC = "dragonic"           # deep, slow


class VoiceGender(str, enum.Enum):
    MASCULINE = "masculine"
    FEMININE = "feminine"
    NEUTRAL = "neutral"
    MONSTROUS = "monstrous"


class VoiceTimbre(str, enum.Enum):
    WARM = "warm"
    NASAL = "nasal"
    BREATHY = "breathy"
    GRAVELLY = "gravelly"
    ROBOTIC = "robotic"
    MONSTROUS = "monstrous"
    MELODIC = "melodic"


class VoiceEmotion(str, enum.Enum):
    CALM = "calm"
    CHEERFUL = "cheerful"
    SURLY = "surly"
    ANXIOUS = "anxious"
    SOLEMN = "solemn"
    EXCITED = "excited"
    MENACING = "menacing"


@dataclasses.dataclass(frozen=True)
class VoiceProfile:
    pitch_hz_low: int = 100
    pitch_hz_high: int = 220
    speech_speed_wpm: int = 145
    accent: VoiceAccent = VoiceAccent.NEUTRAL
    gender: VoiceGender = VoiceGender.NEUTRAL
    timbre: VoiceTimbre = VoiceTimbre.WARM
    emotional_default: VoiceEmotion = VoiceEmotion.CALM
    notes: str = ""

    def with_emotion(
        self, emotion: VoiceEmotion,
    ) -> "VoiceProfile":
        return dataclasses.replace(
            self, emotional_default=emotion,
        )


@dataclasses.dataclass(frozen=True)
class FactionDefault:
    faction_id: str
    profile: VoiceProfile


@dataclasses.dataclass
class VoiceProfileRegistry:
    _faction_defaults: dict[
        str, FactionDefault,
    ] = dataclasses.field(default_factory=dict)
    _npc_overrides: dict[
        str, VoiceProfile,
    ] = dataclasses.field(default_factory=dict)

    def register_faction_default(
        self, *, faction_id: str, profile: VoiceProfile,
    ) -> FactionDefault:
        fd = FactionDefault(
            faction_id=faction_id, profile=profile,
        )
        self._faction_defaults[faction_id] = fd
        return fd

    def register_npc(
        self, *, npc_id: str, profile: VoiceProfile,
    ) -> VoiceProfile:
        self._npc_overrides[npc_id] = profile
        return profile

    def voice_for(
        self, *, npc_id: str,
        faction_id: t.Optional[str] = None,
    ) -> t.Optional[VoiceProfile]:
        if npc_id in self._npc_overrides:
            return self._npc_overrides[npc_id]
        if faction_id is not None and faction_id in self._faction_defaults:
            return self._faction_defaults[faction_id].profile
        return None

    def resolve_for_speech(
        self, *, npc_id: str, faction_id: t.Optional[str] = None,
        override_emotion: t.Optional[VoiceEmotion] = None,
    ) -> t.Optional[VoiceProfile]:
        base = self.voice_for(
            npc_id=npc_id, faction_id=faction_id,
        )
        if base is None:
            return None
        if override_emotion is not None:
            return base.with_emotion(override_emotion)
        return base

    def has_override(self, npc_id: str) -> bool:
        return npc_id in self._npc_overrides

    def total_npc_overrides(self) -> int:
        return len(self._npc_overrides)

    def total_faction_defaults(self) -> int:
        return len(self._faction_defaults)


# --------------------------------------------------------------------
# Default seed
# --------------------------------------------------------------------
_DEFAULTS: tuple[
    tuple[str, VoiceProfile], ...,
] = (
    ("bastok", VoiceProfile(
        pitch_hz_low=85, pitch_hz_high=180,
        accent=VoiceAccent.BASTOKAN,
        gender=VoiceGender.MASCULINE,
        timbre=VoiceTimbre.GRAVELLY,
        emotional_default=VoiceEmotion.CALM,
    )),
    ("san_doria", VoiceProfile(
        pitch_hz_low=110, pitch_hz_high=240,
        accent=VoiceAccent.SANDORIAN,
        gender=VoiceGender.MASCULINE,
        timbre=VoiceTimbre.WARM,
        emotional_default=VoiceEmotion.SOLEMN,
    )),
    ("windurst", VoiceProfile(
        pitch_hz_low=180, pitch_hz_high=320,
        accent=VoiceAccent.WINDURSTIAN,
        gender=VoiceGender.FEMININE,
        timbre=VoiceTimbre.MELODIC,
        emotional_default=VoiceEmotion.CHEERFUL,
    )),
    ("jeuno", VoiceProfile(
        pitch_hz_low=120, pitch_hz_high=220,
        accent=VoiceAccent.JEUNOAN,
        gender=VoiceGender.NEUTRAL,
        timbre=VoiceTimbre.WARM,
        emotional_default=VoiceEmotion.CALM,
    )),
    ("kazham", VoiceProfile(
        pitch_hz_low=140, pitch_hz_high=260,
        accent=VoiceAccent.KAZHAMI,
        gender=VoiceGender.FEMININE,
        timbre=VoiceTimbre.WARM,
        emotional_default=VoiceEmotion.CHEERFUL,
    )),
    ("norg", VoiceProfile(
        pitch_hz_low=80, pitch_hz_high=170,
        accent=VoiceAccent.NORG,
        gender=VoiceGender.MASCULINE,
        timbre=VoiceTimbre.GRAVELLY,
        emotional_default=VoiceEmotion.SURLY,
    )),
    ("orc", VoiceProfile(
        pitch_hz_low=70, pitch_hz_high=140,
        accent=VoiceAccent.BEASTMEN,
        gender=VoiceGender.MASCULINE,
        timbre=VoiceTimbre.MONSTROUS,
        emotional_default=VoiceEmotion.MENACING,
    )),
    ("yagudo", VoiceProfile(
        pitch_hz_low=200, pitch_hz_high=380,
        accent=VoiceAccent.BEASTMEN,
        gender=VoiceGender.NEUTRAL,
        timbre=VoiceTimbre.NASAL,
        emotional_default=VoiceEmotion.MENACING,
    )),
    ("dragon", VoiceProfile(
        pitch_hz_low=40, pitch_hz_high=110,
        accent=VoiceAccent.DRAGONIC,
        gender=VoiceGender.MONSTROUS,
        timbre=VoiceTimbre.MONSTROUS,
        speech_speed_wpm=110,
        emotional_default=VoiceEmotion.SOLEMN,
    )),
)


def seed_default_voice_profiles(
    registry: VoiceProfileRegistry,
) -> VoiceProfileRegistry:
    for faction_id, profile in _DEFAULTS:
        registry.register_faction_default(
            faction_id=faction_id, profile=profile,
        )
    return registry


__all__ = [
    "VoiceAccent", "VoiceGender", "VoiceTimbre", "VoiceEmotion",
    "VoiceProfile", "FactionDefault",
    "VoiceProfileRegistry",
    "seed_default_voice_profiles",
]
