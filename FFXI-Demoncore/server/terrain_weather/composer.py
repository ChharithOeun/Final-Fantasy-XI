"""EnvironmentEffectComposer — combines terrain + weather + race +
fomor lighting + GEO bubbles into a single per-unit modifier bundle.

This is the headline API: pass in the zone environment, the unit's
race + flags + position, and an optional GeoManipulator; receive an
EffectiveModifier that downstream systems (combat, weight_physics,
mob_resistances) consume.

All factors stack MULTIPLICATIVELY. Every component returns 1.0 by
default; the composer simply multiplies the relevant tweaks.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .fomor_lighting import fomor_lighting_strength
from .manipulators import GeoBubble, GeoManipulator
from .race_modifiers import (
    race_terrain_multiplier,
    race_weather_multiplier,
)
from .terrain import TerrainType, ZoneEnvironment
from .weather import WeatherType, weather_elemental_amp


@dataclasses.dataclass
class EffectiveModifier:
    """The bundle of environment-driven tweaks for a single unit.

    All multiplicative; 1.0 = no effect. Per-element multipliers are
    keyed by element name (not the Element enum) to keep this module
    stand-alone.
    """
    # All-stats vitality mult (race/terrain/weather composite)
    vitality_mult: float = 1.0
    # Per-element cast/damage multipliers (weather + GEO bubbles)
    elemental_mult: dict[str, float] = dataclasses.field(default_factory=dict)
    # Fomor-only multiplier (1.0 for non-fomors)
    fomor_strength_mult: float = 1.0
    # Movement speed tweak (sandstorm / blizzard / heat-wave drag)
    speed_mult: float = 1.0
    # Accuracy delta (sandstorm/fog reduce; clear can buff)
    accuracy_mod: float = 0.0
    # Notes that were composed in (debug/UI)
    notes: list[str] = dataclasses.field(default_factory=list)

    def elemental_multiplier_for(self, element: str) -> float:
        return self.elemental_mult.get(element, 1.0)


# Per-weather kinematic side-effects (speed + accuracy)
WEATHER_SIDE_EFFECTS: dict[WeatherType, tuple[float, float]] = {
    # weather → (speed_mult, accuracy_mod)
    WeatherType.CLEAR:      (1.00,  0.0),
    WeatherType.RAIN:       (0.97, -2.0),
    WeatherType.SUNSHOWER:  (0.99,  0.0),
    WeatherType.THUNDER:    (0.95, -3.0),
    WeatherType.FOG:        (0.95, -8.0),    # visibility crash
    WeatherType.SANDSTORM:  (0.90, -12.0),
    WeatherType.SNOW_LIGHT: (0.95, -1.0),
    WeatherType.BLIZZARD:   (0.80, -8.0),
    WeatherType.HEAT_WAVE:  (0.95, -3.0),    # heat exhaustion
    WeatherType.WIND_GALES: (0.90, -5.0),
    WeatherType.AURORA:     (1.00,  0.0),
    WeatherType.GLOOM:      (1.00, -2.0),
}


class EnvironmentEffectComposer:
    """Combines all environmental factors into an EffectiveModifier."""

    KNOWN_ELEMENTS = ("fire", "ice", "water", "lightning",
                        "earth", "wind", "light", "dark")

    def compose(self,
                  *,
                  env: ZoneEnvironment,
                  race: str,
                  is_fomor: bool = False,
                  unit_position: t.Optional[tuple[float, float]] = None,
                  geo: t.Optional[GeoManipulator] = None) -> EffectiveModifier:
        """Build the modifier bundle for a unit at this position in
        this environment."""
        notes: list[str] = []

        # Resolve effective terrain + weather (GEO bubble can override)
        effective_terrain = env.terrain
        effective_weather = env.weather
        bubble: t.Optional[GeoBubble] = None
        if geo is not None and unit_position is not None:
            bubble = geo.bubble_at(env.zone_id, unit_position)
            if bubble is not None:
                if bubble.terrain_override is not None:
                    effective_terrain = bubble.terrain_override
                    notes.append(f"GEO terrain override: {effective_terrain.value}")
                if bubble.weather_override is not None:
                    effective_weather = bubble.weather_override
                    notes.append(f"GEO weather override: {effective_weather.value}")

        # 1) Race terrain + weather multipliers
        race_terrain = race_terrain_multiplier(race, effective_terrain)
        race_weather = race_weather_multiplier(race, effective_weather)
        vitality = race_terrain * race_weather
        if race_terrain != 1.0:
            notes.append(f"race+terrain ({race}/{effective_terrain.value}) "
                          f"= {race_terrain:.2f}")
        if race_weather != 1.0:
            notes.append(f"race+weather ({race}/{effective_weather.value}) "
                          f"= {race_weather:.2f}")

        # 2) Fomor lighting strength
        fomor_mult = 1.0
        if is_fomor:
            fomor_mult = fomor_lighting_strength(env.lighting)
            if fomor_mult != 1.0:
                notes.append(f"fomor lighting ({env.lighting.value}) "
                              f"= {fomor_mult:.2f}")

        # 3) Per-element weather amp + GEO bubble elemental boost
        elemental_mult: dict[str, float] = {}
        for el in self.KNOWN_ELEMENTS:
            amp = weather_elemental_amp(effective_weather, el,
                                          intensity=env.weather_intensity)
            if amp != 1.0:
                elemental_mult[el] = amp
        if bubble is not None and bubble.elemental_boost is not None:
            el, mult = bubble.elemental_boost
            elemental_mult[el] = elemental_mult.get(el, 1.0) * mult
            notes.append(f"GEO bubble {el} x{mult:.2f}")

        # 4) Weather side-effects (speed + accuracy)
        speed_mult, accuracy_mod = WEATHER_SIDE_EFFECTS.get(
            effective_weather, (1.0, 0.0))
        # Intensity attenuates the deviation from baseline
        intensity = env.weather_intensity
        if speed_mult != 1.0:
            speed_mult = 1.0 + (speed_mult - 1.0) * intensity
        if accuracy_mod != 0.0:
            accuracy_mod = accuracy_mod * intensity

        return EffectiveModifier(
            vitality_mult=vitality,
            elemental_mult=elemental_mult,
            fomor_strength_mult=fomor_mult,
            speed_mult=speed_mult,
            accuracy_mod=accuracy_mod,
            notes=notes,
        )
