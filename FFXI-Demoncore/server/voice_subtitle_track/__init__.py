"""Voice subtitle track — subtitle prefs + accumulation log.

Subtitles render under voiced lines in cutscenes and (optionally)
above NPC heads in the active world. This module owns the
SUBTITLE STREAM the renderer consumes.

Per-player preferences:
  enabled (master toggle)
  font_size (10..40)
  font_family (default, serif, sans, dyslexic)
  color
  background_alpha (0..100)
  language (en / ja / fr / de / es)
  show_speaker_name
  show_in_active_world (separate from cutscene; some prefer
                       cutscene-only)

Lines are pushed via push_line(); the renderer pulls the
RECENT track via current_subtitles(player_id, max_lines).
Lines auto-expire after their hold_seconds.

Public surface
--------------
    SubtitleLanguage enum
    FontFamily enum
    SubtitlePrefs dataclass
    SubtitleLine dataclass
    VoiceSubtitleTrack
        .prefs_for(player_id) -> SubtitlePrefs
        .set_pref(player_id, **fields)
        .push_line(player_id, speaker_name, text, hold_seconds,
                   from_cutscene)
        .current_subtitles(player_id, max_lines) -> tuple[SubtitleLine]
        .tick(player_id, now_seconds) -> tuple[expired ids]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Bounds.
MIN_FONT = 10
MAX_FONT = 40
MIN_BG_ALPHA = 0
MAX_BG_ALPHA = 100
DEFAULT_FONT = 18
DEFAULT_BG_ALPHA = 60


class SubtitleLanguage(str, enum.Enum):
    EN = "en"
    JA = "ja"
    FR = "fr"
    DE = "de"
    ES = "es"


class FontFamily(str, enum.Enum):
    DEFAULT = "default"
    SERIF = "serif"
    SANS = "sans"
    DYSLEXIC = "dyslexic"


@dataclasses.dataclass
class SubtitlePrefs:
    player_id: str
    enabled: bool = True
    font_size: int = DEFAULT_FONT
    font_family: FontFamily = FontFamily.DEFAULT
    color: str = "white"
    background_alpha: int = DEFAULT_BG_ALPHA
    language: SubtitleLanguage = SubtitleLanguage.EN
    show_speaker_name: bool = True
    show_in_active_world: bool = True


@dataclasses.dataclass(frozen=True)
class SubtitleLine:
    line_id: str
    speaker_name: str
    text: str
    pushed_at_seconds: float
    expires_at_seconds: float
    from_cutscene: bool


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


@dataclasses.dataclass
class VoiceSubtitleTrack:
    _prefs: dict[str, SubtitlePrefs] = dataclasses.field(
        default_factory=dict,
    )
    _lines: dict[
        str, list[SubtitleLine],
    ] = dataclasses.field(default_factory=dict)
    _next_id: int = 0

    def prefs_for(
        self, *, player_id: str,
    ) -> SubtitlePrefs:
        p = self._prefs.get(player_id)
        if p is None:
            p = SubtitlePrefs(player_id=player_id)
            self._prefs[player_id] = p
        return p

    def set_pref(
        self, *, player_id: str,
        enabled: t.Optional[bool] = None,
        font_size: t.Optional[int] = None,
        font_family: t.Optional[FontFamily] = None,
        color: t.Optional[str] = None,
        background_alpha: t.Optional[int] = None,
        language: t.Optional[SubtitleLanguage] = None,
        show_speaker_name: t.Optional[bool] = None,
        show_in_active_world: t.Optional[bool] = None,
    ) -> SubtitlePrefs:
        p = self.prefs_for(player_id=player_id)
        if enabled is not None:
            p.enabled = enabled
        if font_size is not None:
            p.font_size = _clamp(
                font_size, MIN_FONT, MAX_FONT,
            )
        if font_family is not None:
            p.font_family = font_family
        if color is not None and color:
            p.color = color
        if background_alpha is not None:
            p.background_alpha = _clamp(
                background_alpha,
                MIN_BG_ALPHA, MAX_BG_ALPHA,
            )
        if language is not None:
            p.language = language
        if show_speaker_name is not None:
            p.show_speaker_name = show_speaker_name
        if show_in_active_world is not None:
            p.show_in_active_world = show_in_active_world
        return p

    def push_line(
        self, *, player_id: str,
        speaker_name: str, text: str,
        hold_seconds: float,
        now_seconds: float = 0.0,
        from_cutscene: bool = False,
    ) -> t.Optional[SubtitleLine]:
        prefs = self.prefs_for(player_id=player_id)
        if not prefs.enabled:
            return None
        if not text:
            return None
        if (
            not from_cutscene
            and not prefs.show_in_active_world
        ):
            return None
        if hold_seconds <= 0:
            return None
        lid = f"sub_{self._next_id}"
        self._next_id += 1
        line = SubtitleLine(
            line_id=lid,
            speaker_name=speaker_name,
            text=text,
            pushed_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + hold_seconds
            ),
            from_cutscene=from_cutscene,
        )
        self._lines.setdefault(
            player_id, [],
        ).append(line)
        return line

    def current_subtitles(
        self, *, player_id: str, max_lines: int = 4,
    ) -> tuple[SubtitleLine, ...]:
        lines = self._lines.get(player_id, [])
        if max_lines <= 0:
            return ()
        return tuple(lines[-max_lines:])

    def tick(
        self, *, player_id: str, now_seconds: float,
    ) -> tuple[str, ...]:
        lines = self._lines.get(player_id)
        if lines is None:
            return ()
        expired: list[str] = []
        kept: list[SubtitleLine] = []
        for line in lines:
            if now_seconds >= line.expires_at_seconds:
                expired.append(line.line_id)
            else:
                kept.append(line)
        if expired:
            self._lines[player_id] = kept
        return tuple(expired)

    def total_active_lines(
        self, *, player_id: str,
    ) -> int:
        return len(self._lines.get(player_id, []))


__all__ = [
    "MIN_FONT", "MAX_FONT",
    "MIN_BG_ALPHA", "MAX_BG_ALPHA",
    "DEFAULT_FONT", "DEFAULT_BG_ALPHA",
    "SubtitleLanguage", "FontFamily",
    "SubtitlePrefs", "SubtitleLine",
    "VoiceSubtitleTrack",
]
