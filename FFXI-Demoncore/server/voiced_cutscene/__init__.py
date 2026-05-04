"""Voiced cutscene player — voice + subtitle track for cutscenes.

A cutscene is a SCRIPT of LINES. Each line carries: who speaks,
the dialogue text, the voice clip id, the subtitle string
(usually the same as text but can differ for translation), the
emotion, and an optional camera/animation cue.

The player advances through the script in three input modes:
* AUTO: line waits for its voice clip to finish then advances
* MANUAL: player presses "next" to advance
* HYBRID: voice plays then waits a beat for player input

skip(), pause(), resume(), and rewind_one_line() are exposed.

Public surface
--------------
    AdvanceMode enum
    LineDirection enum  (subtitle direction)
    CutsceneLine dataclass
    Cutscene dataclass
    PlaybackState dataclass
    VoicedCutscenePlayer
        .register_cutscene(cutscene_id, lines)
        .start(player_id, cutscene_id, mode) -> PlaybackState
        .advance(player_id) -> PlaybackState
        .skip(player_id)
        .pause(player_id) / resume / rewind_one_line
        .state_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AdvanceMode(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"
    HYBRID = "hybrid"


class LineEmotion(str, enum.Enum):
    NEUTRAL = "neutral"
    JOYFUL = "joyful"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SAD = "sad"
    URGENT = "urgent"


class PlaybackStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PLAYING = "playing"
    PAUSED = "paused"
    SKIPPED = "skipped"
    COMPLETE = "complete"


@dataclasses.dataclass(frozen=True)
class CutsceneLine:
    line_index: int
    speaker_id: str
    text: str                       # the spoken dialogue
    subtitle: str = ""              # falls back to text
    voice_clip_id: t.Optional[str] = None
    emotion: LineEmotion = LineEmotion.NEUTRAL
    camera_cue: str = ""
    animation_cue: str = ""


@dataclasses.dataclass(frozen=True)
class Cutscene:
    cutscene_id: str
    title: str
    lines: tuple[CutsceneLine, ...]


@dataclasses.dataclass
class PlaybackState:
    player_id: str
    cutscene_id: str
    mode: AdvanceMode
    line_index: int = 0
    status: PlaybackStatus = PlaybackStatus.NOT_STARTED


@dataclasses.dataclass
class VoicedCutscenePlayer:
    _cutscenes: dict[str, Cutscene] = dataclasses.field(
        default_factory=dict,
    )
    _states: dict[str, PlaybackState] = dataclasses.field(
        default_factory=dict,
    )

    def register_cutscene(
        self, *, cutscene_id: str, title: str,
        lines: tuple[CutsceneLine, ...],
    ) -> t.Optional[Cutscene]:
        if cutscene_id in self._cutscenes:
            return None
        if not lines:
            return None
        # Validate contiguous indexes
        for i, line in enumerate(lines):
            if line.line_index != i:
                return None
        cs = Cutscene(
            cutscene_id=cutscene_id, title=title,
            lines=lines,
        )
        self._cutscenes[cutscene_id] = cs
        return cs

    def cutscene(
        self, cutscene_id: str,
    ) -> t.Optional[Cutscene]:
        return self._cutscenes.get(cutscene_id)

    def start(
        self, *, player_id: str, cutscene_id: str,
        mode: AdvanceMode = AdvanceMode.AUTO,
    ) -> t.Optional[PlaybackState]:
        cs = self._cutscenes.get(cutscene_id)
        if cs is None:
            return None
        st = PlaybackState(
            player_id=player_id, cutscene_id=cutscene_id,
            mode=mode, line_index=0,
            status=PlaybackStatus.PLAYING,
        )
        self._states[player_id] = st
        return st

    def state_for(
        self, player_id: str,
    ) -> t.Optional[PlaybackState]:
        return self._states.get(player_id)

    def current_line(
        self, *, player_id: str,
    ) -> t.Optional[CutsceneLine]:
        st = self._states.get(player_id)
        if st is None or st.status not in (
            PlaybackStatus.PLAYING, PlaybackStatus.PAUSED,
        ):
            return None
        cs = self._cutscenes.get(st.cutscene_id)
        if cs is None:
            return None
        if not (0 <= st.line_index < len(cs.lines)):
            return None
        return cs.lines[st.line_index]

    def advance(
        self, *, player_id: str,
    ) -> t.Optional[PlaybackState]:
        st = self._states.get(player_id)
        if st is None or st.status != PlaybackStatus.PLAYING:
            return None
        cs = self._cutscenes.get(st.cutscene_id)
        if cs is None:
            return None
        next_idx = st.line_index + 1
        if next_idx >= len(cs.lines):
            st.status = PlaybackStatus.COMPLETE
        else:
            st.line_index = next_idx
        return st

    def skip(
        self, *, player_id: str,
    ) -> t.Optional[PlaybackState]:
        st = self._states.get(player_id)
        if st is None:
            return None
        if st.status in (
            PlaybackStatus.SKIPPED,
            PlaybackStatus.COMPLETE,
        ):
            return None
        st.status = PlaybackStatus.SKIPPED
        return st

    def pause(
        self, *, player_id: str,
    ) -> bool:
        st = self._states.get(player_id)
        if st is None or st.status != PlaybackStatus.PLAYING:
            return False
        st.status = PlaybackStatus.PAUSED
        return True

    def resume(
        self, *, player_id: str,
    ) -> bool:
        st = self._states.get(player_id)
        if st is None or st.status != PlaybackStatus.PAUSED:
            return False
        st.status = PlaybackStatus.PLAYING
        return True

    def rewind_one_line(
        self, *, player_id: str,
    ) -> bool:
        st = self._states.get(player_id)
        if st is None:
            return False
        if st.status not in (
            PlaybackStatus.PLAYING, PlaybackStatus.PAUSED,
        ):
            return False
        if st.line_index <= 0:
            return False
        st.line_index -= 1
        return True

    def total_cutscenes(self) -> int:
        return len(self._cutscenes)


__all__ = [
    "AdvanceMode", "LineEmotion", "PlaybackStatus",
    "CutsceneLine", "Cutscene", "PlaybackState",
    "VoicedCutscenePlayer",
]
