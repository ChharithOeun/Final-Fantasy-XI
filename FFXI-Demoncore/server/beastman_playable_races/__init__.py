"""Beastman playable races — Yagudo / Quadav / Lamia / Orc.

Four new playable races introduced in the Shadowlands
expansion. Each carries a distinct stat profile, racial trait
set, language, and starting beastman city. Lamia is
female-only (canon biological constraint); the other three
support both genders. All four races plug into existing
character_stats and equipment_stats with race scaling.

Public surface
--------------
    BeastmanRace enum
    GenderConstraint enum
    RacialTrait enum
    StatProfile dataclass
    BeastmanRaceProfile dataclass
    BeastmanPlayableRaces
        .race_profile(race)
        .can_select(race, gender) -> bool
        .traits_for(race) -> tuple[RacialTrait]
        .starting_city(race) -> str
        .language(race) -> str
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BeastmanRace(str, enum.Enum):
    YAGUDO = "yagudo"
    QUADAV = "quadav"
    LAMIA = "lamia"
    ORC = "orc"


class GenderConstraint(str, enum.Enum):
    EITHER = "either"
    FEMALE_ONLY = "female_only"
    MALE_ONLY = "male_only"


class RacialTrait(str, enum.Enum):
    BEAK_STRIKE = "beak_strike"        # Yagudo
    HARD_SHELL = "hard_shell"          # Quadav
    SERPENT_GAZE = "serpent_gaze"      # Lamia
    WAR_FRENZY = "war_frenzy"          # Orc
    FLIGHT_LEAP = "flight_leap"
    POISON_BLOOD = "poison_blood"
    NIGHT_SIGHT = "night_sight"
    IRON_GUT = "iron_gut"
    HONOR_BOND = "honor_bond"
    SAVAGE_ROAR = "savage_roar"


class Gender(str, enum.Enum):
    FEMALE = "female"
    MALE = "male"


@dataclasses.dataclass(frozen=True)
class StatProfile:
    """Base stat values at level 1; canon ranges roughly
    follow Hume = 1.00x baseline."""
    str_: int
    dex: int
    vit: int
    agi: int
    int_: int
    mnd: int
    chr_: int


@dataclasses.dataclass(frozen=True)
class BeastmanRaceProfile:
    race: BeastmanRace
    gender_constraint: GenderConstraint
    starting_city_id: str
    language_label: str
    stat_profile: StatProfile
    racial_traits: tuple[RacialTrait, ...]
    notes: str = ""


# Canonical profiles. Stat numbers are rough — they preserve
# the relative balance between races, not exact retail values.
_PROFILES: dict[BeastmanRace, BeastmanRaceProfile] = {
    BeastmanRace.YAGUDO: BeastmanRaceProfile(
        race=BeastmanRace.YAGUDO,
        gender_constraint=GenderConstraint.EITHER,
        starting_city_id="oztroja_temple",
        language_label="yagudic",
        stat_profile=StatProfile(
            str_=7, dex=8, vit=6,
            agi=9, int_=8, mnd=8, chr_=6,
        ),
        racial_traits=(
            RacialTrait.BEAK_STRIKE,
            RacialTrait.NIGHT_SIGHT,
            RacialTrait.HONOR_BOND,
        ),
        notes=(
            "Order of clergy. Strong INT/AGI; agile and "
            "ritually-trained casters."
        ),
    ),
    BeastmanRace.QUADAV: BeastmanRaceProfile(
        race=BeastmanRace.QUADAV,
        gender_constraint=GenderConstraint.EITHER,
        starting_city_id="palborough_under",
        language_label="quadavic",
        stat_profile=StatProfile(
            str_=9, dex=6, vit=11,
            agi=5, int_=7, mnd=8, chr_=5,
        ),
        racial_traits=(
            RacialTrait.HARD_SHELL,
            RacialTrait.IRON_GUT,
        ),
        notes=(
            "Stone-armored bulwark race. High VIT, low AGI; "
            "tank-favored."
        ),
    ),
    BeastmanRace.LAMIA: BeastmanRaceProfile(
        race=BeastmanRace.LAMIA,
        gender_constraint=GenderConstraint.FEMALE_ONLY,
        starting_city_id="aydeewa_subhold",
        language_label="serpenttongue",
        stat_profile=StatProfile(
            str_=7, dex=10, vit=5,
            agi=10, int_=9, mnd=7, chr_=10,
        ),
        racial_traits=(
            RacialTrait.SERPENT_GAZE,
            RacialTrait.POISON_BLOOD,
            RacialTrait.FLIGHT_LEAP,
        ),
        notes=(
            "Female-only serpentkin. Dex/AGI/CHR-leaning "
            "predators with hypnotic stare."
        ),
    ),
    BeastmanRace.ORC: BeastmanRaceProfile(
        race=BeastmanRace.ORC,
        gender_constraint=GenderConstraint.EITHER,
        starting_city_id="davoi_mead_hall",
        language_label="orcish",
        stat_profile=StatProfile(
            str_=12, dex=7, vit=9,
            agi=6, int_=5, mnd=6, chr_=5,
        ),
        racial_traits=(
            RacialTrait.WAR_FRENZY,
            RacialTrait.SAVAGE_ROAR,
        ),
        notes=(
            "Pure brute force. Highest STR; melee/berserker "
            "favored."
        ),
    ),
}


@dataclasses.dataclass
class BeastmanPlayableRaces:
    def race_profile(
        self, *, race: BeastmanRace,
    ) -> BeastmanRaceProfile:
        return _PROFILES[race]

    def can_select(
        self, *, race: BeastmanRace, gender: Gender,
    ) -> bool:
        prof = _PROFILES[race]
        if prof.gender_constraint == GenderConstraint.EITHER:
            return True
        if prof.gender_constraint == GenderConstraint.FEMALE_ONLY:
            return gender == Gender.FEMALE
        if prof.gender_constraint == GenderConstraint.MALE_ONLY:
            return gender == Gender.MALE
        return False

    def traits_for(
        self, *, race: BeastmanRace,
    ) -> tuple[RacialTrait, ...]:
        return _PROFILES[race].racial_traits

    def starting_city(
        self, *, race: BeastmanRace,
    ) -> str:
        return _PROFILES[race].starting_city_id

    def language(
        self, *, race: BeastmanRace,
    ) -> str:
        return _PROFILES[race].language_label

    def all_races(self) -> tuple[BeastmanRace, ...]:
        return tuple(BeastmanRace)


__all__ = [
    "BeastmanRace", "GenderConstraint",
    "RacialTrait", "Gender",
    "StatProfile", "BeastmanRaceProfile",
    "BeastmanPlayableRaces",
]
