"""Wildskeeper Reives — SoA open-world world boss encounters.

Open-world, single-instance reive encounters spawned at fixed
points across Adoulin's frontier. Up to 18 players can
participate. Reward distribution is *contribution-tracked*:
each player earns Bayld + reive participation tokens
proportional to damage dealt + heals delivered.

Five canonical Wildskeepers:
    Tojil          — fire-aspect colossus (Yorcia Weald)
    Achuka         — wind-aspect (Cirdas Caverns)
    Warder         — earth-aspect (Marjami Ravine)
    Hriata         — water-aspect (Rala Waterways)
    Belphoebe      — light-aspect (Sih Gates)

Public surface
--------------
    Wildskeeper enum
    WildskeeperEntry dataclass / WILDSKEEPER_CATALOG
    ReiveSession dataclass — tracks participants + contributions
        .add_contribution(player_id, damage, healing)
        .resolve() -> dict[player_id, ReiveReward]
    bayld_share(total_bayld, contribution, total_contributions) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_PARTICIPANTS = 18
BAYLD_BASE_POOL = 50_000
PARTICIPATION_TOKEN_BASE = 100


class Wildskeeper(str, enum.Enum):
    TOJIL = "tojil"
    ACHUKA = "achuka"
    WARDER = "warder"
    HRIATA = "hriata"
    BELPHOEBE = "belphoebe"
    # ---- Demoncore extension — new shadow-zone wildskeepers
    VOLDYNE = "voldyne"           # shadow-aspect
    SKARMIR = "skarmir"           # chocobo-woods overlord
    QUENIVAR = "quenivar"         # ancient-ruins capstone


@dataclasses.dataclass(frozen=True)
class WildskeeperEntry:
    boss: Wildskeeper
    label: str
    zone: str
    element: str
    bayld_pool: int
    drop_pool: tuple[str, ...]


WILDSKEEPER_CATALOG: tuple[WildskeeperEntry, ...] = (
    WildskeeperEntry(
        Wildskeeper.TOJIL, "Tojil",
        zone="yorcia_weald", element="fire",
        bayld_pool=BAYLD_BASE_POOL,
        drop_pool=("orobon_rib", "tojil_horn", "fire_ore"),
    ),
    WildskeeperEntry(
        Wildskeeper.ACHUKA, "Achuka",
        zone="cirdas_caverns", element="wind",
        bayld_pool=BAYLD_BASE_POOL,
        drop_pool=("achuka_feather", "wind_ore", "high_kindred_xarc"),
    ),
    WildskeeperEntry(
        Wildskeeper.WARDER, "Warder",
        zone="marjami_ravine", element="earth",
        bayld_pool=BAYLD_BASE_POOL,
        drop_pool=("warder_carapace", "earth_ore", "marjami_rune"),
    ),
    WildskeeperEntry(
        Wildskeeper.HRIATA, "Hriata",
        zone="rala_waterways", element="water",
        bayld_pool=BAYLD_BASE_POOL,
        drop_pool=("hriata_scale", "water_ore", "tide_pearl"),
    ),
    WildskeeperEntry(
        Wildskeeper.BELPHOEBE, "Belphoebe",
        zone="sih_gates", element="light",
        bayld_pool=BAYLD_BASE_POOL * 2,   # SoA capstone, double pool
        drop_pool=("belphoebe_halo", "light_ore", "starseed"),
    ),
    # ---- Demoncore — new shadow-zone wildskeepers
    WildskeeperEntry(
        Wildskeeper.VOLDYNE, "Voldyne, the Shadow-Mantled Saurian",
        zone="shadow_charnel_ridge", element="dark",
        bayld_pool=BAYLD_BASE_POOL * 2,
        drop_pool=("voldyne_mantle_shred", "shadow_ore",
                    "voidwoven_essence",
                    "voidstone_shadow"),
    ),
    WildskeeperEntry(
        Wildskeeper.SKARMIR, "Skarmir, the Roost-Tyrant",
        zone="chocobo_woods", element="wind",
        bayld_pool=BAYLD_BASE_POOL * 2,
        drop_pool=("skarmir_pinion_feather", "tyrant_chocobo_egg",
                    "wind_ore", "chocobo_breeding_certificate"),
    ),
    WildskeeperEntry(
        Wildskeeper.QUENIVAR, "Quenivar, Architect of Ruined Time",
        zone="hollow_pinnacle", element="ice",
        bayld_pool=BAYLD_BASE_POOL * 3,   # full Demoncore capstone
        drop_pool=("quenivar_keystone", "ruin_chronograph",
                    "ice_ore", "shadow_fragment_eternal",
                    "tier_vi_spell_scroll_random"),
    ),
)


WK_BY_BOSS: dict[Wildskeeper, WildskeeperEntry] = {
    e.boss: e for e in WILDSKEEPER_CATALOG
}


def wildskeeper_entry(boss: Wildskeeper) -> t.Optional[WildskeeperEntry]:
    return WK_BY_BOSS.get(boss)


def bayld_share(
    *, total_bayld: int, contribution: int, total_contributions: int,
) -> int:
    if total_contributions <= 0 or contribution <= 0:
        return 0
    return total_bayld * contribution // total_contributions


@dataclasses.dataclass(frozen=True)
class ReiveReward:
    player_id: str
    bayld: int
    participation_tokens: int


@dataclasses.dataclass
class ReiveSession:
    boss: Wildskeeper
    contributions: dict[str, int] = dataclasses.field(default_factory=dict)
    resolved: bool = False

    @property
    def participants(self) -> tuple[str, ...]:
        return tuple(self.contributions.keys())

    @property
    def total_contributions(self) -> int:
        return sum(self.contributions.values())

    def add_contribution(
        self, *, player_id: str, damage: int = 0, healing: int = 0,
    ) -> bool:
        if self.resolved:
            return False
        if len(self.participants) >= MAX_PARTICIPANTS \
                and player_id not in self.contributions:
            return False
        weight = damage + healing * 2     # heals weight 2x
        if weight <= 0:
            return False
        self.contributions[player_id] = (
            self.contributions.get(player_id, 0) + weight
        )
        return True

    def resolve(self) -> dict[str, ReiveReward]:
        if self.resolved:
            return {}
        entry = wildskeeper_entry(self.boss)
        if entry is None:
            self.resolved = True
            return {}
        out: dict[str, ReiveReward] = {}
        total = self.total_contributions
        for pid, contrib in self.contributions.items():
            bayld = bayld_share(
                total_bayld=entry.bayld_pool,
                contribution=contrib,
                total_contributions=total,
            )
            tokens = max(1, contrib // 100)
            tokens = min(tokens, PARTICIPATION_TOKEN_BASE)
            out[pid] = ReiveReward(
                player_id=pid, bayld=bayld,
                participation_tokens=tokens,
            )
        self.resolved = True
        return out


__all__ = [
    "MAX_PARTICIPANTS", "BAYLD_BASE_POOL",
    "PARTICIPATION_TOKEN_BASE",
    "Wildskeeper", "WildskeeperEntry",
    "WILDSKEEPER_CATALOG", "WK_BY_BOSS",
    "wildskeeper_entry", "bayld_share",
    "ReiveReward", "ReiveSession",
]
