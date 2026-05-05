"""Tests for the underwater races registry."""
from __future__ import annotations

from server.underwater_races import (
    Gender,
    SharkSubtype,
    UnderwaterRace,
    UnderwaterRaceRegistry,
)


def test_total_races():
    r = UnderwaterRaceRegistry()
    assert r.total_races() == 5


def test_profile_for_mermaid():
    r = UnderwaterRaceRegistry()
    p = r.profile_for(race=UnderwaterRace.MERMAID)
    assert p.gender_rule == Gender.FEMALE_ONLY
    assert p.swim.true_aquatic is True


def test_profile_for_shark():
    r = UnderwaterRaceRegistry()
    p = r.profile_for(race=UnderwaterRace.SHARK_HUMANOID)
    assert p.gender_rule == Gender.MALE_ONLY


def test_profile_for_jellyfish_genderless():
    r = UnderwaterRaceRegistry()
    p = r.profile_for(race=UnderwaterRace.JELLYFISH)
    assert p.gender_rule == Gender.GENDERLESS


def test_profile_for_octopi_either():
    r = UnderwaterRaceRegistry()
    p = r.profile_for(race=UnderwaterRace.OCTOPI_SQUID)
    assert p.gender_rule == Gender.EITHER


def test_pick_shark_great_white():
    r = UnderwaterRaceRegistry()
    assert r.pick_shark_subtype(seed_pct=5) == SharkSubtype.GREAT_WHITE


def test_pick_shark_hammerhead():
    r = UnderwaterRaceRegistry()
    assert r.pick_shark_subtype(seed_pct=20) == SharkSubtype.HAMMERHEAD


def test_pick_shark_invalid():
    r = UnderwaterRaceRegistry()
    assert r.pick_shark_subtype(seed_pct=200) is None


def test_pick_shark_top_bucket():
    r = UnderwaterRaceRegistry()
    assert r.pick_shark_subtype(seed_pct=99) == SharkSubtype.NURSE


def test_validate_mermaid_female():
    r = UnderwaterRaceRegistry()
    res = r.validate_character(
        race=UnderwaterRace.MERMAID, gender="female",
    )
    assert res.accepted


def test_validate_mermaid_male_rejected():
    r = UnderwaterRaceRegistry()
    res = r.validate_character(
        race=UnderwaterRace.MERMAID, gender="male",
    )
    assert not res.accepted


def test_validate_shark_male():
    r = UnderwaterRaceRegistry()
    res = r.validate_character(
        race=UnderwaterRace.SHARK_HUMANOID, gender="male",
    )
    assert res.accepted


def test_validate_shark_female_rejected():
    r = UnderwaterRaceRegistry()
    res = r.validate_character(
        race=UnderwaterRace.SHARK_HUMANOID, gender="female",
    )
    assert not res.accepted


def test_validate_jellyfish_genderless():
    r = UnderwaterRaceRegistry()
    res = r.validate_character(
        race=UnderwaterRace.JELLYFISH, gender=None,
    )
    assert res.accepted


def test_validate_octopi_must_specify():
    r = UnderwaterRaceRegistry()
    res = r.validate_character(
        race=UnderwaterRace.OCTOPI_SQUID, gender=None,
    )
    assert not res.accepted


def test_validate_octopi_either_works():
    r = UnderwaterRaceRegistry()
    res_m = r.validate_character(
        race=UnderwaterRace.OCTOPI_SQUID, gender="male",
    )
    res_f = r.validate_character(
        race=UnderwaterRace.OCTOPI_SQUID, gender="female",
    )
    assert res_m.accepted
    assert res_f.accepted


def test_validate_unknown_race():
    r = UnderwaterRaceRegistry()
    # Casting via str-enum trick — pass an unrecognized member
    class Fake:
        value = "ghost"
    res = r.validate_character(race=Fake(), gender="any")
    assert not res.accepted


def test_fomor_underwater_genderless():
    r = UnderwaterRaceRegistry()
    p = r.profile_for(race=UnderwaterRace.FOMOR_UNDERWATER)
    assert p.gender_rule == Gender.GENDERLESS
