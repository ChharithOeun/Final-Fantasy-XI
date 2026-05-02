"""Abyssea — WotG-era endgame zone overhaul.

Core systems:

* FIVE Abyssea zones (La Theine, Konschtat, Tahrongi, Misareaux,
  Vunkerl). Each is a parallel "shadow Vana'diel" version of a
  retail outdoor zone.

* VISITANT STATUS — players enter with a timer (default 30 min).
  Time extensions drop from kills and Riftworn Pyxis chests.
  Timer expires -> kicked out, status drops, gear unequips.

* CRUOR — primary Abyssea currency. Drops from kills, scales
  with mob's level + the player's pearl tier. Spent at NPC
  Cruor Prospectors for Atmas / time / pop items / passes.

* ATMA — passive buffs equippable in 3 slots. Each atma is a
  Notorious-Monster-themed bundle of stat bonuses + special
  effects, only active inside Abyssea. NMs drop their atmas
  on kill (some at 100%, others at low rates).

* ATMACITE — Konschtat-and-later equivalent of Atmas, equipped
  in 3 separate slots, harvested from Empyrean Trial NM kills.

* POP NMs — most NMs require popping with a Riftworn key item
  traded at a designated ??? site. Pop items often drop from
  trash mobs in the same zone.

Public surface
--------------
    AbysseaZone enum (5 zones)
    Atma / Atmacite dataclasses
    PlayerVisitant state (timer, cruor, atmas equipped)
    add_visitant_time(seconds) / consume_visitant_time(seconds)
    equip_atma / unequip_atma
    cruor_for_kill(mob_level, pearl_tier) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# ---- Constants -----------------------------------------------------------
DEFAULT_VISITANT_SECONDS = 30 * 60        # 30 min
MAX_VISITANT_SECONDS = 60 * 60            # hard cap (1hr)
ATMA_SLOTS = 3
ATMACITE_SLOTS = 3
TIME_EXTENSION_SECONDS = 5 * 60           # +5 min per chest


class AbysseaZone(str, enum.Enum):
    LA_THEINE = "abyssea_la_theine"
    KONSCHTAT = "abyssea_konschtat"
    TAHRONGI = "abyssea_tahrongi"
    MISAREAUX = "abyssea_misareaux"
    VUNKERL = "abyssea_vunkerl"


class PearlTier(str, enum.Enum):
    """The Cruor amplification pearl Bayld vendors sell. Higher
    tier -> higher cruor multiplier per kill."""
    NONE = "none"
    BRONZE = "bronze"     # +10%
    SILVER = "silver"     # +25%
    GOLD = "gold"         # +50%


_PEARL_MULT: dict[PearlTier, float] = {
    PearlTier.NONE: 1.00,
    PearlTier.BRONZE: 1.10,
    PearlTier.SILVER: 1.25,
    PearlTier.GOLD: 1.50,
}


@dataclasses.dataclass(frozen=True)
class Atma:
    """A passive buff bundle, equippable inside Abyssea only."""
    atma_id: str
    label: str
    drop_source_nm: str
    stat_bonuses: tuple[tuple[str, int], ...]   # ("str", 25), ...
    special_effect: t.Optional[str] = None      # e.g. "regen_5",
                                                #      "haste_15"


@dataclasses.dataclass(frozen=True)
class Atmacite:
    """Empyrean-trial sourced equivalent of Atma, separate slots."""
    atmacite_id: str
    label: str
    drop_source: str
    stat_bonuses: tuple[tuple[str, int], ...]


# Sample atma catalog — modeled on canonical retail
ATMA_CATALOG: dict[str, Atma] = {
    "atma_apocalypse": Atma(
        "atma_apocalypse", "Atma of the Apocalypse",
        drop_source_nm="ironclad_severer",
        stat_bonuses=(("str", 30), ("vit", 20), ("attack", 30)),
        special_effect="last_stand_double_atk",
    ),
    "atma_savage": Atma(
        "atma_savage", "Atma of the Savage",
        drop_source_nm="briareus",
        stat_bonuses=(("str", 25), ("dex", 25), ("attack", 25)),
    ),
    "atma_ultimate": Atma(
        "atma_ultimate", "Atma of the Ultimate",
        drop_source_nm="atma_ultimate_nm",
        stat_bonuses=(("int", 30), ("mab", 30), ("mdef", 15)),
        special_effect="magic_burst_bonus",
    ),
    "atma_lone_wolf": Atma(
        "atma_lone_wolf", "Atma of the Lone Wolf",
        drop_source_nm="lone_wolf_nm",
        stat_bonuses=(("agi", 30), ("evasion", 30)),
        special_effect="critical_hit_rate_15",
    ),
    "atma_sanguine_scythe": Atma(
        "atma_sanguine_scythe", "Atma of the Sanguine Scythe",
        drop_source_nm="cirein_croin",
        stat_bonuses=(("attack", 30), ("acc", 20)),
        special_effect="drain_on_hit",
    ),
}


ATMACITE_CATALOG: dict[str, Atmacite] = {
    "atmacite_athletic": Atmacite(
        "atmacite_athletic", "Atmacite of the Athletic",
        drop_source="empyrean_trial_t1",
        stat_bonuses=(("str", 15), ("vit", 15)),
    ),
    "atmacite_keen_eye": Atmacite(
        "atmacite_keen_eye", "Atmacite of the Keen Eye",
        drop_source="empyrean_trial_t2",
        stat_bonuses=(("dex", 15), ("acc", 15)),
    ),
    "atmacite_sage": Atmacite(
        "atmacite_sage", "Atmacite of the Sage",
        drop_source="empyrean_trial_t2",
        stat_bonuses=(("int", 15), ("mab", 15)),
    ),
    "atmacite_steadfast": Atmacite(
        "atmacite_steadfast", "Atmacite of the Steadfast",
        drop_source="empyrean_trial_t3",
        stat_bonuses=(("vit", 25), ("def", 25)),
    ),
}


def cruor_for_kill(*, mob_level: int, pearl_tier: PearlTier
                    = PearlTier.NONE) -> int:
    """Cruor awarded for a kill. Scales linearly with mob level
    times pearl multiplier."""
    if mob_level <= 0:
        return 0
    base = 50 + 8 * mob_level
    return int(base * _PEARL_MULT[pearl_tier])


@dataclasses.dataclass(frozen=True)
class TimeChange:
    accepted: bool
    new_seconds_remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class AtmaChange:
    accepted: bool
    slot: int = 0
    atma_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerVisitant:
    """Per-player Abyssea state. None of this is preserved when
    the player exits the zone."""
    player_id: str
    zone: t.Optional[AbysseaZone] = None
    seconds_remaining: int = 0
    cruor: int = 0
    atmas_equipped: list[t.Optional[str]] = dataclasses.field(
        default_factory=lambda: [None, None, None],
    )
    atmacites_equipped: list[t.Optional[str]] = dataclasses.field(
        default_factory=lambda: [None, None, None],
    )

    @property
    def in_abyssea(self) -> bool:
        return self.zone is not None and self.seconds_remaining > 0

    def enter(
        self, *, zone: AbysseaZone,
        seconds: int = DEFAULT_VISITANT_SECONDS,
    ) -> bool:
        if self.in_abyssea:
            return False
        self.zone = zone
        self.seconds_remaining = max(1, min(seconds, MAX_VISITANT_SECONDS))
        return True

    def exit(self) -> bool:
        if not self.in_abyssea:
            return False
        self.zone = None
        self.seconds_remaining = 0
        # Atmas don't unequip — they're saved for next entry —
        # but they do nothing outside Abyssea.
        return True

    def add_visitant_time(self, *, seconds: int) -> TimeChange:
        if not self.in_abyssea:
            return TimeChange(False, reason="not in Abyssea")
        if seconds <= 0:
            return TimeChange(
                False,
                new_seconds_remaining=self.seconds_remaining,
                reason="seconds must be > 0",
            )
        self.seconds_remaining = min(
            MAX_VISITANT_SECONDS,
            self.seconds_remaining + seconds,
        )
        return TimeChange(
            True, new_seconds_remaining=self.seconds_remaining,
        )

    def consume_visitant_time(self, *, seconds: int) -> TimeChange:
        if not self.in_abyssea:
            return TimeChange(False, reason="not in Abyssea")
        self.seconds_remaining = max(0, self.seconds_remaining - seconds)
        if self.seconds_remaining == 0:
            self.zone = None
            return TimeChange(
                True, new_seconds_remaining=0,
                reason="visitant status expired",
            )
        return TimeChange(
            True, new_seconds_remaining=self.seconds_remaining,
        )

    def grant_cruor(self, *, amount: int) -> bool:
        if amount <= 0:
            return False
        self.cruor += amount
        return True

    def spend_cruor(self, *, amount: int) -> bool:
        if amount <= 0 or self.cruor < amount:
            return False
        self.cruor -= amount
        return True

    def equip_atma(self, *, slot: int, atma_id: str) -> AtmaChange:
        if slot < 0 or slot >= ATMA_SLOTS:
            return AtmaChange(False, reason="slot OOR")
        if atma_id not in ATMA_CATALOG:
            return AtmaChange(False, reason="unknown atma")
        # Refuse double-equip of same atma in different slot
        if atma_id in [a for a in self.atmas_equipped if a is not None
                        and self.atmas_equipped.index(a) != slot]:
            return AtmaChange(False, reason="atma already equipped")
        self.atmas_equipped[slot] = atma_id
        return AtmaChange(True, slot=slot, atma_id=atma_id)

    def unequip_atma(self, *, slot: int) -> AtmaChange:
        if slot < 0 or slot >= ATMA_SLOTS:
            return AtmaChange(False, reason="slot OOR")
        prev = self.atmas_equipped[slot]
        self.atmas_equipped[slot] = None
        return AtmaChange(True, slot=slot, atma_id=prev)

    def aggregate_atma_stats(self) -> dict[str, int]:
        """Sum of stat bonuses from currently equipped atmas. Only
        active while in Abyssea."""
        if not self.in_abyssea:
            return {}
        out: dict[str, int] = {}
        for atma_id in self.atmas_equipped:
            if atma_id is None:
                continue
            atma = ATMA_CATALOG.get(atma_id)
            if atma is None:
                continue
            for stat, val in atma.stat_bonuses:
                out[stat] = out.get(stat, 0) + val
        return out


__all__ = [
    "DEFAULT_VISITANT_SECONDS", "MAX_VISITANT_SECONDS",
    "ATMA_SLOTS", "ATMACITE_SLOTS", "TIME_EXTENSION_SECONDS",
    "AbysseaZone", "PearlTier",
    "Atma", "Atmacite",
    "ATMA_CATALOG", "ATMACITE_CATALOG",
    "TimeChange", "AtmaChange",
    "cruor_for_kill", "PlayerVisitant",
]
