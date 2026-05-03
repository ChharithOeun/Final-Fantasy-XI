"""High Tier Battlefields (HTBC) — Mission BC tiered fights.

Canonical FFXI revisits classic mission boss fights at four
escalating tiers (T1 / T2 / T3 / Apex). Each tier requires a
specific Hourglass key item, has a 30-min timer, and drops
job-tier-relevant gear and Reforged Materials.

Iconic battlefield families:
    Throne Room (Shadow Lord encounter line)
    Promyvion (Carbuncle/Diabolos prime fights)
    Sea Lord (Aquarius encounter)
    Wyrm Lord (Bahamut prime)
    Vrtra Lord (Promathia revisit)

Public surface
--------------
    HTBCFamily enum
    HTBCTier enum (T1/T2/T3/APEX)
    Hourglass dataclass
    HTBCEntry / HTBC_CATALOG
    hourglass_required_for(family, tier) -> Hourglass
    can_attempt(family, tier, hourglass_held) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class HTBCFamily(str, enum.Enum):
    THRONE_ROOM = "throne_room"
    PROMYVION = "promyvion"
    SEA_LORD = "sea_lord"
    WYRM_LORD = "wyrm_lord"
    VRTRA_LORD = "vrtra_lord"
    # ---- Demoncore ML-tier families (entrance in shadow zones)
    SHADOW_CONCLAVE = "shadow_conclave"      # ML 100-125
    DEMON_LORD = "demon_lord"                # ML 125-150


class HTBCTier(str, enum.Enum):
    T1 = "t1"
    T2 = "t2"
    T3 = "t3"
    APEX = "apex"        # capstone (was canonically called "100yd")
    # ---- Demoncore ML-tier sub-tiers — only valid for ML families.
    # Five steps across the lvl 100-150 range; each gates higher
    # ML drops.
    ML_100 = "ml_100"    # entry — recommended ML 5-ish
    ML_110 = "ml_110"
    ML_120 = "ml_120"
    ML_130 = "ml_130"
    ML_150 = "ml_150"    # capstone


@dataclasses.dataclass(frozen=True)
class Hourglass:
    hourglass_id: str
    label: str
    family: HTBCFamily
    tier: HTBCTier


@dataclasses.dataclass(frozen=True)
class HTBCEntry:
    family: HTBCFamily
    tier: HTBCTier
    label: str
    timer_seconds: int
    party_size_min: int
    party_size_max: int
    drop_pool: tuple[str, ...]


# Sample HTBC catalog: 5 families × 4 tiers = 20 entries
_BASE_DROPS = (
    "reforged_material_lump",
    "reforged_material_carapace",
    "reforged_material_orichalcum",
    "rem_augment_stone",
)


_ML_FAMILIES: tuple[HTBCFamily, ...] = (
    HTBCFamily.SHADOW_CONCLAVE,
    HTBCFamily.DEMON_LORD,
)

_ML_TIERS: tuple[HTBCTier, ...] = (
    HTBCTier.ML_100,
    HTBCTier.ML_110,
    HTBCTier.ML_120,
    HTBCTier.ML_130,
    HTBCTier.ML_150,
)

_LEGACY_TIERS: tuple[HTBCTier, ...] = (
    HTBCTier.T1, HTBCTier.T2, HTBCTier.T3, HTBCTier.APEX,
)


def _drop_for(family: HTBCFamily, tier: HTBCTier) -> tuple[str, ...]:
    if tier in _ML_TIERS:
        # Each ML sub-tier gets richer drops as the level rises
        ml_index = _ML_TIERS.index(tier)
        common = _BASE_DROPS + ("shadow_fragment_common",)
        if ml_index >= 1:
            common = common + ("shadow_fragment_refined",)
        if ml_index >= 2:
            common = common + ("shadow_fragment_pristine",)
        if ml_index >= 3:
            common = common + ("tier_vi_spell_scroll_random",)
        if ml_index >= 4:
            common = common + (
                "shadow_fragment_eternal",
                f"{family.value}_capstone_drop",
            )
        return common + (f"{family.value}_{tier.value}_unique_drop",)
    base = _BASE_DROPS[: 1 if tier == HTBCTier.T1
                          else 2 if tier == HTBCTier.T2
                          else 3 if tier == HTBCTier.T3
                          else 4]
    return base + (f"{family.value}_{tier.value}_unique_drop",)


_TIER_PARTY_SIZE: dict[HTBCTier, tuple[int, int]] = {
    HTBCTier.T1: (3, 6),
    HTBCTier.T2: (6, 12),
    HTBCTier.T3: (12, 18),
    HTBCTier.APEX: (12, 18),
    HTBCTier.ML_100: (12, 18),
    HTBCTier.ML_110: (12, 18),
    HTBCTier.ML_120: (12, 18),
    HTBCTier.ML_130: (18, 18),
    HTBCTier.ML_150: (18, 18),
}


def _build_catalog() -> tuple[HTBCEntry, ...]:
    out: list[HTBCEntry] = []
    for family in HTBCFamily:
        is_ml_family = family in _ML_FAMILIES
        applicable_tiers = (
            _ML_TIERS if is_ml_family else _LEGACY_TIERS
        )
        for tier in applicable_tiers:
            mn, mx = _TIER_PARTY_SIZE[tier]
            out.append(HTBCEntry(
                family=family, tier=tier,
                label=(
                    f"{family.value.replace('_', ' ').title()} "
                    f"({tier.value.upper()})"
                ),
                timer_seconds=30 * 60,
                party_size_min=mn, party_size_max=mx,
                drop_pool=_drop_for(family, tier),
            ))
    return tuple(out)


HTBC_CATALOG: tuple[HTBCEntry, ...] = _build_catalog()


HTBC_BY_KEY: dict[tuple[HTBCFamily, HTBCTier], HTBCEntry] = {
    (e.family, e.tier): e for e in HTBC_CATALOG
}


def _hourglass_id(family: HTBCFamily, tier: HTBCTier) -> str:
    return f"hourglass_{family.value}_{tier.value}"


def hourglass_required_for(
    *, family: HTBCFamily, tier: HTBCTier,
) -> Hourglass:
    return Hourglass(
        hourglass_id=_hourglass_id(family, tier),
        label=(
            f"{family.value.replace('_', ' ').title()} "
            f"{tier.value.upper()} Hourglass"
        ),
        family=family, tier=tier,
    )


def can_attempt(
    *, family: HTBCFamily, tier: HTBCTier,
    hourglass_held: t.Iterable[str],
) -> bool:
    return _hourglass_id(family, tier) in set(hourglass_held)


def htbc_entry(
    *, family: HTBCFamily, tier: HTBCTier,
) -> t.Optional[HTBCEntry]:
    return HTBC_BY_KEY.get((family, tier))


__all__ = [
    "HTBCFamily", "HTBCTier",
    "Hourglass", "HTBCEntry",
    "HTBC_CATALOG", "HTBC_BY_KEY",
    "hourglass_required_for", "can_attempt", "htbc_entry",
]
