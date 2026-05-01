"""Voice bank — Higgs Audio anchor catalog + custom 30-second record path.

Per CHARACTER_CREATION.md: 'Three pre-cloned voice anchors per race,
plus a Custom option that lets the player record a 30-second
reference (saved to their account voice bank for in-game lines)'.
"""
from __future__ import annotations

import dataclasses
import enum

from .nations_races import Race


CUSTOM_RECORD_DURATION_SECONDS: int = 30


@dataclasses.dataclass(frozen=True)
class VoiceAnchor:
    """One pre-cloned reference voice."""
    anchor_id: str
    label: str
    race: Race
    pitch_register: str         # 'low' / 'mid' / 'high'
    sample_phrase: str


# 3 anchors per race x 5 races = 15 anchors.
VOICE_ANCHORS: dict[str, VoiceAnchor] = {}


def _add(anchor: VoiceAnchor) -> None:
    VOICE_ANCHORS[anchor.anchor_id] = anchor


# Hume (3)
_add(VoiceAnchor(anchor_id="hume_low_cogley",
                    label="Cogley (gruff)",
                    race=Race.HUME, pitch_register="low",
                    sample_phrase="...alright, let's see what's out there."))
_add(VoiceAnchor(anchor_id="hume_mid_marin",
                    label="Marin (warm)",
                    race=Race.HUME, pitch_register="mid",
                    sample_phrase="Today is mine."))
_add(VoiceAnchor(anchor_id="hume_high_kerry",
                    label="Kerry (bright)",
                    race=Race.HUME, pitch_register="high",
                    sample_phrase="Bring it on."))

# Elvaan (3)
_add(VoiceAnchor(anchor_id="elvaan_low_curilla",
                    label="Curilla (regal)",
                    race=Race.ELVAAN, pitch_register="low",
                    sample_phrase="By my honor."))
_add(VoiceAnchor(anchor_id="elvaan_mid_trion",
                    label="Trion (formal)",
                    race=Race.ELVAAN, pitch_register="mid",
                    sample_phrase="The day is ours."))
_add(VoiceAnchor(anchor_id="elvaan_high_excenmille",
                    label="Excenmille (proud)",
                    race=Race.ELVAAN, pitch_register="high",
                    sample_phrase="Vive la Reine!"))

# Tarutaru (3)
_add(VoiceAnchor(anchor_id="taru_low_shantotto",
                    label="Shantotto (commanding)",
                    race=Race.TARUTARU, pitch_register="low",
                    sample_phrase="Behold the genius!"))
_add(VoiceAnchor(anchor_id="taru_mid_yoran",
                    label="Yoran (gentle)",
                    race=Race.TARUTARU, pitch_register="mid",
                    sample_phrase="Hello-hello!"))
_add(VoiceAnchor(anchor_id="taru_high_kupipi",
                    label="Kupipi (excited)",
                    race=Race.TARUTARU, pitch_register="high",
                    sample_phrase="Adventure awaits!"))

# Mithra (3)
_add(VoiceAnchor(anchor_id="mithra_low_naja",
                    label="Naja (sharp)",
                    race=Race.MITHRA, pitch_register="low",
                    sample_phrase="Mercenary's the name."))
_add(VoiceAnchor(anchor_id="mithra_mid_perih",
                    label="Perih (cool)",
                    race=Race.MITHRA, pitch_register="mid",
                    sample_phrase="Lead the way."))
_add(VoiceAnchor(anchor_id="mithra_high_iroha",
                    label="Iroha (eager)",
                    race=Race.MITHRA, pitch_register="high",
                    sample_phrase="To the hunt!"))

# Galka (3)
_add(VoiceAnchor(anchor_id="galka_low_zeid",
                    label="Zeid (deep)",
                    race=Race.GALKA, pitch_register="low",
                    sample_phrase="I know my path."))
_add(VoiceAnchor(anchor_id="galka_mid_volker",
                    label="Volker (steady)",
                    race=Race.GALKA, pitch_register="mid",
                    sample_phrase="Stand fast."))
_add(VoiceAnchor(anchor_id="galka_high_ironeater",
                    label="Iron Eater (booming)",
                    race=Race.GALKA, pitch_register="high",
                    sample_phrase="The forge calls."))


def voice_anchors_for_race(race: Race) -> list[VoiceAnchor]:
    return [a for a in VOICE_ANCHORS.values() if a.race == race]


@dataclasses.dataclass
class CustomVoiceRecording:
    """A player's recorded 30-second reference, registered with the
    voice bank service."""
    account_id: str
    voice_bank_id: str
    duration_seconds: float
    sample_rate_hz: int
    saved_path: str


def register_custom_voice(*,
                              account_id: str,
                              duration_seconds: float,
                              sample_rate_hz: int,
                              saved_path: str
                              ) -> CustomVoiceRecording:
    """Record a custom voice. Doc: 30 second reference."""
    if duration_seconds <= 0:
        raise ValueError("duration must be positive")
    if duration_seconds > CUSTOM_RECORD_DURATION_SECONDS + 0.5:
        # Allow a half-second of slack; reject anything materially over
        raise ValueError(
            f"recording exceeds the {CUSTOM_RECORD_DURATION_SECONDS}s "
            f"reference window")
    if sample_rate_hz < 16_000:
        raise ValueError("sample rate too low for voice cloning")
    return CustomVoiceRecording(
        account_id=account_id,
        voice_bank_id=f"voicebank_{account_id}",
        duration_seconds=duration_seconds,
        sample_rate_hz=sample_rate_hz,
        saved_path=saved_path,
    )
