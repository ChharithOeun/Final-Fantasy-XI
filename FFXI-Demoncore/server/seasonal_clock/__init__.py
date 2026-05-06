"""Seasonal clock — 4-season calendar driving weather distributions.

Vana'diel runs through SPRING / SUMMER / AUTUMN / WINTER.
Each season has its own weather weight distribution per
zone-climate. Spring brings rain and floods; summer brings
clear and thunderstorms; autumn brings fog; winter brings
snow and blizzards. The seasonal_clock just computes which
season is active given a Vana'diel timestamp, plus a
per-climate weather weight table.

Public surface
--------------
    Season enum
    Climate enum (TEMPERATE / DESERT / TUNDRA / TROPICAL /
                  HIGHLAND)
    SeasonalClock
        .season_for(vana_seconds, seconds_per_year) -> Season
        .day_of_year(vana_seconds, seconds_per_year) -> int
        .weather_weights(season, climate) -> dict[str, int]
"""
from __future__ import annotations

import enum
import typing as t


class Season(str, enum.Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class Climate(str, enum.Enum):
    TEMPERATE = "temperate"
    DESERT = "desert"
    TUNDRA = "tundra"
    TROPICAL = "tropical"
    HIGHLAND = "highland"


# weights are not normalized; caller decides
_WEATHER_TABLE: dict[
    tuple[Season, Climate], dict[str, int],
] = {
    # TEMPERATE
    (Season.SPRING, Climate.TEMPERATE): {
        "clear": 30, "rain": 50, "thunderstorm": 15, "fog": 5,
    },
    (Season.SUMMER, Climate.TEMPERATE): {
        "clear": 60, "rain": 20, "thunderstorm": 20,
    },
    (Season.AUTUMN, Climate.TEMPERATE): {
        "clear": 30, "rain": 30, "fog": 35, "snow": 5,
    },
    (Season.WINTER, Climate.TEMPERATE): {
        "clear": 30, "snow": 50, "blizzard": 15, "fog": 5,
    },
    # DESERT
    (Season.SPRING, Climate.DESERT): {
        "clear": 75, "sandstorm": 25,
    },
    (Season.SUMMER, Climate.DESERT): {
        "clear": 60, "sandstorm": 40,
    },
    (Season.AUTUMN, Climate.DESERT): {
        "clear": 80, "sandstorm": 20,
    },
    (Season.WINTER, Climate.DESERT): {
        "clear": 90, "sandstorm": 10,
    },
    # TUNDRA
    (Season.SPRING, Climate.TUNDRA): {
        "clear": 20, "snow": 50, "blizzard": 30,
    },
    (Season.SUMMER, Climate.TUNDRA): {
        "clear": 40, "rain": 30, "snow": 30,
    },
    (Season.AUTUMN, Climate.TUNDRA): {
        "clear": 20, "snow": 40, "blizzard": 40,
    },
    (Season.WINTER, Climate.TUNDRA): {
        "blizzard": 80, "snow": 20,
    },
    # TROPICAL
    (Season.SPRING, Climate.TROPICAL): {
        "clear": 30, "rain": 60, "thunderstorm": 10,
    },
    (Season.SUMMER, Climate.TROPICAL): {
        "clear": 20, "rain": 30, "thunderstorm": 50,
    },
    (Season.AUTUMN, Climate.TROPICAL): {
        "clear": 40, "rain": 50, "thunderstorm": 10,
    },
    (Season.WINTER, Climate.TROPICAL): {
        "clear": 70, "rain": 30,
    },
    # HIGHLAND
    (Season.SPRING, Climate.HIGHLAND): {
        "clear": 40, "rain": 30, "fog": 30,
    },
    (Season.SUMMER, Climate.HIGHLAND): {
        "clear": 60, "rain": 20, "fog": 20,
    },
    (Season.AUTUMN, Climate.HIGHLAND): {
        "clear": 30, "fog": 50, "snow": 20,
    },
    (Season.WINTER, Climate.HIGHLAND): {
        "snow": 60, "blizzard": 30, "clear": 10,
    },
}


_SEASON_ORDER = (
    Season.SPRING, Season.SUMMER,
    Season.AUTUMN, Season.WINTER,
)


class SeasonalClock:

    def season_for(
        self, *, vana_seconds: int, seconds_per_year: int,
    ) -> Season:
        if seconds_per_year <= 0:
            return Season.SPRING
        if vana_seconds < 0:
            vana_seconds = 0
        within = vana_seconds % seconds_per_year
        quarter = (within * 4) // seconds_per_year
        return _SEASON_ORDER[min(3, max(0, quarter))]

    def day_of_year(
        self, *, vana_seconds: int, seconds_per_year: int,
    ) -> int:
        if seconds_per_year <= 0:
            return 0
        if vana_seconds < 0:
            return 0
        within = vana_seconds % seconds_per_year
        # 360-day year
        return (within * 360) // seconds_per_year

    def weather_weights(
        self, *, season: Season, climate: Climate,
    ) -> dict[str, int]:
        return dict(_WEATHER_TABLE.get((season, climate), {}))


__all__ = ["Season", "Climate", "SeasonalClock"]
