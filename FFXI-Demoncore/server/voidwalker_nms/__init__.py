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


class VoidstoneKind(str, enum.Enum):
    """Each region has its own family of voidstones tiered T1-T4."""
    CLEAR = "clear"          # T1 — common
    AMBER = "amber"          # T2 — uncommon
    SAPPHIRE = "sapphire"    # T3 — rare
    OBSIDIAN = "obsidian"    # T4 — legendary


_TIER_FOR_STONE: dict[VoidstoneKind, VoidwalkerTier] = {
    VoidstoneKind.CLEAR: VoidwalkerTier.T1,
    VoidstoneKind.AMBER: VoidwalkerTier.T2,
    VoidstoneKind.SAPPHIRE: VoidwalkerTier.T3,
    VoidstoneKind.OBSIDIAN: VoidwalkerTier.T4,
}


_DROP_NEXT_STONE: dict[VoidstoneKind, t.Optional[VoidstoneKind]] = {
    VoidstoneKind.CLEAR: VoidstoneKind.AMBER,
    VoidstoneKind.AMBER: VoidstoneKind.SAPPHIRE,
    VoidstoneKind.SAPPHIRE: VoidstoneKind.OBSIDIAN,
    VoidstoneKind.OBSIDIAN: None,    # T4 is the cap
}


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
    base = (
        "riftworn_pyxis",
        f"voidstone_{_DROP_NEXT_STONE[VoidstoneKind.CLEAR].value}"
        if tier == VoidwalkerTier.T1 else
        f"voidstone_{_DROP_NEXT_STONE[VoidstoneKind.AMBER].value}"
        if tier == VoidwalkerTier.T2 else
        f"voidstone_{_DROP_NEXT_STONE[VoidstoneKind.SAPPHIRE].value}"
        if tier == VoidwalkerTier.T3 else
        "voidwalker_relic_dust",
    )
    return base + (f"voidwalker_{tier.value}_{region.value}_drop",)


def _build_catalog() -> tuple[VoidwalkerNM, ...]:
    out: list[VoidwalkerNM] = []
    for region in _SAMPLE_REGIONS:
        for tier in VoidwalkerTier:
            min_party = {
                VoidwalkerTier.T1: 1, VoidwalkerTier.T2: 3,
                VoidwalkerTier.T3: 6, VoidwalkerTier.T4: 6,
            }[tier]
            max_party = 6 if tier != VoidwalkerTier.T4 else 18
            out.append(VoidwalkerNM(
                nm_id=f"voidwalker_{region.value}_{tier.value}",
                label=f"Voidwalker NM {tier.value.upper()} ({region.value})",
                region=region, tier=tier,
                party_size_min=min_party, party_size_max=max_party,
                drop_pool=_drop_pool_for(tier, region),
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
    "pop_nm", "is_voidstone_compatible",
]
