"""VR eye tracking — gaze drives soft-target + NPC eye contact.

Modern VR HMDs with eye-tracking (Quest Pro, Vision Pro,
Pico 4 Enterprise) report where the player is looking.
We use that for two gameplay features:

    SOFT-TARGET     glance at a mob -> game treats it as
                    a "soft target". A subsequent action
                    button confirms the lock. Faster than
                    using a thumbstick to target each mob.

    NPC EYE CONTACT NPCs detect when you're looking at
                    them. Triggers ambient barks ("can I
                    help you?"), enables hover-to-speak
                    interactions, and looks-back-at-you
                    head-IK animations.

A gaze sample is (origin x/y/z, direction nx/ny/nz, ts).
We don't care about the raw eye images, just the gaze ray.

Soft-target resolution:
    For each candidate entity we compute the angular
    distance from gaze direction to (entity_pos - origin).
    The smallest angle within _SOFT_TARGET_CONE_DEG
    "wins". If none qualify, no soft target.

NPC eye contact:
    Same cone but tighter (_EYE_CONTACT_CONE_DEG). Tracks
    a 2-second running history — held for at least
    _EYE_CONTACT_DWELL_MS counts as "the player IS
    looking at this NPC right now". Triggers eye-contact
    events and gives the NPC a meaningful signal to
    respond to.

Hardware fallback:
    Not all VR headsets ship with eye tracking. The
    is_supported() flag lets the caller decide whether
    to fall back to "gaze direction = head forward
    direction", a much rougher proxy.

Public surface
--------------
    GazeSample dataclass (frozen)
    Entity dataclass (frozen)
    SoftTarget dataclass (frozen)
    EyeContactEvent dataclass (frozen)
    VrEyeTracking
        .ingest(player_id, sample) -> bool
        .soft_target(player_id, entities) -> Optional[SoftTarget]
        .eye_contact(player_id, entities, now_ms)
            -> list[EyeContactEvent]
        .set_supported(player_id, supported) -> bool
        .is_supported(player_id) -> bool
        .clear(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import math
import typing as t


_SOFT_TARGET_CONE_DEG = 8.0
_EYE_CONTACT_CONE_DEG = 4.0
_EYE_CONTACT_DWELL_MS = 600
_HISTORY_MS = 2000


@dataclasses.dataclass(frozen=True)
class GazeSample:
    origin_x: float
    origin_y: float
    origin_z: float
    dir_x: float
    dir_y: float
    dir_z: float
    timestamp_ms: int


@dataclasses.dataclass(frozen=True)
class Entity:
    entity_id: str
    x: float
    y: float
    z: float


@dataclasses.dataclass(frozen=True)
class SoftTarget:
    entity_id: str
    angle_deg: float


@dataclasses.dataclass(frozen=True)
class EyeContactEvent:
    entity_id: str
    started_ms: int
    duration_ms: int


def _normalize(x, y, z) -> tuple[float, float, float]:
    m = math.sqrt(x * x + y * y + z * z)
    if m <= 1e-9:
        return (0.0, 0.0, 0.0)
    return (x / m, y / m, z / m)


def _angle_to_entity(
    sample: GazeSample, entity: Entity,
) -> float:
    dx = entity.x - sample.origin_x
    dy = entity.y - sample.origin_y
    dz = entity.z - sample.origin_z
    enx, eny, enz = _normalize(dx, dy, dz)
    if (enx, eny, enz) == (0.0, 0.0, 0.0):
        return 180.0
    gnx, gny, gnz = _normalize(
        sample.dir_x, sample.dir_y, sample.dir_z,
    )
    if (gnx, gny, gnz) == (0.0, 0.0, 0.0):
        return 180.0
    dot = enx * gnx + eny * gny + enz * gnz
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


@dataclasses.dataclass
class VrEyeTracking:
    _samples: dict[
        str, list[GazeSample],
    ] = dataclasses.field(default_factory=dict)
    _supported: dict[str, bool] = dataclasses.field(
        default_factory=dict,
    )

    def ingest(
        self, *, player_id: str, sample: GazeSample,
    ) -> bool:
        if not player_id:
            return False
        buf = self._samples.setdefault(player_id, [])
        if buf and sample.timestamp_ms < buf[-1].timestamp_ms:
            return False
        buf.append(sample)
        # Trim to history window
        cutoff = sample.timestamp_ms - _HISTORY_MS
        while buf and buf[0].timestamp_ms < cutoff:
            buf.pop(0)
        return True

    def soft_target(
        self, *, player_id: str,
        entities: t.Sequence[Entity],
    ) -> t.Optional[SoftTarget]:
        buf = self._samples.get(player_id, [])
        if not buf:
            return None
        latest = buf[-1]
        best: t.Optional[SoftTarget] = None
        for ent in entities:
            ang = _angle_to_entity(latest, ent)
            if ang > _SOFT_TARGET_CONE_DEG:
                continue
            if best is None or ang < best.angle_deg:
                best = SoftTarget(
                    entity_id=ent.entity_id,
                    angle_deg=round(ang, 2),
                )
        return best

    def eye_contact(
        self, *, player_id: str,
        entities: t.Sequence[Entity], now_ms: int,
    ) -> list[EyeContactEvent]:
        buf = self._samples.get(player_id, [])
        if not buf:
            return []
        # For each entity, compute the longest CURRENT
        # streak (continuous samples within tight cone,
        # ending at now_ms) and report if it meets dwell.
        out = []
        for ent in entities:
            streak_start: t.Optional[int] = None
            last_in: t.Optional[int] = None
            for s in buf:
                ang = _angle_to_entity(s, ent)
                if ang <= _EYE_CONTACT_CONE_DEG:
                    if streak_start is None:
                        streak_start = s.timestamp_ms
                    last_in = s.timestamp_ms
                else:
                    streak_start = None
                    last_in = None
            if streak_start is None or last_in is None:
                continue
            dur = last_in - streak_start
            # Allow a tiny gap between last-sample and now
            if dur < _EYE_CONTACT_DWELL_MS:
                continue
            out.append(EyeContactEvent(
                entity_id=ent.entity_id,
                started_ms=streak_start,
                duration_ms=dur,
            ))
        out.sort(key=lambda e: -e.duration_ms)
        return out

    def set_supported(
        self, *, player_id: str, supported: bool,
    ) -> bool:
        if not player_id:
            return False
        prev = self._supported.get(player_id)
        self._supported[player_id] = supported
        return prev != supported

    def is_supported(self, *, player_id: str) -> bool:
        return self._supported.get(player_id, False)

    def clear(self, *, player_id: str) -> bool:
        touched = False
        if player_id in self._samples:
            del self._samples[player_id]
            touched = True
        if player_id in self._supported:
            del self._supported[player_id]
            touched = True
        return touched


__all__ = [
    "GazeSample", "Entity", "SoftTarget",
    "EyeContactEvent", "VrEyeTracking",
]
