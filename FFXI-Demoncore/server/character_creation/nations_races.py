"""Nations + races — the foundational picks per CHARACTER_CREATION.md."""
from __future__ import annotations

import dataclasses
import enum


class Nation(str, enum.Enum):
    BASTOK = "bastok"
    SAN_DORIA = "san_doria"
    WINDURST = "windurst"
    WHITEGATE = "whitegate"


class Race(str, enum.Enum):
    HUME = "hume"
    ELVAAN = "elvaan"
    TARUTARU = "tarutaru"
    MITHRA = "mithra"
    GALKA = "galka"


@dataclasses.dataclass(frozen=True)
class NationProfile:
    nation: Nation
    label: str
    starting_zone: str
    opening_cinematic: str
    default_voice_tone: str
    signature_attire: str
    veteran_only: bool = False


NATIONS: dict[Nation, NationProfile] = {
    Nation.BASTOK: NationProfile(
        nation=Nation.BASTOK, label="Bastok",
        starting_zone="bastok_mines",
        opening_cinematic="bastok_forge_dawn",
        default_voice_tone="gruff_pragmatic",
        signature_attire="bronze_smith",
    ),
    Nation.SAN_DORIA: NationProfile(
        nation=Nation.SAN_DORIA, label="San d'Oria",
        starting_zone="south_sandoria",
        opening_cinematic="san_doria_cathedral_bell",
        default_voice_tone="formal_proud",
        signature_attire="initiate_knight",
    ),
    Nation.WINDURST: NationProfile(
        nation=Nation.WINDURST, label="Windurst",
        starting_zone="windurst_woods",
        opening_cinematic="windurst_chimes_dawn",
        default_voice_tone="curious_lyrical",
        signature_attire="apprentice_robes",
    ),
    Nation.WHITEGATE: NationProfile(
        nation=Nation.WHITEGATE, label="Aht Urhgan Whitegate",
        starting_zone="aht_urhgan_whitegate",
        opening_cinematic="whitegate_market_call",
        default_voice_tone="cosmopolitan",
        signature_attire="mercenary_wraps",
        veteran_only=True,
    ),
}


@dataclasses.dataclass(frozen=True)
class RaceProfile:
    race: Race
    label: str
    proportions: str           # 'short' / 'medium' / 'tall' / 'broad'
    fur_or_groom: bool         # KawaiiPhysics + UE5 Groom
    has_tail: bool             # Galka: False post-redesign
    notes: str = ""


RACES: dict[Race, RaceProfile] = {
    Race.HUME: RaceProfile(
        race=Race.HUME, label="Hume", proportions="medium",
        fur_or_groom=False, has_tail=False,
        notes="Demoncore: improved face topology + better hair shaders",
    ),
    Race.ELVAAN: RaceProfile(
        race=Race.ELVAAN, label="Elvaan", proportions="tall",
        fur_or_groom=False, has_tail=False,
        notes="Demoncore: eye + ear meshes redone for closer camera",
    ),
    Race.TARUTARU: RaceProfile(
        race=Race.TARUTARU, label="Tarutaru", proportions="short",
        fur_or_groom=False, has_tail=False,
        notes="Demoncore: chibi style preserved; shaders modernized",
    ),
    Race.MITHRA: RaceProfile(
        race=Race.MITHRA, label="Mithra", proportions="medium",
        fur_or_groom=True, has_tail=True,
        notes="Demoncore: UE5 Groom fur + KawaiiPhysics ears + tail",
    ),
    Race.GALKA: RaceProfile(
        race=Race.GALKA, label="Galka", proportions="broad",
        fur_or_groom=True, has_tail=False,           # tail removed
        notes=("Demoncore: TAIL REMOVED at extract step (user request); "
                  "broader shoulders + bigger silhouette"),
    ),
}


# Per-nation 'one line of opening dialogue' for the voice preview.
NATION_OPENING_LINES: dict[Nation, str] = {
    Nation.BASTOK: "...alright, let's see what's out there.",
    Nation.SAN_DORIA: "Today is mine.",
    Nation.WINDURST: "Look at that — the chimes already.",
    Nation.WHITEGATE: "The bazaar awaits.",
}


def opening_line_for(nation: Nation) -> str:
    return NATION_OPENING_LINES[nation]


def nation_unlocked_for(nation: Nation, *, is_veteran: bool) -> bool:
    """Whitegate is veteran-account-only; everything else is open."""
    profile = NATIONS[nation]
    if profile.veteran_only and not is_veteran:
        return False
    return True


def galka_tail_removed() -> bool:
    """Doc-canonical assertion: galka tail is not rendered."""
    return RACES[Race.GALKA].has_tail is False
