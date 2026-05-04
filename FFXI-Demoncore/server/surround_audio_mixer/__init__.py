"""Surround audio mixer — 3D positional audio for 7.1.

Computes per-listener azimuth + elevation + distance attenuation
for every active sound source so the renderer can spatialize
into 7.1 surround. Players naturally sense where things are: an
NM roar from the left rear, a footstep behind, a voice 30 yalms
ahead.

Public surface
--------------
    SoundLayer enum
    SoundSource dataclass
    Listener dataclass
    AudioMixSample dataclass
    SurroundAudioMixer
        .add_source(source_id, layer, zone, x, y, z, base_db)
        .remove_source(source_id)
        .listener_at(listener_id, zone, x, y, z, facing_radians)
        .mix_for(listener_id) -> tuple[AudioMixSample]
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Distance attenuation: drop dB linearly per yalm (dist scaling).
DEFAULT_ROLLOFF_DB_PER_YALM = 0.3
# Inaudible cutoff.
INAUDIBLE_DB_FLOOR = -60.0
# Radius where audio is full strength (no attenuation).
NEAR_FIELD_RADIUS = 5.0


class SoundLayer(str, enum.Enum):
    SFX = "sfx"
    VOICE = "voice"
    MUSIC = "music"
    AMBIENT = "ambient"
    UI = "ui"


@dataclasses.dataclass
class SoundSource:
    source_id: str
    layer: SoundLayer
    zone_id: str
    x: float
    y: float
    z: float
    base_db: float = 0.0       # peak loudness at near field


@dataclasses.dataclass
class Listener:
    listener_id: str
    zone_id: str
    x: float
    y: float
    z: float
    facing_radians: float = 0.0    # 0 = facing +y / north


@dataclasses.dataclass(frozen=True)
class AudioMixSample:
    source_id: str
    layer: SoundLayer
    azimuth_radians: float    # 0 = front, +pi/2 = right, etc.
    elevation_radians: float
    distance: float
    attenuated_db: float
    audible: bool


@dataclasses.dataclass
class SurroundAudioMixer:
    rolloff_db_per_yalm: float = DEFAULT_ROLLOFF_DB_PER_YALM
    inaudible_db_floor: float = INAUDIBLE_DB_FLOOR
    near_field_radius: float = NEAR_FIELD_RADIUS
    _sources: dict[str, SoundSource] = dataclasses.field(
        default_factory=dict,
    )
    _listeners: dict[str, Listener] = dataclasses.field(
        default_factory=dict,
    )

    def add_source(
        self, *, source_id: str, layer: SoundLayer,
        zone_id: str, x: float, y: float, z: float = 0.0,
        base_db: float = 0.0,
    ) -> t.Optional[SoundSource]:
        if source_id in self._sources:
            return None
        src = SoundSource(
            source_id=source_id, layer=layer,
            zone_id=zone_id, x=x, y=y, z=z,
            base_db=base_db,
        )
        self._sources[source_id] = src
        return src

    def remove_source(self, *, source_id: str) -> bool:
        return self._sources.pop(source_id, None) is not None

    def listener_at(
        self, *, listener_id: str, zone_id: str,
        x: float, y: float, z: float = 0.0,
        facing_radians: float = 0.0,
    ) -> Listener:
        listener = Listener(
            listener_id=listener_id, zone_id=zone_id,
            x=x, y=y, z=z,
            facing_radians=facing_radians,
        )
        self._listeners[listener_id] = listener
        return listener

    def listener(
        self, listener_id: str,
    ) -> t.Optional[Listener]:
        return self._listeners.get(listener_id)

    def _attenuate(self, distance: float, base_db: float) -> float:
        if distance <= self.near_field_radius:
            return base_db
        beyond = distance - self.near_field_radius
        return base_db - beyond * self.rolloff_db_per_yalm

    def mix_for(
        self, *, listener_id: str,
    ) -> tuple[AudioMixSample, ...]:
        listener = self._listeners.get(listener_id)
        if listener is None:
            return ()
        out: list[AudioMixSample] = []
        for src in self._sources.values():
            if src.zone_id != listener.zone_id:
                continue
            dx = src.x - listener.x
            dy = src.y - listener.y
            dz = src.z - listener.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            attenuated = self._attenuate(dist, src.base_db)
            audible = attenuated > self.inaudible_db_floor
            # World-frame angle to source: 0 rad = +y (north),
            # +pi/2 = east, -pi/2 = west
            world_angle = math.atan2(dx, dy)
            # Listener-relative azimuth: subtract facing
            azimuth = world_angle - listener.facing_radians
            # Normalize to [-pi, pi]
            azimuth = (
                (azimuth + math.pi) % (2 * math.pi)
            ) - math.pi
            # Elevation: angle above/below horizontal plane
            horiz = math.sqrt(dx * dx + dy * dy)
            elevation = (
                math.atan2(dz, horiz) if horiz > 0
                else (math.pi / 2 if dz > 0 else -math.pi / 2)
                if dz != 0 else 0.0
            )
            out.append(AudioMixSample(
                source_id=src.source_id, layer=src.layer,
                azimuth_radians=azimuth,
                elevation_radians=elevation,
                distance=dist,
                attenuated_db=attenuated,
                audible=audible,
            ))
        return tuple(out)

    def total_sources(self) -> int:
        return len(self._sources)


__all__ = [
    "DEFAULT_ROLLOFF_DB_PER_YALM",
    "INAUDIBLE_DB_FLOOR",
    "NEAR_FIELD_RADIUS",
    "SoundLayer",
    "SoundSource", "Listener", "AudioMixSample",
    "SurroundAudioMixer",
]
