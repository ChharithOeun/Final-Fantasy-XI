"""Storyboard panels — per-shot visual planning sheet.

The image-side companion to ``screenplay_engine``. A scene
in the screenplay decomposes into a list of shots; each
shot becomes a Panel with framing, camera move, lens hint,
focus target, and (optionally) the dialogue line being
spoken on that beat. Panels aggregate into a StoryboardSheet
budgeted to a target page count, the way a real animation
or live-action production board does.

The continuity rules (180-degree axis, eye-trace direction)
are checked between consecutive panels to flag the kind of
breaks the continuity supervisor will catch on set later.

Public surface
--------------
    AspectRatio enum
    Framing enum
    CameraMove enum
    Panel dataclass (frozen)
    StoryboardSheet dataclass (frozen)
    ContinuityIssue dataclass (frozen)
    StoryboardSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AspectRatio(enum.Enum):
    """Industry-standard projection ratios."""
    ACADEMY = "1.33"          # 4:3 retro
    HDTV = "1.78"             # 16:9
    THEATRICAL_FLAT = "1.85"  # standard cinema
    UNIVISIUM = "2.00"        # Vittorio Storaro's compromise
    ANAMORPHIC = "2.39"       # scope
    SOCIAL_VERTICAL = "0.5625"  # 9:16 phone

    @property
    def numeric(self) -> float:
        return float(self.value)


class Framing(enum.Enum):
    """Shot size, wide → tight."""
    WIDE = "wide"
    FULL = "full"
    MEDIUM = "medium"
    COWBOY = "cowboy"        # hips up — gunfighter framing
    CLOSE = "close"
    EXTREME_CLOSE = "extreme_close"
    TWO_SHOT = "two_shot"
    OTS = "ots"              # over-the-shoulder
    INSERT = "insert"        # a hand, a letter, a watch face


class CameraMove(enum.Enum):
    STATIC = "static"
    PAN_L = "pan_l"
    PAN_R = "pan_r"
    TILT_U = "tilt_u"
    TILT_D = "tilt_d"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    TRUCK = "truck"
    CRANE_UP = "crane_up"
    CRANE_DOWN = "crane_down"
    HANDHELD = "handheld"
    STEADICAM = "steadicam"
    WHIP = "whip"
    ZOOM = "zoom"


@dataclasses.dataclass(frozen=True)
class Panel:
    panel_id: str
    scene_id: str
    shot_index: int
    aspect_ratio: AspectRatio
    framing: Framing
    camera_move: CameraMove
    action_description: str
    lens_mm_hint: float
    focus_target: str
    has_dialogue: bool = False
    dialogue_excerpt: str = ""
    sound_cue: str = ""
    # Eye-trace target for continuity — left/right edge of
    # frame the viewer's gaze rests on at the cut. Used to
    # flag eye-trace breaks across consecutive panels.
    eye_trace: str = "center"  # "left" / "center" / "right"
    # Side of the 180° axis the camera sits on. "A" / "B".
    axis_side: str = "A"


@dataclasses.dataclass(frozen=True)
class StoryboardSheet:
    scene_id: str
    panels: tuple[Panel, ...]
    target_page_budget: float


@dataclasses.dataclass(frozen=True)
class ContinuityIssue:
    panel_a: str
    panel_b: str
    kind: str           # "axis_jump" | "eye_trace_break" | "lens_jump"
    message: str
    severity: str       # "note" | "warning" | "error"


# ------------------------------------------------------------
# Continuity rule helpers
# ------------------------------------------------------------
def _axis_legal_crossing(prev: Panel, curr: Panel) -> bool:
    """INSERT and EXTREME_CLOSE legally cross the 180° axis."""
    bypass = {Framing.INSERT, Framing.EXTREME_CLOSE}
    if prev.framing in bypass or curr.framing in bypass:
        return True
    return False


def _eye_trace_break(prev: Panel, curr: Panel) -> bool:
    """Eye-trace break: viewer's gaze on left edge of prev
    panel snapping to the right edge of curr panel forces a
    micro-saccade across the cut. We flag the worst case.
    """
    if prev.eye_trace == "left" and curr.eye_trace == "right":
        return True
    if prev.eye_trace == "right" and curr.eye_trace == "left":
        return True
    return False


def _lens_jump(prev: Panel, curr: Panel) -> bool:
    """Cutting from a 24mm wide to a 200mm tight without an
    intermediate frame size feels jarring — we flag any
    cut that more than triples the focal length.
    """
    if prev.lens_mm_hint <= 0 or curr.lens_mm_hint <= 0:
        return False
    ratio = max(prev.lens_mm_hint, curr.lens_mm_hint) / min(
        prev.lens_mm_hint, curr.lens_mm_hint,
    )
    return ratio > 3.0


# ------------------------------------------------------------
# System
# ------------------------------------------------------------
@dataclasses.dataclass
class StoryboardSystem:
    """In-memory storyboard book."""
    _panels: dict[str, Panel] = dataclasses.field(default_factory=dict)

    def register_panel(self, panel: Panel) -> Panel:
        if panel.panel_id in self._panels:
            raise ValueError(
                f"panel already registered: {panel.panel_id}",
            )
        if panel.shot_index < 0:
            raise ValueError(
                f"shot_index must be >= 0: {panel.shot_index}",
            )
        if panel.lens_mm_hint < 0:
            raise ValueError(
                f"lens_mm_hint must be >= 0: {panel.lens_mm_hint}",
            )
        if panel.eye_trace not in ("left", "center", "right"):
            raise ValueError(
                f"eye_trace must be left|center|right: "
                f"{panel.eye_trace!r}",
            )
        if panel.axis_side not in ("A", "B"):
            raise ValueError(
                f"axis_side must be A or B: {panel.axis_side!r}",
            )
        if panel.has_dialogue and not panel.dialogue_excerpt:
            raise ValueError(
                "has_dialogue=True requires dialogue_excerpt",
            )
        self._panels[panel.panel_id] = panel
        return panel

    def lookup(self, panel_id: str) -> Panel:
        if panel_id not in self._panels:
            raise KeyError(f"unknown panel_id: {panel_id}")
        return self._panels[panel_id]

    def panels_for_scene(
        self, scene_id: str,
    ) -> tuple[Panel, ...]:
        out = sorted(
            (p for p in self._panels.values() if p.scene_id == scene_id),
            key=lambda p: p.shot_index,
        )
        return tuple(out)

    def panels_for_shot(
        self, scene_id: str, shot_index: int,
    ) -> tuple[Panel, ...]:
        return tuple(
            p for p in self._panels.values()
            if p.scene_id == scene_id and p.shot_index == shot_index
        )

    def sheet(
        self, scene_id: str, max_panels: int = 32,
        target_page_budget: float = 1.0,
    ) -> StoryboardSheet:
        if max_panels <= 0:
            raise ValueError("max_panels must be > 0")
        if target_page_budget <= 0:
            raise ValueError("target_page_budget must be > 0")
        panels = self.panels_for_scene(scene_id)
        return StoryboardSheet(
            scene_id=scene_id,
            panels=panels[:max_panels],
            target_page_budget=target_page_budget,
        )

    def validate_continuity_with(
        self, prev_panel_id: str, current: Panel,
    ) -> tuple[ContinuityIssue, ...]:
        prev = self.lookup(prev_panel_id)
        issues: list[ContinuityIssue] = []
        # 180-degree axis jump
        if (
            prev.axis_side != current.axis_side
            and not _axis_legal_crossing(prev, current)
        ):
            issues.append(
                ContinuityIssue(
                    panel_a=prev.panel_id,
                    panel_b=current.panel_id,
                    kind="axis_jump",
                    message=(
                        f"camera crossed 180° axis "
                        f"({prev.axis_side}->{current.axis_side}) "
                        f"without an INSERT/ECU bridge"
                    ),
                    severity="warning",
                ),
            )
        # Eye-trace break
        if _eye_trace_break(prev, current):
            issues.append(
                ContinuityIssue(
                    panel_a=prev.panel_id,
                    panel_b=current.panel_id,
                    kind="eye_trace_break",
                    message=(
                        f"eye-trace snaps "
                        f"{prev.eye_trace}->{current.eye_trace}"
                    ),
                    severity="note",
                ),
            )
        # Lens jump
        if _lens_jump(prev, current):
            issues.append(
                ContinuityIssue(
                    panel_a=prev.panel_id,
                    panel_b=current.panel_id,
                    kind="lens_jump",
                    message=(
                        f"focal length jump "
                        f"{prev.lens_mm_hint}mm -> "
                        f"{current.lens_mm_hint}mm"
                    ),
                    severity="note",
                ),
            )
        return tuple(issues)

    def all_panels(self) -> tuple[Panel, ...]:
        return tuple(self._panels.values())

    def panels_with_dialogue(self) -> tuple[Panel, ...]:
        return tuple(
            p for p in self._panels.values() if p.has_dialogue
        )

    def panel_count(self) -> int:
        return len(self._panels)


__all__ = [
    "AspectRatio", "Framing", "CameraMove",
    "Panel", "StoryboardSheet", "ContinuityIssue",
    "StoryboardSystem",
]
