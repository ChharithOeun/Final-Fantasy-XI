"""Scene pacing — tempo + cut decisions, Murch's Rule of Six.

Walter Murch's "In the Blink of an Eye" lays out six things
a cut should serve, ranked by importance. We encode the
Murch weights as a 1.0-summing distribution and let the
director_ai feed in per-axis 0..1 scores. score_against_
murch_six returns the weighted sum; advise_cut + should_cut_
now use it to recommend whether the next frame should hold
the current shot or jump to a new one.

Per-scene-kind pacing profiles encode avg / min / max shot
durations, allowed jump cuts, and cross-cut density — read
out of COMBAT_TEMPO.md and CINEMATIC_GRAMMAR.md.

Public surface
--------------
    BeatKind enum
    PacingProfile dataclass (frozen)
    Beat dataclass (frozen)
    ScenePacingSystem
    score_against_murch_six
    recommended_shot_duration
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BeatKind(enum.Enum):
    SETUP = "setup"
    ESCALATION = "escalation"
    REVEAL = "reveal"
    CLIMAX = "climax"
    FALLOUT = "fallout"
    BREATHER = "breather"


# Murch's "Rule of Six" — weights from In the Blink of an Eye.
# 51 / 23 / 10 / 7 / 5 / 4 — summing to 100.
MURCH_WEIGHTS: dict[str, float] = {
    "emotion":   0.51,
    "story":     0.23,
    "rhythm":    0.10,
    "eye_trace": 0.07,
    "plane_2d":  0.05,
    "space_3d":  0.04,
}
assert abs(sum(MURCH_WEIGHTS.values()) - 1.0) < 1e-9


@dataclasses.dataclass(frozen=True)
class PacingProfile:
    scene_kind: str
    avg_shot_duration_s: float
    min_shot_duration_s: float
    max_shot_duration_s: float
    allowed_jump_cuts: bool
    cross_cut_density: float    # 0..1, fraction of scene as cross-cuts


# Per-scene-kind defaults — sourced from cinema convention.
PROFILES: dict[str, PacingProfile] = {
    p.scene_kind: p for p in (
        PacingProfile(
            scene_kind="dialogue",
            avg_shot_duration_s=4.5,
            min_shot_duration_s=1.5,
            max_shot_duration_s=12.0,
            allowed_jump_cuts=False,
            cross_cut_density=0.0,
        ),
        PacingProfile(
            scene_kind="combat_open",
            avg_shot_duration_s=2.2,
            min_shot_duration_s=0.6,
            max_shot_duration_s=6.0,
            allowed_jump_cuts=True,
            cross_cut_density=0.4,
        ),
        PacingProfile(
            scene_kind="combat_close",
            avg_shot_duration_s=1.4,
            min_shot_duration_s=0.4,
            max_shot_duration_s=3.5,
            allowed_jump_cuts=True,
            cross_cut_density=0.55,
        ),
        PacingProfile(
            scene_kind="exploration",
            avg_shot_duration_s=6.5,
            min_shot_duration_s=2.5,
            max_shot_duration_s=20.0,
            allowed_jump_cuts=False,
            cross_cut_density=0.05,
        ),
        PacingProfile(
            scene_kind="emotional_beat",
            avg_shot_duration_s=5.5,
            min_shot_duration_s=2.0,
            max_shot_duration_s=15.0,
            allowed_jump_cuts=False,
            cross_cut_density=0.0,
        ),
        PacingProfile(
            scene_kind="reveal",
            avg_shot_duration_s=3.5,
            min_shot_duration_s=1.0,
            max_shot_duration_s=10.0,
            allowed_jump_cuts=False,
            cross_cut_density=0.1,
        ),
        PacingProfile(
            scene_kind="action_set_piece",
            avg_shot_duration_s=1.8,
            min_shot_duration_s=0.4,
            max_shot_duration_s=5.0,
            allowed_jump_cuts=True,
            cross_cut_density=0.5,
        ),
    )
}


# Per-beat-kind shot duration in seconds — shorthand for the
# director's "this is climax, cut faster".
_BEAT_DURATION: dict[BeatKind, float] = {
    BeatKind.SETUP:      6.0,
    BeatKind.ESCALATION: 3.5,
    BeatKind.REVEAL:     4.0,
    BeatKind.CLIMAX:     1.2,
    BeatKind.FALLOUT:    4.5,
    BeatKind.BREATHER:   8.0,
}


@dataclasses.dataclass(frozen=True)
class Beat:
    kind: BeatKind
    duration_s: float
    intensity: float  # 0..1


@dataclasses.dataclass(frozen=True)
class Sequence:
    scene_kind: str
    profile: PacingProfile
    beats: tuple[Beat, ...]


def score_against_murch_six(scores: dict[str, float]) -> float:
    """Weighted Murch sum.

    Each axis must be in [0, 1]; missing axes default to 0.
    Returns a score in [0, 1].
    """
    out = 0.0
    for axis, weight in MURCH_WEIGHTS.items():
        v = scores.get(axis, 0.0)
        if not (0.0 <= v <= 1.0):
            raise ValueError(
                f"axis {axis} score out of [0,1]: {v}",
            )
        out += weight * v
    return out


def recommended_shot_duration(
    beat_kind: BeatKind, scene_kind: t.Optional[str] = None,
) -> float:
    """Pick a target shot duration for the next beat.

    The base comes from the beat-kind table; if a scene_kind
    is supplied, we clamp to that profile's min/max so we
    never emit a duration shorter than the scene-kind allows.
    """
    if beat_kind not in _BEAT_DURATION:
        raise ValueError(f"unknown beat: {beat_kind}")
    base = _BEAT_DURATION[beat_kind]
    if scene_kind is None:
        return base
    if scene_kind not in PROFILES:
        raise ValueError(f"unknown scene_kind: {scene_kind}")
    p = PROFILES[scene_kind]
    if base < p.min_shot_duration_s:
        return p.min_shot_duration_s
    if base > p.max_shot_duration_s:
        return p.max_shot_duration_s
    return base


@dataclasses.dataclass
class ScenePacingSystem:
    _sequences: dict[str, Sequence] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def register_sequence(
        self, *, scene_kind: str, beats: t.Sequence[Beat],
    ) -> str:
        if scene_kind not in PROFILES:
            raise ValueError(
                f"unknown scene_kind: {scene_kind}",
            )
        if not beats:
            raise ValueError(
                "at least one beat required",
            )
        for b in beats:
            if not (0.0 <= b.intensity <= 1.0):
                raise ValueError(
                    "beat intensity must be in [0,1]",
                )
            if b.duration_s <= 0:
                raise ValueError(
                    "beat duration_s must be positive",
                )
        sid = f"seq_{self._next}"
        self._next += 1
        self._sequences[sid] = Sequence(
            scene_kind=scene_kind,
            profile=PROFILES[scene_kind],
            beats=tuple(beats),
        )
        return sid

    def get(self, sid: str) -> Sequence:
        if sid not in self._sequences:
            raise KeyError(f"unknown sequence: {sid}")
        return self._sequences[sid]

    def beat_at(self, sid: str, t_s: float) -> Beat:
        """Which beat is alive at time t_s?"""
        if t_s < 0:
            raise ValueError("t_s must be >= 0")
        seq = self.get(sid)
        cur = 0.0
        for b in seq.beats:
            if cur <= t_s < cur + b.duration_s:
                return b
            cur += b.duration_s
        # past the end — return last beat
        return seq.beats[-1]

    def advise_cut(
        self, *,
        sid: str,
        now_t: float,
        current_shot_duration: float,
        six_axis_scores: dict[str, float],
    ) -> dict:
        """Return a structured recommendation:

            { "should_cut": bool,
              "murch_score": float,
              "reason": str }
        """
        if current_shot_duration < 0:
            raise ValueError(
                "current_shot_duration must be >= 0",
            )
        seq = self.get(sid)
        prof = seq.profile
        beat = self.beat_at(sid, now_t)
        score = score_against_murch_six(six_axis_scores)
        # Force cut if we exceed the profile's max.
        if current_shot_duration >= prof.max_shot_duration_s:
            return {
                "should_cut": True,
                "murch_score": score,
                "reason": "exceeded_max_shot_duration",
            }
        # Block cut if we're under the profile's min, unless
        # jump cuts are explicitly allowed.
        if current_shot_duration < prof.min_shot_duration_s:
            if not prof.allowed_jump_cuts:
                return {
                    "should_cut": False,
                    "murch_score": score,
                    "reason": "below_min_shot_duration",
                }
        # Climax beats want short shots — bias toward cut.
        # Setup / breather beats want long shots — bias hold.
        threshold = 0.5
        if beat.kind == BeatKind.CLIMAX:
            threshold = 0.35
        elif beat.kind in (
            BeatKind.SETUP, BeatKind.BREATHER,
        ):
            threshold = 0.65
        if score >= threshold:
            return {
                "should_cut": True,
                "murch_score": score,
                "reason": "murch_threshold_met",
            }
        return {
            "should_cut": False,
            "murch_score": score,
            "reason": "murch_threshold_not_met",
        }

    def should_cut_now(
        self, *,
        sid: str, now_t: float,
        current_shot_duration: float,
        six_axis_scores: dict[str, float],
    ) -> bool:
        return bool(self.advise_cut(
            sid=sid, now_t=now_t,
            current_shot_duration=current_shot_duration,
            six_axis_scores=six_axis_scores,
        )["should_cut"])

    def total_duration(self, sid: str) -> float:
        seq = self.get(sid)
        return sum(b.duration_s for b in seq.beats)


def list_profiles() -> tuple[str, ...]:
    return tuple(sorted(PROFILES))


__all__ = [
    "BeatKind", "Beat",
    "PacingProfile", "PROFILES",
    "Sequence", "ScenePacingSystem",
    "MURCH_WEIGHTS",
    "score_against_murch_six",
    "recommended_shot_duration",
    "list_profiles",
]
