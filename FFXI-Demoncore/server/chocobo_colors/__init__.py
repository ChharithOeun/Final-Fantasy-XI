"""Chocobo colors — per-color profile catalog.

10 chocobo colors, each with a stat block, an element affinity
(or NONE / RANDOM), a movement profile, signature abilities,
and gameplay flags. All chocobos can SKILLCHAIN, MAGIC_BURST,
and CAST_SUPPORT_MAGIC on other chocobos. When a chocobo dies it
turns into a FOMOR variant of itself; the RAINBOW exception
re-eggs as an R/EX rainbow egg instead.

Stat tier shorthand: LOW / MID / HIGH / HIGHEST / LOWEST.

Public surface
--------------
    ChocoboColor enum (10 entries)
    Element enum
    Tier enum
    MovementProfile dataclass
    Ability dataclass
    ChocoboColorProfile dataclass
    ChocoboColorRegistry
        .profile_for(color)
        .all_colors()
        .ability_ids(color)
        .can_breed(color)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ChocoboColor(str, enum.Enum):
    YELLOW = "yellow"
    BROWN = "brown"
    LIGHT_BLUE = "light_blue"
    BLUE = "blue"
    LIGHT_PURPLE = "light_purple"
    GREEN = "green"
    RED = "red"
    WHITE = "white"
    RAINBOW = "rainbow"
    GREY = "grey"


class Element(str, enum.Enum):
    NONE = "none"
    EARTH = "earth"
    WATER = "water"
    ICE = "ice"
    LIGHTNING = "lightning"
    WIND = "wind"
    FIRE = "fire"
    HOLY = "holy"
    DARK = "dark"
    RANDOM = "random"


class Tier(str, enum.Enum):
    LOWEST = "lowest"
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    HIGHEST = "highest"


@dataclasses.dataclass(frozen=True)
class MovementProfile:
    run_speed_tier: Tier
    can_swim: bool = False
    can_fly: bool = False
    can_dive: bool = False
    walks_on_lava: bool = False
    walks_on_water: bool = False
    skates_on_ice: bool = False
    double_jump: bool = False
    glide: bool = False
    jump_height_tier: Tier = Tier.MID
    fastest_in_terrain: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Ability:
    ability_id: str
    cooldown_seconds: int = 0
    description: str = ""


@dataclasses.dataclass(frozen=True)
class ChocoboColorProfile:
    color: ChocoboColor
    element: Element
    hp_tier: Tier
    mp_tier: Tier
    phys_def_tier: Tier
    mag_def_tier: Tier
    movement: MovementProfile
    abilities: tuple[Ability, ...]
    can_breed: bool = True
    notes: str = ""


_PROFILES: dict[ChocoboColor, ChocoboColorProfile] = {
    ChocoboColor.YELLOW: ChocoboColorProfile(
        color=ChocoboColor.YELLOW,
        element=Element.NONE,
        hp_tier=Tier.MID,
        mp_tier=Tier.LOWEST,
        phys_def_tier=Tier.MID,
        mag_def_tier=Tier.MID,
        movement=MovementProfile(
            run_speed_tier=Tier.HIGHEST,
            jump_height_tier=Tier.HIGHEST,
            fastest_in_terrain="any",
        ),
        abilities=(
            Ability(ability_id="reduced_elem_dmg",
                    description="Significantly reduced elemental damage."),
            Ability(ability_id="skillchain"),
        ),
        notes="All-terrain workhorse. Cannot swim or fly.",
    ),
    ChocoboColor.BROWN: ChocoboColorProfile(
        color=ChocoboColor.BROWN,
        element=Element.EARTH,
        hp_tier=Tier.HIGHEST,
        mp_tier=Tier.MID,
        phys_def_tier=Tier.HIGHEST,
        mag_def_tier=Tier.MID,
        movement=MovementProfile(
            run_speed_tier=Tier.LOWEST,
        ),
        abilities=(
            Ability(ability_id="earth_spells_full"),
            Ability(ability_id="dig_bonus",
                    description="High dig success/reward."),
            Ability(ability_id="aoe_stoneskin", cooldown_seconds=180),
            Ability(ability_id="skillchain"),
        ),
    ),
    ChocoboColor.LIGHT_BLUE: ChocoboColorProfile(
        color=ChocoboColor.LIGHT_BLUE,
        element=Element.WATER,
        hp_tier=Tier.MID,
        mp_tier=Tier.MID,
        phys_def_tier=Tier.LOW,
        mag_def_tier=Tier.MID,
        movement=MovementProfile(
            run_speed_tier=Tier.LOWEST,
            can_swim=True,
            can_dive=True,
            fastest_in_terrain="water",
        ),
        abilities=(
            Ability(ability_id="water_spells_full"),
            Ability(ability_id="hold_breath_10min",
                    description="Holds breath underwater for 10 min."),
            Ability(ability_id="debuff_resist"),
            Ability(ability_id="skillchain"),
        ),
    ),
    ChocoboColor.BLUE: ChocoboColorProfile(
        color=ChocoboColor.BLUE,
        element=Element.ICE,
        hp_tier=Tier.MID,
        mp_tier=Tier.HIGH,
        phys_def_tier=Tier.LOW,
        mag_def_tier=Tier.HIGH,
        movement=MovementProfile(
            run_speed_tier=Tier.MID,
            skates_on_ice=True,
            fastest_in_terrain="cold",
        ),
        abilities=(
            Ability(ability_id="ice_spells_full"),
            Ability(ability_id="status_immune"),
            Ability(ability_id="skate_double_speed"),
            Ability(ability_id="skillchain"),
        ),
    ),
    ChocoboColor.LIGHT_PURPLE: ChocoboColorProfile(
        color=ChocoboColor.LIGHT_PURPLE,
        element=Element.LIGHTNING,
        hp_tier=Tier.MID,
        mp_tier=Tier.HIGH,
        phys_def_tier=Tier.LOW,
        mag_def_tier=Tier.HIGH,
        movement=MovementProfile(
            run_speed_tier=Tier.MID,
            fastest_in_terrain="storm_or_cloud",
        ),
        abilities=(
            Ability(ability_id="lightning_spells_aoe_low_tier"),
            Ability(ability_id="flash_step_30y", cooldown_seconds=300),
            Ability(ability_id="skillchain"),
        ),
    ),
    ChocoboColor.GREEN: ChocoboColorProfile(
        color=ChocoboColor.GREEN,
        element=Element.WIND,
        hp_tier=Tier.LOW,
        mp_tier=Tier.LOW,
        phys_def_tier=Tier.MID,
        mag_def_tier=Tier.MID,
        movement=MovementProfile(
            run_speed_tier=Tier.HIGH,
        ),
        abilities=(
            Ability(ability_id="wind_spells_full"),
            Ability(ability_id="thf_lockpick_high"),
            Ability(ability_id="thf_mug_bully_steal"),
            Ability(ability_id="thf_sata"),
            Ability(ability_id="back_attack_huge_dmg"),
            Ability(ability_id="evasion_high"),
            Ability(ability_id="skillchain"),
        ),
        notes="Susceptible to debuffs/status.",
    ),
    ChocoboColor.RED: ChocoboColorProfile(
        color=ChocoboColor.RED,
        element=Element.FIRE,
        hp_tier=Tier.MID,
        mp_tier=Tier.HIGH,
        phys_def_tier=Tier.MID,
        mag_def_tier=Tier.MID,
        movement=MovementProfile(
            run_speed_tier=Tier.MID,
            walks_on_lava=True,
            fastest_in_terrain="hot",
        ),
        abilities=(
            Ability(ability_id="fire_spells_full"),
            Ability(ability_id="meteor_long_cast"),
            Ability(ability_id="cast_while_running"),
            Ability(ability_id="skillchain"),
        ),
    ),
    ChocoboColor.WHITE: ChocoboColorProfile(
        color=ChocoboColor.WHITE,
        element=Element.HOLY,
        hp_tier=Tier.LOW,
        mp_tier=Tier.HIGHEST,
        phys_def_tier=Tier.LOW,
        mag_def_tier=Tier.MID,
        movement=MovementProfile(
            run_speed_tier=Tier.LOW,
        ),
        abilities=(
            Ability(ability_id="white_magic_full"),
            Ability(ability_id="aoe_cure_heal"),
            Ability(ability_id="raise_iii"),
            Ability(ability_id="immune_sleep_silence"),
            Ability(ability_id="party_telecrystal_warp",
                    cooldown_seconds=600),
            Ability(ability_id="double_mb_vs_undead_fomor"),
            Ability(ability_id="skillchain"),
        ),
    ),
    ChocoboColor.RAINBOW: ChocoboColorProfile(
        color=ChocoboColor.RAINBOW,
        element=Element.RANDOM,
        hp_tier=Tier.HIGH,
        mp_tier=Tier.HIGH,
        phys_def_tier=Tier.HIGH,
        mag_def_tier=Tier.HIGH,
        movement=MovementProfile(
            run_speed_tier=Tier.LOWEST,
            walks_on_water=True,
            walks_on_lava=True,
        ),
        abilities=(
            Ability(ability_id="random_element_constant"),
            Ability(ability_id="berserk_constant"),
            Ability(ability_id="mounted_no_attack"),
            Ability(ability_id="mounted_random_help_or_harm"),
            Ability(ability_id="geo_bubbles_random"),
            Ability(ability_id="summon_avatars_unlimited"),
            Ability(ability_id="call_beasts_unlimited"),
            Ability(ability_id="activate_automatons_unlimited"),
            Ability(ability_id="solo_skillchain"),
            Ability(ability_id="double_magic_burst"),
        ),
        can_breed=False,
        notes="0.0001% egg roll OR Mog Bonanza 1st place. "
              "Weak to opposite of current random element. "
              "Dies into a rainbow R/EX egg, not a fomor.",
    ),
    ChocoboColor.GREY: ChocoboColorProfile(
        color=ChocoboColor.GREY,
        element=Element.DARK,
        hp_tier=Tier.MID,
        mp_tier=Tier.HIGH,
        phys_def_tier=Tier.MID,
        mag_def_tier=Tier.MID,
        movement=MovementProfile(
            run_speed_tier=Tier.HIGH,
            double_jump=True,
            glide=True,
        ),
        abilities=(
            Ability(ability_id="dark_magic_full"),
            Ability(ability_id="aoe_death_low_proc"),
            Ability(ability_id="drain_aspir"),
            Ability(ability_id="prefers_long_range"),
            Ability(ability_id="dot_caster"),
            Ability(ability_id="aoe_warp_ii_party",
                    cooldown_seconds=900),
            Ability(ability_id="skillchain"),
            Ability(ability_id="double_magic_burst"),
        ),
        notes="Cannot stand still on water/lava.",
    ),
}


@dataclasses.dataclass
class ChocoboColorRegistry:
    def profile_for(
        self, *, color: ChocoboColor,
    ) -> t.Optional[ChocoboColorProfile]:
        return _PROFILES.get(color)

    def all_colors(self) -> tuple[ChocoboColor, ...]:
        return tuple(_PROFILES.keys())

    def ability_ids(
        self, *, color: ChocoboColor,
    ) -> tuple[str, ...]:
        p = _PROFILES.get(color)
        if p is None:
            return ()
        return tuple(a.ability_id for a in p.abilities)

    def can_breed(self, *, color: ChocoboColor) -> bool:
        p = _PROFILES.get(color)
        if p is None:
            return False
        return p.can_breed

    def total_colors(self) -> int:
        return len(_PROFILES)


__all__ = [
    "ChocoboColor", "Element", "Tier",
    "MovementProfile", "Ability", "ChocoboColorProfile",
    "ChocoboColorRegistry",
]
