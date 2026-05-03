"""Voidwalker NMs — T1-T4 tiered NMs with Voidstone pop triggers.

Distributed across most retail outdoor regions. Players obtain
Voidstones (rare drops from regular mobs in the same region),
trade them at a designated ??? site to pop a Voidwalker NM.

Tiering:
    T1 — easy, 1-3 players, common voidstone
    T2 — moderate, 3-6 players, uncommon voidstone
    T3 — hard, 6 players, rare voidstone
    T4 — endgame, full party, legendary voidstone

Drops include Riftworn Pyxis chests (which sometimes hold time
extension scrolls usable in Abyssea), Voidwalker-specific
weapons, and the next-tier Voidstone for the same region.

Public surface
--------------
    VoidwalkerTier enum
    VoidwalkerRegion enum
    VoidstoneKind enum
    VoidwalkerNM dataclass / VOIDWALKER_CATALOG
    pop_nm(stone, region) -> Optional[VoidwalkerNM]
    is_voidstone_compatible(stone, nm) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class VoidwalkerTier(str, enum.Enum):
    T1 = "t1"
    T2 = "t2"
    T3 = "t3"
    T4 = "t4"
    T5 = "t5"     # endgame — only spawns in unreleased shadow zones


class VoidwalkerRegion(str, enum.Enum):
    RONFAURE = "ronfaure"
    ZULKHEIM = "zulkheim"
    NORVALLEN = "norvallen"
    GUSTABERG = "gustaberg"
    DERFLAND = "derfland"
    SARUTABARUTA = "sarutabaruta"
    KOLSHUSHU = "kolshushu"
    ARAGONEU = "aragoneu"
    FAUREGANDI = "fauregandi"
    # ---- Unreleased "shadow" zones — host T5 voidwalkers
    SHADOW_REACHES = "shadow_reaches"
    HOLLOW_PINNACLE = "hollow_pinnacle"
    UNDERDEEP_SPIRES = "underdeep_spires"


class VoidstoneKind(str, enum.Enum):
    """Each region has its own family of voidstones tiered T1-T5."""
    CLEAR = "clear"          # T1 — common
    AMBER = "amber"          # T2 — uncommon
    SAPPHIRE = "sapphire"    # T3 — rare
    OBSIDIAN = "obsidian"    # T4 — legendary
    SHADOW = "shadow"        # T5 — drops only from T4 kills in
                              #      unreleased shadow zones


_TIER_FOR_STONE: dict[VoidstoneKind, VoidwalkerTier] = {
    VoidstoneKind.CLEAR: VoidwalkerTier.T1,
    VoidstoneKind.AMBER: VoidwalkerTier.T2,
    VoidstoneKind.SAPPHIRE: VoidwalkerTier.T3,
    VoidstoneKind.OBSIDIAN: VoidwalkerTier.T4,
    VoidstoneKind.SHADOW: VoidwalkerTier.T5,
}


_DROP_NEXT_STONE: dict[VoidstoneKind, t.Optional[VoidstoneKind]] = {
    VoidstoneKind.CLEAR: VoidstoneKind.AMBER,
    VoidstoneKind.AMBER: VoidstoneKind.SAPPHIRE,
    VoidstoneKind.SAPPHIRE: VoidstoneKind.OBSIDIAN,
    VoidstoneKind.OBSIDIAN: VoidstoneKind.SHADOW,   # T4 -> T5 stone
    VoidstoneKind.SHADOW: None,                     # T5 caps the chain
}


# T5 voidwalker NMs only exist in the three unreleased shadow zones.
T5_REGIONS: tuple[VoidwalkerRegion, ...] = (
    VoidwalkerRegion.SHADOW_REACHES,
    VoidwalkerRegion.HOLLOW_PINNACLE,
    VoidwalkerRegion.UNDERDEEP_SPIRES,
)


@dataclasses.dataclass(frozen=True)
class VoidwalkerNM:
    nm_id: str
    label: str
    region: VoidwalkerRegion
    tier: VoidwalkerTier
    party_size_min: int
    party_size_max: int
    drop_pool: tuple[str, ...]


# Sample catalog — at least one NM per region per tier in canonical
# retail; here we include 3 regions × 4 tiers = 12 entries to keep
# the seed slice readable.
_SAMPLE_REGIONS = (VoidwalkerRegion.RONFAURE,
                    VoidwalkerRegion.GUSTABERG,
                    VoidwalkerRegion.SARUTABARUTA)


def _drop_pool_for(tier: VoidwalkerTier,
                    region: VoidwalkerRegion) -> tuple[str, ...]:
    # Determine the next-stone drop based on this tier's stone
    tier_stone = next(
        s for s, t in _TIER_FOR_STONE.items() if t == tier
    )
    nxt = _DROP_NEXT_STONE.get(tier_stone)
    nxt_drop = (
        f"voidstone_{nxt.value}" if nxt is not None
        else "voidwalker_eternal_essence"   # T5 cap drop
    )
    base = ("riftworn_pyxis", nxt_drop)
    return base + (f"voidwalker_{tier.value}_{region.value}_drop",)


# T1-T4 distribution: 3 sample core regions
_T1_T4_PARTY_SIZE: dict[VoidwalkerTier, tuple[int, int]] = {
    VoidwalkerTier.T1: (1, 6),
    VoidwalkerTier.T2: (3, 6),
    VoidwalkerTier.T3: (6, 6),
    VoidwalkerTier.T4: (6, 18),
    VoidwalkerTier.T5: (12, 18),
}


def _build_catalog() -> tuple[VoidwalkerNM, ...]:
    out: list[VoidwalkerNM] = []
    # T1-T4 in core sample regions
    for region in _SAMPLE_REGIONS:
        for tier in (VoidwalkerTier.T1, VoidwalkerTier.T2,
                      VoidwalkerTier.T3, VoidwalkerTier.T4):
            mn, mx = _T1_T4_PARTY_SIZE[tier]
            out.append(VoidwalkerNM(
                nm_id=f"voidwalker_{region.value}_{tier.value}",
                label=f"Voidwalker NM {tier.value.upper()} "
                       f"({region.value})",
                region=region, tier=tier,
                party_size_min=mn, party_size_max=mx,
                drop_pool=_drop_pool_for(tier, region),
            ))
    # T5 only in shadow zones — one NM per shadow zone, each named
    # after the zone for thematic flavor.
    for region in T5_REGIONS:
        mn, mx = _T1_T4_PARTY_SIZE[VoidwalkerTier.T5]
        out.append(VoidwalkerNM(
            nm_id=f"voidwalker_{region.value}_t5",
            label=(
                f"Voidwalker T5 — "
                f"{region.value.replace('_', ' ').title()}"
            ),
            region=region, tier=VoidwalkerTier.T5,
            party_size_min=mn, party_size_max=mx,
            drop_pool=_drop_pool_for(VoidwalkerTier.T5, region),
        ))
    return tuple(out)


VOIDWALKER_CATALOG: tuple[VoidwalkerNM, ...] = _build_catalog()


NM_BY_REGION_TIER: dict[
    tuple[VoidwalkerRegion, VoidwalkerTier], VoidwalkerNM
] = {
    (n.region, n.tier): n for n in VOIDWALKER_CATALOG
}


def pop_nm(*, stone: VoidstoneKind, region: VoidwalkerRegion
            ) -> t.Optional[VoidwalkerNM]:
    """Trade a voidstone at the region's ??? site. Returns the
    NM that pops, or None if the region/tier doesn't have an NM
    in our catalog."""
    tier = _TIER_FOR_STONE.get(stone)
    if tier is None:
        return None
    return NM_BY_REGION_TIER.get((region, tier))


def is_voidstone_compatible(
    *, stone: VoidstoneKind, nm: VoidwalkerNM,
) -> bool:
    return _TIER_FOR_STONE[stone] == nm.tier


__all__ = [
    "VoidwalkerTier", "VoidwalkerRegion", "VoidstoneKind",
    "VoidwalkerNM",
    "VOIDWALKER_CATALOG", "NM_BY_REGION_TIER",
    "T5_REGIONS",
    "pop_nm", "is_voidstone_compatible",
]
