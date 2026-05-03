"""Su gear progression — Su5 i-lvl ladder (119 -> 175).

Mirrors Ambuscade Repurpose's progression, but for Su gear/weapons.
The key twist is that upgrading a Su5 piece CONSUMES old Su gear
(Su2 / Su3 / Su4) of the same slot — you don't need to roll a
brand-new piece, you feed the bench your prior tiers.

i-lvl ladder
------------
The first tier is the canonical Su5 fresh-out-of-Odyssey i-lvl 119.
After that, each upgrade tier is +5 i-lvl:

    T0 = 119   (Su5 fresh)
    T1 = 125   (stabilized — costs one Su2 piece as fuel)
    T2 = 130   (costs Su2 + Su3 fuel)
    T3 = 135   (...)
    ...
    T11 = 175  (top — costs Su2 + Su3 + Su4 + a refined Su5 token)

Each ladder step demands at least one OLD Su piece (the "fuel") of
the same slot/weapon-kind. Higher tiers demand correspondingly
rarer fuel — so the entire Su pipeline (Sortie / Odyssey / Sheol)
keeps producing economic value all the way up the ladder.

Weapons follow the same axes but their fuel chain is harder to
acquire (the canonical "Su weapons mats are rarer than gear"
rule). The fuel requirement table on the WEAPON side calls for
two pieces of fuel per tier instead of one, plus a higher-tier
floor at the top of the chain.

This module is a state-modeling layer; the actual fuel tables
and drop sources live alongside in su_recipe_slips. What this
module exposes:

    SuKind enum (ARMOR / WEAPON)
    SuSlot enum (slots + weapon-kinds in one enum for simplicity)
    SuArchetype enum (caster / melee / ranger / NIN / BLU / PUP /
                      BST / DNC / RUN — same bundles as ambuscade)
    SuPiece dataclass — single tracked piece
    PlayerSuProgression — collection per-player
    AdvanceResult / advance_ilvl(...)
    ilvl_for_su_tier(tier) -> int
    fuel_required(kind, tier) -> tuple[FuelRequirement, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


SU_LADDER_TIERS = 12        # T0..T11
SU_BASE_ILVL = 119          # T0 — Su5 unmodified


class SuKind(str, enum.Enum):
    ARMOR = "armor"
    WEAPON = "weapon"


class SuSlot(str, enum.Enum):
    """Armor slots + weapon kinds in a single namespace. Weapon
    kinds collapse the giant FFXI weapon list down to canonical
    families that all behave the same way for upgrade purposes."""
    # Armor
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    NECK = "neck"
    EARRING = "earring"
    RING = "ring"
    BACK = "back"
    WAIST = "waist"
    # Weapons
    MAIN_HAND_MELEE = "main_hand_melee"
    MAIN_HAND_MAGIC = "main_hand_magic"
    RANGED = "ranged"
    AMMO = "ammo"


_ARMOR_SLOTS: frozenset[SuSlot] = frozenset({
    SuSlot.HEAD, SuSlot.BODY, SuSlot.HANDS, SuSlot.LEGS, SuSlot.FEET,
    SuSlot.NECK, SuSlot.EARRING, SuSlot.RING, SuSlot.BACK, SuSlot.WAIST,
})

_WEAPON_SLOTS: frozenset[SuSlot] = frozenset({
    SuSlot.MAIN_HAND_MELEE, SuSlot.MAIN_HAND_MAGIC,
    SuSlot.RANGED, SuSlot.AMMO,
})


def kind_for_slot(slot: SuSlot) -> SuKind:
    if slot in _WEAPON_SLOTS:
        return SuKind.WEAPON
    return SuKind.ARMOR


class SuArchetype(str, enum.Enum):
    CASTER = "caster"
    MELEE = "melee"
    RANGER = "ranger"
    NINJA = "ninja"
    BLUE_MAGE = "blue_mage"
    PUPPET = "puppet"
    BEAST = "beast"
    DANCER = "dancer"
    RUNE = "rune"


class SuFuelTier(str, enum.Enum):
    """Which old Su tier is being fed in as fuel."""
    SU2 = "su2"
    SU3 = "su3"
    SU4 = "su4"
    SU5_TOKEN = "su5_token"   # rarefied refined currency for top tier


def ilvl_for_su_tier(tier: int) -> int:
    """Map T0..T11 to actual i-lvl values.

    T0 = 119, then T1 = 125, T2 = 130, ..., T11 = 175. The first
    bump is +6 (the "stabilize" step) and the rest are +5.
    """
    if not (0 <= tier < SU_LADDER_TIERS):
        raise ValueError(f"su tier {tier} out of range 0-11")
    if tier == 0:
        return SU_BASE_ILVL
    return 120 + 5 * tier


# Per-tier stat bump (additive over base block, similar to
# ambuscade ILVL_STAT_BUMP). Su gear is slightly higher tier-per-
# tier because there's no "+quality" axis to play with.
SU_ILVL_STAT_BUMP_PER_TIER = 4


_BASE_STATS_BY_SLOT: dict[SuSlot, dict[str, int]] = {
    # Armor (richer base than ambuscade — Su gear is endgame)
    SuSlot.HEAD: {"str": 6, "dex": 6, "int": 6, "mnd": 6,
                   "hp": 35, "defense": 40},
    SuSlot.BODY: {"str": 9, "vit": 9, "int": 7, "mnd": 7,
                   "hp": 70, "defense": 80},
    SuSlot.HANDS: {"str": 6, "dex": 8, "int": 5, "mnd": 5,
                    "hp": 30, "defense": 35, "attack": 6},
    SuSlot.LEGS: {"str": 8, "vit": 8, "agi": 6, "mnd": 6,
                   "hp": 55, "defense": 65},
    SuSlot.FEET: {"agi": 9, "dex": 6, "vit": 5,
                   "hp": 30, "defense": 30, "evasion": 6},
    SuSlot.NECK: {"int": 5, "mnd": 5, "chr": 5, "hp": 18},
    SuSlot.EARRING: {"dex": 4, "agi": 4, "hp": 12},
    SuSlot.RING: {"str": 4, "dex": 4, "int": 4, "mnd": 4, "hp": 12},
    SuSlot.BACK: {"str": 5, "dex": 5, "agi": 5, "hp": 25},
    SuSlot.WAIST: {"str": 5, "vit": 5, "dex": 5, "hp": 18},
    # Weapons — base damage + relevant-stat boost
    SuSlot.MAIN_HAND_MELEE: {
        "damage": 80, "delay": 240, "str": 8, "attack": 12,
    },
    SuSlot.MAIN_HAND_MAGIC: {
        "damage": 50, "delay": 240, "int": 8, "magic_attack": 12,
    },
    SuSlot.RANGED: {
        "damage": 70, "delay": 280, "agi": 8, "ranged_attack": 12,
    },
    SuSlot.AMMO: {
        "damage": 12, "agi": 3, "accuracy": 5,
    },
}


def base_stat_block(*, slot: SuSlot) -> dict[str, int]:
    return dict(_BASE_STATS_BY_SLOT[slot])


def apply_su_tier_bonus(
    *, base: dict[str, int], ilvl_tier: int,
) -> dict[str, int]:
    if not (0 <= ilvl_tier < SU_LADDER_TIERS):
        raise ValueError(f"ilvl_tier {ilvl_tier} out of range 0-11")
    bump = ilvl_tier * SU_ILVL_STAT_BUMP_PER_TIER
    out = {}
    for k, v in base.items():
        # delay stays fixed — it's a weapon-cycle constant
        if k == "delay":
            out[k] = v
        else:
            out[k] = v + bump
    return out


@dataclasses.dataclass(frozen=True)
class FuelRequirement:
    """One unit of fuel consumed by an upgrade step."""
    fuel_tier: SuFuelTier
    count: int = 1


def fuel_required(
    *, kind: SuKind, ilvl_tier: int,
) -> tuple[FuelRequirement, ...]:
    """Return what old Su gear (or refined token) the upgrade
    bench requires to advance INTO ilvl_tier.

    Armor tier curve (consumed PER upgrade step):
        T0  -> N/A (initial craft, no fuel)
        T1  -> 1x Su2
        T2  -> 1x Su2 + 1x Su3
        T3  -> 1x Su3
        T4  -> 1x Su3 + 1x Su4
        T5  -> 1x Su4
        T6  -> 2x Su4
        T7  -> 1x Su4 + 1x Su5 token
        T8  -> 1x Su5 token
        T9  -> 2x Su5 token
        T10 -> 3x Su5 token
        T11 -> 4x Su5 token

    Weapon tier curve: same shape but DOUBLED per step (canonical
    "Su weapons take more mats than Su gear" rule).
    """
    if not (0 <= ilvl_tier < SU_LADDER_TIERS):
        raise ValueError(f"ilvl_tier {ilvl_tier} out of range 0-11")
    if ilvl_tier == 0:
        return ()
    armor_table: dict[int, tuple[FuelRequirement, ...]] = {
        1: (FuelRequirement(SuFuelTier.SU2, 1),),
        2: (FuelRequirement(SuFuelTier.SU2, 1),
            FuelRequirement(SuFuelTier.SU3, 1)),
        3: (FuelRequirement(SuFuelTier.SU3, 1),),
        4: (FuelRequirement(SuFuelTier.SU3, 1),
            FuelRequirement(SuFuelTier.SU4, 1)),
        5: (FuelRequirement(SuFuelTier.SU4, 1),),
        6: (FuelRequirement(SuFuelTier.SU4, 2),),
        7: (FuelRequirement(SuFuelTier.SU4, 1),
            FuelRequirement(SuFuelTier.SU5_TOKEN, 1)),
        8: (FuelRequirement(SuFuelTier.SU5_TOKEN, 1),),
        9: (FuelRequirement(SuFuelTier.SU5_TOKEN, 2),),
        10: (FuelRequirement(SuFuelTier.SU5_TOKEN, 3),),
        11: (FuelRequirement(SuFuelTier.SU5_TOKEN, 4),),
    }
    base_reqs = armor_table[ilvl_tier]
    if kind == SuKind.ARMOR:
        return base_reqs
    # Weapons: double everything
    return tuple(
        FuelRequirement(r.fuel_tier, r.count * 2) for r in base_reqs
    )


@dataclasses.dataclass
class SuPiece:
    piece_id: str
    slot: SuSlot
    archetype: SuArchetype
    ilvl_tier: int = 0   # 0..11

    @property
    def kind(self) -> SuKind:
        return kind_for_slot(self.slot)

    @property
    def ilvl(self) -> int:
        return ilvl_for_su_tier(self.ilvl_tier)

    def stats(self) -> dict[str, int]:
        return apply_su_tier_bonus(
            base=base_stat_block(slot=self.slot),
            ilvl_tier=self.ilvl_tier,
        )


@dataclasses.dataclass(frozen=True)
class AdvanceResult:
    accepted: bool
    new_ilvl_tier: int = 0
    new_ilvl: int = 0
    fuel_consumed: tuple[FuelRequirement, ...] = ()
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerSuProgression:
    player_id: str
    _pieces: dict[str, SuPiece] = dataclasses.field(
        default_factory=dict,
    )

    @property
    def pieces(self) -> tuple[SuPiece, ...]:
        return tuple(self._pieces.values())

    def get(self, piece_id: str) -> t.Optional[SuPiece]:
        return self._pieces.get(piece_id)

    def craft_new(
        self, *, piece_id: str, slot: SuSlot,
        archetype: SuArchetype,
    ) -> SuPiece:
        """Drop a fresh Su5 piece (T0, i-lvl 119) into the
        progression. This is the entry point — the actual loot
        drop from Odyssey/Sortie/Sheol is what hands the player
        a Su5; this just records that it exists."""
        piece = SuPiece(
            piece_id=piece_id, slot=slot, archetype=archetype,
        )
        self._pieces[piece_id] = piece
        return piece

    def advance_ilvl(
        self, *, piece_id: str, target_step: int,
        available_fuel: t.Optional[
            dict[SuFuelTier, int]
        ] = None,
    ) -> AdvanceResult:
        """Advance the Su piece's i-lvl tier. Must move exactly
        one tier at a time and the supplied fuel pool must
        cover the requirement.

        `available_fuel` is a dict of {fuel_tier -> count} the
        player offers to the bench. Pass None / empty to query
        what's required without committing fuel — but in that
        case the upgrade will fail unless the upgrade is free
        (i.e. T0)."""
        p = self._pieces.get(piece_id)
        if p is None:
            return AdvanceResult(False, reason="no such piece")
        if target_step != p.ilvl_tier + 1:
            return AdvanceResult(
                False, reason="must advance one tier at a time",
            )
        if target_step >= SU_LADDER_TIERS:
            return AdvanceResult(False, reason="already at max i-lvl")
        required = fuel_required(kind=p.kind, ilvl_tier=target_step)
        pool = dict(available_fuel or {})
        for req in required:
            have = pool.get(req.fuel_tier, 0)
            if have < req.count:
                return AdvanceResult(
                    False,
                    reason=(
                        f"insufficient fuel: need {req.count}x"
                        f" {req.fuel_tier.value}, have {have}"
                    ),
                )
            pool[req.fuel_tier] = have - req.count
        # Commit
        p.ilvl_tier = target_step
        return AdvanceResult(
            accepted=True,
            new_ilvl_tier=p.ilvl_tier,
            new_ilvl=p.ilvl,
            fuel_consumed=required,
        )

    def can_advance(self, *, piece_id: str) -> bool:
        p = self._pieces.get(piece_id)
        if p is None:
            return False
        return p.ilvl_tier < SU_LADDER_TIERS - 1

    def total_fuel_for_full_climb(
        self, *, kind: SuKind,
    ) -> dict[SuFuelTier, int]:
        """Aggregate fuel needed to take a fresh T0 piece all the
        way to T11 (the full ladder). Useful for vendor pricing /
        UI tooltips."""
        totals: dict[SuFuelTier, int] = {}
        for tier in range(1, SU_LADDER_TIERS):
            for req in fuel_required(kind=kind, ilvl_tier=tier):
                totals[req.fuel_tier] = (
                    totals.get(req.fuel_tier, 0) + req.count
                )
        return totals


__all__ = [
    "SU_LADDER_TIERS", "SU_BASE_ILVL",
    "SU_ILVL_STAT_BUMP_PER_TIER",
    "SuKind", "SuSlot", "SuArchetype", "SuFuelTier",
    "kind_for_slot", "ilvl_for_su_tier",
    "base_stat_block", "apply_su_tier_bonus",
    "FuelRequirement", "fuel_required",
    "SuPiece", "AdvanceResult", "PlayerSuProgression",
]
