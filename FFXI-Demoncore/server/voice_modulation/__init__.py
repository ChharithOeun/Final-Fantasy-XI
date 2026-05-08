"""Voice modulation — per-player voice settings.

The TTS pipeline (voice_pipeline / voice_profile_registry)
uses an NPC-specific voice profile by default. For a
PLAYER character, demoncore lets each player customize:

    pitch_semitones      -12..+12 (±1 octave)
    timbre_warm_cool      -1.0..+1.0 (cool to warm)
    speed_multiplier      0.8..1.2
    breathiness            0.0..1.0
    accent_token          optional preset (e.g.
                          "elvaan_court", "galka_growl",
                          "tarutaru_lilt")
    aggression_lift       0.0..1.0 (raises pitch + speed
                          when in_combat=True)

The render pipeline reads these on every TTS request and
applies them. Race-baseline curves are applied UNDER
the player overrides; e.g. galka has +0 bias on pitch
but the player can drop -8 semitones for a deeper voice.

Locked in: changing any setting requires the player
to be at a Voice Mage NPC + pay a fee. No hot-swap mid-
combat.

Public surface
--------------
    AccentPreset enum
    VoiceProfile dataclass (frozen)
    VoiceModulation
        .set_pitch(player, semitones) -> bool
        .set_timbre(player, warm_cool) -> bool
        .set_speed(player, multiplier) -> bool
        .set_breathiness(player, level) -> bool
        .set_accent(player, accent) -> bool
        .set_aggression_lift(player, level) -> bool
        .reset(player) -> bool
        .profile(player) -> VoiceProfile
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AccentPreset(str, enum.Enum):
    NEUTRAL = "neutral"
    ELVAAN_COURT = "elvaan_court"
    GALKA_GROWL = "galka_growl"
    TARUTARU_LILT = "tarutaru_lilt"
    HUME_BASTOK = "hume_bastok"
    MITHRA_KAZHAM = "mithra_kazham"


@dataclasses.dataclass(frozen=True)
class VoiceProfile:
    pitch_semitones: int
    timbre_warm_cool: float
    speed_multiplier: float
    breathiness: float
    accent: AccentPreset
    aggression_lift: float


_DEFAULT = VoiceProfile(
    pitch_semitones=0,
    timbre_warm_cool=0.0,
    speed_multiplier=1.0,
    breathiness=0.0,
    accent=AccentPreset.NEUTRAL,
    aggression_lift=0.0,
)


@dataclasses.dataclass
class VoiceModulation:
    _profiles: dict[str, VoiceProfile] = dataclasses.field(
        default_factory=dict,
    )

    def _get(self, player_id: str) -> VoiceProfile:
        return self._profiles.get(player_id, _DEFAULT)

    def _set(
        self, player_id: str, profile: VoiceProfile,
    ) -> None:
        self._profiles[player_id] = profile

    def set_pitch(
        self, *, player_id: str, semitones: int,
    ) -> bool:
        if not player_id:
            return False
        if semitones < -12 or semitones > 12:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, pitch_semitones=semitones,
        ))
        return True

    def set_timbre(
        self, *, player_id: str, warm_cool: float,
    ) -> bool:
        if not player_id:
            return False
        if warm_cool < -1.0 or warm_cool > 1.0:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, timbre_warm_cool=warm_cool,
        ))
        return True

    def set_speed(
        self, *, player_id: str, multiplier: float,
    ) -> bool:
        if not player_id:
            return False
        if multiplier < 0.8 or multiplier > 1.2:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, speed_multiplier=multiplier,
        ))
        return True

    def set_breathiness(
        self, *, player_id: str, level: float,
    ) -> bool:
        if not player_id:
            return False
        if level < 0.0 or level > 1.0:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, breathiness=level,
        ))
        return True

    def set_accent(
        self, *, player_id: str, accent: AccentPreset,
    ) -> bool:
        if not player_id:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, accent=accent,
        ))
        return True

    def set_aggression_lift(
        self, *, player_id: str, level: float,
    ) -> bool:
        if not player_id:
            return False
        if level < 0.0 or level > 1.0:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, aggression_lift=level,
        ))
        return True

    def reset(self, *, player_id: str) -> bool:
        if player_id not in self._profiles:
            return False
        del self._profiles[player_id]
        return True

    def profile(
        self, *, player_id: str,
    ) -> VoiceProfile:
        return self._get(player_id)


__all__ = ["AccentPreset", "VoiceProfile", "VoiceModulation"]
