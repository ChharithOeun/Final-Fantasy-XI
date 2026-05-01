"""Weather types + per-weather elemental amplification.

Per the user direction: weather amplifies certain elements (rain
boosts water/lightning; sandstorm reduces accuracy; thunder boosts
lightning; sunshower boosts light/water; aurora boosts light;
gloom boosts dark) and dampens their opposites. Pulling an NM into
a zone with hostile weather is a real tactic.
"""
from __future__ import annotations

import enum
import typing as t

# Forward-declared element strings. We avoid importing the Element
# enum here to keep this module standalone; the composer reconciles
# element names back to mob_resistances.Element.
ElementName = str


class WeatherType(str, enum.Enum):
    """Active weather. Each carries an elemental amplification map +
    side effects (sandstorm reduces accuracy, snow slows movement)."""
    CLEAR = "clear"
    RAIN = "rain"
    SUNSHOWER = "sunshower"
    THUNDER = "thunder"
    FOG = "fog"
    SANDSTORM = "sandstorm"
    SNOW_LIGHT = "snow_light"
    BLIZZARD = "blizzard"
    HEAT_WAVE = "heat_wave"
    WIND_GALES = "wind_gales"
    AURORA = "aurora"          # rare, light boost
    GLOOM = "gloom"            # rare, dark boost


# Per-weather: ElementName -> damage multiplier when casting this element.
# Above 1.0 = boost; below 1.0 = damp. Missing entries default to 1.0.
WEATHER_ELEMENTAL_AMP_TABLE: dict[WeatherType, dict[ElementName, float]] = {
    WeatherType.CLEAR:      {},
    WeatherType.RAIN:       {"water": 1.15, "lightning": 1.10, "fire": 0.85},
    WeatherType.SUNSHOWER:  {"water": 1.05, "light": 1.10, "dark": 0.95},
    WeatherType.THUNDER:    {"lightning": 1.20, "water": 1.05, "earth": 0.85},
    WeatherType.FOG:        {"water": 1.05, "ice": 1.05, "fire": 0.95},
    WeatherType.SANDSTORM:  {"earth": 1.20, "wind": 1.10, "ice": 0.85, "water": 0.85},
    WeatherType.SNOW_LIGHT: {"ice": 1.10, "water": 1.05, "fire": 0.90},
    WeatherType.BLIZZARD:   {"ice": 1.25, "water": 1.10, "fire": 0.75},
    WeatherType.HEAT_WAVE:  {"fire": 1.20, "ice": 0.80, "water": 0.90},
    WeatherType.WIND_GALES: {"wind": 1.20, "earth": 0.85},
    WeatherType.AURORA:     {"light": 1.25, "dark": 0.75},
    WeatherType.GLOOM:      {"dark": 1.25, "light": 0.75},
}


def weather_elemental_amp(weather: WeatherType,
                            element: ElementName,
                            intensity: float = 1.0) -> float:
    """The cast-damage multiplier for `element` under this weather.

    Intensity 0..1 attenuates the deviation from 1.0. A 50%-intensity
    blizzard gives ice 1.0 + 0.50 * 0.25 = 1.125 instead of 1.25.
    """
    table = WEATHER_ELEMENTAL_AMP_TABLE.get(weather, {})
    base = table.get(element, 1.0)
    if intensity == 1.0 or base == 1.0:
        return base
    intensity = max(0.0, min(1.0, intensity))
    deviation = base - 1.0
    return 1.0 + deviation * intensity
