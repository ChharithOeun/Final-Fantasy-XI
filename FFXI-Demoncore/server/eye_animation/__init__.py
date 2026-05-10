"""Eye animation — microsaccades, blinks, look-at, pupils.

Eyes are the cheapest tell in a "is this character alive?"
test. A character whose eyes never blink and never move
reads as a wax dummy from across the room. This module
runs the per-NPC eye state at ~60 Hz and exposes the look-
at-target socket the crowd_director uses for player
glances.

Blink rates per mood (blinks per minute):

    CALM        17
    FOCUSED     12
    ANXIOUS     30
    IN_COMBAT    8   (suppressed; combat focus)
    DEAD         0

Pupil diameter (mm) is a function of scene illuminance and
mood. Bright sun (~80 000 lux) constricts pupils to ~2 mm;
a dim cave (~5 lux) opens them to ~7 mm. Fear adds a 1 mm
sympathetic dilation spike on top.

Look-at: when a target NPC enters the engagement radius,
``set_look_target`` records the contact. Each ``update``
bleeds the look-toward direction toward the target's xyz
and accumulates a hold timer. After 2 to 4 s the eyes dart
away (``release_target``) — that's the social-natural
glance shape.

Tear sim: emotional beats (WEARY, AFRAID, TENDER) push tear
amount up; calm beats decay it. Coupled to performance
direction's intent_tag.

Public surface
--------------
    Mood enum
    EyeState dataclass
    EyeAnimationSystem
    BLINK_RATE_PER_MIN
"""
from __future__ import annotations

import dataclasses
import enum
import math
import random
import typing as t


class Mood(enum.Enum):
    CALM = "calm"
    FOCUSED = "focused"
    ANXIOUS = "anxious"
    IN_COMBAT = "in_combat"
    DEAD = "dead"


BLINK_RATE_PER_MIN: dict[Mood, float] = {
    Mood.CALM: 17.0,
    Mood.FOCUSED: 12.0,
    Mood.ANXIOUS: 30.0,
    Mood.IN_COMBAT: 8.0,
    Mood.DEAD: 0.0,
}


# Tear-driving intent tags. WEARY / AFRAID / TENDER push
# tear_amount toward 1.0; everything else decays it.
_TEAR_INTENTS: frozenset[str] = frozenset({
    "WEARY", "AFRAID", "TENDER",
})


@dataclasses.dataclass
class EyeState:
    npc_id: str
    look_at_target_id: str | None = None
    gaze_direction_xyz: tuple[float, float, float] = (
        0.0, 0.0, 1.0,
    )
    blink_phase: float = 0.5  # 0..1 cyclic
    microsaccade_amplitude_deg: float = 0.0
    saccade_velocity_dps: float = 0.0
    pupil_diameter_mm: float = 4.0
    tear_amount: float = 0.0
    contact_hold_s: float = 0.0
    is_sleeping: bool = False


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _illum_to_pupil_mm(scene_lux: float) -> float:
    """Tuned log-curve. Bright daylight (~80 000 lux) ->
    2 mm; dim cave (~5 lux) -> ~7 mm. Linear interpolation
    in log10 lux between hand-picked anchors."""
    if scene_lux < 0:
        scene_lux = 0.0
    # Anchors: (lux, pupil_mm). Sorted ascending in lux.
    anchors = (
        (0.1, 7.0),
        (10.0, 6.5),
        (100.0, 5.0),
        (1000.0, 4.0),
        (10_000.0, 3.0),
        (80_000.0, 2.0),
    )
    if scene_lux <= anchors[0][0]:
        return anchors[0][1]
    if scene_lux >= anchors[-1][0]:
        return anchors[-1][1]
    for (l1, p1), (l2, p2) in zip(anchors, anchors[1:]):
        if l1 <= scene_lux <= l2:
            # Linear interp in log10.
            t_ = (
                (math.log10(scene_lux) - math.log10(l1))
                / (math.log10(l2) - math.log10(l1))
            )
            return _clamp(p1 + t_ * (p2 - p1), 2.0, 7.0)
    return _clamp(anchors[-1][1], 2.0, 7.0)


@dataclasses.dataclass
class EyeAnimationSystem:
    engagement_radius_m: float = 6.0
    contact_hold_min_s: float = 2.0
    contact_hold_max_s: float = 4.0
    seed: int = 0xE7E5  # deterministic by default
    _states: dict[str, EyeState] = dataclasses.field(
        default_factory=dict,
    )
    _rng: random.Random | None = dataclasses.field(
        default=None, init=False,
    )

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        if self.engagement_radius_m <= 0:
            raise ValueError(
                "engagement_radius_m must be > 0",
            )
        if not (
            0.0
            < self.contact_hold_min_s
            <= self.contact_hold_max_s
        ):
            raise ValueError(
                "contact_hold_min/max ordering invalid",
            )

    # ---- registration ----

    def register_eyes(self, npc_id: str) -> EyeState:
        if not npc_id:
            raise ValueError("npc_id required")
        if npc_id in self._states:
            raise ValueError(
                f"already registered: {npc_id}",
            )
        st = EyeState(npc_id=npc_id)
        self._states[npc_id] = st
        return st

    def get(self, npc_id: str) -> EyeState:
        if npc_id not in self._states:
            raise KeyError(f"unknown npc: {npc_id}")
        return self._states[npc_id]

    def has(self, npc_id: str) -> bool:
        return npc_id in self._states

    # ---- look-at ----

    def set_look_target(
        self, npc_id: str, target_id: str | None,
    ) -> None:
        st = self.get(npc_id)
        if target_id != st.look_at_target_id:
            st.contact_hold_s = 0.0
        st.look_at_target_id = target_id

    def is_currently_looking_at(
        self, npc_id: str, target_id: str,
    ) -> bool:
        return self.get(npc_id).look_at_target_id == target_id

    def release_target(self, npc_id: str) -> None:
        self.set_look_target(npc_id, None)

    # ---- per-step update ----

    def update(
        self,
        npc_id: str,
        dt: float,
        scene_lux: float,
        mood: Mood,
        intent_tag: str | None = None,
    ) -> EyeState:
        if dt <= 0:
            raise ValueError("dt must be > 0")
        st = self.get(npc_id)
        if mood == Mood.DEAD:
            # Eyes open, no blink, no saccade, no tears.
            st.blink_phase = 0.5
            st.microsaccade_amplitude_deg = 0.0
            st.saccade_velocity_dps = 0.0
            st.pupil_diameter_mm = 4.0
            st.tear_amount = 0.0
            return st
        if st.is_sleeping:
            # Eyes closed, no microsaccades.
            st.blink_phase = 0.075  # mid-closed
            st.microsaccade_amplitude_deg = 0.0
            return st
        # Blink advance: blink_phase wraps 0..1 over the
        # blink-cycle period derived from the mood rate.
        rate = BLINK_RATE_PER_MIN[mood]
        if rate > 0:
            cycle_s = 60.0 / rate
            advance = dt / cycle_s
            st.blink_phase = (st.blink_phase + advance) % 1.0
        else:
            st.blink_phase = 0.5
        # Microsaccades — 1-2 per second, 0.1-1 deg.
        # Sample an amplitude every step.
        st.microsaccade_amplitude_deg = round(
            self._rng.uniform(0.1, 1.0), 4,
        )
        # Velocity in deg/s: amplitude / dt.
        st.saccade_velocity_dps = round(
            st.microsaccade_amplitude_deg / max(dt, 1e-3),
            2,
        )
        # Pupil diameter — illuminance + fear bump.
        base = _illum_to_pupil_mm(scene_lux)
        if mood == Mood.ANXIOUS:
            base = min(7.0, base + 1.0)
        st.pupil_diameter_mm = round(base, 3)
        # Tear sim — push toward 1 if intent tag is tear-
        # friendly; decay otherwise.
        if intent_tag and intent_tag.upper() in _TEAR_INTENTS:
            st.tear_amount = _clamp(
                st.tear_amount + 0.4 * dt, 0.0, 1.0,
            )
        else:
            st.tear_amount = _clamp(
                st.tear_amount - 0.2 * dt, 0.0, 1.0,
            )
        # Contact hold timer.
        if st.look_at_target_id is not None:
            st.contact_hold_s += dt
            if st.contact_hold_s > self.contact_hold_max_s:
                # Dart away.
                st.look_at_target_id = None
                st.contact_hold_s = 0.0
        return st

    def blink_now(self, npc_id: str) -> None:
        """Force a blink: phase resets to 0 (closing)."""
        self.get(npc_id).blink_phase = 0.0

    def is_blinking(self, npc_id: str) -> bool:
        """True iff the eye is closed or in motion to close."""
        ph = self.get(npc_id).blink_phase
        return ph < 0.15

    def is_eye_closed(self, npc_id: str) -> bool:
        ph = self.get(npc_id).blink_phase
        return 0.05 <= ph < 0.10

    def tear_amount(self, npc_id: str) -> float:
        return self.get(npc_id).tear_amount

    # ---- engagement ----

    def npcs_engaging_with(
        self,
        target_id: str,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                npc_id for npc_id, st in self._states.items()
                if st.look_at_target_id == target_id
            )
        )

    def in_engagement_range(
        self,
        npc_pos: tuple[float, float, float],
        target_pos: tuple[float, float, float],
    ) -> bool:
        d = math.sqrt(
            (npc_pos[0] - target_pos[0]) ** 2
            + (npc_pos[1] - target_pos[1]) ** 2
            + (npc_pos[2] - target_pos[2]) ** 2
        )
        return d <= self.engagement_radius_m

    def set_sleeping(self, npc_id: str, sleeping: bool) -> None:
        self.get(npc_id).is_sleeping = sleeping

    def all_npcs(self) -> tuple[str, ...]:
        return tuple(sorted(self._states.keys()))


__all__ = [
    "Mood",
    "EyeState",
    "EyeAnimationSystem",
    "BLINK_RATE_PER_MIN",
]
