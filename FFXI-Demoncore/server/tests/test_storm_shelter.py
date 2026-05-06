"""Tests for storm_shelter."""
from __future__ import annotations

from server.storm_shelter import ShelterIntent, StormShelterEngine


def test_register_happy():
    e = StormShelterEngine()
    ok = e.register_npc(
        npc_id="farmer", fear_threshold=40,
        preferred_shelter_id="barn",
    )
    assert ok is True


def test_blank_id_blocked():
    e = StormShelterEngine()
    out = e.register_npc(npc_id="", fear_threshold=40)
    assert out is False


def test_threshold_out_of_range():
    e = StormShelterEngine()
    assert e.register_npc(
        npc_id="x", fear_threshold=-1,
    ) is False
    assert e.register_npc(
        npc_id="x", fear_threshold=101,
    ) is False


def test_duplicate_blocked():
    e = StormShelterEngine()
    e.register_npc(npc_id="x", fear_threshold=40)
    again = e.register_npc(npc_id="x", fear_threshold=50)
    assert again is False


def test_unknown_npc():
    e = StormShelterEngine()
    out = e.check_npc(
        npc_id="ghost", current_intensity=80,
        weather_kind="thunderstorm",
    )
    assert out == ShelterIntent.UNKNOWN_NPC


def test_fearless_no_shelter():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="sailor", fear_threshold=0, fearless=True,
    )
    out = e.check_npc(
        npc_id="sailor", current_intensity=100,
        weather_kind="thunderstorm",
    )
    assert out == ShelterIntent.NONE


def test_below_threshold_no_shelter():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="farmer", fear_threshold=60,
        preferred_shelter_id="barn",
    )
    out = e.check_npc(
        npc_id="farmer", current_intensity=50,
        weather_kind="thunderstorm",
    )
    assert out == ShelterIntent.NONE


def test_above_threshold_seeks_shelter():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="farmer", fear_threshold=40,
        preferred_shelter_id="barn",
    )
    out = e.check_npc(
        npc_id="farmer", current_intensity=70,
        weather_kind="thunderstorm",
    )
    assert out == ShelterIntent.AT_SHELTER


def test_no_preferred_shelter_seeks_any():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="wanderer", fear_threshold=40,
    )
    out = e.check_npc(
        npc_id="wanderer", current_intensity=70,
        weather_kind="thunderstorm",
    )
    assert out == ShelterIntent.SEEK_SHELTER


def test_clear_weather_clears_shelter():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="farmer", fear_threshold=40,
        preferred_shelter_id="barn",
    )
    e.check_npc(
        npc_id="farmer", current_intensity=70,
        weather_kind="thunderstorm",
    )
    out = e.check_npc(
        npc_id="farmer", current_intensity=0,
        weather_kind="clear",
    )
    assert out == ShelterIntent.NONE


def test_blizzard_drives_shelter():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="farmer", fear_threshold=40,
        preferred_shelter_id="barn",
    )
    out = e.check_npc(
        npc_id="farmer", current_intensity=80,
        weather_kind="blizzard",
    )
    assert out == ShelterIntent.AT_SHELTER


def test_sandstorm_drives_shelter():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="trader", fear_threshold=40,
        preferred_shelter_id="caravan_tent",
    )
    out = e.check_npc(
        npc_id="trader", current_intensity=80,
        weather_kind="sandstorm",
    )
    assert out == ShelterIntent.AT_SHELTER


def test_rain_does_not_drive_shelter():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="farmer", fear_threshold=40,
        preferred_shelter_id="barn",
    )
    # rain (not in shelter-worthy set)
    out = e.check_npc(
        npc_id="farmer", current_intensity=100,
        weather_kind="rain",
    )
    assert out == ShelterIntent.NONE


def test_npcs_at_shelter_index():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="a", fear_threshold=40,
        preferred_shelter_id="barn",
    )
    e.register_npc(
        npc_id="b", fear_threshold=40,
        preferred_shelter_id="barn",
    )
    e.register_npc(
        npc_id="c", fear_threshold=40,
        preferred_shelter_id="church",
    )
    e.check_npc(
        npc_id="a", current_intensity=80,
        weather_kind="thunderstorm",
    )
    e.check_npc(
        npc_id="b", current_intensity=80,
        weather_kind="thunderstorm",
    )
    e.check_npc(
        npc_id="c", current_intensity=80,
        weather_kind="thunderstorm",
    )
    barn = e.npcs_at_shelter(shelter_id="barn")
    assert barn == ("a", "b")


def test_clear_shelter():
    e = StormShelterEngine()
    e.register_npc(
        npc_id="a", fear_threshold=40,
        preferred_shelter_id="barn",
    )
    e.check_npc(
        npc_id="a", current_intensity=80,
        weather_kind="thunderstorm",
    )
    ok = e.clear_shelter(npc_id="a")
    assert ok is True
    out = e.npcs_at_shelter(shelter_id="barn")
    assert "a" not in out


def test_clear_shelter_when_not_sheltered():
    e = StormShelterEngine()
    out = e.clear_shelter(npc_id="ghost")
    assert out is False


def test_total_npcs():
    e = StormShelterEngine()
    e.register_npc(npc_id="a", fear_threshold=40)
    e.register_npc(npc_id="b", fear_threshold=40)
    assert e.total_npcs() == 2


def test_four_shelter_intents():
    assert len(list(ShelterIntent)) == 4
