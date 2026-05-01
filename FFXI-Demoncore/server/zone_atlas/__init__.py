"""Zone atlas — canonical FFXI zone graph.

Encodes a representative subset of FFXI zones with adjacencies,
zone tier (per COMBAT_TEMPO.md ZoneTier), native mob families,
and town-safety flag. Used by:
    - encounter_gen for spawn composition
    - hardcore_death.boss_assist for adjacent_zone_ids lookup
    - siege_system for nation perimeter
    - terrain_weather for default environment

The graph is undirected (adjacency is symmetric).
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ZoneTier(str, enum.Enum):
    """Mirrors combat_tempo.zone_density.ZoneTier."""
    NEWBIE = "newbie"
    MID_TIER = "mid_tier"
    HIGH_TIER = "high_tier"
    END_GAME = "end_game"
    NATION_CITY = "nation_city"
    SAFE_HAVEN = "safe_haven"


@dataclasses.dataclass(frozen=True)
class Zone:
    """One zone in the atlas."""
    zone_id: str
    label: str
    tier: ZoneTier
    nation: str                  # 'bastok' / 'sandy' / 'windy' / 'neutral'
    native_families: tuple[str, ...]    # mob_class_library family ids
    is_town_safe: bool = False
    is_outpost: bool = False


# Representative atlas — covers the big-name zones touched by other
# modules. Not exhaustive (FFXI has hundreds); designers add as zones
# come online.
_ZONE_TABLE: tuple[Zone, ...] = (
    # Bastok ring
    Zone("bastok_mines", "Bastok Mines", ZoneTier.NATION_CITY,
         "bastok", (), is_town_safe=True),
    Zone("bastok_markets", "Bastok Markets", ZoneTier.NATION_CITY,
         "bastok", (), is_town_safe=True),
    Zone("bastok_metalworks", "Bastok Metalworks",
         ZoneTier.NATION_CITY, "bastok", (), is_town_safe=True),
    Zone("south_gustaberg", "South Gustaberg", ZoneTier.NEWBIE,
         "bastok", ("goblin", "orc", "bee")),
    Zone("north_gustaberg", "North Gustaberg", ZoneTier.NEWBIE,
         "bastok", ("goblin", "orc")),
    Zone("zeruhn_mines", "Zeruhn Mines", ZoneTier.NEWBIE,
         "bastok", ("bee", "bug")),
    Zone("dangruf_wadi", "Dangruf Wadi", ZoneTier.MID_TIER,
         "bastok", ("goblin", "bug")),
    Zone("korroloka_tunnel", "Korroloka Tunnel", ZoneTier.MID_TIER,
         "bastok", ("slime", "bug", "skeleton")),
    Zone("pashhow_marshlands", "Pashhow Marshlands",
         ZoneTier.MID_TIER, "bastok", ("goblin", "skeleton")),
    Zone("rolanberry_fields", "Rolanberry Fields",
         ZoneTier.MID_TIER, "bastok", ("goblin", "bee")),
    Zone("crawlers_nest", "Crawlers' Nest", ZoneTier.MID_TIER,
         "bastok", ("bug",)),
    Zone("beadeaux", "Beadeaux", ZoneTier.HIGH_TIER,
         "bastok", ("quadav",)),

    # Sandy ring
    Zone("south_sandoria", "Southern San d'Oria",
         ZoneTier.NATION_CITY, "sandy", (), is_town_safe=True),
    Zone("north_sandoria", "Northern San d'Oria",
         ZoneTier.NATION_CITY, "sandy", (), is_town_safe=True),
    Zone("east_ronfaure", "East Ronfaure", ZoneTier.NEWBIE,
         "sandy", ("orc", "goblin")),
    Zone("west_ronfaure", "West Ronfaure", ZoneTier.NEWBIE,
         "sandy", ("orc", "goblin")),
    Zone("la_theine_plateau", "La Theine Plateau", ZoneTier.MID_TIER,
         "sandy", ("orc", "goblin")),
    Zone("jugner_forest", "Jugner Forest", ZoneTier.MID_TIER,
         "sandy", ("orc",)),
    Zone("davoi", "Davoi", ZoneTier.HIGH_TIER,
         "sandy", ("orc",)),

    # Windy ring
    Zone("windurst_woods", "Windurst Woods", ZoneTier.NATION_CITY,
         "windy", (), is_town_safe=True),
    Zone("windurst_walls", "Windurst Walls", ZoneTier.NATION_CITY,
         "windy", (), is_town_safe=True),
    Zone("east_sarutabaruta", "East Sarutabaruta", ZoneTier.NEWBIE,
         "windy", ("yagudo", "goblin")),
    Zone("west_sarutabaruta", "West Sarutabaruta", ZoneTier.NEWBIE,
         "windy", ("yagudo", "goblin")),
    Zone("tahrongi_canyon", "Tahrongi Canyon", ZoneTier.MID_TIER,
         "windy", ("yagudo",)),
    Zone("buburimu_peninsula", "Buburimu Peninsula",
         ZoneTier.MID_TIER, "windy", ("yagudo", "bee")),
    Zone("yhoator_jungle", "Yhoator Jungle", ZoneTier.MID_TIER,
         "windy", ("yagudo", "tonberry")),
    Zone("castle_oztroja", "Castle Oztroja", ZoneTier.HIGH_TIER,
         "windy", ("yagudo",)),

    # Jeuno + neutral hubs
    Zone("lower_jeuno", "Lower Jeuno", ZoneTier.NATION_CITY,
         "neutral", (), is_town_safe=True),
    Zone("upper_jeuno", "Upper Jeuno", ZoneTier.NATION_CITY,
         "neutral", (), is_town_safe=True),
    Zone("port_jeuno", "Port Jeuno", ZoneTier.NATION_CITY,
         "neutral", (), is_town_safe=True),
    Zone("ru_lude_gardens", "Ru'Lude Gardens", ZoneTier.NATION_CITY,
         "neutral", (), is_town_safe=True),

    # Endgame
    Zone("dynamis_bastok", "Dynamis - Bastok", ZoneTier.END_GAME,
         "neutral", ("goblin", "skeleton")),
    Zone("dynamis_jeuno", "Dynamis - Jeuno", ZoneTier.END_GAME,
         "neutral", ("goblin",)),
    Zone("sky", "Sky (Tu'Lia)", ZoneTier.END_GAME,
         "neutral", ("dragon", "demon")),
    Zone("sea", "Sea (Al'Taieu)", ZoneTier.END_GAME,
         "neutral", ("demon",)),
    Zone("limbus", "Limbus", ZoneTier.END_GAME,
         "neutral", ("demon",)),
    Zone("phomiuna_aqueducts", "Phomiuna Aqueducts",
         ZoneTier.HIGH_TIER, "neutral", ("naga",)),

    # Aht Urhgan
    Zone("aht_urhgan_whitegate", "Aht Urhgan Whitegate",
         ZoneTier.NATION_CITY, "aht_urhgan", (), is_town_safe=True),
    Zone("bhaflau_thickets", "Bhaflau Thickets", ZoneTier.MID_TIER,
         "aht_urhgan", ("bee", "bug")),

    # Outpost / waypoint
    Zone("selbina", "Selbina", ZoneTier.SAFE_HAVEN,
         "neutral", (), is_town_safe=True, is_outpost=True),
    Zone("mhaura", "Mhaura", ZoneTier.SAFE_HAVEN,
         "neutral", (), is_town_safe=True, is_outpost=True),
    Zone("norg", "Norg", ZoneTier.SAFE_HAVEN,
         "neutral", (), is_town_safe=True, is_outpost=True),
)


# Adjacency edges as (zone_a, zone_b) tuples. The atlas registers
# both directions automatically.
_EDGES: tuple[tuple[str, str], ...] = (
    # Bastok ring
    ("bastok_mines", "bastok_markets"),
    ("bastok_markets", "bastok_metalworks"),
    ("bastok_mines", "south_gustaberg"),
    ("bastok_mines", "zeruhn_mines"),
    ("south_gustaberg", "north_gustaberg"),
    ("north_gustaberg", "dangruf_wadi"),
    ("south_gustaberg", "korroloka_tunnel"),
    ("korroloka_tunnel", "pashhow_marshlands"),
    ("pashhow_marshlands", "rolanberry_fields"),
    ("rolanberry_fields", "crawlers_nest"),
    ("pashhow_marshlands", "beadeaux"),
    # Sandy ring
    ("south_sandoria", "north_sandoria"),
    ("south_sandoria", "east_ronfaure"),
    ("south_sandoria", "west_ronfaure"),
    ("east_ronfaure", "la_theine_plateau"),
    ("west_ronfaure", "la_theine_plateau"),
    ("la_theine_plateau", "jugner_forest"),
    ("jugner_forest", "davoi"),
    # Windy ring
    ("windurst_woods", "windurst_walls"),
    ("windurst_woods", "east_sarutabaruta"),
    ("windurst_woods", "west_sarutabaruta"),
    ("east_sarutabaruta", "tahrongi_canyon"),
    ("west_sarutabaruta", "tahrongi_canyon"),
    ("tahrongi_canyon", "buburimu_peninsula"),
    ("buburimu_peninsula", "yhoator_jungle"),
    ("yhoator_jungle", "castle_oztroja"),
    # Jeuno hub
    ("lower_jeuno", "upper_jeuno"),
    ("upper_jeuno", "port_jeuno"),
    ("upper_jeuno", "ru_lude_gardens"),
    ("rolanberry_fields", "lower_jeuno"),
    ("jugner_forest", "lower_jeuno"),
    ("buburimu_peninsula", "lower_jeuno"),
    # Endgame ports
    ("ru_lude_gardens", "dynamis_jeuno"),
    ("bastok_metalworks", "dynamis_bastok"),
    ("port_jeuno", "sky"),
    ("port_jeuno", "sea"),
    ("ru_lude_gardens", "limbus"),
    # Outposts
    ("buburimu_peninsula", "mhaura"),
    ("port_jeuno", "selbina"),
    ("yhoator_jungle", "norg"),
    ("phomiuna_aqueducts", "lower_jeuno"),
    # Aht Urhgan
    ("aht_urhgan_whitegate", "bhaflau_thickets"),
    ("port_jeuno", "aht_urhgan_whitegate"),
)


# Public lookups built once at import.
ZONES: dict[str, Zone] = {z.zone_id: z for z in _ZONE_TABLE}
_ADJ: dict[str, set[str]] = {z.zone_id: set() for z in _ZONE_TABLE}
for _a, _b in _EDGES:
    if _a in _ADJ and _b in _ADJ:
        _ADJ[_a].add(_b)
        _ADJ[_b].add(_a)


def get_zone(zone_id: str) -> Zone:
    return ZONES[zone_id]


def is_known_zone(zone_id: str) -> bool:
    return zone_id in ZONES


def adjacent_zones(zone_id: str) -> tuple[str, ...]:
    """Return zone_ids directly connected to this zone."""
    return tuple(sorted(_ADJ.get(zone_id, set())))


def zones_in_tier(tier: ZoneTier) -> tuple[Zone, ...]:
    return tuple(z for z in ZONES.values() if z.tier == tier)


def zones_in_nation(nation: str) -> tuple[Zone, ...]:
    return tuple(z for z in ZONES.values() if z.nation == nation)


def zones_with_family(family_id: str) -> tuple[Zone, ...]:
    """Reverse lookup: which zones natively spawn this family?"""
    return tuple(z for z in ZONES.values()
                  if family_id in z.native_families)


def shortest_path(*, src: str, dst: str) -> t.Optional[tuple[str, ...]]:
    """BFS shortest path between two zones. Returns None if no
    path exists (or either zone is unknown)."""
    if src not in ZONES or dst not in ZONES:
        return None
    if src == dst:
        return (src,)
    visited = {src}
    parent: dict[str, str] = {}
    queue: list[str] = [src]
    while queue:
        node = queue.pop(0)
        for nb in _ADJ.get(node, ()):
            if nb in visited:
                continue
            visited.add(nb)
            parent[nb] = node
            if nb == dst:
                # Reconstruct
                path: list[str] = [dst]
                while path[-1] != src:
                    path.append(parent[path[-1]])
                return tuple(reversed(path))
            queue.append(nb)
    return None


def zone_count() -> int:
    return len(ZONES)


def edge_count() -> int:
    """Each undirected edge is one entry in _EDGES (counted once)."""
    return len(_EDGES)


__all__ = [
    "ZoneTier", "Zone", "ZONES",
    "get_zone", "is_known_zone",
    "adjacent_zones", "zones_in_tier", "zones_in_nation",
    "zones_with_family", "shortest_path",
    "zone_count", "edge_count",
]
