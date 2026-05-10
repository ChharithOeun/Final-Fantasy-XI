"""Director AI — cinematographer / shot picker.

Encodes the rules from CINEMATIC_GRAMMAR.md, LAYERED_
COMPOSITION.md, and BOSS_GRAMMAR.md as a decision matrix
keyed on (scene_kind, tempo, focus_target_count). Returns
a ranked top-3 of shot suggestions; enforces the 180-degree
rule and reverse-shot pacing; scores any candidate shot for
how well it serves the current scene state.

The server publishes shot intent; UE5 picks the matching
camera rig and lens via cinematic_camera + lens_optics.

Public surface
--------------
    ShotType enum
    SceneKind enum
    Tempo enum
    ShotSuggestion dataclass (frozen)
    DirectorAI
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ShotType(enum.Enum):
    WIDE_ESTABLISHING = "wide_establishing"
    MEDIUM = "medium"
    MEDIUM_TWO_SHOT = "medium_two_shot"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_THE_SHOULDER = "over_the_shoulder"
    POV = "pov"
    OVERHEAD = "overhead"
    DUTCH_ANGLE = "dutch_angle"
    HANDHELD = "handheld"


class SceneKind(enum.Enum):
    DIALOGUE = "dialogue"
    COMBAT_OPEN = "combat_open"      # open arena
    COMBAT_CLOSE = "combat_close"    # close quarters
    EXPLORATION = "exploration"
    EMOTIONAL_BEAT = "emotional_beat"
    REVEAL = "reveal"
    ACTION_SET_PIECE = "action_set_piece"


class Tempo(enum.Enum):
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


@dataclasses.dataclass(frozen=True)
class ShotSuggestion:
    shot: ShotType
    score: float


# Decision matrix: (SceneKind, Tempo) → ranked shot list with
# a base score. focus_target_count refines the picks
# (0 → no people, 1 → CU/MED, 2+ → MED_TWO_SHOT / OTS).
_MATRIX: dict[
    tuple[SceneKind, Tempo],
    tuple[tuple[ShotType, float], ...],
] = {
    # ---- DIALOGUE ----
    (SceneKind.DIALOGUE, Tempo.SLOW): (
        (ShotType.MEDIUM, 0.95),
        (ShotType.OVER_THE_SHOULDER, 0.9),
        (ShotType.CLOSE_UP, 0.85),
        (ShotType.MEDIUM_TWO_SHOT, 0.8),
    ),
    (SceneKind.DIALOGUE, Tempo.MEDIUM): (
        (ShotType.OVER_THE_SHOULDER, 0.95),
        (ShotType.MEDIUM, 0.9),
        (ShotType.CLOSE_UP, 0.85),
        (ShotType.MEDIUM_TWO_SHOT, 0.75),
    ),
    (SceneKind.DIALOGUE, Tempo.FAST): (
        (ShotType.CLOSE_UP, 0.95),
        (ShotType.OVER_THE_SHOULDER, 0.9),
        (ShotType.EXTREME_CLOSE_UP, 0.8),
        (ShotType.MEDIUM, 0.7),
    ),
    # ---- COMBAT_OPEN ----
    (SceneKind.COMBAT_OPEN, Tempo.SLOW): (
        (ShotType.WIDE_ESTABLISHING, 0.95),
        (ShotType.OVERHEAD, 0.85),
        (ShotType.MEDIUM, 0.7),
    ),
    (SceneKind.COMBAT_OPEN, Tempo.MEDIUM): (
        (ShotType.MEDIUM, 0.9),
        (ShotType.WIDE_ESTABLISHING, 0.85),
        (ShotType.OVERHEAD, 0.8),
    ),
    (SceneKind.COMBAT_OPEN, Tempo.FAST): (
        (ShotType.HANDHELD, 0.95),
        (ShotType.MEDIUM, 0.85),
        (ShotType.DUTCH_ANGLE, 0.8),
    ),
    # ---- COMBAT_CLOSE ----
    (SceneKind.COMBAT_CLOSE, Tempo.SLOW): (
        (ShotType.MEDIUM, 0.9),
        (ShotType.CLOSE_UP, 0.85),
        (ShotType.OVER_THE_SHOULDER, 0.8),
    ),
    (SceneKind.COMBAT_CLOSE, Tempo.MEDIUM): (
        (ShotType.HANDHELD, 0.9),
        (ShotType.CLOSE_UP, 0.85),
        (ShotType.MEDIUM, 0.8),
    ),
    (SceneKind.COMBAT_CLOSE, Tempo.FAST): (
        (ShotType.HANDHELD, 0.95),
        (ShotType.DUTCH_ANGLE, 0.9),
        (ShotType.CLOSE_UP, 0.85),
    ),
    # ---- EXPLORATION ----
    (SceneKind.EXPLORATION, Tempo.SLOW): (
        (ShotType.WIDE_ESTABLISHING, 0.95),
        (ShotType.OVERHEAD, 0.8),
        (ShotType.MEDIUM, 0.7),
    ),
    (SceneKind.EXPLORATION, Tempo.MEDIUM): (
        (ShotType.MEDIUM, 0.9),
        (ShotType.WIDE_ESTABLISHING, 0.85),
        (ShotType.POV, 0.75),
    ),
    (SceneKind.EXPLORATION, Tempo.FAST): (
        (ShotType.POV, 0.9),
        (ShotType.HANDHELD, 0.85),
        (ShotType.MEDIUM, 0.75),
    ),
    # ---- EMOTIONAL_BEAT ----
    (SceneKind.EMOTIONAL_BEAT, Tempo.SLOW): (
        (ShotType.EXTREME_CLOSE_UP, 0.98),
        (ShotType.CLOSE_UP, 0.9),
        (ShotType.MEDIUM, 0.6),
    ),
    (SceneKind.EMOTIONAL_BEAT, Tempo.MEDIUM): (
        (ShotType.CLOSE_UP, 0.95),
        (ShotType.EXTREME_CLOSE_UP, 0.9),
        (ShotType.OVER_THE_SHOULDER, 0.8),
    ),
    (SceneKind.EMOTIONAL_BEAT, Tempo.FAST): (
        (ShotType.CLOSE_UP, 0.9),
        (ShotType.HANDHELD, 0.8),
        (ShotType.MEDIUM, 0.7),
    ),
    # ---- REVEAL ----
    (SceneKind.REVEAL, Tempo.SLOW): (
        (ShotType.WIDE_ESTABLISHING, 0.98),
        (ShotType.OVERHEAD, 0.9),
        (ShotType.MEDIUM, 0.7),
    ),
    (SceneKind.REVEAL, Tempo.MEDIUM): (
        (ShotType.WIDE_ESTABLISHING, 0.95),
        (ShotType.MEDIUM, 0.85),
        (ShotType.OVERHEAD, 0.8),
    ),
    (SceneKind.REVEAL, Tempo.FAST): (
        (ShotType.WIDE_ESTABLISHING, 0.9),
        (ShotType.DUTCH_ANGLE, 0.85),
        (ShotType.MEDIUM, 0.75),
    ),
    # ---- ACTION_SET_PIECE ----
    (SceneKind.ACTION_SET_PIECE, Tempo.SLOW): (
        (ShotType.WIDE_ESTABLISHING, 0.9),
        (ShotType.OVERHEAD, 0.85),
        (ShotType.MEDIUM, 0.7),
    ),
    (SceneKind.ACTION_SET_PIECE, Tempo.MEDIUM): (
        (ShotType.MEDIUM, 0.9),
        (ShotType.WIDE_ESTABLISHING, 0.85),
        (ShotType.HANDHELD, 0.8),
    ),
    (SceneKind.ACTION_SET_PIECE, Tempo.FAST): (
        (ShotType.HANDHELD, 0.95),
        (ShotType.DUTCH_ANGLE, 0.9),
        (ShotType.WIDE_ESTABLISHING, 0.85),
        (ShotType.OVERHEAD, 0.8),
    ),
}


# Reverse-shot pairing — pick_next_shot uses this to keep
# dialogue scenes alive (cut from one OTS to its mirror).
_REVERSE_SHOT: dict[ShotType, ShotType] = {
    ShotType.OVER_THE_SHOULDER: ShotType.OVER_THE_SHOULDER,
    ShotType.CLOSE_UP: ShotType.CLOSE_UP,
    ShotType.MEDIUM: ShotType.MEDIUM,
}


@dataclasses.dataclass
class DirectorAI:
    """Stateless picker — scene state lives in the caller."""

    def suggest_shots(
        self, scene_kind: SceneKind, tempo: Tempo,
        focus_targets: int,
    ) -> tuple[ShotSuggestion, ...]:
        if focus_targets < 0:
            raise ValueError(
                f"focus_targets must be >= 0: {focus_targets}",
            )
        key = (scene_kind, tempo)
        if key not in _MATRIX:
            raise KeyError(
                f"no rule for ({scene_kind}, {tempo})",
            )
        ranked: list[tuple[ShotType, float]] = list(
            _MATRIX[key],
        )
        # Refine by focus_targets — two-shot or OTS only
        # makes sense with 2+ targets; CU/ECU only makes
        # sense with at least 1 target.
        refined: list[tuple[ShotType, float]] = []
        for shot, score in ranked:
            if focus_targets == 0:
                if shot in (
                    ShotType.MEDIUM_TWO_SHOT,
                    ShotType.OVER_THE_SHOULDER,
                    ShotType.CLOSE_UP,
                    ShotType.EXTREME_CLOSE_UP,
                    ShotType.POV,
                ):
                    continue
            elif focus_targets == 1:
                if shot in (
                    ShotType.MEDIUM_TWO_SHOT,
                    ShotType.OVER_THE_SHOULDER,
                ):
                    score = score * 0.5
            else:  # 2+
                if shot in (
                    ShotType.MEDIUM_TWO_SHOT,
                    ShotType.OVER_THE_SHOULDER,
                ):
                    score = min(1.0, score + 0.05)
            refined.append((shot, score))
        # sort by score desc, take top 3
        refined.sort(key=lambda it: it[1], reverse=True)
        return tuple(
            ShotSuggestion(shot=s, score=round(sc, 3))
            for s, sc in refined[:3]
        )

    def violates_180(
        self, prev_shot: ShotType,
        candidate: ShotType,
        *, side_flipped: bool = False,
    ) -> bool:
        """The 180-degree rule:

        Two characters in dialogue are framed with a fixed
        "axis" between them. Cutting from a shot on side A
        to a shot on side B without a transition (insert,
        push-in, or motivated cut) jumps the line and
        confuses the viewer.

        We model it as: any cut between framings on opposite
        sides of the axis (side_flipped=True) is a violation,
        EXCEPT for INSERT-style shots — OVERHEAD, EXTREME_
        CLOSE_UP, POV — which legally cross the line.
        """
        if not side_flipped:
            return False
        legal_crossings = {
            ShotType.OVERHEAD,
            ShotType.EXTREME_CLOSE_UP,
            ShotType.POV,
        }
        if candidate in legal_crossings:
            return False
        if prev_shot in legal_crossings:
            return False
        return True

    def pick_next_shot(
        self, prev_shot: ShotType, beat_index: int,
    ) -> ShotType:
        """Reverse-shot rhythm: alternate every other beat
        between OTS pairs in dialogue. For non-pair shots,
        return prev_shot unchanged on even beats and the
        scene-grammar default on odd beats.
        """
        if beat_index < 0:
            raise ValueError(
                f"beat_index must be >= 0: {beat_index}",
            )
        if prev_shot in _REVERSE_SHOT and beat_index % 2 == 1:
            return _REVERSE_SHOT[prev_shot]
        # On even beats, hold the same shot (i.e. let the
        # editor decide). For non-paired shots, also hold.
        return prev_shot

    def score_shot(
        self, shot: ShotType,
        scene_kind: SceneKind,
        tempo: Tempo,
        focus_targets: int,
    ) -> float:
        """Score how well the candidate serves scene state.

        Looks the candidate up in the matrix; returns 0.0 if
        the matrix doesn't recommend it. focus-refinement
        applied on top, same as suggest_shots.
        """
        suggestions = self.suggest_shots(
            scene_kind, tempo, focus_targets,
        )
        # Walk full ranked list, not just top 3 — but the
        # public suggest_shots returns top 3. Re-derive.
        if focus_targets < 0:
            raise ValueError(
                f"focus_targets must be >= 0: {focus_targets}",
            )
        key = (scene_kind, tempo)
        if key not in _MATRIX:
            return 0.0
        for s, sc in _MATRIX[key]:
            if s == shot:
                if focus_targets == 0 and shot in (
                    ShotType.MEDIUM_TWO_SHOT,
                    ShotType.OVER_THE_SHOULDER,
                    ShotType.CLOSE_UP,
                    ShotType.EXTREME_CLOSE_UP,
                    ShotType.POV,
                ):
                    return 0.0
                if focus_targets == 1 and shot in (
                    ShotType.MEDIUM_TWO_SHOT,
                    ShotType.OVER_THE_SHOULDER,
                ):
                    return round(sc * 0.5, 3)
                if focus_targets >= 2 and shot in (
                    ShotType.MEDIUM_TWO_SHOT,
                    ShotType.OVER_THE_SHOULDER,
                ):
                    return round(min(1.0, sc + 0.05), 3)
                return round(sc, 3)
        return 0.0


__all__ = [
    "ShotType", "SceneKind", "Tempo",
    "ShotSuggestion", "DirectorAI",
]
