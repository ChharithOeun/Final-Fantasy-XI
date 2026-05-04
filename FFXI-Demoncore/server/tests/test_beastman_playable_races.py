"""Tests for the beastman playable races."""
from __future__ import annotations

from server.beastman_playable_races import (
    BeastmanPlayableRaces,
    BeastmanRace,
    Gender,
    GenderConstraint,
    RacialTrait,
)


def test_all_four_races():
    r = BeastmanPlayableRaces()
    races = r.all_races()
    assert set(races) == {
        BeastmanRace.YAGUDO,
        BeastmanRace.QUADAV,
        BeastmanRace.LAMIA,
        BeastmanRace.ORC,
    }


def test_yagudo_profile():
    r = BeastmanPlayableRaces()
    prof = r.race_profile(race=BeastmanRace.YAGUDO)
    assert prof.gender_constraint == GenderConstraint.EITHER
    assert RacialTrait.BEAK_STRIKE in prof.racial_traits
    assert prof.starting_city_id == "oztroja_temple"


def test_quadav_profile_high_vit():
    r = BeastmanPlayableRaces()
    prof = r.race_profile(race=BeastmanRace.QUADAV)
    assert prof.stat_profile.vit > 10
    assert RacialTrait.HARD_SHELL in prof.racial_traits


def test_lamia_female_only():
    r = BeastmanPlayableRaces()
    prof = r.race_profile(race=BeastmanRace.LAMIA)
    assert (
        prof.gender_constraint
        == GenderConstraint.FEMALE_ONLY
    )


def test_lamia_can_select_female():
    r = BeastmanPlayableRaces()
    assert r.can_select(
        race=BeastmanRace.LAMIA, gender=Gender.FEMALE,
    )


def test_lamia_cannot_select_male():
    r = BeastmanPlayableRaces()
    assert not r.can_select(
        race=BeastmanRace.LAMIA, gender=Gender.MALE,
    )


def test_orc_can_select_either_gender():
    r = BeastmanPlayableRaces()
    assert r.can_select(
        race=BeastmanRace.ORC, gender=Gender.MALE,
    )
    assert r.can_select(
        race=BeastmanRace.ORC, gender=Gender.FEMALE,
    )


def test_orc_high_str():
    r = BeastmanPlayableRaces()
    prof = r.race_profile(race=BeastmanRace.ORC)
    # Orc should be the strongest STR base
    others = [
        r.race_profile(race=br).stat_profile.str_
        for br in BeastmanRace
        if br != BeastmanRace.ORC
    ]
    assert prof.stat_profile.str_ > max(others)


def test_yagudo_int_higher_than_orc():
    r = BeastmanPlayableRaces()
    yagudo_int = r.race_profile(
        race=BeastmanRace.YAGUDO,
    ).stat_profile.int_
    orc_int = r.race_profile(
        race=BeastmanRace.ORC,
    ).stat_profile.int_
    assert yagudo_int > orc_int


def test_lamia_dex_and_chr_high():
    r = BeastmanPlayableRaces()
    prof = r.race_profile(race=BeastmanRace.LAMIA)
    assert prof.stat_profile.dex >= 10
    assert prof.stat_profile.chr_ >= 10


def test_traits_for_returns_tuple():
    r = BeastmanPlayableRaces()
    traits = r.traits_for(race=BeastmanRace.QUADAV)
    assert isinstance(traits, tuple)
    assert RacialTrait.HARD_SHELL in traits


def test_starting_city_for_each_race():
    r = BeastmanPlayableRaces()
    cities = {
        race: r.starting_city(race=race)
        for race in BeastmanRace
    }
    # Each race must have a distinct starting city
    assert len(set(cities.values())) == len(BeastmanRace)


def test_language_for_each_race():
    r = BeastmanPlayableRaces()
    for race in BeastmanRace:
        lang = r.language(race=race)
        assert lang


def test_quadav_low_agi():
    r = BeastmanPlayableRaces()
    prof = r.race_profile(race=BeastmanRace.QUADAV)
    assert prof.stat_profile.agi <= 6


def test_lamia_serpent_gaze_trait():
    r = BeastmanPlayableRaces()
    assert RacialTrait.SERPENT_GAZE in r.traits_for(
        race=BeastmanRace.LAMIA,
    )


def test_orc_war_frenzy_trait():
    r = BeastmanPlayableRaces()
    assert RacialTrait.WAR_FRENZY in r.traits_for(
        race=BeastmanRace.ORC,
    )


def test_yagudo_honor_bond_trait():
    r = BeastmanPlayableRaces()
    assert RacialTrait.HONOR_BOND in r.traits_for(
        race=BeastmanRace.YAGUDO,
    )


def test_quadav_iron_gut_trait():
    r = BeastmanPlayableRaces()
    assert RacialTrait.IRON_GUT in r.traits_for(
        race=BeastmanRace.QUADAV,
    )
