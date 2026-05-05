"""Abyssal gear augment — augment pipeline for ocean gear.

Surface gear has the augment_engine for random stat rolls.
Underwater gear has its own pipeline because the relevant
stats are different: WATER_RES, PRESSURE_NEGATE,
BREATH_EFFICIENCY, KRAKEN_RESIST, PEARL_LUCK. Stats are
tier-banded so an UNCOMMON augment can't roll a 99
PRESSURE_NEGATE.

Augment process:
  Player brings a base piece and a CATALYST. Catalyst tier
  determines the augment band:
    BRINE_DROP        - common; small bonus
    PEARLDUST         - uncommon; mid bonus
    KRAKEN_INK_VIAL   - rare; high bonus

Each augment gives 1..3 stats from the catalog at a
band-determined value. Augmenting an already-augmented
piece OVERWRITES the previous augment (one augment slot per
piece).

We deterministically derive the rolled values from the
PIECE_ID + CATALYST + ROLL_SEED so the same inputs always
produce the same augment — this is so testers can verify
the system is fair without hidden RNG.

Public surface
--------------
    AugmentBand enum
    OceanStat enum
    Catalyst enum
    AugmentRoll dataclass
    AbyssalGearAugment
        .augment(piece_id, catalyst, roll_seed)
        .augment_for(piece_id) -> AugmentRoll | None
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AugmentBand(str, enum.Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"


class OceanStat(str, enum.Enum):
    WATER_RES = "water_res"
    PRESSURE_NEGATE = "pressure_negate"
    BREATH_EFFICIENCY = "breath_efficiency"
    KRAKEN_RESIST = "kraken_resist"
    PEARL_LUCK = "pearl_luck"


class Catalyst(str, enum.Enum):
    BRINE_DROP = "brine_drop"
    PEARLDUST = "pearldust"
    KRAKEN_INK_VIAL = "kraken_ink_vial"


_CATALYST_BAND: dict[Catalyst, AugmentBand] = {
    Catalyst.BRINE_DROP: AugmentBand.COMMON,
    Catalyst.PEARLDUST: AugmentBand.UNCOMMON,
    Catalyst.KRAKEN_INK_VIAL: AugmentBand.RARE,
}

# (min_value, max_value, num_stats_min, num_stats_max)
_BAND_PROFILE: dict[AugmentBand, tuple[int, int, int, int]] = {
    AugmentBand.COMMON: (1, 5, 1, 1),
    AugmentBand.UNCOMMON: (4, 12, 1, 2),
    AugmentBand.RARE: (10, 25, 2, 3),
}

_STAT_ORDER: tuple[OceanStat, ...] = (
    OceanStat.WATER_RES,
    OceanStat.PRESSURE_NEGATE,
    OceanStat.BREATH_EFFICIENCY,
    OceanStat.KRAKEN_RESIST,
    OceanStat.PEARL_LUCK,
)


@dataclasses.dataclass(frozen=True)
class AugmentRoll:
    accepted: bool
    piece_id: str
    band: t.Optional[AugmentBand] = None
    stats: tuple[tuple[OceanStat, int], ...] = ()
    reason: t.Optional[str] = None


@dataclasses.dataclass
class AbyssalGearAugment:
    _augments: dict[str, AugmentRoll] = dataclasses.field(
        default_factory=dict,
    )

    @staticmethod
    def _derive_stats(
        *, piece_id: str,
        band: AugmentBand,
        roll_seed: int,
    ) -> tuple[tuple[OceanStat, int], ...]:
        # deterministic derivation: hash piece_id + seed -> picks
        min_v, max_v, n_min, n_max = _BAND_PROFILE[band]
        h = hash((piece_id, band.value, roll_seed))
        # number of stats
        n_range = n_max - n_min + 1
        n_stats = n_min + (h % n_range)
        # pick stats — rotate through _STAT_ORDER from h
        start = h % len(_STAT_ORDER)
        chosen: list[OceanStat] = []
        for i in range(n_stats):
            chosen.append(_STAT_ORDER[(start + i) % len(_STAT_ORDER)])
        # values: derived from h, scaled to [min_v..max_v]
        v_range = max_v - min_v + 1
        result: list[tuple[OceanStat, int]] = []
        for i, stat in enumerate(chosen):
            value = min_v + ((h >> (i * 4)) % v_range)
            # clamp positive
            if value < min_v:
                value = min_v
            result.append((stat, value))
        return tuple(result)

    def augment(
        self, *, piece_id: str,
        catalyst: Catalyst,
        roll_seed: int,
    ) -> AugmentRoll:
        if not piece_id:
            return AugmentRoll(False, piece_id="", reason="bad piece")
        if catalyst not in _CATALYST_BAND:
            return AugmentRoll(
                False, piece_id=piece_id, reason="unknown catalyst",
            )
        if roll_seed < 0:
            return AugmentRoll(
                False, piece_id=piece_id, reason="bad seed",
            )
        band = _CATALYST_BAND[catalyst]
        stats = self._derive_stats(
            piece_id=piece_id, band=band, roll_seed=roll_seed,
        )
        roll = AugmentRoll(
            accepted=True,
            piece_id=piece_id,
            band=band,
            stats=stats,
        )
        # overwrite any previous augment on this piece
        self._augments[piece_id] = roll
        return roll

    def augment_for(
        self, *, piece_id: str,
    ) -> t.Optional[AugmentRoll]:
        return self._augments.get(piece_id)


__all__ = [
    "AugmentBand", "OceanStat", "Catalyst",
    "AugmentRoll", "AbyssalGearAugment",
]
