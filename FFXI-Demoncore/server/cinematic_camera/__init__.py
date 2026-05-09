"""Cinematic camera — real-camera body simulation.

Demoncore drives UE5 Cine Camera Actors via Live Link. The
server publishes a ``render_intent`` that names a real camera
body (Arri, RED, Sony, Blackmagic, Canon, iPhone) and the
shooter-set parameters (shutter angle, ISO, white balance).
UE5 reads it and configures the Cine Camera + post-process
volume to match.

This module is the source of truth for those camera bodies.
A profile encodes sensor geometry, native ISO, dynamic range,
max resolution, color-matrix id, and gate aspect — everything
UE5 needs to produce film-accurate captures.

Public surface
--------------
    CameraProfile dataclass (frozen)
    PROFILES dict (name -> CameraProfile)
    CinematicCameraSystem
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class CameraProfile:
    name: str
    sensor_w_mm: float
    sensor_h_mm: float
    pixel_pitch_um: float
    native_iso: int
    iso_min: int
    iso_max: int
    dynamic_range_stops: float
    max_resolution: tuple[int, int]
    color_matrix_id: str
    gate_aspect: float
    rolling_shutter_ms: float


# Spec sheet sourced from manufacturer public data.
PROFILES: dict[str, CameraProfile] = {
    p.name: p for p in (
        CameraProfile(
            name="arri_alexa_35",
            sensor_w_mm=27.99, sensor_h_mm=19.22,
            pixel_pitch_um=6.07,
            native_iso=800, iso_min=160, iso_max=6400,
            dynamic_range_stops=17.0,
            max_resolution=(4608, 3164),
            color_matrix_id="ARRI_REVEAL",
            gate_aspect=27.99 / 19.22,
            rolling_shutter_ms=8.5,
        ),
        CameraProfile(
            name="arri_alexa_mini_lf",
            sensor_w_mm=36.70, sensor_h_mm=25.54,
            pixel_pitch_um=8.25,
            native_iso=800, iso_min=160, iso_max=3200,
            dynamic_range_stops=14.5,
            max_resolution=(4448, 3096),
            color_matrix_id="ARRI_LOGC4",
            gate_aspect=36.70 / 25.54,
            rolling_shutter_ms=11.0,
        ),
        CameraProfile(
            name="red_v_raptor_8k_vv",
            sensor_w_mm=40.96, sensor_h_mm=21.60,
            pixel_pitch_um=5.00,
            native_iso=800, iso_min=250, iso_max=12800,
            dynamic_range_stops=17.0,
            max_resolution=(8192, 4320),
            color_matrix_id="RED_IPP2",
            gate_aspect=40.96 / 21.60,
            rolling_shutter_ms=7.0,
        ),
        CameraProfile(
            name="sony_venice_2",
            sensor_w_mm=35.90, sensor_h_mm=24.00,
            pixel_pitch_um=5.95,
            native_iso=800, iso_min=80, iso_max=12800,
            dynamic_range_stops=16.0,
            max_resolution=(8640, 5760),
            color_matrix_id="SONY_S_GAMUT3_CINE",
            gate_aspect=35.90 / 24.00,
            rolling_shutter_ms=9.5,
        ),
        CameraProfile(
            name="blackmagic_ursa_mini_pro_12k",
            sensor_w_mm=27.03, sensor_h_mm=14.25,
            pixel_pitch_um=2.20,
            native_iso=800, iso_min=125, iso_max=25600,
            dynamic_range_stops=14.0,
            max_resolution=(12288, 6480),
            color_matrix_id="BMD_GEN5",
            gate_aspect=27.03 / 14.25,
            rolling_shutter_ms=14.0,
        ),
        CameraProfile(
            name="iphone_16_pro",
            sensor_w_mm=9.80, sensor_h_mm=7.35,
            pixel_pitch_um=2.44,
            native_iso=125, iso_min=32, iso_max=8000,
            dynamic_range_stops=13.0,
            max_resolution=(4032, 3024),
            color_matrix_id="APPLE_LOG",
            gate_aspect=9.80 / 7.35,
            rolling_shutter_ms=20.0,
        ),
        CameraProfile(
            name="canon_c500_mk2",
            sensor_w_mm=38.10, sensor_h_mm=20.10,
            pixel_pitch_um=6.40,
            native_iso=800, iso_min=160, iso_max=25600,
            dynamic_range_stops=15.0,
            max_resolution=(5952, 3140),
            color_matrix_id="CANON_CLOG2",
            gate_aspect=38.10 / 20.10,
            rolling_shutter_ms=10.0,
        ),
    )
}


@dataclasses.dataclass
class CinematicCameraSystem:
    """Mutable camera state driven by the director.

    Fields are pulled by ``get_render_intent`` and pushed to
    UE5's Cine Camera + post-process volume each frame.
    """
    _profile: t.Optional[CameraProfile] = None
    shutter_angle_deg: float = 180.0
    iso: int = 800
    white_balance_kelvin: int = 5600

    def select_profile(self, name: str) -> CameraProfile:
        if name not in PROFILES:
            raise ValueError(f"unknown camera profile: {name}")
        self._profile = PROFILES[name]
        # Snap ISO to native if current ISO is outside the new
        # camera's range. Keeps state self-consistent.
        prof = self._profile
        if not (prof.iso_min <= self.iso <= prof.iso_max):
            self.iso = prof.native_iso
        return self._profile

    @property
    def profile(self) -> t.Optional[CameraProfile]:
        return self._profile

    def set_shutter_angle(self, deg: float) -> None:
        if deg <= 0 or deg > 360:
            raise ValueError(
                f"shutter angle must be in (0, 360]: {deg}"
            )
        self.shutter_angle_deg = float(deg)

    def set_iso(self, value: int) -> None:
        if self._profile is None:
            raise RuntimeError("no profile selected")
        prof = self._profile
        if not (prof.iso_min <= value <= prof.iso_max):
            raise ValueError(
                f"ISO {value} out of range "
                f"[{prof.iso_min}..{prof.iso_max}] "
                f"for {prof.name}"
            )
        self.iso = int(value)

    def set_white_balance(self, kelvin: int) -> None:
        if not (1000 <= kelvin <= 20000):
            raise ValueError(
                f"white balance kelvin out of range: {kelvin}"
            )
        self.white_balance_kelvin = int(kelvin)

    def shutter_speed_seconds(
        self, *, fps: float,
    ) -> float:
        """Convert shutter-angle + fps to a real shutter time
        UE5 can hand the motion-blur sampler.

            t = (angle / 360) / fps
        """
        if fps <= 0:
            raise ValueError(f"fps must be positive: {fps}")
        return (self.shutter_angle_deg / 360.0) / fps

    def get_render_intent(self) -> dict:
        if self._profile is None:
            raise RuntimeError("no profile selected")
        prof = self._profile
        return {
            "profile": prof.name,
            "sensor_w_mm": prof.sensor_w_mm,
            "sensor_h_mm": prof.sensor_h_mm,
            "pixel_pitch_um": prof.pixel_pitch_um,
            "max_resolution": prof.max_resolution,
            "color_matrix_id": prof.color_matrix_id,
            "gate_aspect": prof.gate_aspect,
            "rolling_shutter_ms": prof.rolling_shutter_ms,
            "dynamic_range_stops": prof.dynamic_range_stops,
            "shutter_angle_deg": self.shutter_angle_deg,
            "iso": self.iso,
            "white_balance_kelvin": self.white_balance_kelvin,
        }


def list_profiles() -> tuple[str, ...]:
    return tuple(sorted(PROFILES))


def profile(name: str) -> CameraProfile:
    if name not in PROFILES:
        raise ValueError(f"unknown camera profile: {name}")
    return PROFILES[name]


__all__ = [
    "CameraProfile", "PROFILES",
    "CinematicCameraSystem",
    "list_profiles", "profile",
]
