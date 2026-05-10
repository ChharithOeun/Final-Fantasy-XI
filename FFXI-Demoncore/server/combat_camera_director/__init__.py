"""Combat camera director — when combat starts, the camera
becomes a director.

The player's camera_rig owns the rig in normal play —
follow-cam over the shoulder, snap to first-person on
toggle. When combat starts, this module *takes over*.
ENGAGE_START fires a 1.5s push-in that frames player +
target. SKILLCHAIN_OPEN cuts to a low-angle. MAGIC_BURST
holds on the impact. BOSS_INTRO is a 4s pull-back
establishing-shot. Each event has a CombatShot — shot kind,
duration, lens hint, focus priority — and an interrupt
priority that decides what overrides what.

The director is a state machine: NORMAL -> COMBAT_AUTO ->
CINEMATIC_SETPIECE -> BACK_TO_NORMAL. NORMAL is "rig owns
itself". COMBAT_AUTO is "director picks shot kinds for
ongoing combat". CINEMATIC_SETPIECE is "director runs a
specific sequence (boss intro, kill blow) for the
duration". BACK_TO_NORMAL is the brief return frame after
a setpiece ends.

Higher-priority events interrupt lower. BOSS_INTRO at 10
beats CRITICAL_HIT at 3. Equal priority: queue the new
event, run when current ends.

Murch six-axis cuts (emotion, story, rhythm, eye-trace,
2D-plane, 3D-space) drive should_cut_for: a critical hit
fires the rhythm + emotion axes -> cut even mid-shot. A
plain auto-attack scores low on all six -> hold the
current shot.

Public surface
--------------
    CombatCameraEvent enum
    DirectorState enum
    FocusPriority enum
    CombatShot dataclass (frozen)
    DirectorContext dataclass (frozen)
    CombatCameraDirector
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CombatCameraEvent(enum.Enum):
    ENGAGE_START = "engage_start"
    ENGAGE_END = "engage_end"
    SKILLCHAIN_OPEN = "skillchain_open"
    MAGIC_BURST_FIRED = "magic_burst_fired"
    BOSS_INTRO = "boss_intro"
    BOSS_PHASE_CHANGE = "boss_phase_change"
    PLAYER_DOWN = "player_down"
    RAISE_BEGIN = "raise_begin"
    CRITICAL_HIT = "critical_hit"
    KILL_BLOW = "kill_blow"
    ULTIMATE_ABILITY_USED = "ultimate_ability_used"


class DirectorState(enum.Enum):
    NORMAL = "normal"
    COMBAT_AUTO = "combat_auto"
    CINEMATIC_SETPIECE = "cinematic_setpiece"
    BACK_TO_NORMAL = "back_to_normal"


class FocusPriority(enum.Enum):
    MAIN_TARGET = "main_target"
    SUB_TARGET = "sub_target"
    PLAYER = "player"
    ATTACKER = "attacker"


@dataclasses.dataclass(frozen=True)
class CombatShot:
    shot_kind: str  # cf. director_ai shot vocabulary
    duration_s: float
    lens_mm_hint: float
    focus_target_priority: FocusPriority
    hand_back_to_player_rig_after: bool
    interrupt_priority: int  # 0..10


@dataclasses.dataclass(frozen=True)
class DirectorContext:
    player_id: str
    rig_id: str
    target_id: str = ""
    sub_target_id: str = ""
    attacker_id: str = ""


# Event -> default interrupt priority, used when an event
# is fired without a registered handler.
_DEFAULT_PRIORITY: dict[CombatCameraEvent, int] = {
    CombatCameraEvent.BOSS_INTRO: 10,
    CombatCameraEvent.PLAYER_DOWN: 9,
    CombatCameraEvent.BOSS_PHASE_CHANGE: 8,
    CombatCameraEvent.ULTIMATE_ABILITY_USED: 7,
    CombatCameraEvent.MAGIC_BURST_FIRED: 6,
    CombatCameraEvent.SKILLCHAIN_OPEN: 5,
    CombatCameraEvent.KILL_BLOW: 4,
    CombatCameraEvent.CRITICAL_HIT: 3,
    CombatCameraEvent.RAISE_BEGIN: 2,
    CombatCameraEvent.ENGAGE_START: 2,
    CombatCameraEvent.ENGAGE_END: 1,
}


# Murch's six-axis cut rules — each event scores on each
# axis, sum >= threshold means "cut now"; otherwise hold.
# Axes: emotion, story, rhythm, eye-trace, 2D plane, 3D space.
# Score 0..3 per axis, sum >= 12 (out of 18) triggers a cut.
_MURCH_SCORES: dict[
    CombatCameraEvent, tuple[int, int, int, int, int, int],
] = {
    CombatCameraEvent.BOSS_INTRO: (3, 3, 3, 3, 3, 3),
    CombatCameraEvent.PLAYER_DOWN: (3, 3, 3, 2, 2, 2),
    CombatCameraEvent.BOSS_PHASE_CHANGE: (3, 3, 3, 2, 2, 2),
    CombatCameraEvent.ULTIMATE_ABILITY_USED: (3, 2, 3, 2, 2, 2),
    CombatCameraEvent.MAGIC_BURST_FIRED: (2, 2, 3, 2, 2, 2),
    CombatCameraEvent.SKILLCHAIN_OPEN: (2, 2, 3, 1, 2, 2),
    CombatCameraEvent.KILL_BLOW: (3, 2, 2, 2, 1, 1),
    CombatCameraEvent.CRITICAL_HIT: (2, 1, 3, 1, 1, 1),
    CombatCameraEvent.RAISE_BEGIN: (2, 2, 1, 1, 1, 1),
    CombatCameraEvent.ENGAGE_START: (1, 2, 2, 2, 2, 2),
    CombatCameraEvent.ENGAGE_END: (1, 1, 1, 1, 1, 1),
}
_MURCH_THRESHOLD = 12
# Minimum hold-time before another cut, in seconds.
_MIN_CUT_INTERVAL_S = 0.6


@dataclasses.dataclass
class _SetpieceInternal:
    rig_id: str
    event: CombatCameraEvent
    shot: CombatShot
    elapsed_s: float = 0.0


@dataclasses.dataclass
class CombatCameraDirector:
    _handlers: dict[
        CombatCameraEvent, CombatShot,
    ] = dataclasses.field(default_factory=dict)
    _state_per_rig: dict[
        str, DirectorState,
    ] = dataclasses.field(default_factory=dict)
    _setpieces: dict[
        str, _SetpieceInternal,
    ] = dataclasses.field(default_factory=dict)
    _queued: dict[
        str, list[tuple[CombatCameraEvent, CombatShot]],
    ] = dataclasses.field(default_factory=dict)

    # ---------------------------------------------- handler
    def register_event_handler(
        self,
        event_kind: CombatCameraEvent,
        combat_shot: CombatShot,
    ) -> None:
        if combat_shot.duration_s <= 0:
            raise ValueError("duration_s must be > 0")
        if combat_shot.lens_mm_hint <= 0:
            raise ValueError("lens_mm_hint must be > 0")
        if not (0 <= combat_shot.interrupt_priority <= 10):
            raise ValueError(
                "interrupt_priority must be in 0..10",
            )
        if not combat_shot.shot_kind:
            raise ValueError("shot_kind required")
        self._handlers[event_kind] = combat_shot

    def handler_count(self) -> int:
        return len(self._handlers)

    def handler_for(
        self, event_kind: CombatCameraEvent,
    ) -> CombatShot | None:
        return self._handlers.get(event_kind)

    def populate_defaults(self) -> int:
        defaults: list[
            tuple[CombatCameraEvent, CombatShot]
        ] = [
            (CombatCameraEvent.ENGAGE_START, CombatShot(
                shot_kind="push_in_two_shot",
                duration_s=1.5, lens_mm_hint=50.0,
                focus_target_priority=FocusPriority.PLAYER,
                hand_back_to_player_rig_after=True,
                interrupt_priority=2,
            )),
            (CombatCameraEvent.ENGAGE_END, CombatShot(
                shot_kind="pullout_wide",
                duration_s=0.8, lens_mm_hint=35.0,
                focus_target_priority=FocusPriority.PLAYER,
                hand_back_to_player_rig_after=True,
                interrupt_priority=1,
            )),
            (CombatCameraEvent.SKILLCHAIN_OPEN, CombatShot(
                shot_kind="low_angle_close",
                duration_s=1.2, lens_mm_hint=85.0,
                focus_target_priority=FocusPriority.MAIN_TARGET,
                hand_back_to_player_rig_after=True,
                interrupt_priority=5,
            )),
            (CombatCameraEvent.MAGIC_BURST_FIRED, CombatShot(
                shot_kind="impact_hold",
                duration_s=0.9, lens_mm_hint=100.0,
                focus_target_priority=FocusPriority.MAIN_TARGET,
                hand_back_to_player_rig_after=True,
                interrupt_priority=6,
            )),
            (CombatCameraEvent.BOSS_INTRO, CombatShot(
                shot_kind="establishing_pullback",
                duration_s=4.0, lens_mm_hint=24.0,
                focus_target_priority=FocusPriority.MAIN_TARGET,
                hand_back_to_player_rig_after=True,
                interrupt_priority=10,
            )),
            (CombatCameraEvent.BOSS_PHASE_CHANGE, CombatShot(
                shot_kind="orbit_reveal",
                duration_s=2.5, lens_mm_hint=35.0,
                focus_target_priority=FocusPriority.MAIN_TARGET,
                hand_back_to_player_rig_after=True,
                interrupt_priority=8,
            )),
            (CombatCameraEvent.PLAYER_DOWN, CombatShot(
                shot_kind="ko_orbit_slow",
                duration_s=3.0, lens_mm_hint=50.0,
                focus_target_priority=FocusPriority.PLAYER,
                hand_back_to_player_rig_after=False,
                interrupt_priority=9,
            )),
            (CombatCameraEvent.RAISE_BEGIN, CombatShot(
                shot_kind="rise_up_pan",
                duration_s=2.0, lens_mm_hint=50.0,
                focus_target_priority=FocusPriority.PLAYER,
                hand_back_to_player_rig_after=True,
                interrupt_priority=2,
            )),
            (CombatCameraEvent.CRITICAL_HIT, CombatShot(
                shot_kind="quick_zoom",
                duration_s=0.5, lens_mm_hint=85.0,
                focus_target_priority=FocusPriority.MAIN_TARGET,
                hand_back_to_player_rig_after=True,
                interrupt_priority=3,
            )),
            (CombatCameraEvent.KILL_BLOW, CombatShot(
                shot_kind="finishing_slowdown",
                duration_s=1.0, lens_mm_hint=85.0,
                focus_target_priority=FocusPriority.MAIN_TARGET,
                hand_back_to_player_rig_after=True,
                interrupt_priority=4,
            )),
            (CombatCameraEvent.ULTIMATE_ABILITY_USED, CombatShot(
                shot_kind="dramatic_pullout_circle",
                duration_s=2.5, lens_mm_hint=35.0,
                focus_target_priority=FocusPriority.PLAYER,
                hand_back_to_player_rig_after=True,
                interrupt_priority=7,
            )),
        ]
        n = 0
        for ev, shot in defaults:
            self.register_event_handler(ev, shot)
            n += 1
        return n

    # ---------------------------------------------- state
    def state_for(self, rig_id: str) -> DirectorState:
        return self._state_per_rig.get(
            rig_id, DirectorState.NORMAL,
        )

    def transition_to(
        self, rig_id: str, state: DirectorState,
    ) -> DirectorState:
        prev = self.state_for(rig_id)
        self._state_per_rig[rig_id] = state
        return prev

    # ---------------------------------------------- trigger
    def trigger(
        self,
        event_kind: CombatCameraEvent,
        context: DirectorContext,
    ) -> CombatShot | None:
        shot = self._handlers.get(event_kind)
        if shot is None:
            return None
        rig_id = context.rig_id
        # Already running a setpiece — interrupt-or-queue.
        if rig_id in self._setpieces:
            cur = self._setpieces[rig_id]
            if (
                shot.interrupt_priority
                > cur.shot.interrupt_priority
            ):
                # Higher priority — interrupt
                self._setpieces[rig_id] = _SetpieceInternal(
                    rig_id=rig_id,
                    event=event_kind,
                    shot=shot,
                )
                self._state_per_rig[rig_id] = (
                    DirectorState.CINEMATIC_SETPIECE
                )
                return shot
            else:
                # Lower or equal — queue
                self._queued.setdefault(rig_id, []).append(
                    (event_kind, shot),
                )
                return None
        # Nothing running — start setpiece
        self._setpieces[rig_id] = _SetpieceInternal(
            rig_id=rig_id,
            event=event_kind,
            shot=shot,
        )
        self._state_per_rig[rig_id] = (
            DirectorState.CINEMATIC_SETPIECE
        )
        return shot

    def interrupt_with(
        self,
        event_kind: CombatCameraEvent,
        context: DirectorContext,
    ) -> CombatShot | None:
        return self.trigger(event_kind, context)

    def current_setpiece(self, rig_id: str) -> CombatShot | None:
        sp = self._setpieces.get(rig_id)
        return sp.shot if sp else None

    def current_event(
        self, rig_id: str,
    ) -> CombatCameraEvent | None:
        sp = self._setpieces.get(rig_id)
        return sp.event if sp else None

    def queued_count(self, rig_id: str) -> int:
        return len(self._queued.get(rig_id, []))

    # ---------------------------------------------- end
    def ends_setpiece(
        self, rig_id: str,
    ) -> CombatShot | None:
        if rig_id not in self._setpieces:
            return None
        del self._setpieces[rig_id]
        # Pop queued events: re-trigger highest priority
        # queued event next.
        q = self._queued.get(rig_id, [])
        if q:
            q.sort(
                key=lambda it: -it[1].interrupt_priority,
            )
            ev, shot = q.pop(0)
            self._queued[rig_id] = q
            self._setpieces[rig_id] = _SetpieceInternal(
                rig_id=rig_id, event=ev, shot=shot,
            )
            self._state_per_rig[rig_id] = (
                DirectorState.CINEMATIC_SETPIECE
            )
            return shot
        # No queue — hand back to normal
        self._state_per_rig[rig_id] = (
            DirectorState.BACK_TO_NORMAL
        )
        return None

    def tick(self, rig_id: str, dt: float) -> CombatShot | None:
        if dt < 0:
            raise ValueError("dt must be >= 0")
        sp = self._setpieces.get(rig_id)
        if sp is None:
            return None
        sp.elapsed_s += dt
        if sp.elapsed_s >= sp.shot.duration_s:
            return self.ends_setpiece(rig_id)
        return sp.shot

    # ---------------------------------------------- Murch
    def should_cut_for(
        self,
        event_kind: CombatCameraEvent,
        time_since_last_cut_s: float,
        scene_state: t.Mapping[str, t.Any] | None = None,
    ) -> bool:
        if time_since_last_cut_s < _MIN_CUT_INTERVAL_S:
            return False
        scores = _MURCH_SCORES.get(event_kind)
        if scores is None:
            return False
        total = sum(scores)
        # Dramatic scenes (boss-fight bool) raise threshold
        # by 1, demanding stronger justification.
        thresh = _MURCH_THRESHOLD
        ss = dict(scene_state or {})
        if ss.get("dramatic_hold", False):
            thresh += 1
        return total >= thresh

    def murch_score(
        self, event_kind: CombatCameraEvent,
    ) -> int:
        scores = _MURCH_SCORES.get(event_kind)
        return sum(scores) if scores else 0

    # ---------------------------------------------- priority
    def default_priority_for(
        self, event_kind: CombatCameraEvent,
    ) -> int:
        return _DEFAULT_PRIORITY.get(event_kind, 0)


__all__ = [
    "CombatCameraEvent",
    "DirectorState",
    "FocusPriority",
    "CombatShot",
    "DirectorContext",
    "CombatCameraDirector",
]
