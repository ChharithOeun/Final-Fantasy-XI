"""Performance capture — facial + body mocap pipeline.

Demoncore drives UE5 Live Link sources and OmniLive Workflows
to capture actor performance. The server holds the device
registry, the per-take session lifecycle, and the picker that
chooses the right rig for a scene kind. UE5 reads the device
intent and opens the matching Live Link subject.

Five capture devices are supported out of the box:

    Live Link Face (iPhone TrueDepth ARKit) — facial only,
        52 ARKit blendshapes at 60Hz, occlusion-tolerant.
    Rokoko Smartsuit Pro II — body only, 19 IMU sensors at
        100Hz, no lighting requirement.
    OptiTrack Prime 41 — optical body tracking, 41 markers,
        240Hz, requires controlled lighting.
    Faceware Mark IV — facial via head-mounted camera, no
        ARKit; requires bright on-actor lighting.
    MetaHuman Animator — video-only facial, runs after-the-
        fact on iPhone or Stereo HMC footage.

Public surface
--------------
    DeviceKind enum
    SessionState enum
    CaptureDevice dataclass (frozen)
    TakeRecord dataclass (frozen)
    DEVICES dict
    PerformanceCaptureSystem
    list_devices, device, best_device_for
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DeviceKind(enum.Enum):
    FACIAL = "facial"
    BODY = "body"
    HYBRID = "hybrid"


class SessionState(enum.Enum):
    REGISTERED = "registered"
    CALIBRATED = "calibrated"
    CAPTURING = "capturing"
    POST = "post"
    ARCHIVED = "archived"


@dataclasses.dataclass(frozen=True)
class CaptureDevice:
    name: str
    kind: DeviceKind
    tracker_count: int           # markers / sensors / blendshapes
    sample_rate_hz: int
    latency_ms: float
    occlusion_robust: bool
    lighting_required: bool
    tracker_calibration_minutes: int


# Spec sheet sourced from manufacturer public data.
DEVICES: dict[str, CaptureDevice] = {
    d.name: d for d in (
        CaptureDevice(
            name="live_link_face",
            kind=DeviceKind.FACIAL,
            tracker_count=52,        # ARKit blendshapes
            sample_rate_hz=60,
            latency_ms=18.0,
            occlusion_robust=True,
            lighting_required=False,
            tracker_calibration_minutes=1,
        ),
        CaptureDevice(
            name="rokoko_smartsuit_pro_ii",
            kind=DeviceKind.BODY,
            tracker_count=19,        # IMU sensors
            sample_rate_hz=100,
            latency_ms=12.0,
            occlusion_robust=True,
            lighting_required=False,
            tracker_calibration_minutes=5,
        ),
        CaptureDevice(
            name="optitrack_prime_41",
            kind=DeviceKind.BODY,
            tracker_count=41,        # optical markers
            sample_rate_hz=240,
            latency_ms=4.0,
            occlusion_robust=False,
            lighting_required=True,
            tracker_calibration_minutes=20,
        ),
        CaptureDevice(
            name="faceware_mark_iv",
            kind=DeviceKind.FACIAL,
            tracker_count=78,        # facial landmarks
            sample_rate_hz=72,
            latency_ms=22.0,
            occlusion_robust=False,
            lighting_required=True,
            tracker_calibration_minutes=10,
        ),
        CaptureDevice(
            name="metahuman_animator",
            kind=DeviceKind.FACIAL,
            tracker_count=200,       # dense video landmarks
            sample_rate_hz=60,
            latency_ms=0.0,          # offline
            occlusion_robust=True,
            lighting_required=False,
            tracker_calibration_minutes=2,
        ),
    )
}


@dataclasses.dataclass(frozen=True)
class TakeRecord:
    take_id: str
    actor_id: str
    devices: tuple[str, ...]
    state: SessionState
    note: str = ""


SCENE_DEVICE_HINTS: dict[str, str] = {
    # Real-time hero work: low-latency optical body.
    "boss_intro": "optitrack_prime_41",
    "combat":     "optitrack_prime_41",
    # Dialogue is facial-led; LLF wins for hero closeups.
    "dialogue":   "live_link_face",
    "emotional":  "live_link_face",
    # Field / on-location: Rokoko (no lighting reqs).
    "field":      "rokoko_smartsuit_pro_ii",
    "exploration":"rokoko_smartsuit_pro_ii",
    # Post / async pickup: MetaHuman Animator runs offline.
    "pickup":     "metahuman_animator",
}


@dataclasses.dataclass
class PerformanceCaptureSystem:
    """Mutable capture session state.

    register_device → calibrate → start_session → end_session
    → archive. UE5 reads the active TakeRecord every frame to
    know which Live Link subjects are hot.
    """
    _registered: dict[str, CaptureDevice] = dataclasses.field(
        default_factory=dict,
    )
    _calibrated: set[str] = dataclasses.field(
        default_factory=set,
    )
    _takes: dict[str, TakeRecord] = dataclasses.field(
        default_factory=dict,
    )
    _active_take: t.Optional[str] = None
    _next: int = 1

    def register_device(self, name: str) -> CaptureDevice:
        if name not in DEVICES:
            raise ValueError(f"unknown device: {name}")
        d = DEVICES[name]
        self._registered[name] = d
        return d

    def is_registered(self, name: str) -> bool:
        return name in self._registered

    def calibrate(self, name: str) -> None:
        if name not in self._registered:
            raise RuntimeError(
                f"device not registered: {name}",
            )
        self._calibrated.add(name)

    def is_calibrated(self, name: str) -> bool:
        return name in self._calibrated

    def start_session(
        self, *, actor_id: str,
        devices: t.Sequence[str],
    ) -> TakeRecord:
        if self._active_take is not None:
            raise RuntimeError("a take is already capturing")
        if not actor_id:
            raise ValueError("actor_id required")
        if not devices:
            raise ValueError("at least one device required")
        for name in devices:
            if name not in self._registered:
                raise RuntimeError(
                    f"device not registered: {name}",
                )
            if name not in self._calibrated:
                raise RuntimeError(
                    f"device not calibrated: {name}",
                )
        tid = f"take_{self._next}"
        self._next += 1
        rec = TakeRecord(
            take_id=tid,
            actor_id=actor_id,
            devices=tuple(devices),
            state=SessionState.CAPTURING,
        )
        self._takes[tid] = rec
        self._active_take = tid
        return rec

    def end_session(self) -> TakeRecord:
        if self._active_take is None:
            raise RuntimeError("no active take")
        tid = self._active_take
        rec = self._takes[tid]
        new = dataclasses.replace(rec, state=SessionState.POST)
        self._takes[tid] = new
        self._active_take = None
        return new

    def archive(self, take_id: str) -> TakeRecord:
        if take_id not in self._takes:
            raise ValueError(f"unknown take: {take_id}")
        rec = self._takes[take_id]
        if rec.state != SessionState.POST:
            raise RuntimeError(
                f"take {take_id} not in POST: {rec.state}",
            )
        new = dataclasses.replace(
            rec, state=SessionState.ARCHIVED,
        )
        self._takes[take_id] = new
        return new

    def get_take(self, take_id: str) -> TakeRecord:
        if take_id not in self._takes:
            raise ValueError(f"unknown take: {take_id}")
        return self._takes[take_id]

    def takes(self) -> tuple[TakeRecord, ...]:
        return tuple(self._takes.values())

    @property
    def active_take(self) -> t.Optional[str]:
        return self._active_take


def list_devices() -> tuple[str, ...]:
    return tuple(sorted(DEVICES))


def device(name: str) -> CaptureDevice:
    if name not in DEVICES:
        raise ValueError(f"unknown device: {name}")
    return DEVICES[name]


def best_device_for(scene_kind: str) -> str:
    """Pick the best default device for a scene kind.

    Falls back to live_link_face if scene_kind is unknown —
    that's the cheapest hero-facing facial rig.
    """
    return SCENE_DEVICE_HINTS.get(scene_kind, "live_link_face")


__all__ = [
    "DeviceKind", "SessionState",
    "CaptureDevice", "TakeRecord",
    "DEVICES", "PerformanceCaptureSystem",
    "list_devices", "device", "best_device_for",
]
