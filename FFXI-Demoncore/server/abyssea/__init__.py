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


# =====================================================================
# Chaos Zone — Demoncore Abyssea revival
# =====================================================================
#
# Canonical Abyssea is dead content; players skip it on the way to
# Adoulin. To revive it, each Abyssea zone gets a "Chaos Zone" — a
# high-density quadrant with:
#
#   * 3-4x the normal mob density
#   * Mobs 5-10 levels above the zone's outer ring
#   * Drop pool keyed to zone-specific NEW DROPS used by quests
#   * Quests that ONLY accept Chaos Zone drops, with rich rewards
#     (Cruor, atma keys, Riftworn Pyxis vouchers, gear scraps)
#
# Goals: make Abyssea a real grind destination again. Get players
# back into the WotG content for ML 100-150 prep.
#
# Public surface
# --------------
#     ChaosZoneSpec / CHAOS_ZONE_SPECS
#     ChaosDrop / CHAOS_DROP_CATALOG
#     ChaosQuest / CHAOS_QUEST_CATALOG
#     PlayerChaosProgress (per-zone drop wallet + quest tracker)


@dataclasses.dataclass(frozen=True)
class ChaosZoneSpec:
    zone: AbysseaZone
    quadrant_label: str        # which corner of the map
    mob_density_multiplier: int    # vs vanilla zone (3 = 3x)
    mob_level_floor: int           # zone outer ring + N
    mob_level_ceiling: int


CHAOS_ZONE_SPECS: dict[AbysseaZone, ChaosZoneSpec] = {
    AbysseaZone.LA_THEINE: ChaosZoneSpec(
        AbysseaZone.LA_THEINE, "northwest cliff",
        mob_density_multiplier=3, mob_level_floor=82,
        mob_level_ceiling=87,
    ),
    AbysseaZone.KONSCHTAT: ChaosZoneSpec(
        AbysseaZone.KONSCHTAT, "shattered north pass",
        mob_density_multiplier=4, mob_level_floor=85,
        mob_level_ceiling=90,
    ),
    AbysseaZone.TAHRONGI: ChaosZoneSpec(
        AbysseaZone.TAHRONGI, "ridge of faded oaths",
        mob_density_multiplier=3, mob_level_floor=88,
        mob_level_ceiling=93,
    ),
    AbysseaZone.MISAREAUX: ChaosZoneSpec(
        AbysseaZone.MISAREAUX, "drowned cathedral basin",
        mob_density_multiplier=4, mob_level_floor=92,
        mob_level_ceiling=98,
    ),
    AbysseaZone.VUNKERL: ChaosZoneSpec(
        AbysseaZone.VUNKERL, "spire of the godless",
        mob_density_multiplier=4, mob_level_floor=95,
        mob_level_ceiling=99,
    ),
}


@dataclasses.dataclass(frozen=True)
class ChaosDrop:
    drop_id: str
    label: str
    zone: AbysseaZone
    drop_rate_pct: int


# Per-zone drops the Chaos Zone introduces. Only the Chaos quadrant
# spawns mobs that drop these.
CHAOS_DROP_CATALOG: dict[AbysseaZone, tuple[ChaosDrop, ...]] = {
    AbysseaZone.LA_THEINE: (
        ChaosDrop("clouded_la_theine_eye",
                   "Clouded La Theine Eye",
                   AbysseaZone.LA_THEINE, 8),
        ChaosDrop("shattered_oath_fragment",
                   "Shattered Oath Fragment",
                   AbysseaZone.LA_THEINE, 4),
    ),
    AbysseaZone.KONSCHTAT: (
        ChaosDrop("scorched_konschtat_horn",
                   "Scorched Konschtat Horn",
                   AbysseaZone.KONSCHTAT, 7),
        ChaosDrop("northern_pass_seal",
                   "Northern Pass Seal",
                   AbysseaZone.KONSCHTAT, 3),
    ),
    AbysseaZone.TAHRONGI: (
        ChaosDrop("oath_dust_tahrongi",
                   "Oath Dust of Tahrongi",
                   AbysseaZone.TAHRONGI, 7),
        ChaosDrop("ridge_keyleaf",
                   "Ridge Keyleaf",
                   AbysseaZone.TAHRONGI, 3),
    ),
    AbysseaZone.MISAREAUX: (
        ChaosDrop("drowned_choral_marker",
                   "Drowned Choral Marker",
                   AbysseaZone.MISAREAUX, 6),
        ChaosDrop("cathedral_locket",
                   "Cathedral Locket",
                   AbysseaZone.MISAREAUX, 2),
    ),
    AbysseaZone.VUNKERL: (
        ChaosDrop("godless_spire_shard",
                   "Godless Spire Shard",
                   AbysseaZone.VUNKERL, 5),
        ChaosDrop("vunkerl_eternal_quill",
                   "Vunkerl Eternal Quill",
                   AbysseaZone.VUNKERL, 2),
    ),
}


@dataclasses.dataclass(frozen=True)
class ChaosQuestReward:
    cruor: int = 0
    riftworn_pyxis_voucher: int = 0
    atma_key: t.Optional[str] = None
    title_unlock: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ChaosQuest:
    quest_id: str
    zone: AbysseaZone
    label: str
    required_drops: tuple[tuple[str, int], ...]
    reward: ChaosQuestReward


# Each zone gets 2 sample chaos quests demonstrating the structure.
# Real content batch will fill out the long tail.
CHAOS_QUEST_CATALOG: dict[AbysseaZone, tuple[ChaosQuest, ...]] = {
    AbysseaZone.LA_THEINE: (
        ChaosQuest(
            "la_theine_clouded_offering", AbysseaZone.LA_THEINE,
            "Clouded Offering",
            required_drops=(("clouded_la_theine_eye", 5),),
            reward=ChaosQuestReward(cruor=10000,
                                     riftworn_pyxis_voucher=2),
        ),
        ChaosQuest(
            "la_theine_oath_keeper", AbysseaZone.LA_THEINE,
            "Oath Keeper",
            required_drops=(("shattered_oath_fragment", 3),),
            reward=ChaosQuestReward(cruor=20000,
                                     atma_key="atma_savage",
                                     title_unlock="Oath Keeper"),
        ),
    ),
    AbysseaZone.KONSCHTAT: (
        ChaosQuest(
            "konschtat_horn_call", AbysseaZone.KONSCHTAT,
            "Horn Call of Konschtat",
            required_drops=(("scorched_konschtat_horn", 5),),
            reward=ChaosQuestReward(cruor=12000,
                                     riftworn_pyxis_voucher=2),
        ),
        ChaosQuest(
            "konschtat_pass_seal", AbysseaZone.KONSCHTAT,
            "The Sealed Pass",
            required_drops=(("northern_pass_seal", 3),),
            reward=ChaosQuestReward(cruor=25000,
                                     atma_key="atma_apocalypse"),
        ),
    ),
    AbysseaZone.TAHRONGI: (
        ChaosQuest(
            "tahrongi_dust_collector", AbysseaZone.TAHRONGI,
            "Dust Collector",
            required_drops=(("oath_dust_tahrongi", 6),),
            reward=ChaosQuestReward(cruor=14000,
                                     riftworn_pyxis_voucher=2),
        ),
        ChaosQuest(
            "tahrongi_ridge_climber", AbysseaZone.TAHRONGI,
            "Ridge Climber",
            required_drops=(("ridge_keyleaf", 3),),
            reward=ChaosQuestReward(cruor=28000,
                                     atma_key="atma_lone_wolf"),
        ),
    ),
    AbysseaZone.MISAREAUX: (
        ChaosQuest(
            "misareaux_choral_finder", AbysseaZone.MISAREAUX,
            "Choral Finder",
            required_drops=(("drowned_choral_marker", 6),),
            reward=ChaosQuestReward(cruor=18000,
                                     riftworn_pyxis_voucher=3),
        ),
        ChaosQuest(
            "misareaux_locket_keeper", AbysseaZone.MISAREAUX,
            "The Locket Keeper",
            required_drops=(("cathedral_locket", 3),),
            reward=ChaosQuestReward(cruor=35000,
                                     atma_key="atma_ultimate"),
        ),
    ),
    AbysseaZone.VUNKERL: (
        ChaosQuest(
            "vunkerl_spire_offering", AbysseaZone.VUNKERL,
            "Spire Offering",
            required_drops=(("godless_spire_shard", 6),),
            reward=ChaosQuestReward(cruor=22000,
                                     riftworn_pyxis_voucher=4),
        ),
        ChaosQuest(
            "vunkerl_eternal_chronicle", AbysseaZone.VUNKERL,
            "The Eternal Chronicle",
            required_drops=(("vunkerl_eternal_quill", 3),),
            reward=ChaosQuestReward(cruor=40000,
                                     atma_key="atma_sanguine_scythe",
                                     title_unlock="Vana'diel Chronicler"),
        ),
    ),
}


def chaos_zone_spec(zone: AbysseaZone) -> t.Optional[ChaosZoneSpec]:
    return CHAOS_ZONE_SPECS.get(zone)


def chaos_drops_for(zone: AbysseaZone) -> tuple[ChaosDrop, ...]:
    return CHAOS_DROP_CATALOG.get(zone, ())


def chaos_quests_for(zone: AbysseaZone) -> tuple[ChaosQuest, ...]:
    return CHAOS_QUEST_CATALOG.get(zone, ())


@dataclasses.dataclass(frozen=True)
class ChaosTurnIn:
    accepted: bool
    quest_id: t.Optional[str] = None
    cruor_awarded: int = 0
    riftworn_vouchers_awarded: int = 0
    atma_key_awarded: t.Optional[str] = None
    title_unlocked: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerChaosProgress:
    """Per-player tracker for Chaos Zone drops + quest claims."""
    player_id: str
    chaos_drops: dict[str, int] = dataclasses.field(default_factory=dict)
    completed_quests: list[str] = dataclasses.field(default_factory=list)

    def add_drop(self, *, drop_id: str, quantity: int = 1) -> bool:
        if quantity <= 0:
            return False
        self.chaos_drops[drop_id] = (
            self.chaos_drops.get(drop_id, 0) + quantity
        )
        return True

    def turn_in_quest(self, *, quest: ChaosQuest) -> ChaosTurnIn:
        if quest.quest_id in self.completed_quests:
            return ChaosTurnIn(False, quest_id=quest.quest_id,
                                reason="already completed")
        for drop_id, qty in quest.required_drops:
            if self.chaos_drops.get(drop_id, 0) < qty:
                return ChaosTurnIn(False, quest_id=quest.quest_id,
                                    reason="missing drops")
        # Consume drops
        for drop_id, qty in quest.required_drops:
            self.chaos_drops[drop_id] -= qty
        self.completed_quests.append(quest.quest_id)
        r = quest.reward
        return ChaosTurnIn(
            accepted=True, quest_id=quest.quest_id,
            cruor_awarded=r.cruor,
            riftworn_vouchers_awarded=r.riftworn_pyxis_voucher,
            atma_key_awarded=r.atma_key,
            title_unlocked=r.title_unlock,
        )


__all__ = [
    "DEFAULT_VISITANT_SECONDS", "MAX_VISITANT_SECONDS",
    "ATMA_SLOTS", "ATMACITE_SLOTS", "TIME_EXTENSION_SECONDS",
    "AbysseaZone", "PearlTier",
    "Atma", "Atmacite",
    "ATMA_CATALOG", "ATMACITE_CATALOG",
    "TimeChange", "AtmaChange",
    "cruor_for_kill", "PlayerVisitant",
    # ---- Chaos Zone
    "ChaosZoneSpec", "ChaosDrop", "ChaosQuest", "ChaosQuestReward",
    "CHAOS_ZONE_SPECS", "CHAOS_DROP_CATALOG", "CHAOS_QUEST_CATALOG",
    "ChaosTurnIn", "PlayerChaosProgress",
    "chaos_zone_spec", "chaos_drops_for", "chaos_quests_for",
]
