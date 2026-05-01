"""Level-band-matching spawn pool for fomors.

Per the design doc rule: a fomor only spawns in zones that match its
level band. As a fomor levels up (kill counts), its spawn pool widens.

Practical level bands per FFXI:
    1-15   -> Ronfaure, Gustaberg, Sarutabaruta, Ghelsba Outpost, etc.
    16-30  -> Konschtat, La Theine, Tahrongi, Buburimu, Mhaura/Selbina
    25-42  -> Pashhow, Rolanberry, Meriphataud, Jugner
    35-55  -> Crawlers' Nest, Garlaige, Eldieme, Ranguemont
    50-70  -> Boyahda, Quicksand Caves, Onzozo, Korroloka
    65-85  -> Castle Zvahl, Castle Oztroja, Toraimarai
    80-99  -> Sky / Sea / Dynamis / Promyvion / Limbus / Salvage

A leveled-up fomor unlocks ALL bands at-or-below its level — a level-50
fomor can spawn in Pashhow (28-42 band) or Crawlers' (35-55).
"""
from __future__ import annotations

import dataclasses


# Each entry: zone_name -> (min_level, max_level)
ZONE_LEVEL_BANDS: dict[str, tuple[int, int]] = {
    # Tier 1 - starter
    "ronfaure_east": (1, 15),
    "ronfaure_west": (1, 15),
    "gustaberg_north": (1, 15),
    "gustaberg_south": (1, 15),
    "sarutabaruta_east": (1, 15),
    "sarutabaruta_west": (1, 15),
    "ghelsba_outpost": (5, 18),
    # Tier 2 - low
    "konschtat_highlands": (16, 30),
    "la_theine_plateau": (16, 30),
    "tahrongi_canyon": (16, 30),
    "buburimu_peninsula": (16, 30),
    # Tier 3 - mid
    "pashhow_marshlands": (25, 42),
    "rolanberry_fields": (25, 42),
    "meriphataud_mountains": (25, 42),
    "jugner_forest": (25, 42),
    # Tier 4 - upper-mid
    "crawlers_nest": (35, 55),
    "garlaige_citadel": (35, 55),
    "eldieme_necropolis": (35, 55),
    "ranguemont_pass": (35, 55),
    # Tier 5 - high
    "boyahda_tree": (50, 70),
    "quicksand_caves": (50, 70),
    "onzozo": (50, 70),
    "korroloka_tunnel": (50, 70),
    # Tier 6 - upper
    "castle_zvahl_baileys": (65, 85),
    "castle_oztroja": (65, 85),
    "toraimarai_canal": (65, 85),
    # Tier 7 - apex
    "sky_ruaun": (80, 99),
    "sea_ahriman": (80, 99),
    "dynamis_jeuno": (80, 99),
    "promyvion_holla": (80, 99),
    "limbus_temenos": (80, 99),
    "salvage_zhayolm": (80, 99),
}


@dataclasses.dataclass
class SpawnPool:
    """Picks a list of zones a fomor of a given level can spawn in.

    A 'leveled-up' fomor (one that's gained levels through accumulated
    kills) can spawn in any band whose min_level is <= the fomor's
    current level. A 'fresh' fomor stays inside its base band only —
    this is what keeps starter zones starter-only.
    """

    bands: dict[str, tuple[int, int]] = dataclasses.field(
        default_factory=lambda: dict(ZONE_LEVEL_BANDS))

    def zones_for_level(self, fomor_level: int,
                         *, leveled_up: bool = False) -> list[str]:
        """Return the zones the fomor is eligible to spawn in.

        leveled_up=False (default): only zones whose band CONTAINS the
        fomor level. Strict matching for fresh fomors.
        leveled_up=True: any zone whose band starts at-or-below the
        fomor level. Lets old fomors range wider.
        """
        out: list[str] = []
        for zone, (lo, hi) in self.bands.items():
            if leveled_up:
                if lo <= fomor_level:
                    out.append(zone)
            else:
                if lo <= fomor_level <= hi:
                    out.append(zone)
        return sorted(out)

    def is_zone_eligible(self, zone: str, fomor_level: int,
                          *, leveled_up: bool = False) -> bool:
        band = self.bands.get(zone)
        if band is None:
            return False
        lo, hi = band
        if leveled_up:
            return lo <= fomor_level
        return lo <= fomor_level <= hi
