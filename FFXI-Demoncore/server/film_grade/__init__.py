"""Film grade — ACES color pipeline + LUT chain.

Demoncore's color science is ACES end-to-end. The server
chooses a film stock LUT (Kodak Vision3, Fuji Eterna,
Cinestyle, Bleach Bypass, Day-for-Night, Demoncore
Standard) and publishes it via OCIO config. UE5's
post-process volume applies the chain in this order:

    scene linear (ACEScg)
        -> per-stock LUT (look)
        -> ACES 1.3 RRT (Reference Rendering Transform)
        -> ODT (Output Device Transform; sRGB / Rec.709 /
                P3 / Rec.2020)

Per-scene exposure metering targets Zone V skin tone
(0.18 linear). White balance is shooter-set in kelvin.

Public surface
--------------
    SourceSpace enum
    Look enum
    LUT dataclass (frozen)
    LUTS dict
    FilmGradeSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


SKIN_TONE_TARGET = 0.18  # zone V, linear


class SourceSpace(str, enum.Enum):
    ACESCG = "ACEScg"
    SRGB = "sRGB"
    LOG = "Log"


class Look(str, enum.Enum):
    NEUTRAL = "neutral"
    WARM_DAYLIGHT = "warm_daylight"
    COOL_TUNGSTEN = "cool_tungsten"
    DESATURATED = "desaturated"
    HIGH_CONTRAST = "high_contrast"
    NIGHT = "night"
    DEMONCORE = "demoncore"


@dataclasses.dataclass(frozen=True)
class LUT:
    name: str
    source_space: SourceSpace
    target_look: Look
    shadow_tint: tuple[float, float, float]
    mid_tint: tuple[float, float, float]
    highlight_tint: tuple[float, float, float]


LUTS: dict[str, LUT] = {l.name: l for l in (
    LUT(
        name="kodak_vision3_250d",
        source_space=SourceSpace.ACESCG,
        target_look=Look.WARM_DAYLIGHT,
        shadow_tint=(0.95, 0.97, 1.05),
        mid_tint=(1.02, 1.00, 0.98),
        highlight_tint=(1.05, 1.02, 0.96),
    ),
    LUT(
        name="kodak_vision3_500t",
        source_space=SourceSpace.ACESCG,
        target_look=Look.COOL_TUNGSTEN,
        shadow_tint=(0.92, 0.96, 1.10),
        mid_tint=(0.98, 1.00, 1.04),
        highlight_tint=(1.02, 1.00, 1.06),
    ),
    LUT(
        name="fuji_eterna_250d",
        source_space=SourceSpace.ACESCG,
        target_look=Look.DESATURATED,
        shadow_tint=(0.98, 0.98, 1.02),
        mid_tint=(1.00, 1.01, 1.00),
        highlight_tint=(1.01, 1.01, 0.99),
    ),
    LUT(
        name="cinestyle_technicolor",
        source_space=SourceSpace.LOG,
        target_look=Look.NEUTRAL,
        shadow_tint=(1.00, 1.00, 1.00),
        mid_tint=(1.00, 1.00, 1.00),
        highlight_tint=(1.00, 1.00, 1.00),
    ),
    LUT(
        name="bleach_bypass",
        source_space=SourceSpace.ACESCG,
        target_look=Look.HIGH_CONTRAST,
        shadow_tint=(0.85, 0.85, 0.85),
        mid_tint=(0.95, 0.95, 0.95),
        highlight_tint=(1.10, 1.10, 1.10),
    ),
    LUT(
        name="day_for_night",
        source_space=SourceSpace.ACESCG,
        target_look=Look.NIGHT,
        shadow_tint=(0.50, 0.55, 0.85),
        mid_tint=(0.60, 0.65, 0.90),
        highlight_tint=(0.70, 0.75, 0.95),
    ),
    LUT(
        name="demoncore_standard",
        source_space=SourceSpace.ACESCG,
        target_look=Look.DEMONCORE,
        shadow_tint=(0.92, 0.95, 1.05),
        mid_tint=(1.02, 1.00, 0.98),
        highlight_tint=(1.06, 1.00, 0.94),
    ),
)}


# White balance cookbook — kelvin -> common name. The system
# stores the integer kelvin value; this map is descriptive.
_WB_LABELS: tuple[tuple[int, str], ...] = (
    (3200, "tungsten"),
    (4300, "fluorescent"),
    (5600, "daylight"),
    (6500, "cloudy"),
    (10000, "overcast"),
)


def wb_label(kelvin: int) -> str:
    """Return the closest descriptive name for a kelvin
    value."""
    return min(_WB_LABELS, key=lambda kv: abs(kv[0] - kelvin))[1]


@dataclasses.dataclass
class FilmGradeSystem:
    _lut: t.Optional[LUT] = None
    exposure_ev: float = 0.0
    white_balance_kelvin: int = 5600
    rrt_version: str = "ACES_1.3_RRT"
    odt_version: str = "ACES_1.3_ODT_Rec709"

    def apply_lut(self, name: str) -> LUT:
        if name not in LUTS:
            raise ValueError(f"unknown LUT: {name}")
        self._lut = LUTS[name]
        return self._lut

    @property
    def current_lut(self) -> t.Optional[LUT]:
        return self._lut

    def exposure_meter(self, scene_avg_luminance: float) -> float:
        """Compute EV correction so scene_avg_luminance lands
        at zone V (0.18 linear). Positive EV brightens the
        scene (under-exposed source); negative EV darkens it.

        Returns the EV delta (stops) the renderer should
        apply via post-process exposure compensation.
        """
        if scene_avg_luminance <= 0:
            raise ValueError(
                "scene_avg_luminance must be positive",
            )
        # ev = log2(target / measured)
        import math
        ev = math.log2(SKIN_TONE_TARGET / scene_avg_luminance)
        self.exposure_ev = ev
        return ev

    def white_balance_kelvin_set(self, k: int) -> str:
        """Set white balance and return the descriptive
        label."""
        if not (1000 <= k <= 20000):
            raise ValueError(f"kelvin out of range: {k}")
        self.white_balance_kelvin = int(k)
        return wb_label(k)

    def aces_transform(
        self, linear_rgb: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        """Apply per-channel exposure + LUT mid-tint as a
        first-order approximation of ACEScg -> RRT/ODT.

        This is intentionally not a real RRT/ODT — UE5 does
        the actual transform. The server publishes the
        intent; this method exists as a reproducible test
        oracle and as a sanity check that the LUT chain is
        wired before assets ship.
        """
        if any(c < 0 for c in linear_rgb):
            raise ValueError(
                "linear_rgb must be non-negative",
            )
        r, g, b = linear_rgb
        gain = 2.0 ** self.exposure_ev
        if self._lut is not None:
            tr, tg, tb = self._lut.mid_tint
        else:
            tr = tg = tb = 1.0
        return (r * gain * tr, g * gain * tg, b * gain * tb)

    def get_render_intent(self) -> dict:
        return {
            "lut": self._lut.name if self._lut else None,
            "source_space": (
                self._lut.source_space.value
                if self._lut else None
            ),
            "target_look": (
                self._lut.target_look.value
                if self._lut else None
            ),
            "exposure_ev": self.exposure_ev,
            "white_balance_kelvin": self.white_balance_kelvin,
            "white_balance_label": wb_label(
                self.white_balance_kelvin,
            ),
            "rrt": self.rrt_version,
            "odt": self.odt_version,
            "skin_tone_target": SKIN_TONE_TARGET,
        }


def list_luts() -> tuple[str, ...]:
    return tuple(sorted(LUTS))


__all__ = [
    "SourceSpace", "Look", "LUT", "LUTS",
    "FilmGradeSystem",
    "SKIN_TONE_TARGET", "wb_label", "list_luts",
]
