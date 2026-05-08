"""Tests for hair_growth_styling."""
from __future__ import annotations

from server.hair_growth_styling import (
    HairColor, HairGrowthStyling,
)


def test_default_profile():
    h = HairGrowthStyling()
    p = h.profile(player_id="bob", now_day=0)
    assert p.style_id == "default_short"
    assert p.base_length_cm == 5.0
    assert p.color == HairColor.BLACK


def test_style_happy():
    h = HairGrowthStyling()
    assert h.style(
        player_id="bob", style_id="braided",
        length_cm=15.0, color=HairColor.RED,
        now_day=10,
    ) is True


def test_style_blank_player_blocked():
    h = HairGrowthStyling()
    assert h.style(
        player_id="", style_id="x",
        length_cm=5, color=HairColor.BLACK, now_day=10,
    ) is False


def test_style_blank_id_blocked():
    h = HairGrowthStyling()
    assert h.style(
        player_id="bob", style_id="",
        length_cm=5, color=HairColor.BLACK, now_day=10,
    ) is False


def test_style_negative_length_blocked():
    h = HairGrowthStyling()
    assert h.style(
        player_id="bob", style_id="x",
        length_cm=-1, color=HairColor.BLACK, now_day=10,
    ) is False


def test_style_huge_length_blocked():
    h = HairGrowthStyling()
    assert h.style(
        player_id="bob", style_id="x",
        length_cm=500, color=HairColor.BLACK, now_day=10,
    ) is False


def test_set_growth_rate():
    h = HairGrowthStyling()
    assert h.set_growth_rate(
        player_id="bob", multiplier=1.5,
    ) is True


def test_set_growth_rate_zero_blocked():
    h = HairGrowthStyling()
    assert h.set_growth_rate(
        player_id="bob", multiplier=0,
    ) is False


def test_set_growth_rate_too_high_blocked():
    h = HairGrowthStyling()
    assert h.set_growth_rate(
        player_id="bob", multiplier=10,
    ) is False


def test_current_length_grows_over_time():
    h = HairGrowthStyling()
    h.style(
        player_id="bob", style_id="buzz",
        length_cm=2.0, color=HairColor.BLACK, now_day=0,
    )
    # 7 days at 0.14/day = 0.98cm grown
    cur = h.current_length_cm(
        player_id="bob", now_day=7,
    )
    assert 2.9 < cur < 3.0


def test_growth_with_mithra_rate():
    h = HairGrowthStyling()
    h.style(
        player_id="bob", style_id="buzz",
        length_cm=2.0, color=HairColor.BLACK, now_day=0,
    )
    h.set_growth_rate(player_id="bob", multiplier=2.0)
    cur = h.current_length_cm(
        player_id="bob", now_day=7,
    )
    # 2x rate -> ~1.96cm grown
    assert 3.9 < cur < 4.0


def test_no_state_returns_default():
    h = HairGrowthStyling()
    cur = h.current_length_cm(
        player_id="ghost", now_day=100,
    )
    assert cur == 5.0


def test_profile_includes_current_length():
    h = HairGrowthStyling()
    h.style(
        player_id="bob", style_id="buzz",
        length_cm=2.0, color=HairColor.BLACK, now_day=0,
    )
    p = h.profile(player_id="bob", now_day=14)
    # 14 * 0.14 = 1.96 grown
    assert 3.9 < p.current_length_cm < 4.0


def test_styling_resets_growth_clock():
    h = HairGrowthStyling()
    h.style(
        player_id="bob", style_id="buzz",
        length_cm=2.0, color=HairColor.BLACK, now_day=0,
    )
    # 30 days -> ~6.2cm
    h.style(
        player_id="bob", style_id="trim",
        length_cm=3.0, color=HairColor.BLACK, now_day=30,
    )
    # Just trimmed; current = 3.0
    cur = h.current_length_cm(
        player_id="bob", now_day=30,
    )
    assert cur == 3.0


def test_needs_barber():
    h = HairGrowthStyling()
    h.style(
        player_id="bob", style_id="short",
        length_cm=5.0, color=HairColor.BLACK, now_day=0,
    )
    # After 60 days -> 5 + 60*0.14 = 13.4
    assert h.needs_barber(
        player_id="bob", now_day=60,
        max_length_cm=10.0,
    ) is True


def test_doesnt_need_barber_yet():
    h = HairGrowthStyling()
    h.style(
        player_id="bob", style_id="short",
        length_cm=5.0, color=HairColor.BLACK, now_day=0,
    )
    # After 14 days -> ~7cm
    assert h.needs_barber(
        player_id="bob", now_day=14,
        max_length_cm=10.0,
    ) is False


def test_dyed_color():
    h = HairGrowthStyling()
    h.style(
        player_id="bob", style_id="punk",
        length_cm=8.0, color=HairColor.DYED_PINK,
        now_day=0,
    )
    p = h.profile(player_id="bob", now_day=0)
    assert p.color == HairColor.DYED_PINK


def test_nine_hair_colors():
    assert len(list(HairColor)) == 9


def test_negative_now_day_no_growth():
    h = HairGrowthStyling()
    h.style(
        player_id="bob", style_id="buzz",
        length_cm=2.0, color=HairColor.BLACK, now_day=10,
    )
    # now_day < last_styled_day; clamped to 0 elapsed
    cur = h.current_length_cm(
        player_id="bob", now_day=5,
    )
    assert cur == 2.0
