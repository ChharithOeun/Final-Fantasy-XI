"""Expansion pass — entitlement gates for zones/missions.

Canonical FFXI expansion order:
* base game (San d'Oria/Bastok/Windurst/Jeuno/Norg/Tavnazia)
* RoZ — Rise of the Zilart
* CoP — Chains of Promathia
* ToAU — Treasures of Aht Urhgan
* WotG — Wings of the Goddess
* SoA — Seekers of Adoulin
* SoV — Seekers of the City of Adoulin Vana'diel (engine update)

Each expansion owns a set of zones and a mission storyline.
PlayerExpansionPass tracks which expansions a player owns. The
gates are pure functions: pass them the player's entitlements
and ask "can I enter zone X" or "can I start mission Y."

Public surface
--------------
    Expansion enum
    EXPANSION_LABELS
    PlayerExpansionPass
        .grant(expansion) / .revoke(expansion)
        .owns(expansion) / .owns_all(*expansions)
    can_enter_zone(zone_id, pass) -> bool
    can_start_mission(mission_id, pass) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Expansion(str, enum.Enum):
    BASE = "base"
    ROZ = "roz"
    COP = "cop"
    TOAU = "toau"
    WOTG = "wotg"
    SOA = "soa"
    SOV = "sov"


EXPANSION_LABELS: dict[Expansion, str] = {
    Expansion.BASE: "Final Fantasy XI",
    Expansion.ROZ: "Rise of the Zilart",
    Expansion.COP: "Chains of Promathia",
    Expansion.TOAU: "Treasures of Aht Urhgan",
    Expansion.WOTG: "Wings of the Goddess",
    Expansion.SOA: "Seekers of Adoulin",
    Expansion.SOV: "Seekers of the City of Adoulin Vana'diel",
}


# Zone-id -> required expansion. (sample slice, not exhaustive)
_ZONE_EXPANSION: dict[str, Expansion] = {
    # Base zones
    "northern_sandoria": Expansion.BASE,
    "bastok_markets": Expansion.BASE,
    "windurst_woods": Expansion.BASE,
    "lower_jeuno": Expansion.BASE,
    # RoZ
    "tu_lia": Expansion.ROZ,
    "ruaun_gardens": Expansion.ROZ,
    "ve_lugannon_palace": Expansion.ROZ,
    # CoP
    "tavnazian_safehold": Expansion.COP,
    "promyvion_holla": Expansion.COP,
    "promyvion_dem": Expansion.COP,
    "promyvion_mea": Expansion.COP,
    "al_taieu": Expansion.COP,
    # ToAU
    "aht_urhgan_whitegate": Expansion.TOAU,
    "alzadaal_undersea_ruins": Expansion.TOAU,
    "halvung": Expansion.TOAU,
    # WotG
    "southern_sandoria_s": Expansion.WOTG,
    "bastok_markets_s": Expansion.WOTG,
    "windurst_waters_s": Expansion.WOTG,
    "abyssea_la_theine": Expansion.WOTG,   # late-WotG add-on
    # SoA
    "western_adoulin": Expansion.SOA,
    "eastern_adoulin": Expansion.SOA,
    "yorcia_weald": Expansion.SOA,
    # SoV
    "outer_ra_kaznar": Expansion.SOV,
    "reisenjima": Expansion.SOV,
}


# Mission-id -> required expansion.
_MISSION_EXPANSION: dict[str, Expansion] = {
    "sandy_mission_1": Expansion.BASE,
    "bastok_mission_1": Expansion.BASE,
    "windy_mission_1": Expansion.BASE,
    "roz_mission_1": Expansion.ROZ,
    "cop_mission_1_recollection": Expansion.COP,
    "toau_mission_1": Expansion.TOAU,
    "wotg_mission_1": Expansion.WOTG,
    "soa_mission_1": Expansion.SOA,
    "sov_mission_1": Expansion.SOV,
}


@dataclasses.dataclass
class PlayerExpansionPass:
    player_id: str
    _owned: set[Expansion] = dataclasses.field(
        default_factory=lambda: {Expansion.BASE},
    )

    @property
    def owned(self) -> frozenset[Expansion]:
        return frozenset(self._owned)

    def grant(self, *, expansion: Expansion) -> bool:
        if expansion in self._owned:
            return False
        self._owned.add(expansion)
        return True

    def revoke(self, *, expansion: Expansion) -> bool:
        if expansion == Expansion.BASE:
            # Can't revoke base game ownership
            return False
        if expansion not in self._owned:
            return False
        self._owned.remove(expansion)
        return True

    def owns(self, expansion: Expansion) -> bool:
        return expansion in self._owned

    def owns_all(self, *expansions: Expansion) -> bool:
        return all(e in self._owned for e in expansions)


def can_enter_zone(*, zone_id: str,
                    player_pass: PlayerExpansionPass) -> bool:
    required = _ZONE_EXPANSION.get(zone_id)
    if required is None:
        # Unknown zone — default-allow (assume base game)
        return True
    return player_pass.owns(required)


def can_start_mission(*, mission_id: str,
                       player_pass: PlayerExpansionPass) -> bool:
    required = _MISSION_EXPANSION.get(mission_id)
    if required is None:
        return False
    return player_pass.owns(required)


__all__ = [
    "Expansion", "EXPANSION_LABELS",
    "PlayerExpansionPass",
    "can_enter_zone", "can_start_mission",
]
