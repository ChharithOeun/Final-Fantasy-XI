"""Underwater races — 5 NPC/world-only races for the deep cities.

These races are *not* player-creatable; they exist purely as world
inhabitants and lore. Player avatars stay in the hume/beastman
roster; this module describes who lives in the underwater cities
and how their gender/subtype rules read.

Demoncore's underwater expansion adds five sea-dwelling races with
distinct gender constraints, subtypes, and combat profiles:

  MERMAID            - female-only; siren matriarchy
  JELLYFISH          - genderless; gel-body morphology
  SHARK_HUMANOID     - male-only with a random SharkSubtype
                       (great_white / hammerhead / bull / tiger /
                        mako / nurse). Each subtype has a small
                        flavour modifier (bite / armor / speed)
  OCTOPI_SQUID       - either; Octopus or Squid morphology
  FOMOR_UNDERWATER   - undead echoes; spawn on hume/beastman drowning

Each race has a HOME_CITY (the underwater city analogue) and a
SWIM_PROFILE (HOLD_BREATH minutes + TRUE_AQUATIC flag — true
aquatics never run out of breath).

Public surface
--------------
    UnderwaterRace enum
    Gender enum         FEMALE_ONLY / MALE_ONLY / EITHER /
                        GENDERLESS
    SharkSubtype enum
    OctoSquidShape enum
    SwimProfile dataclass
    UnderwaterRaceProfile dataclass
    UnderwaterRaceRegistry
        .profile_for(race)
        .pick_shark_subtype(seed_pct)
        .validate_character(race, gender)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class UnderwaterRace(str, enum.Enum):
    MERMAID = "mermaid"
    JELLYFISH = "jellyfish"
    SHARK_HUMANOID = "shark_humanoid"
    OCTOPI_SQUID = "octopi_squid"
    FOMOR_UNDERWATER = "fomor_underwater"


class Gender(str, enum.Enum):
    FEMALE_ONLY = "female_only"
    MALE_ONLY = "male_only"
    EITHER = "either"
    GENDERLESS = "genderless"


class SharkSubtype(str, enum.Enum):
    GREAT_WHITE = "great_white"
    HAMMERHEAD = "hammerhead"
    BULL = "bull"
    TIGER = "tiger"
    MAKO = "mako"
    NURSE = "nurse"


class OctoSquidShape(str, enum.Enum):
    OCTOPUS = "octopus"
    SQUID = "squid"


@dataclasses.dataclass(frozen=True)
class SwimProfile:
    hold_breath_minutes: int
    true_aquatic: bool


@dataclasses.dataclass(frozen=True)
class UnderwaterRaceProfile:
    race: UnderwaterRace
    gender_rule: Gender
    home_city: str
    swim: SwimProfile
    description: str
    is_player_playable: bool = False


_PROFILES: dict[UnderwaterRace, UnderwaterRaceProfile] = {
    UnderwaterRace.MERMAID: UnderwaterRaceProfile(
        race=UnderwaterRace.MERMAID,
        gender_rule=Gender.FEMALE_ONLY,
        home_city="silmaril_sirenhall",
        swim=SwimProfile(hold_breath_minutes=999, true_aquatic=True),
        description="Female-only siren matriarchy.",
    ),
    UnderwaterRace.JELLYFISH: UnderwaterRaceProfile(
        race=UnderwaterRace.JELLYFISH,
        gender_rule=Gender.GENDERLESS,
        home_city="luminous_drift",
        swim=SwimProfile(hold_breath_minutes=999, true_aquatic=True),
        description="Gel-bodied luminous drifters.",
    ),
    UnderwaterRace.SHARK_HUMANOID: UnderwaterRaceProfile(
        race=UnderwaterRace.SHARK_HUMANOID,
        gender_rule=Gender.MALE_ONLY,
        home_city="reef_spire",
        swim=SwimProfile(hold_breath_minutes=999, true_aquatic=True),
        description="Male-only humanoid sharks; subtype rolled at "
                    "character creation.",
    ),
    UnderwaterRace.OCTOPI_SQUID: UnderwaterRaceProfile(
        race=UnderwaterRace.OCTOPI_SQUID,
        gender_rule=Gender.EITHER,
        home_city="coral_caverns",
        swim=SwimProfile(hold_breath_minutes=999, true_aquatic=True),
        description="Cephalopod humanoids — Octopus or Squid shape.",
    ),
    UnderwaterRace.FOMOR_UNDERWATER: UnderwaterRaceProfile(
        race=UnderwaterRace.FOMOR_UNDERWATER,
        gender_rule=Gender.GENDERLESS,
        home_city="drowned_void",
        swim=SwimProfile(hold_breath_minutes=999, true_aquatic=True),
        description="Echo-form undead from drowned humes/beastmen.",
    ),
}


# Shark subtype roll uses cumulative thresholds so that
# pick_shark_subtype is deterministic given a seed_pct.
_SHARK_ROLL: list[tuple[int, SharkSubtype]] = [
    (15, SharkSubtype.GREAT_WHITE),
    (35, SharkSubtype.HAMMERHEAD),
    (50, SharkSubtype.BULL),
    (70, SharkSubtype.TIGER),
    (90, SharkSubtype.MAKO),
    (100, SharkSubtype.NURSE),
]


@dataclasses.dataclass(frozen=True)
class ValidateResult:
    accepted: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass
class UnderwaterRaceRegistry:
    def profile_for(
        self, *, race: UnderwaterRace,
    ) -> t.Optional[UnderwaterRaceProfile]:
        return _PROFILES.get(race)

    def pick_shark_subtype(
        self, *, seed_pct: int,
    ) -> t.Optional[SharkSubtype]:
        if not (0 <= seed_pct <= 100):
            return None
        for ceil, sub in _SHARK_ROLL:
            if seed_pct < ceil:
                return sub
        return _SHARK_ROLL[-1][1]

    def validate_character(
        self, *, race: UnderwaterRace,
        gender: t.Optional[str],
    ) -> ValidateResult:
        """Reject ALL player-creation attempts — underwater races are
        NPC/world only. Kept on the surface so character-creator UI
        gets a consistent, explanatory rejection."""
        prof = _PROFILES.get(race)
        if prof is None:
            return ValidateResult(False, reason="unknown race")
        if not prof.is_player_playable:
            return ValidateResult(
                False, reason="race is NPC/world only",
            )
        # If a future race ever flips is_player_playable=True, fall
        # through to the canonical gender-rule check.
        rule = prof.gender_rule
        if rule == Gender.FEMALE_ONLY and gender != "female":
            return ValidateResult(
                False, reason="race is female-only",
            )
        if rule == Gender.MALE_ONLY and gender != "male":
            return ValidateResult(
                False, reason="race is male-only",
            )
        if rule == Gender.EITHER and gender not in ("male", "female"):
            return ValidateResult(
                False, reason="must specify male or female",
            )
        return ValidateResult(accepted=True)

    def validate_npc(
        self, *, race: UnderwaterRace,
        gender: t.Optional[str],
    ) -> ValidateResult:
        """NPC-spawn validator — applies the gender rule but ignores
        the is_player_playable lockout (used by the world spawner
        to seed underwater cities and overworld encounters)."""
        prof = _PROFILES.get(race)
        if prof is None:
            return ValidateResult(False, reason="unknown race")
        rule = prof.gender_rule
        if rule == Gender.FEMALE_ONLY and gender != "female":
            return ValidateResult(
                False, reason="race is female-only",
            )
        if rule == Gender.MALE_ONLY and gender != "male":
            return ValidateResult(
                False, reason="race is male-only",
            )
        if rule == Gender.EITHER and gender not in ("male", "female"):
            return ValidateResult(
                False, reason="must specify male or female",
            )
        return ValidateResult(accepted=True)

    def is_player_playable(
        self, *, race: UnderwaterRace,
    ) -> bool:
        prof = _PROFILES.get(race)
        if prof is None:
            return False
        return prof.is_player_playable

    def total_races(self) -> int:
        return len(_PROFILES)


__all__ = [
    "UnderwaterRace", "Gender",
    "SharkSubtype", "OctoSquidShape",
    "SwimProfile", "UnderwaterRaceProfile",
    "ValidateResult",
    "UnderwaterRaceRegistry",
]
