"""Equipment stats — aggregate equipped item stats into character.

Each item carries a stat-bonus block + restrictions (min level,
race, job). Latents activate under conditions (HP < 33%, in town,
etc.). The equipped-set aggregator sums all visible bonuses.

Public surface
--------------
    EquipmentStatBlock dataclass (str/dex/.../accuracy/attack)
    LatentTrigger enum
    Equipment dataclass (item with restrictions)
    LoadOut per character
        .equip(slot, item)
        .unequip(slot)
        .total_stats(player_ctx)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LatentTrigger(str, enum.Enum):
    NONE = "none"
    HP_BELOW_33 = "hp_below_33"
    HP_BELOW_75 = "hp_below_75"
    MP_BELOW_50 = "mp_below_50"
    NIGHT_ONLY = "night_only"
    DAY_ONLY = "day_only"
    IN_TOWN = "in_town"


@dataclasses.dataclass(frozen=True)
class EquipmentStatBlock:
    str_: int = 0
    dex: int = 0
    vit: int = 0
    agi: int = 0
    int_: int = 0
    mnd: int = 0
    chr_: int = 0
    hp: int = 0
    mp: int = 0
    attack: int = 0
    accuracy: int = 0
    defense: int = 0
    evasion: int = 0
    magic_attack: int = 0
    magic_defense: int = 0
    haste: int = 0       # %
    refresh: int = 0     # MP/tick


def _add_blocks(
    a: EquipmentStatBlock, b: EquipmentStatBlock,
) -> EquipmentStatBlock:
    return EquipmentStatBlock(
        str_=a.str_ + b.str_,
        dex=a.dex + b.dex,
        vit=a.vit + b.vit,
        agi=a.agi + b.agi,
        int_=a.int_ + b.int_,
        mnd=a.mnd + b.mnd,
        chr_=a.chr_ + b.chr_,
        hp=a.hp + b.hp,
        mp=a.mp + b.mp,
        attack=a.attack + b.attack,
        accuracy=a.accuracy + b.accuracy,
        defense=a.defense + b.defense,
        evasion=a.evasion + b.evasion,
        magic_attack=a.magic_attack + b.magic_attack,
        magic_defense=a.magic_defense + b.magic_defense,
        haste=a.haste + b.haste,
        refresh=a.refresh + b.refresh,
    )


@dataclasses.dataclass(frozen=True)
class Equipment:
    item_id: str
    slot: str                                    # head/body/hands/etc
    base_stats: EquipmentStatBlock
    latent_stats: EquipmentStatBlock = EquipmentStatBlock()
    latent_trigger: LatentTrigger = LatentTrigger.NONE
    min_level: int = 1
    job_restriction: tuple[str, ...] = ()        # () = all jobs
    race_restriction: tuple[str, ...] = ()       # () = all races


@dataclasses.dataclass(frozen=True)
class PlayerContext:
    """Snapshot used to evaluate latents."""
    level: int = 1
    job: str = ""
    race: str = ""
    hp_percent: float = 100.0
    mp_percent: float = 100.0
    in_town: bool = False
    is_night: bool = False


def can_equip(
    *, equipment: Equipment, ctx: PlayerContext,
) -> bool:
    if ctx.level < equipment.min_level:
        return False
    if equipment.job_restriction and \
            ctx.job not in equipment.job_restriction:
        return False
    if equipment.race_restriction and \
            ctx.race not in equipment.race_restriction:
        return False
    return True


def latent_active(
    *, trigger: LatentTrigger, ctx: PlayerContext,
) -> bool:
    if trigger == LatentTrigger.NONE:
        return False
    if trigger == LatentTrigger.HP_BELOW_33:
        return ctx.hp_percent < 33
    if trigger == LatentTrigger.HP_BELOW_75:
        return ctx.hp_percent < 75
    if trigger == LatentTrigger.MP_BELOW_50:
        return ctx.mp_percent < 50
    if trigger == LatentTrigger.NIGHT_ONLY:
        return ctx.is_night
    if trigger == LatentTrigger.DAY_ONLY:
        return not ctx.is_night
    if trigger == LatentTrigger.IN_TOWN:
        return ctx.in_town
    return False


@dataclasses.dataclass
class LoadOut:
    player_id: str
    slots: dict[str, Equipment] = dataclasses.field(
        default_factory=dict,
    )

    def equip(
        self, *, equipment: Equipment, ctx: PlayerContext,
    ) -> bool:
        if not can_equip(equipment=equipment, ctx=ctx):
            return False
        self.slots[equipment.slot] = equipment
        return True

    def unequip(self, *, slot: str) -> bool:
        if slot not in self.slots:
            return False
        del self.slots[slot]
        return True

    def total_stats(
        self, *, ctx: PlayerContext,
    ) -> EquipmentStatBlock:
        total = EquipmentStatBlock()
        for eq in self.slots.values():
            total = _add_blocks(total, eq.base_stats)
            if latent_active(
                trigger=eq.latent_trigger, ctx=ctx,
            ):
                total = _add_blocks(total, eq.latent_stats)
        return total

    def slot_count(self) -> int:
        return len(self.slots)


__all__ = [
    "LatentTrigger", "EquipmentStatBlock",
    "Equipment", "PlayerContext",
    "can_equip", "latent_active",
    "LoadOut",
]
