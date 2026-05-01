"""ChaosMode camera operator — combat camera language.

Per CINEMATIC_GRAMMAR.md the active-combat camera doesn't replay a
pre-recorded Sequencer. It runs real-time per the ChaosMode operator
script:

| Event                           | Camera reaction                       |
|---------------------------------|---------------------------------------|
| (default)                       | third-person follow                   |
| skillchain_detonation           | 50ms whip toward halo, 200ms pause    |
| mb_landed                       | 100ms zoom-in, 300ms pause            |
| boss_phase_transition           | 1s slow-mo + tilt during armor drop   |
| intervention_mb_succeeded       | 200ms pulse toward intervening healer |
| player_wipe                     | 1.5s tilt up to sky as screen fades   |

These are auto-driven by the LSB combat broker pushing camera_event
messages. No director needed during play.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CameraEvent(str, enum.Enum):
    """Doc-named events the LSB combat broker emits."""
    DEFAULT = "default"
    SKILLCHAIN_DETONATION = "skillchain_detonation"
    MB_LANDED = "mb_landed"
    BOSS_PHASE_TRANSITION = "boss_phase_transition"
    INTERVENTION_MB_SUCCEEDED = "intervention_mb_succeeded"
    PLAYER_WIPE = "player_wipe"


@dataclasses.dataclass(frozen=True)
class ChaosReaction:
    """One row of the ChaosMode reaction table."""
    event: CameraEvent
    pre_motion_seconds: float       # whip / zoom duration
    hold_seconds: float             # pause after motion
    motion_kind: str                # 'whip_to_target' | 'zoom_in' | etc.
    use_slowmo: bool = False
    fade_target: t.Optional[str] = None    # 'sky' for wipe


REACTIONS: dict[CameraEvent, ChaosReaction] = {
    CameraEvent.DEFAULT: ChaosReaction(
        event=CameraEvent.DEFAULT,
        pre_motion_seconds=0.0,
        hold_seconds=0.0,
        motion_kind="follow",
    ),
    CameraEvent.SKILLCHAIN_DETONATION: ChaosReaction(
        event=CameraEvent.SKILLCHAIN_DETONATION,
        pre_motion_seconds=0.050,         # 50ms whip
        hold_seconds=0.200,                # 200ms pause
        motion_kind="whip_to_target",
    ),
    CameraEvent.MB_LANDED: ChaosReaction(
        event=CameraEvent.MB_LANDED,
        pre_motion_seconds=0.100,         # 100ms zoom-in
        hold_seconds=0.300,
        motion_kind="zoom_in_target",
    ),
    CameraEvent.BOSS_PHASE_TRANSITION: ChaosReaction(
        event=CameraEvent.BOSS_PHASE_TRANSITION,
        pre_motion_seconds=1.000,         # 1s slow-mo
        hold_seconds=0.0,
        motion_kind="tilt_during_armor_drop",
        use_slowmo=True,
    ),
    CameraEvent.INTERVENTION_MB_SUCCEEDED: ChaosReaction(
        event=CameraEvent.INTERVENTION_MB_SUCCEEDED,
        pre_motion_seconds=0.200,         # 200ms pulse
        hold_seconds=0.0,
        motion_kind="pulse_to_healer",
    ),
    CameraEvent.PLAYER_WIPE: ChaosReaction(
        event=CameraEvent.PLAYER_WIPE,
        pre_motion_seconds=1.500,         # 1.5s tilt
        hold_seconds=0.0,
        motion_kind="tilt_up_fade",
        fade_target="sky",
    ),
}


def get_reaction(event: CameraEvent) -> ChaosReaction:
    return REACTIONS[event]


def total_reaction_seconds(event: CameraEvent) -> float:
    """Total time the reaction occupies — pre_motion + hold."""
    r = REACTIONS[event]
    return r.pre_motion_seconds + r.hold_seconds


@dataclasses.dataclass
class CameraTimeline:
    """An ordered list of CameraEvents the operator script processed.

    Used for replay testing — feed a recorded combat event stream
    and verify the camera fires the right reactions in order.
    """
    events: list[tuple[float, CameraEvent]] = dataclasses.field(
        default_factory=list)

    def push(self, *, at_time: float, event: CameraEvent) -> None:
        self.events.append((at_time, event))

    def total_camera_time_in_window(self,
                                          *,
                                          start: float,
                                          end: float) -> float:
        """Sum of reaction durations from events that fired in
        [start, end]. Useful for tuning — cinematic shouldn't spend
        more than ~20%% of combat time in non-default reactions."""
        out = 0.0
        for t, ev in self.events:
            if start <= t <= end:
                out += total_reaction_seconds(ev)
        return out

    def event_count(self, event: CameraEvent) -> int:
        return sum(1 for _, ev in self.events if ev == event)
