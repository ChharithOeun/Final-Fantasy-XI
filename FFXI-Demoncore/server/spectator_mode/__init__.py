"""Spectator mode — watch other players for streaming,
esports, and demo replay.

The streamer wants a clean broadcast feed. The esports
caster wants a director-cam with the action picked
auto. The replay viewer wants to scrub the last sixty
seconds and save the kill. Spectator mode is the layer
that delivers all three from one source — the
net_replication snapshot stream, the director_ai shot
picker, and a sixty-second rolling per-player buffer.

Six SpectatorMode values:
- FREE_CAM — fly anywhere
- FOLLOW_PLAYER — orbit the watched player
- DIRECTOR_CAM — auto-pick the best angle from director_ai
- POV_INSIDE_PLAYER — first-person as the watched player
- REPLAY_PLAYBACK — play the saved replay clip
- BROADCAST_OVERLAY — esports HUD on top (party comp left,
  party comp right, DPS chart bottom, current target
  middle-top)

Replay buffer: ROLLING_BUFFER_SECONDS=60 of snapshots per
active player. Trigger save on any of CRITICAL_KILL,
WORLD_FIRST_NM, MAGIC_BURST_BOSS_KILL, DEATH. The save
flips a copy out of the rolling buffer into permanent
storage and returns a clip handle.

Streaming hooks emit OBS-compatible NDI / RTMP metadata
— scene name, source ids, suggested cuts. Per-event
scene-switch suggestions ("boss phase changed → cut to
wide") drive the caster's automation.

Public surface
--------------
    SpectatorMode enum
    ReplayEvent enum
    SpectatorSession dataclass (frozen)
    ReplayClip dataclass (frozen)
    SceneSwitchSuggestion dataclass (frozen)
    SpectatorSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Rolling replay buffer length (seconds).
ROLLING_BUFFER_SECONDS = 60

# Default permitted zoom range (meters from subject).
DEFAULT_ZOOM_MIN_M = 1.5
DEFAULT_ZOOM_MAX_M = 30.0


class SpectatorMode(enum.Enum):
    FREE_CAM = "free_cam"
    FOLLOW_PLAYER = "follow_player"
    DIRECTOR_CAM = "director_cam"
    POV_INSIDE_PLAYER = "pov_inside_player"
    REPLAY_PLAYBACK = "replay_playback"
    BROADCAST_OVERLAY = "broadcast_overlay"


class ReplayEvent(enum.Enum):
    CRITICAL_KILL = "critical_kill"
    WORLD_FIRST_NM = "world_first_nm"
    MAGIC_BURST_BOSS_KILL = "magic_burst_boss_kill"
    DEATH = "death"


@dataclasses.dataclass(frozen=True)
class SpectatorSession:
    spec_id: str
    watched_player_id: str
    mode: SpectatorMode
    broadcast_overlay_visible: bool
    friendly_names_visible: bool
    hp_bars_visible: bool
    dps_visible: bool
    allowed_zoom_range_m: tuple[float, float]


@dataclasses.dataclass(frozen=True)
class ReplayClip:
    clip_id: str
    player_id: str
    event_kind: ReplayEvent
    saved_at_ms: int
    span_start_ms: int
    span_end_ms: int
    file_path_stub: str


@dataclasses.dataclass(frozen=True)
class SceneSwitchSuggestion:
    cue: str           # human cue ("boss phase changed")
    target_scene: str  # OBS scene name
    reason: str


@dataclasses.dataclass
class _BufferEntry:
    ts_ms: int
    snapshot_summary: dict


@dataclasses.dataclass
class _SessionInternal:
    session: SpectatorSession


@dataclasses.dataclass
class SpectatorSystem:
    _sessions: dict[str, _SessionInternal] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> rolling buffer
    _buffer: dict[str, list[_BufferEntry]] = dataclasses.field(
        default_factory=dict,
    )
    # clip_id -> ReplayClip
    _clips: dict[str, ReplayClip] = dataclasses.field(
        default_factory=dict,
    )
    _clip_counter: int = 0

    # ---------------------------------------------- sessions
    def start_spectator(
        self,
        spec_id: str,
        watched_player_id: str,
        mode: SpectatorMode,
    ) -> SpectatorSession:
        if not spec_id:
            raise ValueError("spec_id required")
        if not watched_player_id:
            raise ValueError("watched_player_id required")
        if spec_id in self._sessions:
            raise ValueError(
                f"duplicate spec_id: {spec_id}",
            )
        sess = SpectatorSession(
            spec_id=spec_id,
            watched_player_id=watched_player_id,
            mode=mode,
            broadcast_overlay_visible=(
                mode == SpectatorMode.BROADCAST_OVERLAY
            ),
            friendly_names_visible=True,
            hp_bars_visible=True,
            dps_visible=(
                mode == SpectatorMode.BROADCAST_OVERLAY
            ),
            allowed_zoom_range_m=(
                DEFAULT_ZOOM_MIN_M, DEFAULT_ZOOM_MAX_M,
            ),
        )
        self._sessions[spec_id] = _SessionInternal(session=sess)
        return sess

    def end_spectator(self, spec_id: str) -> None:
        if spec_id not in self._sessions:
            raise KeyError(f"unknown spec_id: {spec_id}")
        del self._sessions[spec_id]

    def get_session(self, spec_id: str) -> SpectatorSession:
        if spec_id not in self._sessions:
            raise KeyError(f"unknown spec_id: {spec_id}")
        return self._sessions[spec_id].session

    def session_count(self) -> int:
        return len(self._sessions)

    def has_session(self, spec_id: str) -> bool:
        return spec_id in self._sessions

    # ---------------------------------------------- mode
    def set_mode(
        self,
        spec_id: str,
        mode: SpectatorMode,
    ) -> SpectatorSession:
        if spec_id not in self._sessions:
            raise KeyError(f"unknown spec_id: {spec_id}")
        cur = self._sessions[spec_id].session
        new = dataclasses.replace(
            cur,
            mode=mode,
            broadcast_overlay_visible=(
                mode == SpectatorMode.BROADCAST_OVERLAY
            ),
            dps_visible=(
                mode == SpectatorMode.BROADCAST_OVERLAY
            ),
        )
        self._sessions[spec_id].session = new
        return new

    def set_overlay_visibility(
        self,
        spec_id: str,
        *,
        friendly_names: t.Optional[bool] = None,
        hp_bars: t.Optional[bool] = None,
        dps: t.Optional[bool] = None,
    ) -> SpectatorSession:
        if spec_id not in self._sessions:
            raise KeyError(f"unknown spec_id: {spec_id}")
        cur = self._sessions[spec_id].session
        new = dataclasses.replace(
            cur,
            friendly_names_visible=(
                friendly_names
                if friendly_names is not None
                else cur.friendly_names_visible
            ),
            hp_bars_visible=(
                hp_bars
                if hp_bars is not None
                else cur.hp_bars_visible
            ),
            dps_visible=(
                dps if dps is not None else cur.dps_visible
            ),
        )
        self._sessions[spec_id].session = new
        return new

    def set_zoom_range(
        self,
        spec_id: str,
        min_m: float,
        max_m: float,
    ) -> SpectatorSession:
        if spec_id not in self._sessions:
            raise KeyError(f"unknown spec_id: {spec_id}")
        if min_m < 0 or max_m < 0:
            raise ValueError("zoom range must be >= 0")
        if min_m > max_m:
            raise ValueError("min_m must be <= max_m")
        cur = self._sessions[spec_id].session
        new = dataclasses.replace(
            cur, allowed_zoom_range_m=(min_m, max_m),
        )
        self._sessions[spec_id].session = new
        return new

    # ---------------------------------------------- buffer
    def push_snapshot(
        self,
        player_id: str,
        ts_ms: int,
        snapshot_summary: dict,
    ) -> int:
        if not player_id:
            raise ValueError("player_id required")
        buf = self._buffer.setdefault(player_id, [])
        buf.append(
            _BufferEntry(
                ts_ms=ts_ms,
                snapshot_summary=snapshot_summary,
            ),
        )
        # Drop anything older than buffer length.
        cutoff = ts_ms - ROLLING_BUFFER_SECONDS * 1000
        self._buffer[player_id] = [
            e for e in buf if e.ts_ms >= cutoff
        ]
        return len(self._buffer[player_id])

    def replay_buffer_for(
        self,
        player_id: str,
    ) -> tuple[tuple[int, dict], ...]:
        return tuple(
            (e.ts_ms, e.snapshot_summary)
            for e in self._buffer.get(player_id, [])
        )

    def buffer_size(self, player_id: str) -> int:
        return len(self._buffer.get(player_id, []))

    # ---------------------------------------------- save
    def save_replay(
        self,
        player_id: str,
        event_kind: ReplayEvent,
        timestamp_ms: int,
    ) -> ReplayClip:
        if not player_id:
            raise ValueError("player_id required")
        buf = self._buffer.get(player_id, [])
        if not buf:
            raise ValueError(
                "no buffer entries to save",
            )
        self._clip_counter += 1
        clip_id = (
            f"clip_{player_id}_{self._clip_counter}"
        )
        span_start = max(
            buf[0].ts_ms,
            timestamp_ms - ROLLING_BUFFER_SECONDS * 1000,
        )
        clip = ReplayClip(
            clip_id=clip_id,
            player_id=player_id,
            event_kind=event_kind,
            saved_at_ms=timestamp_ms,
            span_start_ms=span_start,
            span_end_ms=timestamp_ms,
            file_path_stub=(
                f"replays/{player_id}/{clip_id}.mp4"
            ),
        )
        self._clips[clip_id] = clip
        return clip

    def get_clip(self, clip_id: str) -> ReplayClip:
        if clip_id not in self._clips:
            raise KeyError(f"unknown clip_id: {clip_id}")
        return self._clips[clip_id]

    def clip_count(self) -> int:
        return len(self._clips)

    # ---------------------------------------------- broadcast
    def broadcast_metadata_for(
        self,
        spec_id: str,
    ) -> dict:
        if spec_id not in self._sessions:
            raise KeyError(f"unknown spec_id: {spec_id}")
        sess = self._sessions[spec_id].session
        # Emit NDI + RTMP-friendly metadata.
        return {
            "ndi_source_name": f"demoncore_{spec_id}",
            "rtmp_stream_key": f"demoncore-{spec_id}",
            "scene_name": (
                f"watching_{sess.watched_player_id}"
            ),
            "overlay_visible": (
                sess.broadcast_overlay_visible
            ),
            "elements": {
                "party_comp_left": True,
                "party_comp_right": (
                    sess.mode == SpectatorMode.BROADCAST_OVERLAY
                ),
                "dps_chart_bottom": sess.dps_visible,
                "current_target_top": True,
            },
            "mode": sess.mode.value,
            "friendly_names": sess.friendly_names_visible,
            "hp_bars": sess.hp_bars_visible,
        }

    def suggest_scene_switch(
        self,
        cue: str,
    ) -> SceneSwitchSuggestion:
        # Stateless mapping — common cues to OBS scene names.
        mapping = {
            "boss_phase_changed": (
                "wide_combat",
                "phase change deserves a wide reset",
            ),
            "critical_kill": (
                "subject_close",
                "tight on the player who got the kill",
            ),
            "world_first_nm": (
                "celebration",
                "switch to all-party reaction overlay",
            ),
            "magic_burst_boss_kill": (
                "vfx_replay",
                "queue the slow-mo replay scene",
            ),
            "death": (
                "wide_combat",
                "pull wide for context on the wipe",
            ),
        }
        if cue not in mapping:
            return SceneSwitchSuggestion(
                cue=cue,
                target_scene="default",
                reason="no rule",
            )
        scene, reason = mapping[cue]
        return SceneSwitchSuggestion(
            cue=cue, target_scene=scene, reason=reason,
        )

    # ---------------------------------------------- director
    def director_cam_pick(
        self,
        scene_state: dict,
    ) -> str:
        """Picks a shot kind label. Pulls fields from
        scene_state and maps to director_ai's vocabulary —
        WIDE_ESTABLISHING / MEDIUM / OVER_THE_SHOULDER /
        CLOSE_UP / HANDHELD / OVERHEAD / EXTREME_CLOSE_UP.
        """
        tempo = scene_state.get("tempo", "medium")
        focus_targets = scene_state.get("focus_targets", 1)
        kind = scene_state.get("scene_kind", "exploration")
        # Combat fast — handheld.
        if kind in ("combat_close", "combat_open") and (
            tempo == "fast"
        ):
            return "handheld"
        # Reveal — wide establishing.
        if kind == "reveal":
            return "wide_establishing"
        # Dialogue + 2 — OTS.
        if kind == "dialogue" and focus_targets >= 2:
            return "over_the_shoulder"
        # Dialogue + 1 — close up.
        if kind == "dialogue" and focus_targets == 1:
            return "close_up"
        # Emotional beat — close up.
        if kind == "emotional_beat":
            return "close_up"
        # Action set piece — overhead.
        if kind == "action_set_piece":
            return "overhead"
        # Default — medium.
        return "medium"


__all__ = [
    "SpectatorMode",
    "ReplayEvent",
    "SpectatorSession",
    "ReplayClip",
    "SceneSwitchSuggestion",
    "SpectatorSystem",
    "ROLLING_BUFFER_SECONDS",
    "DEFAULT_ZOOM_MIN_M",
    "DEFAULT_ZOOM_MAX_M",
]
