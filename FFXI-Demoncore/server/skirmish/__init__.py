"""Skirmish — SoA augment-stones mini-instance.

Players enter a Skirmish with a chosen tier of stone (Yhel /
Vidu / Dwarven, plus +1 / +2 / +3 polished variants). The
stone determines:
* augment quality on the Skirmish gear that drops
* mob composition difficulty
* Bayld and Plutons payout

Three Skirmish ruins (Rala / Cirdas / Yorcia) host the
runs. Stones are consumed on entry; gear drops as augmentable
shells, and a separate NPC inscribes stones onto the gear to
finalize augments.

Public surface
--------------
    SkirmishRuin enum
    StoneTier enum / StoneFamily enum
    SkirmishStone dataclass / STONE_CATALOG
    SkirmishEntry dataclass / SKIRMISH_CATALOG
    augment_quality_for(stone_tier) -> int
    PlayerSkirmish (track stones, bayld, plutons)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SkirmishRuin(str, enum.Enum):
    RALA_WATERWAYS = "rala_waterways"
    CIRDAS_CAVERNS = "cirdas_caverns"
    YORCIA_WEALD = "yorcia_weald"


class StoneFamily(str, enum.Enum):
    """Each stone family is themed to a Skirmish ruin and a
    job-archetype."""
    YHEL = "yhel"            # Rala — caster slant
    VIDU = "vidu"            # Cirdas — melee slant
    DWARVEN = "dwarven"      # Yorcia — hybrid


class StoneTier(str, enum.Enum):
    """Polished stone variants: NQ / +1 / +2 / +3. Higher tier
    -> better augment rolls."""
    NQ = "nq"
    PLUS_1 = "+1"
    PLUS_2 = "+2"
    PLUS_3 = "+3"


# Per-tier augment quality target
_AUGMENT_QUALITY: dict[StoneTier, int] = {
    StoneTier.NQ: 1,
    StoneTier.PLUS_1: 2,
    StoneTier.PLUS_2: 3,
    StoneTier.PLUS_3: 4,
}


# Per-tier Bayld payout multiplier
_BAYLD_MULT: dict[StoneTier, float] = {
    StoneTier.NQ: 1.0,
    StoneTier.PLUS_1: 1.25,
    StoneTier.PLUS_2: 1.5,
    StoneTier.PLUS_3: 2.0,
}


@dataclasses.dataclass(frozen=True)
class SkirmishStone:
    stone_id: str
    family: StoneFamily
    tier: StoneTier
    label: str


@dataclasses.dataclass(frozen=True)
class SkirmishEntry:
    ruin: SkirmishRuin
    label: str
    eligible_stone_family: StoneFamily
    timer_seconds: int
    base_bayld_payout: int
    base_plutons_payout: int


SKIRMISH_CATALOG: tuple[SkirmishEntry, ...] = (
    SkirmishEntry(
        SkirmishRuin.RALA_WATERWAYS, "Rala Waterways",
        eligible_stone_family=StoneFamily.YHEL,
        timer_seconds=30 * 60,
        base_bayld_payout=2000, base_plutons_payout=80,
    ),
    SkirmishEntry(
        SkirmishRuin.CIRDAS_CAVERNS, "Cirdas Caverns",
        eligible_stone_family=StoneFamily.VIDU,
        timer_seconds=30 * 60,
        base_bayld_payout=2000, base_plutons_payout=80,
    ),
    SkirmishEntry(
        SkirmishRuin.YORCIA_WEALD, "Yorcia Weald",
        eligible_stone_family=StoneFamily.DWARVEN,
        timer_seconds=30 * 60,
        base_bayld_payout=2500, base_plutons_payout=120,
    ),
)


# Generated catalog: each ruin's family × 4 tiers = 12 stones
def _build_stone_catalog() -> dict[str, SkirmishStone]:
    out: dict[str, SkirmishStone] = {}
    for fam in StoneFamily:
        for tier in StoneTier:
            sid = f"stone_{fam.value}_{tier.value.replace('+', 'p')}"
            label_tier = "" if tier == StoneTier.NQ else f" {tier.value}"
            out[sid] = SkirmishStone(
                stone_id=sid, family=fam, tier=tier,
                label=f"{fam.value.title()} Stone{label_tier}",
            )
    return out


STONE_CATALOG: dict[str, SkirmishStone] = _build_stone_catalog()


def augment_quality_for(*, tier: StoneTier) -> int:
    return _AUGMENT_QUALITY[tier]


def bayld_payout(*, ruin: SkirmishRuin, tier: StoneTier) -> int:
    base = next(
        e for e in SKIRMISH_CATALOG if e.ruin == ruin
    ).base_bayld_payout
    return int(base * _BAYLD_MULT[tier])


def plutons_payout(*, ruin: SkirmishRuin, tier: StoneTier) -> int:
    base = next(
        e for e in SKIRMISH_CATALOG if e.ruin == ruin
    ).base_plutons_payout
    return int(base * _BAYLD_MULT[tier])


def is_stone_compatible(*, ruin: SkirmishRuin, stone_id: str) -> bool:
    stone = STONE_CATALOG.get(stone_id)
    if stone is None:
        return False
    entry = next((e for e in SKIRMISH_CATALOG if e.ruin == ruin), None)
    if entry is None:
        return False
    return stone.family == entry.eligible_stone_family


@dataclasses.dataclass
class PlayerSkirmish:
    player_id: str
    stones: dict[str, int] = dataclasses.field(default_factory=dict)
    bayld: int = 0
    plutons: int = 0

    def add_stone(self, *, stone_id: str, quantity: int = 1) -> bool:
        if stone_id not in STONE_CATALOG or quantity <= 0:
            return False
        self.stones[stone_id] = self.stones.get(stone_id, 0) + quantity
        return True

    def consume_stone(self, *, stone_id: str) -> bool:
        if self.stones.get(stone_id, 0) <= 0:
            return False
        self.stones[stone_id] -= 1
        return True

    def award_run(
        self, *, ruin: SkirmishRuin, tier: StoneTier,
    ) -> bool:
        self.bayld += bayld_payout(ruin=ruin, tier=tier)
        self.plutons += plutons_payout(ruin=ruin, tier=tier)
        return True


__all__ = [
    "SkirmishRuin", "StoneFamily", "StoneTier",
    "SkirmishStone", "SkirmishEntry",
    "STONE_CATALOG", "SKIRMISH_CATALOG",
    "augment_quality_for", "bayld_payout", "plutons_payout",
    "is_stone_compatible",
    "PlayerSkirmish",
]
