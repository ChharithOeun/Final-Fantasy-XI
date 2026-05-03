"""Pet bonding — Trust/SMN/BST/PUP emotional bonds.

A pet (Trust spirit, summon, jug-pet beast, automaton) builds an
emotional bond with the master over time. Bond level affects:
* willingness to engage hard targets
* combat performance multiplier
* unlock of unique pet voice barks and quirks
* refusal to follow into instances if bond is broken

Bond rises through co-combat survival, victory shares, gift-feeds,
and the master's verbal praise. Bond falls when the master abandons
the pet to die, dismisses it after a one-shot, or starves it.

Distinct from squadron_system (mercenaries on contract) — pet
bonding is the SOUL of an individual companion.

Public surface
--------------
    PetKind enum
    BondTier enum
    PetBond dataclass
    BondEvent dataclass
    PetBondingRegistry
        .register_pet(master_id, pet_id, kind)
        .record_event(master_id, pet_id, event)
        .bond_for(master_id, pet_id)
        .bond_tier(master_id, pet_id)
        .pets_for(master_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Bond range: -100 (broken) to +1000 (legendary).
MIN_BOND = -100
MAX_BOND = 1000


class PetKind(str, enum.Enum):
    TRUST_SPIRIT = "trust_spirit"
    SUMMON_AVATAR = "summon_avatar"
    BST_JUG = "bst_jug"
    PUP_AUTOMATON = "pup_automaton"
    GEO_LUOPAN = "geo_luopan"


class BondTier(str, enum.Enum):
    BROKEN = "broken"          # < 0
    DISTANT = "distant"        # 0..50
    FAMILIAR = "familiar"      # 51..200
    LOYAL = "loyal"            # 201..500
    DEVOTED = "devoted"        # 501..800
    SOULBOUND = "soulbound"    # 801..1000


class BondEventKind(str, enum.Enum):
    SHARED_VICTORY = "shared_victory"
    PRAISE = "praise"
    GIFT_FEED = "gift_feed"
    HEALED_PET = "healed_pet"
    SHARED_PERIL = "shared_peril"      # both barely survived
    ABANDONED_TO_DIE = "abandoned_to_die"
    DISMISSED_QUICKLY = "dismissed_quickly"
    STARVED = "starved"
    REVIVED_AFTER_DEATH = "revived_after_death"


# Default bond deltas per event kind.
BOND_DELTA_BY_EVENT: dict[BondEventKind, int] = {
    BondEventKind.SHARED_VICTORY: 5,
    BondEventKind.PRAISE: 2,
    BondEventKind.GIFT_FEED: 8,
    BondEventKind.HEALED_PET: 4,
    BondEventKind.SHARED_PERIL: 12,
    BondEventKind.ABANDONED_TO_DIE: -25,
    BondEventKind.DISMISSED_QUICKLY: -3,
    BondEventKind.STARVED: -10,
    BondEventKind.REVIVED_AFTER_DEATH: 20,
}


@dataclasses.dataclass(frozen=True)
class BondEvent:
    kind: BondEventKind
    weight_multiplier: float = 1.0
    note: str = ""
    at_seconds: float = 0.0


@dataclasses.dataclass
class PetBond:
    master_id: str
    pet_id: str
    pet_kind: PetKind
    bond_score: int = 0
    fights_shared: int = 0
    times_revived: int = 0
    nickname: str = ""
    last_event_at_seconds: float = 0.0


def _tier_for_score(score: int) -> BondTier:
    if score < 0:
        return BondTier.BROKEN
    if score <= 50:
        return BondTier.DISTANT
    if score <= 200:
        return BondTier.FAMILIAR
    if score <= 500:
        return BondTier.LOYAL
    if score <= 800:
        return BondTier.DEVOTED
    return BondTier.SOULBOUND


@dataclasses.dataclass(frozen=True)
class BondModifier:
    """Effective combat / behavior multipliers for a pet."""
    damage_mult: float
    survivability_mult: float
    refuses_to_follow: bool


def modifier_for_tier(tier: BondTier) -> BondModifier:
    table: dict[BondTier, BondModifier] = {
        BondTier.BROKEN: BondModifier(0.6, 0.7, True),
        BondTier.DISTANT: BondModifier(0.85, 0.9, False),
        BondTier.FAMILIAR: BondModifier(1.0, 1.0, False),
        BondTier.LOYAL: BondModifier(1.10, 1.10, False),
        BondTier.DEVOTED: BondModifier(1.20, 1.20, False),
        BondTier.SOULBOUND: BondModifier(1.35, 1.30, False),
    }
    return table[tier]


@dataclasses.dataclass
class PetBondingRegistry:
    _bonds: dict[tuple[str, str], PetBond] = dataclasses.field(
        default_factory=dict,
    )
    _master_pets: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )

    def register_pet(
        self, *, master_id: str, pet_id: str,
        pet_kind: PetKind, nickname: str = "",
    ) -> t.Optional[PetBond]:
        key = (master_id, pet_id)
        if key in self._bonds:
            return None
        bond = PetBond(
            master_id=master_id, pet_id=pet_id,
            pet_kind=pet_kind, nickname=nickname,
        )
        self._bonds[key] = bond
        self._master_pets.setdefault(
            master_id, [],
        ).append(pet_id)
        return bond

    def bond_for(
        self, *, master_id: str, pet_id: str,
    ) -> t.Optional[PetBond]:
        return self._bonds.get((master_id, pet_id))

    def bond_tier(
        self, *, master_id: str, pet_id: str,
    ) -> t.Optional[BondTier]:
        bond = self._bonds.get((master_id, pet_id))
        if bond is None:
            return None
        return _tier_for_score(bond.bond_score)

    def pets_for(self, master_id: str) -> list[str]:
        return list(self._master_pets.get(master_id, []))

    def record_event(
        self, *, master_id: str, pet_id: str,
        event: BondEvent,
    ) -> t.Optional[int]:
        """Apply the event's bond-delta. Returns new bond_score."""
        bond = self._bonds.get((master_id, pet_id))
        if bond is None:
            return None
        delta = int(
            BOND_DELTA_BY_EVENT[event.kind]
            * event.weight_multiplier,
        )
        bond.bond_score = max(
            MIN_BOND,
            min(MAX_BOND, bond.bond_score + delta),
        )
        bond.last_event_at_seconds = event.at_seconds
        if event.kind == BondEventKind.SHARED_VICTORY:
            bond.fights_shared += 1
        if event.kind == BondEventKind.REVIVED_AFTER_DEATH:
            bond.times_revived += 1
        return bond.bond_score

    def break_bond(
        self, *, master_id: str, pet_id: str,
    ) -> bool:
        bond = self._bonds.get((master_id, pet_id))
        if bond is None:
            return False
        bond.bond_score = MIN_BOND
        return True

    def total_bonds(self) -> int:
        return len(self._bonds)


__all__ = [
    "MIN_BOND", "MAX_BOND",
    "PetKind", "BondTier", "BondEventKind",
    "BOND_DELTA_BY_EVENT",
    "BondEvent", "PetBond", "BondModifier",
    "modifier_for_tier",
    "PetBondingRegistry",
]
