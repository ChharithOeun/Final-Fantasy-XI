"""Voice performance direction — director's per-line notes.

The director's brief in data form. Each line gets an intent
tag set (WEARY / COMEDIC / ANGRY / ...), tempo and pitch
modifiers in semitones, and a pause-before / pause-after
window. Same data structure feeds the AI engine
(``ai_inference_kwargs``) and a real human VA's call sheet
(``human_va_brief``) — that's the whole point of this layer.

The Murch emotional-loading score (0..1) is computed from the
intent tag set; ``scene_pacing`` and ``director_ai`` consume it
for cut weighting.

Public surface
--------------
    Intent enum (15+ tags)
    Direction dataclass (frozen)
    LineRecord dataclass (frozen)
    PerformanceDirection
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Intent(enum.Enum):
    WEARY = "weary"
    COMEDIC = "comedic"
    ANGRY = "angry"
    TENDER = "tender"
    COLD = "cold"
    BREATHLESS = "breathless"
    WHISPER = "whisper"
    SHOUT = "shout"
    SARCASTIC = "sarcastic"
    MENACING = "menacing"
    RESIGNED = "resigned"
    DEFIANT = "defiant"
    AFRAID = "afraid"
    WITHDRAWN = "withdrawn"
    BREAK_FOURTH_WALL = "break_fourth_wall"


# Murch emotion-loading per intent (0..1). Loud + private
# tags (whisper, tender, breathless, menacing) score higher
# because they're emotionally dense per second of screen time.
_INTENT_LOAD: dict[Intent, float] = {
    Intent.WEARY: 0.55,
    Intent.COMEDIC: 0.35,
    Intent.ANGRY: 0.80,
    Intent.TENDER: 0.85,
    Intent.COLD: 0.45,
    Intent.BREATHLESS: 0.85,
    Intent.WHISPER: 0.90,
    Intent.SHOUT: 0.75,
    Intent.SARCASTIC: 0.40,
    Intent.MENACING: 0.85,
    Intent.RESIGNED: 0.70,
    Intent.DEFIANT: 0.70,
    Intent.AFRAID: 0.85,
    Intent.WITHDRAWN: 0.75,
    Intent.BREAK_FOURTH_WALL: 0.50,
}


@dataclasses.dataclass(frozen=True)
class Direction:
    intent_tags: frozenset[Intent]
    tempo_modifier: float          # -2 .. +2
    pitch_modifier_semitones: float  # -2 .. +2
    pause_before_ms: int
    pause_after_ms: int
    allow_alt_takes: bool = True
    reference_clip_uri: str = ""

    def __post_init__(self) -> None:
        if not (-2.0 <= self.tempo_modifier <= 2.0):
            raise ValueError(
                f"tempo_modifier out of [-2,2]: "
                f"{self.tempo_modifier}",
            )
        if not (
            -2.0 <= self.pitch_modifier_semitones <= 2.0
        ):
            raise ValueError(
                "pitch_modifier_semitones out of [-2,2]: "
                f"{self.pitch_modifier_semitones}",
            )
        if self.pause_before_ms < 0:
            raise ValueError(
                f"pause_before_ms < 0: {self.pause_before_ms}",
            )
        if self.pause_after_ms < 0:
            raise ValueError(
                f"pause_after_ms < 0: {self.pause_after_ms}",
            )


@dataclasses.dataclass(frozen=True)
class LineRecord:
    line_id: str
    role_id: str
    base_text: str
    direction: t.Optional[Direction] = None


_DEFAULT_DIRECTION = Direction(
    intent_tags=frozenset(),
    tempo_modifier=0.0,
    pitch_modifier_semitones=0.0,
    pause_before_ms=0, pause_after_ms=0,
)


@dataclasses.dataclass
class PerformanceDirection:
    _lines: dict[str, LineRecord] = dataclasses.field(
        default_factory=dict,
    )

    def register_line(
        self, line_id: str, role_id: str, base_text: str,
    ) -> LineRecord:
        if not line_id:
            raise ValueError("line_id required")
        if line_id in self._lines:
            raise ValueError(
                f"line_id already registered: {line_id}",
            )
        if not role_id:
            raise ValueError("role_id required")
        rec = LineRecord(
            line_id=line_id, role_id=role_id,
            base_text=base_text,
        )
        self._lines[line_id] = rec
        return rec

    def _get(self, line_id: str) -> LineRecord:
        if line_id not in self._lines:
            raise KeyError(
                f"unknown line_id: {line_id}",
            )
        return self._lines[line_id]

    def set_direction(
        self, line_id: str,
        intent_tags: t.Iterable[Intent],
        tempo_mod: float, pitch_mod: float,
        pause_before_ms: int, pause_after_ms: int,
        *,
        allow_alt_takes: bool = True,
        reference_clip_uri: str = "",
    ) -> Direction:
        rec = self._get(line_id)
        tags = frozenset(intent_tags)
        for tag in tags:
            if not isinstance(tag, Intent):
                raise TypeError(
                    f"intent must be Intent, got {type(tag)}",
                )
        d = Direction(
            intent_tags=tags,
            tempo_modifier=float(tempo_mod),
            pitch_modifier_semitones=float(pitch_mod),
            pause_before_ms=int(pause_before_ms),
            pause_after_ms=int(pause_after_ms),
            allow_alt_takes=allow_alt_takes,
            reference_clip_uri=reference_clip_uri,
        )
        self._lines[line_id] = dataclasses.replace(
            rec, direction=d,
        )
        return d

    def get_direction(self, line_id: str) -> Direction:
        rec = self._get(line_id)
        if rec.direction is None:
            return _DEFAULT_DIRECTION
        return rec.direction

    def lines_with_intent(
        self, intent_tag: Intent,
    ) -> tuple[LineRecord, ...]:
        out: list[LineRecord] = []
        for rec in self._lines.values():
            if rec.direction is None:
                continue
            if intent_tag in rec.direction.intent_tags:
                out.append(rec)
        return tuple(out)

    def direction_packet_for(
        self, role_id: str,
    ) -> tuple[LineRecord, ...]:
        return tuple(
            r for r in self._lines.values()
            if r.role_id == role_id
        )

    @staticmethod
    def to_murch_emotion_score(d: Direction) -> float:
        """Murch loading from intent tag set, gently boosted by
        whisper-class direction (long pauses, low pitch).
        Returns 0..1.
        """
        if not d.intent_tags:
            return 0.10
        scores = [_INTENT_LOAD[t] for t in d.intent_tags]
        # Combine: max of any single tag, lifted toward 1 by
        # the average of the rest. This makes a stack of
        # heavy tags load the line more than any one tag.
        peak = max(scores)
        avg = sum(scores) / len(scores)
        combined = peak + (1.0 - peak) * (avg * 0.6)
        # Long inserted silences imply weight.
        pause_total = (
            d.pause_before_ms + d.pause_after_ms
        )
        if pause_total >= 1500:
            combined = min(1.0, combined + 0.05)
        return round(min(1.0, max(0.0, combined)), 3)

    def emotion_score_for(self, line_id: str) -> float:
        return self.to_murch_emotion_score(
            self.get_direction(line_id),
        )

    # ---- engine integration ----

    def ai_inference_kwargs(self, line_id: str) -> dict:
        """Kwargs for ``voice_pipeline`` synthesis. Tempo and
        pitch modifiers map to engine knobs; intent tags drop
        through as a list the engine can prompt-condition on.
        """
        rec = self._get(line_id)
        d = rec.direction or _DEFAULT_DIRECTION
        return {
            "line_id": rec.line_id,
            "role_id": rec.role_id,
            "text": rec.base_text,
            "intent_tags": [t.value for t in d.intent_tags],
            "tempo_modifier": d.tempo_modifier,
            "pitch_modifier_semitones": (
                d.pitch_modifier_semitones
            ),
            "pause_before_ms": d.pause_before_ms,
            "pause_after_ms": d.pause_after_ms,
            "reference_clip_uri": d.reference_clip_uri,
        }

    def human_va_brief(self, line_id: str) -> str:
        """Human-readable call-sheet entry for a real VA. The
        director hands this to the actor in the booth.
        """
        rec = self._get(line_id)
        d = rec.direction or _DEFAULT_DIRECTION
        tags = (
            ", ".join(sorted(t.value for t in d.intent_tags))
            or "(no tags — neutral read)"
        )
        ref = (
            d.reference_clip_uri
            if d.reference_clip_uri else "(none)"
        )
        return (
            f"# Line {rec.line_id} — role {rec.role_id}\n"
            f"\n"
            f"## Text\n"
            f"> {rec.base_text}\n"
            f"\n"
            f"## Direction\n"
            f"- intent: {tags}\n"
            f"- tempo: {d.tempo_modifier:+.1f}\n"
            f"- pitch: {d.pitch_modifier_semitones:+.1f} st\n"
            f"- pause: {d.pause_before_ms}ms before, "
            f"{d.pause_after_ms}ms after\n"
            f"- alt takes: "
            f"{'yes' if d.allow_alt_takes else 'no'}\n"
            f"- reference clip: {ref}\n"
        )


__all__ = [
    "Intent", "Direction", "LineRecord",
    "PerformanceDirection",
]
