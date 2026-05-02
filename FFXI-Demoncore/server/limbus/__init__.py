"""Limbus — CoP-era Omega/Ultima endgame instance.

Players spend Cosmo-Cleanse (currency) to enter Apollyon /
Temenos chambers. Each chamber tier is a 30-minute timed run
against beastmen-themed encounters, culminating in the
boss tier (Omega in Apollyon, Ultima in Temenos).

Drops:
* Time Extensions (small chance, extends remaining timer)
* Ancient Beastcoins (currency for AF+1 upgrades)
* Boss-specific weapons (Homam, Nashira, Goliard, Pahluwan)

Composes on top of instance_engine for the timed-instance
lifecycle. This module owns the chambers + currency.

Public surface
--------------
    LimbusChamber enum
    LimbusEntry dataclass
    LIMBUS_CATALOG
    cosmo_cleanse_cost(chamber) -> int
    drop_pool(chamber) -> tuple[str, ...]
    is_boss_chamber(chamber) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


COSMO_CLEANSE_BASE_COST = 1
TIME_EXTENSION_SECONDS = 5 * 60     # +5 min per drop


class LimbusWing(str, enum.Enum):
    APOLLYON = "apollyon"      # Omega's wing
    TEMENOS = "temenos"        # Ultima's wing


class LimbusChamber(str, enum.Enum):
    # Apollyon (5 chambers + boss)
    APOLLYON_NW = "apollyon_nw"
    APOLLYON_NE = "apollyon_ne"
    APOLLYON_SW = "apollyon_sw"
    APOLLYON_SE = "apollyon_se"
    APOLLYON_CS = "apollyon_central"
    OMEGA = "omega_chamber"
    # Temenos (4 chambers + boss)
    TEMENOS_N = "temenos_north"
    TEMENOS_E = "temenos_east"
    TEMENOS_W = "temenos_west"
    ULTIMA = "ultima_chamber"


@dataclasses.dataclass(frozen=True)
class LimbusEntry:
    chamber: LimbusChamber
    wing: LimbusWing
    label: str
    is_boss_chamber: bool
    cosmo_cleanse_cost: int
    timer_seconds: int
    party_size_min: int
    party_size_max: int
    drop_pool: tuple[str, ...]


# Sample drop pools — modeled on canonical Limbus
_HOMAM_PIECES = (
    "homam_zucchetto", "homam_corazza", "homam_manopolas",
    "homam_cosciales", "homam_gambieras",
)
_NASHIRA_PIECES = (
    "nashira_turban", "nashira_manteel", "nashira_gages",
    "nashira_seraweels", "nashira_crackows",
)
_GOLIARD_PIECES = (
    "goliard_chapeau", "goliard_saio", "goliard_cuffs",
    "goliard_trews", "goliard_clogs",
)
_PAHLUWAN_PIECES = (
    "pahluwan_qalansuwa", "pahluwan_khazagand", "pahluwan_dastanas",
    "pahluwan_seraweels", "pahluwan_crackows",
)


_TIME_EXT = ("ancient_beastcoin", "time_extension_5min",
              "ancient_beastcoin", "ancient_beastcoin")


LIMBUS_CATALOG: tuple[LimbusEntry, ...] = (
    # Apollyon side
    LimbusEntry(
        LimbusChamber.APOLLYON_NW, LimbusWing.APOLLYON,
        "Apollyon NW (Beastmen Wave)", False,
        cosmo_cleanse_cost=1, timer_seconds=30 * 60,
        party_size_min=3, party_size_max=18,
        drop_pool=_TIME_EXT + _HOMAM_PIECES[:2],
    ),
    LimbusEntry(
        LimbusChamber.APOLLYON_NE, LimbusWing.APOLLYON,
        "Apollyon NE (Demonic Pages)", False,
        cosmo_cleanse_cost=1, timer_seconds=30 * 60,
        party_size_min=3, party_size_max=18,
        drop_pool=_TIME_EXT + _NASHIRA_PIECES[:2],
    ),
    LimbusEntry(
        LimbusChamber.APOLLYON_SW, LimbusWing.APOLLYON,
        "Apollyon SW (Bomb Detonators)", False,
        cosmo_cleanse_cost=1, timer_seconds=30 * 60,
        party_size_min=3, party_size_max=18,
        drop_pool=_TIME_EXT + _GOLIARD_PIECES[:2],
    ),
    LimbusEntry(
        LimbusChamber.APOLLYON_SE, LimbusWing.APOLLYON,
        "Apollyon SE (Skeleton Horde)", False,
        cosmo_cleanse_cost=1, timer_seconds=30 * 60,
        party_size_min=3, party_size_max=18,
        drop_pool=_TIME_EXT + _PAHLUWAN_PIECES[:2],
    ),
    LimbusEntry(
        LimbusChamber.APOLLYON_CS, LimbusWing.APOLLYON,
        "Apollyon Central Shaft (Convergence)", False,
        cosmo_cleanse_cost=2, timer_seconds=30 * 60,
        party_size_min=6, party_size_max=18,
        drop_pool=_TIME_EXT + _HOMAM_PIECES[2:] + _NASHIRA_PIECES[2:],
    ),
    LimbusEntry(
        LimbusChamber.OMEGA, LimbusWing.APOLLYON,
        "Omega Chamber (boss)", True,
        cosmo_cleanse_cost=3, timer_seconds=30 * 60,
        party_size_min=6, party_size_max=18,
        drop_pool=_HOMAM_PIECES + _NASHIRA_PIECES + (
            "homam_zenith_helm", "nashira_seraweels_plus",
        ),
    ),
    # Temenos side
    LimbusEntry(
        LimbusChamber.TEMENOS_N, LimbusWing.TEMENOS,
        "Temenos North", False,
        cosmo_cleanse_cost=1, timer_seconds=30 * 60,
        party_size_min=3, party_size_max=18,
        drop_pool=_TIME_EXT + _GOLIARD_PIECES[2:],
    ),
    LimbusEntry(
        LimbusChamber.TEMENOS_E, LimbusWing.TEMENOS,
        "Temenos East", False,
        cosmo_cleanse_cost=1, timer_seconds=30 * 60,
        party_size_min=3, party_size_max=18,
        drop_pool=_TIME_EXT + _PAHLUWAN_PIECES[2:],
    ),
    LimbusEntry(
        LimbusChamber.TEMENOS_W, LimbusWing.TEMENOS,
        "Temenos West", False,
        cosmo_cleanse_cost=1, timer_seconds=30 * 60,
        party_size_min=3, party_size_max=18,
        drop_pool=_TIME_EXT + _NASHIRA_PIECES[2:],
    ),
    LimbusEntry(
        LimbusChamber.ULTIMA, LimbusWing.TEMENOS,
        "Ultima Chamber (boss)", True,
        cosmo_cleanse_cost=3, timer_seconds=30 * 60,
        party_size_min=6, party_size_max=18,
        drop_pool=_GOLIARD_PIECES + _PAHLUWAN_PIECES + (
            "goliard_chapeau_plus", "pahluwan_qalansuwa_plus",
        ),
    ),
)


CHAMBER_BY_ID: dict[LimbusChamber, LimbusEntry] = {
    e.chamber: e for e in LIMBUS_CATALOG
}


def cosmo_cleanse_cost(chamber: LimbusChamber) -> int:
    e = CHAMBER_BY_ID.get(chamber)
    return e.cosmo_cleanse_cost if e else 0


def drop_pool(chamber: LimbusChamber) -> tuple[str, ...]:
    e = CHAMBER_BY_ID.get(chamber)
    return e.drop_pool if e else ()


def is_boss_chamber(chamber: LimbusChamber) -> bool:
    e = CHAMBER_BY_ID.get(chamber)
    return e.is_boss_chamber if e else False


def chambers_in_wing(wing: LimbusWing) -> tuple[LimbusChamber, ...]:
    return tuple(e.chamber for e in LIMBUS_CATALOG if e.wing == wing)


@dataclasses.dataclass
class PlayerLimbusBalance:
    player_id: str
    cosmo_cleanse: int = 0
    ancient_beastcoins: int = 0

    def can_afford(self, *, chamber: LimbusChamber) -> bool:
        return self.cosmo_cleanse >= cosmo_cleanse_cost(chamber)

    def spend(self, *, chamber: LimbusChamber) -> bool:
        cost = cosmo_cleanse_cost(chamber)
        if self.cosmo_cleanse < cost:
            return False
        self.cosmo_cleanse -= cost
        return True

    def grant_cosmo(self, *, amount: int) -> bool:
        if amount <= 0:
            return False
        self.cosmo_cleanse += amount
        return True


__all__ = [
    "COSMO_CLEANSE_BASE_COST", "TIME_EXTENSION_SECONDS",
    "LimbusWing", "LimbusChamber", "LimbusEntry",
    "LIMBUS_CATALOG", "CHAMBER_BY_ID",
    "cosmo_cleanse_cost", "drop_pool", "is_boss_chamber",
    "chambers_in_wing",
    "PlayerLimbusBalance",
]
