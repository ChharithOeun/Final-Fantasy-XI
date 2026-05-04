"""Macro recorder — record/replay action sequences.

A player toggles RECORDING ON, performs a sequence of in-game
actions (cast Cure, equip set, item use, /sit), then toggles
recording OFF and BIND the resulting sequence to a macro slot
in macro_system or to a radial slot in macro_palette_radial.

Each captured action carries an inter-action delay so the
playback respects the original cadence without exceeding the
global cooldown floor.

Public surface
--------------
    ActionKind enum
    RecordedAction dataclass
    MacroRecording dataclass
    MacroRecorder
        .start(player_id, recording_id, label)
        .capture(player_id, kind, payload, at_seconds)
        .stop(player_id) -> MacroRecording
        .recording(player_id, recording_id)
        .delete(player_id, recording_id)
        .replay_lines(player_id, recording_id) -> list[macro lines]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Maximum captured actions per recording to avoid runaway logs.
MAX_ACTIONS_PER_RECORDING = 64
# Minimum allowed delay between replayed actions.
MIN_INTER_ACTION_DELAY = 0.5
MAX_INTER_ACTION_DELAY = 30.0


class ActionKind(str, enum.Enum):
    SPELL = "spell"
    JOB_ABILITY = "job_ability"
    WEAPONSKILL = "weaponskill"
    ITEM_USE = "item_use"
    EQUIP_SET = "equip_set"
    EMOTE = "emote"
    PET_COMMAND = "pet_command"
    SIT = "sit"
    UNSIT = "unsit"
    SAY = "say"


@dataclasses.dataclass(frozen=True)
class RecordedAction:
    seq_index: int
    kind: ActionKind
    payload: str
    at_seconds: float
    delay_after_seconds: float = 0.0


@dataclasses.dataclass
class MacroRecording:
    recording_id: str
    label: str
    actions: list[RecordedAction] = dataclasses.field(
        default_factory=list,
    )
    started_at_seconds: float = 0.0
    stopped_at_seconds: t.Optional[float] = None
    is_recording: bool = True


@dataclasses.dataclass(frozen=True)
class CaptureResult:
    accepted: bool
    action: t.Optional[RecordedAction] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class MacroRecorder:
    max_actions: int = MAX_ACTIONS_PER_RECORDING
    min_inter_delay: float = MIN_INTER_ACTION_DELAY
    max_inter_delay: float = MAX_INTER_ACTION_DELAY
    # (player_id, recording_id) -> MacroRecording
    _recordings: dict[
        tuple[str, str], MacroRecording,
    ] = dataclasses.field(default_factory=dict)
    # player_id -> active recording_id
    _active: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def start(
        self, *, player_id: str, recording_id: str,
        label: str = "",
        now_seconds: float = 0.0,
    ) -> t.Optional[MacroRecording]:
        if player_id in self._active:
            return None
        key = (player_id, recording_id)
        if key in self._recordings:
            return None
        rec = MacroRecording(
            recording_id=recording_id,
            label=label or recording_id,
            started_at_seconds=now_seconds,
            is_recording=True,
        )
        self._recordings[key] = rec
        self._active[player_id] = recording_id
        return rec

    def capture(
        self, *, player_id: str,
        kind: ActionKind, payload: str,
        at_seconds: float,
    ) -> CaptureResult:
        rid = self._active.get(player_id)
        if rid is None:
            return CaptureResult(
                False, reason="not recording",
            )
        rec = self._recordings.get((player_id, rid))
        if rec is None:
            return CaptureResult(
                False, reason="recording missing",
            )
        if len(rec.actions) >= self.max_actions:
            return CaptureResult(
                False, reason="recording full",
            )
        if not payload:
            return CaptureResult(
                False, reason="empty payload",
            )
        # Compute delay since previous action
        if rec.actions:
            prev = rec.actions[-1]
            raw_delay = at_seconds - prev.at_seconds
            delay = max(
                self.min_inter_delay,
                min(self.max_inter_delay, raw_delay),
            )
            # Update the previous action's delay_after now
            # that we know how long it lasted.
            updated = RecordedAction(
                seq_index=prev.seq_index,
                kind=prev.kind, payload=prev.payload,
                at_seconds=prev.at_seconds,
                delay_after_seconds=delay,
            )
            rec.actions[-1] = updated
        seq = len(rec.actions)
        action = RecordedAction(
            seq_index=seq, kind=kind, payload=payload,
            at_seconds=at_seconds,
            delay_after_seconds=0.0,
        )
        rec.actions.append(action)
        return CaptureResult(accepted=True, action=action)

    def stop(
        self, *, player_id: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[MacroRecording]:
        rid = self._active.pop(player_id, None)
        if rid is None:
            return None
        rec = self._recordings.get((player_id, rid))
        if rec is None:
            return None
        rec.is_recording = False
        rec.stopped_at_seconds = now_seconds
        return rec

    def recording(
        self, *, player_id: str, recording_id: str,
    ) -> t.Optional[MacroRecording]:
        return self._recordings.get(
            (player_id, recording_id),
        )

    def delete(
        self, *, player_id: str, recording_id: str,
    ) -> bool:
        key = (player_id, recording_id)
        if key not in self._recordings:
            return False
        if self._active.get(player_id) == recording_id:
            return False     # don't delete while recording
        del self._recordings[key]
        return True

    def replay_lines(
        self, *, player_id: str, recording_id: str,
    ) -> tuple[str, ...]:
        """Render a tuple of macro-line strings the macro_system
        can register. Each action becomes one line."""
        rec = self._recordings.get(
            (player_id, recording_id),
        )
        if rec is None or rec.is_recording:
            return ()
        out: list[str] = []
        for action in rec.actions:
            line = f"/{action.kind.value} {action.payload}"
            out.append(line)
            if action.delay_after_seconds > 0:
                out.append(
                    f"/wait {action.delay_after_seconds:.1f}",
                )
        return tuple(out)

    def is_recording(
        self, *, player_id: str,
    ) -> bool:
        return player_id in self._active

    def total_recordings(
        self, *, player_id: str,
    ) -> int:
        return sum(
            1 for (pid, _) in self._recordings
            if pid == player_id
        )


__all__ = [
    "MAX_ACTIONS_PER_RECORDING",
    "MIN_INTER_ACTION_DELAY",
    "MAX_INTER_ACTION_DELAY",
    "ActionKind",
    "RecordedAction", "MacroRecording",
    "CaptureResult",
    "MacroRecorder",
]
