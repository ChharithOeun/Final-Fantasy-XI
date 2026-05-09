"""Atmospheric render — volumetrics, god rays, LED-wall feel.

The look of a Mandalorian shot: volumetric haze, god rays
through windows, dust motes drifting in shafts of light, LED
ambient bouncing off skin. Demoncore's server publishes per-
zone atmospheric profiles that UE5 reads to configure
ExponentialHeightFog, VolumetricCloud, LightShafts, and
the LED-wall cyc colour for ICVFX shoots.

Coupling
--------
* Weather (clear / overcast / rain / sandstorm / aurora)
  drives density and scatter anisotropy.
* Time-of-day (dawn / day / dusk / night) drives god-ray
  count and angle.
* Visibility (km) drives the distance_haze_km parameter
  so the renderer matches the simulated weather.

Public surface
--------------
    Weather, TimeOfDay enums
    AtmosphericProfile dataclass (frozen)
    AtmosphericRenderSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Weather(str, enum.Enum):
    CLEAR = "clear"
    OVERCAST = "overcast"
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    AURORA = "aurora"


class TimeOfDay(str, enum.Enum):
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"


# Per-weather density and scatter anisotropy. Anisotropy
# is the Henyey-Greenstein g parameter: positive = forward
# scatter (fog backlit by sun), negative = back scatter.
_WEATHER_TABLE: dict[Weather, tuple[float, float]] = {
    Weather.CLEAR:     (0.05, 0.50),
    Weather.OVERCAST:  (0.40, 0.10),
    Weather.RAIN:      (0.65, -0.10),
    Weather.SANDSTORM: (0.90, 0.30),
    Weather.AURORA:    (0.20, 0.70),
}


# Per-time-of-day god-ray count baseline. Dawn/dusk get
# the most shafts (low sun angle + side window light); day
# gets the strongest individual rays; night gets few but
# god-rays from moon are important narrative beats.
_GODRAY_TABLE: dict[TimeOfDay, int] = {
    TimeOfDay.DAWN: 8,
    TimeOfDay.DAY: 4,
    TimeOfDay.DUSK: 8,
    TimeOfDay.NIGHT: 2,
}


@dataclasses.dataclass(frozen=True)
class AtmosphericProfile:
    """Per-zone profile. The renderer treats unset zones as
    'clear day' default."""
    zone: str
    density: float                 # 0..1
    god_ray_count: int             # active light-shaft sources
    distance_haze_km: float        # depth at which haze ~= 50%
    dust_mote_density: float       # particles per m^3
    led_wall_ambient_color: tuple[float, float, float]
    scatter_anisotropy: float      # -1..1


def _hour_to_tod(hour: int) -> TimeOfDay:
    """Map a 0..23 game-clock hour to a TimeOfDay band.

    dawn   = 5..7
    day    = 8..16
    dusk   = 17..19
    night  = 20..4
    """
    if hour < 0 or hour > 23:
        raise ValueError(f"hour out of range: {hour}")
    if 5 <= hour <= 7:
        return TimeOfDay.DAWN
    if 8 <= hour <= 16:
        return TimeOfDay.DAY
    if 17 <= hour <= 19:
        return TimeOfDay.DUSK
    return TimeOfDay.NIGHT


@dataclasses.dataclass
class AtmosphericRenderSystem:
    _profiles: dict[str, AtmosphericProfile] = dataclasses.field(
        default_factory=dict,
    )

    def set_zone_atmosphere(
        self, zone: str, profile: AtmosphericProfile,
    ) -> None:
        if not zone:
            raise ValueError("zone id required")
        if zone != profile.zone:
            raise ValueError(
                "profile.zone does not match zone arg",
            )
        if not (0 <= profile.density <= 1):
            raise ValueError("density must be in [0,1]")
        if not (-1 <= profile.scatter_anisotropy <= 1):
            raise ValueError(
                "scatter_anisotropy must be in [-1,1]",
            )
        if profile.god_ray_count < 0:
            raise ValueError("god_ray_count must be >= 0")
        self._profiles[zone] = profile

    def get_profile(
        self, zone: str,
    ) -> t.Optional[AtmosphericProfile]:
        return self._profiles.get(zone)

    def god_ray_count_for(self, zone: str, hour: int) -> int:
        """God-ray count for a zone at a given hour. Uses the
        zone's stored count as the high-water mark and scales
        by time-of-day."""
        prof = self._profiles.get(zone)
        base = prof.god_ray_count if prof else 4
        tod = _hour_to_tod(hour)
        # Multiplier per band — dawn/dusk full, day half,
        # night quarter.
        mults = {
            TimeOfDay.DAWN: 1.0,
            TimeOfDay.DUSK: 1.0,
            TimeOfDay.DAY: 0.5,
            TimeOfDay.NIGHT: 0.25,
        }
        return max(0, int(round(base * mults[tod])))

    def distance_haze_km(self, visibility_km: float) -> float:
        """Translate simulated visibility to the renderer's
        distance_haze_km. Visibility is the distance at which
        contrast falls to 2% (Koschmieder); haze_km is the
        distance for 50%. Empirically haze_km ≈ visibility/4.
        """
        if visibility_km <= 0:
            raise ValueError("visibility must be positive")
        return visibility_km / 4.0

    def led_wall_color(
        self, zone: str,
    ) -> tuple[float, float, float]:
        prof = self._profiles.get(zone)
        if prof is None:
            # default neutral grey
            return (0.5, 0.5, 0.5)
        return prof.led_wall_ambient_color

    def apply_weather(
        self, zone: str, weather: Weather,
    ) -> AtmosphericProfile:
        """Update the zone's atmospheric profile to match
        the given weather. Density and scatter snap to the
        weather table; other fields are preserved if a prior
        profile exists, otherwise sensible defaults are
        used."""
        density, anisotropy = _WEATHER_TABLE[weather]
        prior = self._profiles.get(zone)
        if prior is None:
            new_profile = AtmosphericProfile(
                zone=zone, density=density,
                god_ray_count=_GODRAY_TABLE[TimeOfDay.DAY],
                distance_haze_km=10.0,
                dust_mote_density=200.0,
                led_wall_ambient_color=(0.5, 0.5, 0.5),
                scatter_anisotropy=anisotropy,
            )
        else:
            new_profile = dataclasses.replace(
                prior, density=density,
                scatter_anisotropy=anisotropy,
            )
        self._profiles[zone] = new_profile
        return new_profile

    def get_render_intent(self, zone: str, hour: int) -> dict:
        prof = self._profiles.get(zone)
        if prof is None:
            return {
                "zone": zone,
                "density": 0.05,
                "god_rays": self.god_ray_count_for(zone, hour),
                "distance_haze_km": 10.0,
                "dust_motes": 100.0,
                "led_wall_color": (0.5, 0.5, 0.5),
                "scatter_anisotropy": 0.5,
                "tod": _hour_to_tod(hour).value,
            }
        return {
            "zone": zone,
            "density": prof.density,
            "god_rays": self.god_ray_count_for(zone, hour),
            "distance_haze_km": prof.distance_haze_km,
            "dust_motes": prof.dust_mote_density,
            "led_wall_color": prof.led_wall_ambient_color,
            "scatter_anisotropy": prof.scatter_anisotropy,
            "tod": _hour_to_tod(hour).value,
        }


__all__ = [
    "Weather", "TimeOfDay",
    "AtmosphericProfile", "AtmosphericRenderSystem",
]
