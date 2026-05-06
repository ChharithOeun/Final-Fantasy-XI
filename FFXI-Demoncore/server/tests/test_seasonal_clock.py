"""Tests for seasonal_clock."""
from __future__ import annotations

from server.seasonal_clock import Climate, Season, SeasonalClock


YEAR = 360 * 24 * 3600


def test_spring_at_year_start():
    c = SeasonalClock()
    assert c.season_for(
        vana_seconds=0, seconds_per_year=YEAR,
    ) == Season.SPRING


def test_summer_at_quarter_year():
    c = SeasonalClock()
    assert c.season_for(
        vana_seconds=YEAR // 4, seconds_per_year=YEAR,
    ) == Season.SUMMER


def test_autumn_at_half_year():
    c = SeasonalClock()
    assert c.season_for(
        vana_seconds=YEAR // 2, seconds_per_year=YEAR,
    ) == Season.AUTUMN


def test_winter_at_three_quarter_year():
    c = SeasonalClock()
    assert c.season_for(
        vana_seconds=3 * YEAR // 4,
        seconds_per_year=YEAR,
    ) == Season.WINTER


def test_year_wraps():
    c = SeasonalClock()
    assert c.season_for(
        vana_seconds=YEAR + 100,
        seconds_per_year=YEAR,
    ) == Season.SPRING


def test_zero_seconds_per_year_safe():
    c = SeasonalClock()
    assert c.season_for(
        vana_seconds=100, seconds_per_year=0,
    ) == Season.SPRING


def test_negative_seconds_safe():
    c = SeasonalClock()
    assert c.season_for(
        vana_seconds=-100, seconds_per_year=YEAR,
    ) == Season.SPRING


def test_day_of_year():
    c = SeasonalClock()
    assert c.day_of_year(
        vana_seconds=0, seconds_per_year=YEAR,
    ) == 0
    assert c.day_of_year(
        vana_seconds=YEAR // 2, seconds_per_year=YEAR,
    ) == 180


def test_day_of_year_wraps():
    c = SeasonalClock()
    assert c.day_of_year(
        vana_seconds=YEAR + 1000,
        seconds_per_year=YEAR,
    ) < 360


def test_weights_temperate_spring():
    c = SeasonalClock()
    w = c.weather_weights(
        season=Season.SPRING, climate=Climate.TEMPERATE,
    )
    assert "rain" in w
    assert w["rain"] >= 50


def test_weights_desert_summer():
    c = SeasonalClock()
    w = c.weather_weights(
        season=Season.SUMMER, climate=Climate.DESERT,
    )
    assert "sandstorm" in w
    assert "rain" not in w


def test_weights_tundra_winter_blizzard_dominant():
    c = SeasonalClock()
    w = c.weather_weights(
        season=Season.WINTER, climate=Climate.TUNDRA,
    )
    assert w["blizzard"] >= 50


def test_weights_tropical_summer_thunder_heavy():
    c = SeasonalClock()
    w = c.weather_weights(
        season=Season.SUMMER, climate=Climate.TROPICAL,
    )
    assert w["thunderstorm"] >= 30


def test_weights_highland_autumn_fog_heavy():
    c = SeasonalClock()
    w = c.weather_weights(
        season=Season.AUTUMN, climate=Climate.HIGHLAND,
    )
    assert w["fog"] >= 30


def test_weights_returns_copy():
    c = SeasonalClock()
    w1 = c.weather_weights(
        season=Season.SPRING, climate=Climate.TEMPERATE,
    )
    w1["rain"] = 999
    w2 = c.weather_weights(
        season=Season.SPRING, climate=Climate.TEMPERATE,
    )
    # mutation shouldn't leak
    assert w2["rain"] != 999


def test_four_seasons():
    assert len(list(Season)) == 4


def test_five_climates():
    assert len(list(Climate)) == 5


def test_all_climate_season_pairs_have_weights():
    c = SeasonalClock()
    for season in Season:
        for climate in Climate:
            w = c.weather_weights(season=season, climate=climate)
            assert len(w) > 0
