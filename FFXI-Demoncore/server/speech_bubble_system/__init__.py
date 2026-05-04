"""Speech bubble system — voiced bubbles in the active world.

Cutscenes use voiced_cutscene; this module handles the LIVE
WORLD: NPCs and mobs say things and a bubble appears above
their head with the line. The bubble lifetime scales with line
length. Players within EARSHOT see the bubble and hear the
voiced clip via surround_audio_mixer.

Bubbles also serve as a CLUE PROBE — when a side-quest-tagged
line is overheard inside earshot, the side_quest_clue_system
captures an OVERHEARD_CHATTER fragment for the listener.

Public surface
--------------
    BubbleKind enum
    BubbleEmotion enum
    SpeechBubble dataclass
    OverhearEvent dataclass
    SpeechBubbleSystem
        .speak(speaker_id, zone_id, x, y, z, line, kind, emotion,
               duration_seconds, voice_clip_id, side_quest_tag)
        .listeners_in_earshot(speaker_id, listeners) -> overhear events
        .tick(now_seconds) -> tuple[expired bubble ids]
        .active_bubbles_in_zone(zone_id)
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Default earshot radius (yalms-equivalent game units).
DEFAULT_EARSHOT_RADIUS = 18.0
# Per-character display time floor.
MIN_BUBBLE_DURATION = 1.5
MAX_BUBBLE_DURATION = 12.0
DURATION_PER_CHAR_SECONDS = 0.045


class BubbleKind(str, enum.Enum):
    DIALOGUE = "dialogue"             # NPC line directed
    AMBIENT_CHATTER = "ambient_chatter"   # 2 NPCs talking
    BARK = "bark"                     # mob/short shout
    REACTION = "reaction"             # surprise/pain
    SHOPKEEP = "shopkeep"             # vendor pitch
    POSTER_HIT = "poster_hit"         # narration on examine


class BubbleEmotion(str, enum.Enum):
    NEUTRAL = "neutral"
    JOYFUL = "joyful"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SECRETIVE = "secretive"
    SAD = "sad"


@dataclasses.dataclass
class SpeechBubble:
    bubble_id: str
    speaker_id: str
    zone_id: str
    x: float
    y: float
    z: float
    line: str
    kind: BubbleKind
    emotion: BubbleEmotion
    voice_clip_id: t.Optional[str]
    side_quest_tag: t.Optional[str]
    spawned_at_seconds: float
    expires_at_seconds: float


@dataclasses.dataclass(frozen=True)
class OverhearEvent:
    listener_id: str
    bubble_id: str
    speaker_id: str
    distance: float
    line: str
    side_quest_tag: t.Optional[str]


def _duration_for_line(line: str) -> float:
    raw = (
        len(line) * DURATION_PER_CHAR_SECONDS
        + 1.0   # baseline read time
    )
    return max(
        MIN_BUBBLE_DURATION,
        min(MAX_BUBBLE_DURATION, raw),
    )


@dataclasses.dataclass
class SpeechBubbleSystem:
    earshot_radius: float = DEFAULT_EARSHOT_RADIUS
    _bubbles: dict[str, SpeechBubble] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def speak(
        self, *, speaker_id: str, zone_id: str,
        x: float, y: float, z: float,
        line: str,
        kind: BubbleKind = BubbleKind.DIALOGUE,
        emotion: BubbleEmotion = BubbleEmotion.NEUTRAL,
        voice_clip_id: t.Optional[str] = None,
        side_quest_tag: t.Optional[str] = None,
        now_seconds: float = 0.0,
        duration_seconds: t.Optional[float] = None,
    ) -> t.Optional[SpeechBubble]:
        if not line:
            return None
        bid = f"bubble_{self._next_id}"
        self._next_id += 1
        if duration_seconds is None:
            duration_seconds = _duration_for_line(line)
        bub = SpeechBubble(
            bubble_id=bid, speaker_id=speaker_id,
            zone_id=zone_id, x=x, y=y, z=z,
            line=line, kind=kind, emotion=emotion,
            voice_clip_id=voice_clip_id,
            side_quest_tag=side_quest_tag,
            spawned_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + duration_seconds
            ),
        )
        self._bubbles[bid] = bub
        return bub

    def get(self, bubble_id: str) -> t.Optional[SpeechBubble]:
        return self._bubbles.get(bubble_id)

    def listeners_in_earshot(
        self, *, bubble_id: str,
        listeners: tuple[
            tuple[str, str, float, float, float], ...,
        ],
    ) -> tuple[OverhearEvent, ...]:
        """Filter (listener_id, zone_id, x, y, z) tuples to
        those within earshot of the speaking bubble."""
        bub = self._bubbles.get(bubble_id)
        if bub is None:
            return ()
        out: list[OverhearEvent] = []
        for lid, zone, lx, ly, lz in listeners:
            if zone != bub.zone_id:
                continue
            dx = lx - bub.x
            dy = ly - bub.y
            dz = lz - bub.z
            dist = math.sqrt(
                dx * dx + dy * dy + dz * dz,
            )
            if dist > self.earshot_radius:
                continue
            out.append(OverhearEvent(
                listener_id=lid, bubble_id=bubble_id,
                speaker_id=bub.speaker_id,
                distance=dist, line=bub.line,
                side_quest_tag=bub.side_quest_tag,
            ))
        return tuple(out)

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for bid, bub in list(self._bubbles.items()):
            if now_seconds >= bub.expires_at_seconds:
                del self._bubbles[bid]
                expired.append(bid)
        return tuple(expired)

    def active_bubbles_in_zone(
        self, zone_id: str,
    ) -> tuple[SpeechBubble, ...]:
        return tuple(
            b for b in self._bubbles.values()
            if b.zone_id == zone_id
        )

    def total_active(self) -> int:
        return len(self._bubbles)


__all__ = [
    "DEFAULT_EARSHOT_RADIUS",
    "MIN_BUBBLE_DURATION", "MAX_BUBBLE_DURATION",
    "DURATION_PER_CHAR_SECONDS",
    "BubbleKind", "BubbleEmotion",
    "SpeechBubble", "OverhearEvent",
    "SpeechBubbleSystem",
]
