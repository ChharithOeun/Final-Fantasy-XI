"""Previs engine — low-fi camera blocking and timing.

The pre-visualisation pass between storyboard and final
shoot. Each PrevisShot is a duration-bounded animation
clip with a sparse keyframed camera path, sparse keyframed
talent blocking, a low-poly asset list, and an optional
sound track. PrevisSequences chain shots end-to-end and
gate transitions: no two shots can occupy the same time
window, no shot can have a zero or negative duration, and
the camera path keyframes have to be monotonically non-
decreasing in time.

Export targets are the three industry-standard previs
hand-offs: UE5 Sequencer USD (the engine the cinematic
batch ships against), Maya .ma (the previs houses' default),
and Blender .blend (the open-source pipeline). A ShotGrid /
ftrack / Kitsu playblast is the QC video the show producer
reviews to greenlight a shot for the shoot.

Public surface
--------------
    ExportTarget enum
    CameraKey dataclass (frozen)
    BlockingKey dataclass (frozen)
    PrevisShot dataclass (frozen)
    PrevisSequence dataclass (frozen)
    TransitionIssue dataclass (frozen)
    PrevisEngine
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class ExportTarget(enum.Enum):
    UE5_SEQUENCER_USD = "ue5_sequencer_usd"
    MAYA_MA = "maya_ma"
    BLENDER_BLEND = "blender_blend"
    SHOTGRID_PLAYBLAST = "shotgrid_playblast"
    FTRACK_PLAYBLAST = "ftrack_playblast"
    KITSU_PLAYBLAST = "kitsu_playblast"


Vec3 = tuple[float, float, float]


@dataclasses.dataclass(frozen=True)
class CameraKey:
    t: float                    # seconds from shot start
    position: Vec3
    look_at: Vec3
    lens_mm: float


@dataclasses.dataclass(frozen=True)
class BlockingKey:
    t: float
    npc_id: str
    position: Vec3
    action_tag: str             # e.g. "idle", "walk", "draw_sword"


@dataclasses.dataclass(frozen=True)
class PrevisShot:
    shot_id: str
    duration_s: float
    camera_path: tuple[CameraKey, ...]
    talent_blocking: tuple[BlockingKey, ...]
    sound_track_uri: str = ""
    low_poly_assets: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class PrevisSequence:
    sequence_id: str
    shots: tuple[PrevisShot, ...]
    total_runtime_s: float


@dataclasses.dataclass(frozen=True)
class TransitionIssue:
    shot_a: str
    shot_b: str
    kind: str                   # "duration_zero" | "overlap" | "key_order"
    message: str


# ------------------------------------------------------------
# Validation helpers
# ------------------------------------------------------------
def _validate_camera_path(
    shot_id: str, path: t.Sequence[CameraKey], duration_s: float,
) -> None:
    if not path:
        raise ValueError(
            f"shot {shot_id}: camera_path must have >= 1 key",
        )
    last_t = -1.0
    for i, k in enumerate(path):
        if k.t < 0:
            raise ValueError(
                f"shot {shot_id} key {i}: t must be >= 0",
            )
        if k.t > duration_s + 1e-6:
            raise ValueError(
                f"shot {shot_id} key {i}: t={k.t} exceeds duration "
                f"{duration_s}",
            )
        if k.t < last_t:
            raise ValueError(
                f"shot {shot_id}: camera keys must be monotonic "
                f"in t (key {i} t={k.t} < prev {last_t})",
            )
        if k.lens_mm <= 0:
            raise ValueError(
                f"shot {shot_id} key {i}: lens_mm must be > 0",
            )
        last_t = k.t


def _validate_blocking(
    shot_id: str, blocking: t.Sequence[BlockingKey], duration_s: float,
) -> None:
    by_npc: dict[str, float] = {}
    for i, b in enumerate(blocking):
        if b.t < 0:
            raise ValueError(
                f"shot {shot_id} block {i}: t must be >= 0",
            )
        if b.t > duration_s + 1e-6:
            raise ValueError(
                f"shot {shot_id} block {i}: t exceeds duration",
            )
        if not b.npc_id:
            raise ValueError(
                f"shot {shot_id} block {i}: npc_id required",
            )
        prev_t = by_npc.get(b.npc_id, -1.0)
        if b.t < prev_t:
            raise ValueError(
                f"shot {shot_id}: blocking keys for npc "
                f"{b.npc_id} must be monotonic in t",
            )
        by_npc[b.npc_id] = b.t


# ------------------------------------------------------------
# Engine
# ------------------------------------------------------------
@dataclasses.dataclass
class PrevisEngine:
    _shots: dict[str, PrevisShot] = dataclasses.field(
        default_factory=dict,
    )

    def register_previs_shot(self, shot: PrevisShot) -> PrevisShot:
        if shot.shot_id in self._shots:
            raise ValueError(
                f"shot already registered: {shot.shot_id}",
            )
        if shot.duration_s <= 0:
            raise ValueError(
                f"duration_s must be > 0: {shot.duration_s}",
            )
        _validate_camera_path(
            shot.shot_id, shot.camera_path, shot.duration_s,
        )
        _validate_blocking(
            shot.shot_id, shot.talent_blocking, shot.duration_s,
        )
        self._shots[shot.shot_id] = shot
        return shot

    def lookup(self, shot_id: str) -> PrevisShot:
        if shot_id not in self._shots:
            raise KeyError(f"unknown shot_id: {shot_id}")
        return self._shots[shot_id]

    def sequence(
        self, sequence_id: str, shot_ids: t.Sequence[str],
    ) -> PrevisSequence:
        if not sequence_id:
            raise ValueError("sequence_id required")
        if not shot_ids:
            raise ValueError("sequence requires at least one shot")
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError(
                "sequence cannot repeat the same shot",
            )
        shots = tuple(self.lookup(s) for s in shot_ids)
        runtime = sum(s.duration_s for s in shots)
        return PrevisSequence(
            sequence_id=sequence_id,
            shots=shots,
            total_runtime_s=round(runtime, 3),
        )

    def runtime_s(self, seq: PrevisSequence) -> float:
        return seq.total_runtime_s

    def validate_transitions(
        self, seq: PrevisSequence,
    ) -> tuple[TransitionIssue, ...]:
        issues: list[TransitionIssue] = []
        for i in range(len(seq.shots) - 1):
            a = seq.shots[i]
            b = seq.shots[i + 1]
            if a.duration_s <= 0:
                issues.append(
                    TransitionIssue(
                        shot_a=a.shot_id,
                        shot_b=b.shot_id,
                        kind="duration_zero",
                        message="shot a has zero/negative duration",
                    ),
                )
            # camera path tail key time should be <= a.duration_s
            if a.camera_path:
                last = a.camera_path[-1]
                if last.t > a.duration_s + 1e-6:
                    issues.append(
                        TransitionIssue(
                            shot_a=a.shot_id,
                            shot_b=b.shot_id,
                            kind="key_order",
                            message=(
                                "tail camera key extends past shot a "
                                "duration"
                            ),
                        ),
                    )
        return tuple(issues)

    def export_for(
        self, target: ExportTarget, seq: PrevisSequence,
    ) -> dict[str, t.Any]:
        """Return the manifest the exporter consumes — shape
        depends on target. Exporter implementations live in the
        UE5 / Maya / Blender plugins.
        """
        manifest: dict[str, t.Any] = {
            "target": target.value,
            "sequence_id": seq.sequence_id,
            "runtime_s": seq.total_runtime_s,
            "shots": [
                {
                    "shot_id": s.shot_id,
                    "duration_s": s.duration_s,
                    "camera_keys": len(s.camera_path),
                    "blocking_keys": len(s.talent_blocking),
                    "low_poly_assets": list(s.low_poly_assets),
                    "sound_track_uri": s.sound_track_uri,
                }
                for s in seq.shots
            ],
        }
        if target == ExportTarget.UE5_SEQUENCER_USD:
            manifest["fps"] = 24
            manifest["usd_version"] = "0.23"
        elif target == ExportTarget.MAYA_MA:
            manifest["maya_version"] = "2024"
            manifest["fps"] = 24
        elif target == ExportTarget.BLENDER_BLEND:
            manifest["blender_version"] = "4.1"
            manifest["fps"] = 24
        elif target in (
            ExportTarget.SHOTGRID_PLAYBLAST,
            ExportTarget.FTRACK_PLAYBLAST,
            ExportTarget.KITSU_PLAYBLAST,
        ):
            manifest["codec"] = "h264"
            manifest["resolution"] = (1280, 720)
        return manifest

    def simulate_camera_at(
        self, shot_id: str, t_seconds: float,
    ) -> CameraKey:
        """Linearly interpolate the camera path at t."""
        shot = self.lookup(shot_id)
        if t_seconds < 0 or t_seconds > shot.duration_s + 1e-6:
            raise ValueError(
                f"t_seconds {t_seconds} out of range "
                f"[0, {shot.duration_s}]",
            )
        path = shot.camera_path
        if not path:
            raise ValueError(
                f"shot {shot_id} has no camera path",
            )
        if t_seconds <= path[0].t:
            return path[0]
        if t_seconds >= path[-1].t:
            return path[-1]
        # Find bracketing keys
        for i in range(len(path) - 1):
            a = path[i]
            b = path[i + 1]
            if a.t <= t_seconds <= b.t:
                if b.t == a.t:
                    return a
                u = (t_seconds - a.t) / (b.t - a.t)
                return CameraKey(
                    t=t_seconds,
                    position=tuple(  # type: ignore
                        a.position[k] + u * (
                            b.position[k] - a.position[k]
                        )
                        for k in range(3)
                    ),
                    look_at=tuple(  # type: ignore
                        a.look_at[k] + u * (
                            b.look_at[k] - a.look_at[k]
                        )
                        for k in range(3)
                    ),
                    lens_mm=a.lens_mm + u * (b.lens_mm - a.lens_mm),
                )
        return path[-1]

    def all_shots(self) -> tuple[PrevisShot, ...]:
        return tuple(self._shots.values())

    def shot_count(self) -> int:
        return len(self._shots)


__all__ = [
    "ExportTarget",
    "CameraKey", "BlockingKey",
    "PrevisShot", "PrevisSequence",
    "TransitionIssue",
    "PrevisEngine",
]
