"""Lens optics — lens profiles + anamorphic flares.

Demoncore picks the right glass for the shot. The server
publishes a lens profile (Cooke S4, Atlas Orion, Zeiss
Master Prime, Helios 44-2) and aperture; UE5's Cine Camera
realises focal length, T-stop, anamorphic squeeze,
distortion, vignette, flare colour and bokeh shape.

Lens behaviour modelled here:
    - aperture-driven depth of field (thin-lens approx)
    - lens breathing toggle (focus pull warps FOV)
    - flare intensity scaled by light source lux
    - bokeh shape per lens type

Public surface
--------------
    BokehShape, FlareColor enums
    LensProfile dataclass (frozen)
    LENSES dict
    LensOpticsSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


CIRCLE_OF_CONFUSION_MM = 0.025  # 35mm-format reference CoC


class BokehShape(str, enum.Enum):
    CIRCLE = "circle"
    OVAL = "oval"
    CAT_EYE = "cat_eye"


class FlareColor(str, enum.Enum):
    WARM = "warm"
    COOL = "cool"
    BLUE = "blue"
    NEUTRAL = "neutral"


@dataclasses.dataclass(frozen=True)
class LensProfile:
    name: str
    focal_length_mm: float
    t_stop_min: float          # widest aperture (smallest T-num)
    t_stop_max: float
    anamorphic_squeeze: float  # 1.0 spherical / 1.33 / 2.0
    distortion_k1: float       # radial distortion coefficient
    vignette_strength: float   # 0..1
    flare_color: FlareColor
    bokeh_shape: BokehShape
    breathing: bool


# Curated lens kit. Optical numbers approximate the real
# glass; UE5 reads these to drive Cine Camera + post.
LENSES: dict[str, LensProfile] = {l.name: l for l in (
    # Cooke S4 (spherical primes — warm "Cooke look")
    LensProfile("cooke_s4_32mm", 32, 2.0, 22.0, 1.0,
                -0.012, 0.18, FlareColor.WARM,
                BokehShape.CIRCLE, breathing=False),
    LensProfile("cooke_s4_40mm", 40, 2.0, 22.0, 1.0,
                -0.010, 0.16, FlareColor.WARM,
                BokehShape.CIRCLE, breathing=False),
    LensProfile("cooke_s4_50mm", 50, 2.0, 22.0, 1.0,
                -0.008, 0.14, FlareColor.WARM,
                BokehShape.CIRCLE, breathing=False),
    LensProfile("cooke_s4_75mm", 75, 2.0, 22.0, 1.0,
                -0.005, 0.12, FlareColor.WARM,
                BokehShape.CIRCLE, breathing=False),
    LensProfile("cooke_s4_100mm", 100, 2.0, 22.0, 1.0,
                -0.003, 0.10, FlareColor.WARM,
                BokehShape.CIRCLE, breathing=False),
    # Atlas Orion 2x anamorphic — blue streaks, oval bokeh
    LensProfile("atlas_orion_40mm", 40, 2.0, 16.0, 2.0,
                -0.025, 0.30, FlareColor.BLUE,
                BokehShape.OVAL, breathing=True),
    LensProfile("atlas_orion_65mm", 65, 2.0, 16.0, 2.0,
                -0.018, 0.28, FlareColor.BLUE,
                BokehShape.OVAL, breathing=True),
    LensProfile("atlas_orion_100mm", 100, 2.0, 16.0, 2.0,
                -0.012, 0.26, FlareColor.BLUE,
                BokehShape.OVAL, breathing=True),
    # Zeiss Master Prime — clinical, cool, neutral flare
    LensProfile("zeiss_master_35mm", 35, 1.3, 22.0, 1.0,
                -0.006, 0.10, FlareColor.NEUTRAL,
                BokehShape.CIRCLE, breathing=False),
    LensProfile("zeiss_master_50mm", 50, 1.3, 22.0, 1.0,
                -0.004, 0.08, FlareColor.NEUTRAL,
                BokehShape.CIRCLE, breathing=False),
    LensProfile("zeiss_master_85mm", 85, 1.3, 22.0, 1.0,
                -0.002, 0.06, FlareColor.NEUTRAL,
                BokehShape.CIRCLE, breathing=False),
    # Helios 44-2 — vintage Soviet swirl, cat-eye bokeh
    LensProfile("helios_44_2_58mm", 58, 2.0, 16.0, 1.0,
                -0.030, 0.40, FlareColor.WARM,
                BokehShape.CAT_EYE, breathing=True),
)}


@dataclasses.dataclass
class LensOpticsSystem:
    _lens: t.Optional[LensProfile] = None
    aperture: float = 2.8       # T-stop
    focus_distance_m: float = 2.0
    breathing_enabled: bool = True

    def select_lens(self, name: str) -> LensProfile:
        if name not in LENSES:
            raise ValueError(f"unknown lens: {name}")
        self._lens = LENSES[name]
        # Snap aperture into legal range for the new lens.
        if not (
            self._lens.t_stop_min
            <= self.aperture
            <= self._lens.t_stop_max
        ):
            self.aperture = self._lens.t_stop_min
        return self._lens

    @property
    def lens(self) -> t.Optional[LensProfile]:
        return self._lens

    def set_aperture(self, t_stop: float) -> None:
        if self._lens is None:
            raise RuntimeError("no lens selected")
        if not (
            self._lens.t_stop_min
            <= t_stop
            <= self._lens.t_stop_max
        ):
            raise ValueError(
                f"T-stop {t_stop} outside "
                f"[{self._lens.t_stop_min}.."
                f"{self._lens.t_stop_max}] for "
                f"{self._lens.name}"
            )
        self.aperture = float(t_stop)

    def set_focus_distance(self, meters: float) -> None:
        if meters <= 0:
            raise ValueError(
                f"focus distance must be positive: {meters}",
            )
        self.focus_distance_m = float(meters)

    def bokeh_shape(self) -> BokehShape:
        if self._lens is None:
            raise RuntimeError("no lens selected")
        return self._lens.bokeh_shape

    def flare_intensity(self, light_lux: float) -> float:
        """Flare strength scales with light source intensity.
        Anamorphic glass flares hotter than spherical; the
        flare colour comes from the lens profile.

        Returns a unitless multiplier in [0, 1] that UE5
        feeds into the bloom / lens-flare post pass.
        """
        if self._lens is None:
            raise RuntimeError("no lens selected")
        if light_lux < 0:
            raise ValueError(
                f"light_lux must be non-negative: {light_lux}"
            )
        # log-roll-off at 100k lux -> 1.0; 1k lux -> ~0.5.
        import math
        base = math.log10(max(light_lux, 1.0)) / 5.0
        # anamorphic boost
        if self._lens.anamorphic_squeeze >= 1.5:
            base *= 1.5
        return min(1.0, base)

    def depth_of_field_meters(
        self, focus_distance: t.Optional[float] = None,
    ) -> float:
        """Total DoF (near-far) in meters via thin-lens
        approximation:

            DoF ≈ 2 * N * c * d² / f²

        where:
            N = T-stop  (we approximate T as f-number)
            c = circle of confusion (mm)
            d = focus distance (mm)
            f = focal length (mm)
        """
        if self._lens is None:
            raise RuntimeError("no lens selected")
        d_m = (
            focus_distance
            if focus_distance is not None
            else self.focus_distance_m
        )
        if d_m <= 0:
            raise ValueError(
                f"focus distance must be positive: {d_m}",
            )
        f_mm = self._lens.focal_length_mm
        d_mm = d_m * 1000.0
        n = self.aperture
        c_mm = CIRCLE_OF_CONFUSION_MM
        dof_mm = 2 * n * c_mm * (d_mm ** 2) / (f_mm ** 2)
        return dof_mm / 1000.0  # back to meters

    def get_render_intent(self) -> dict:
        if self._lens is None:
            raise RuntimeError("no lens selected")
        L = self._lens
        return {
            "lens": L.name,
            "focal_length_mm": L.focal_length_mm,
            "t_stop": self.aperture,
            "anamorphic_squeeze": L.anamorphic_squeeze,
            "distortion_k1": L.distortion_k1,
            "vignette_strength": L.vignette_strength,
            "flare_color": L.flare_color.value,
            "bokeh_shape": L.bokeh_shape.value,
            "breathing_enabled": (
                self.breathing_enabled and L.breathing
            ),
            "focus_distance_m": self.focus_distance_m,
        }


def list_lenses() -> tuple[str, ...]:
    return tuple(sorted(LENSES))


__all__ = [
    "BokehShape", "FlareColor", "LensProfile", "LENSES",
    "LensOpticsSystem", "list_lenses",
    "CIRCLE_OF_CONFUSION_MM",
]
