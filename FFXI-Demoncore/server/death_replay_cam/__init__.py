"""Death replay cam — permadeath last-N-seconds buffer.

A permadeath player's death is too important to forget. The
death_replay_cam captures the last 30 seconds of their combat
state — incoming attacks, used abilities, party positions, mob
ids — into a per-player ring buffer. On permadeath, the buffer
freezes and is published to the memorial_registry so other
players can reverently review what went wrong (or what went
heroically right).

Frames are SAMPLED, not recorded continuously — typically one
sample per second (configurable). Each frame carries the
attacker, the player's HP%, what action they were executing,
and party teammate HP%. Lightweight enough to leave running.

Public surface
--------------
    FrameKind enum
    ReplayFrame dataclass
    ReplayClip dataclass
    DeathReplayCam
        .capture_frame(player_id, kind, ...)
        .freeze_on_death(player_id) -> ReplayClip
        .clip_for(player_id) -> Optional[ReplayClip]
"""
from __future__ import annotations

import collections
import dataclasses
import enum
import typing as t


# Default clip window in seconds.
DEFAULT_BUFFER_WINDOW_SECONDS = 30
DEFAULT_SAMPLE_INTERVAL_SECONDS = 1.0
MAX_FRAMES_PER_BUFFER = 64


class FrameKind(str, enum.Enum):
    IDLE = "idle"
    AUTO_ATTACK = "auto_attack"
    WEAPONSKILL = "weaponskill"
    SPELL_CAST = "spell_cast"
    JOB_ABILITY = "job_ability"
    DAMAGE_TAKEN = "damage_taken"
    HEAL_RECEIVED = "heal_received"
    KO_HIT = "ko_hit"           # the killing blow
    DODGE = "dodge"
    DEFEAT = "defeat"


@dataclasses.dataclass(frozen=True)
class ReplayFrame:
    timestamp_seconds: float
    kind: FrameKind
    player_hp_pct: int
    actor_id: t.Optional[str]   # who acted (player or attacker)
    target_id: t.Optional[str]
    detail: str = ""
    party_hp_pcts: tuple[tuple[str, int], ...] = ()


@dataclasses.dataclass(frozen=True)
class ReplayClip:
    player_id: str
    captured_at_seconds: float
    window_seconds: int
    frames: tuple[ReplayFrame, ...]
    cause_of_death: t.Optional[str] = None


@dataclasses.dataclass
class DeathReplayCam:
    buffer_window_seconds: int = DEFAULT_BUFFER_WINDOW_SECONDS
    max_frames: int = MAX_FRAMES_PER_BUFFER
    _buffers: dict[
        str, collections.deque,
    ] = dataclasses.field(default_factory=dict)
    _frozen_clips: dict[str, ReplayClip] = dataclasses.field(
        default_factory=dict,
    )

    def capture_frame(
        self, *, player_id: str, kind: FrameKind,
        timestamp_seconds: float,
        player_hp_pct: int,
        actor_id: t.Optional[str] = None,
        target_id: t.Optional[str] = None,
        detail: str = "",
        party_hp_pcts: tuple[
            tuple[str, int], ...,
        ] = (),
    ) -> ReplayFrame:
        if player_id not in self._buffers:
            self._buffers[player_id] = collections.deque(
                maxlen=self.max_frames,
            )
        frame = ReplayFrame(
            timestamp_seconds=timestamp_seconds,
            kind=kind,
            player_hp_pct=max(0, min(100, player_hp_pct)),
            actor_id=actor_id, target_id=target_id,
            detail=detail,
            party_hp_pcts=party_hp_pcts,
        )
        self._buffers[player_id].append(frame)
        # Prune frames older than window
        cutoff = (
            timestamp_seconds - self.buffer_window_seconds
        )
        buf = self._buffers[player_id]
        while buf and buf[0].timestamp_seconds < cutoff:
            buf.popleft()
        return frame

    def freeze_on_death(
        self, *, player_id: str,
        captured_at_seconds: float,
        cause_of_death: t.Optional[str] = None,
    ) -> t.Optional[ReplayClip]:
        buf = self._buffers.get(player_id)
        if buf is None or not buf:
            return None
        clip = ReplayClip(
            player_id=player_id,
            captured_at_seconds=captured_at_seconds,
            window_seconds=self.buffer_window_seconds,
            frames=tuple(buf),
            cause_of_death=cause_of_death,
        )
        self._frozen_clips[player_id] = clip
        # Clear the live buffer so subsequent captures don't
        # contaminate the frozen clip
        del self._buffers[player_id]
        return clip

    def clip_for(
        self, player_id: str,
    ) -> t.Optional[ReplayClip]:
        return self._frozen_clips.get(player_id)

    def reset_buffer(self, *, player_id: str) -> bool:
        if player_id not in self._buffers:
            return False
        del self._buffers[player_id]
        return True

    def total_active_buffers(self) -> int:
        return len(self._buffers)

    def total_frozen_clips(self) -> int:
        return len(self._frozen_clips)


__all__ = [
    "DEFAULT_BUFFER_WINDOW_SECONDS",
    "DEFAULT_SAMPLE_INTERVAL_SECONDS",
    "MAX_FRAMES_PER_BUFFER",
    "FrameKind", "ReplayFrame", "ReplayClip",
    "DeathReplayCam",
]
