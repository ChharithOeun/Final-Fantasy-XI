"""Day / Weather damage modifiers — Vana'diel calendar amplifiers.

Vana'diel's 8-day week + per-zone weather provide elemental
multipliers on offensive (and defensive) magic. Pure-function
lookup, callers pass the current day + zone weather.

Modifier rules (canonical FFXI):
* MATCHING DAY        — spell of same element as the day: +10%
* OPPOSING DAY        — spell of opposing element: -10%
* SINGLE WEATHER      — spell of same element as weather: +10%
* DOUBLE WEATHER      — same-element double weather: +30%
* OPPOSING WEATHER    — spell of opposing element to weather: -30%

The aggregate modifier is the SUM (not product) of the day and
weather modifiers, capped at +35% / -35%.

Vana'diel days, in order:
    Firesday, Earthsday, Watersday, Windsday, Iceday,
    Lightningsday, Lightsday, Darksday

Public surface
--------------
    Element enum (8 elements)
    VanaDay enum (8 days)
    WeatherKind enum (NONE / SINGLE_<E> / DOUBLE_<E>)
    day_modifier(spell_element, day) -> int
    weather_modifier(spell_element, weather) -> int
    total_modifier(spell_element, day, weather) -> int
"""
from __future__ import annotations

import enum


# Aggregate cap (+/-35% across day + weather)
TOTAL_CAP_PCT = 35


class Element(str, enum.Enum):
    FIRE = "fire"
    EARTH = "earth"
    WATER = "water"
    WIND = "wind"
    ICE = "ice"
    LIGHTNING = "lightning"
    LIGHT = "light"
    DARK = "dark"


class VanaDay(str, enum.Enum):
    FIRESDAY = "firesday"
    EARTHSDAY = "earthsday"
    WATERSDAY = "watersday"
    WINDSDAY = "windsday"
    ICEDAY = "iceday"
    LIGHTNINGSDAY = "lightningsday"
    LIGHTSDAY = "lightsday"
    DARKSDAY = "darksday"


class WeatherKind(str, enum.Enum):
    NONE = "none"
    # Single weather (one storm cloud)
    SINGLE_FIRE = "single_fire"
    SINGLE_EARTH = "single_earth"
    SINGLE_WATER = "single_water"
    SINGLE_WIND = "single_wind"
    SINGLE_ICE = "single_ice"
    SINGLE_LIGHTNING = "single_lightning"
    SINGLE_LIGHT = "single_light"
    SINGLE_DARK = "single_dark"
    # Double weather (two storm clouds — rare, maximum amp)
    DOUBLE_FIRE = "double_fire"
    DOUBLE_EARTH = "double_earth"
    DOUBLE_WATER = "double_water"
    DOUBLE_WIND = "double_wind"
    DOUBLE_ICE = "double_ice"
    DOUBLE_LIGHTNING = "double_lightning"
    DOUBLE_LIGHT = "double_light"
    DOUBLE_DARK = "double_dark"


# Canonical FFXI element wheel of opposition
_OPPOSING: dict[Element, Element] = {
    Element.FIRE: Element.WATER,
    Element.WATER: Element.FIRE,
    Element.EARTH: Element.WIND,
    Element.WIND: Element.EARTH,
    Element.ICE: Element.LIGHTNING,
    Element.LIGHTNING: Element.ICE,
    Element.LIGHT: Element.DARK,
    Element.DARK: Element.LIGHT,
}


# Day -> element it matches
_DAY_ELEMENT: dict[VanaDay, Element] = {
    VanaDay.FIRESDAY: Element.FIRE,
    VanaDay.EARTHSDAY: Element.EARTH,
    VanaDay.WATERSDAY: Element.WATER,
    VanaDay.WINDSDAY: Element.WIND,
    VanaDay.ICEDAY: Element.ICE,
    VanaDay.LIGHTNINGSDAY: Element.LIGHTNING,
    VanaDay.LIGHTSDAY: Element.LIGHT,
    VanaDay.DARKSDAY: Element.DARK,
}


# Weather -> (element, doubled?) decode
def _decode_weather(weather: WeatherKind) -> tuple[Element | None, bool]:
    if weather == WeatherKind.NONE:
        return (None, False)
    name = weather.value
    is_double = name.startswith("double_")
    elem_name = name.split("_", 1)[1]
    return (Element(elem_name), is_double)


def day_modifier(*, spell_element: Element, day: VanaDay) -> int:
    """+10 if spell matches day; -10 if opposing; 0 otherwise."""
    day_elem = _DAY_ELEMENT[day]
    if spell_element == day_elem:
        return 10
    if _OPPOSING.get(spell_element) == day_elem:
        return -10
    return 0


def weather_modifier(
    *, spell_element: Element, weather: WeatherKind,
) -> int:
    """+10 single same-element; +30 double same-element;
    -30 opposing-element weather (single OR double); 0 otherwise."""
    weather_elem, is_double = _decode_weather(weather)
    if weather_elem is None:
        return 0
    if spell_element == weather_elem:
        return 30 if is_double else 10
    if _OPPOSING.get(spell_element) == weather_elem:
        return -30
    return 0


def total_modifier(
    *, spell_element: Element, day: VanaDay,
    weather: WeatherKind = WeatherKind.NONE,
) -> int:
    """Sum of day + weather, capped at +/- TOTAL_CAP_PCT."""
    total = (
        day_modifier(spell_element=spell_element, day=day)
        + weather_modifier(spell_element=spell_element, weather=weather)
    )
    return max(-TOTAL_CAP_PCT, min(TOTAL_CAP_PCT, total))


def damage_multiplier(
    *, spell_element: Element, day: VanaDay,
    weather: WeatherKind = WeatherKind.NONE,
) -> float:
    """Convenience helper — returns 1.0 + (modifier_pct / 100)."""
    return 1.0 + total_modifier(
        spell_element=spell_element, day=day, weather=weather,
    ) / 100.0


def opposing_element(element: Element) -> Element:
    return _OPPOSING[element]


__all__ = [
    "TOTAL_CAP_PCT",
    "Element", "VanaDay", "WeatherKind",
    "day_modifier", "weather_modifier",
    "total_modifier", "damage_multiplier",
    "opposing_element",
]
