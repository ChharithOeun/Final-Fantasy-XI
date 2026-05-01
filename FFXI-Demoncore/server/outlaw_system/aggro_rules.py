"""Outlaw-aware aggro decisions.

Per PVP_GLOBAL_OUTLAWS.md aggro table:

| Zone                     | Outlaw treatment                                  | Citizen treatment       |
|--------------------------|---------------------------------------------------|-------------------------|
| Bastok / Sandy / Windy / | Aggroed by all guards + bounty hunters            | Safe                    |
|   Jeuno                  |                                                   |                         |
| Whitegate                | Aggroed by salaheem mercs + Salahem-aligned NPCs  | Safe                    |
| Norg / Selbina / Mhaura  | Safe                                              | Vulnerable to other PCs |
| Open zones               | Open season — beastmen/NPCs/players/mobs all aggro | Standard                |
| Beastman strongholds     | Beastmen still aggro (you're still a hume); other | Standard hostile        |
|                           outlaws within the stronghold tribe might shelter   |                         |
|                           you — case by case                                  |                         |

This module is a small pure-function rule engine. The orchestrator
asks "should I aggro this target?" and we answer yes/no based on the
zone, the entity's faction, and the target's outlaw status.
"""
from __future__ import annotations

import enum
import typing as t

from .bounty import (
    FactionRace,
    OUTLAW_SAFE_HAVENS,
    OutlawStatus,
)


GATED_NATION_CITIES = frozenset({"bastok", "sandoria", "windurst", "jeuno"})
WHITEGATE_ZONES = frozenset({"whitegate", "ahturhgan"})
BEASTMAN_STRONGHOLDS_BY_RACE = {
    "davoi": FactionRace.ORC,
    "beadeaux": FactionRace.QUADAV,
    "castle_oztroja": FactionRace.YAGUDO,
    "giddeus": FactionRace.YAGUDO,
}


class ZoneType(str, enum.Enum):
    NATION_CITY = "nation_city"
    WHITEGATE = "whitegate"
    SAFE_HAVEN = "safe_haven"
    OPEN_WORLD = "open_world"
    BEASTMAN_STRONGHOLD = "beastman_stronghold"


def classify_zone(zone: str) -> tuple[ZoneType, t.Optional[FactionRace]]:
    """Classify a zone for aggro purposes. Returns the zone type and,
    for beastman strongholds, the dominant race. Defaults to OPEN_WORLD
    for unknown zones."""
    z = zone.lower()
    if z in OUTLAW_SAFE_HAVENS:
        return ZoneType.SAFE_HAVEN, None
    if z in GATED_NATION_CITIES:
        return ZoneType.NATION_CITY, None
    if z in WHITEGATE_ZONES:
        return ZoneType.WHITEGATE, None
    for stronghold, race in BEASTMAN_STRONGHOLDS_BY_RACE.items():
        if stronghold in z:
            return ZoneType.BEASTMAN_STRONGHOLD, race
    return ZoneType.OPEN_WORLD, None


class OutlawAggroRules:
    """Pure-function rule engine for outlaw aggro decisions."""

    def should_npc_aggro(self,
                          *,
                          zone: str,
                          npc_faction: FactionRace,
                          npc_role: str,                  # "guard" / "civilian" / "merc" / "tribe"
                          target_status: OutlawStatus,
                          target_race: FactionRace) -> bool:
        """Should `npc` aggro `target`? Captures the zone-by-zone
        rules from the design doc."""
        zone_type, dominant_race = classify_zone(zone)

        # 1. Safe havens: no faction is hostile here. PvP is permitted
        #    (other rules), but town factions don't aggro.
        if zone_type == ZoneType.SAFE_HAVEN:
            return False

        # 2. Nation cities: guards aggro outlaws on sight.
        if zone_type == ZoneType.NATION_CITY:
            if target_status != OutlawStatus.FLAGGED:
                return False
            if npc_role in ("guard", "merc"):
                return True
            # Civilians don't aggro themselves; they just stop talking
            return False

        # 3. Whitegate: salaheem mercs aggro outlaws, regular vendors
        #    don't.
        if zone_type == ZoneType.WHITEGATE:
            if target_status != OutlawStatus.FLAGGED:
                return False
            if npc_role in ("merc", "guard"):
                return True
            return False

        # 4. Beastman strongholds: beastmen still aggro the target if
        #    target is a different race (the standard cross-race aggro
        #    they always have). They additionally aggro outlaws of
        #    their OWN race who haven't been sheltered (we model that
        #    as: same-race outlaw is NOT auto-sheltered; sheltering is
        #    a per-quest flag).
        if zone_type == ZoneType.BEASTMAN_STRONGHOLD:
            assert dominant_race is not None
            if target_race != dominant_race:
                # Standard cross-race aggro
                return True
            # Same race as the stronghold: aggro only if outlaw and
            # not sheltered (sheltering is per-quest; default off)
            return target_status == OutlawStatus.FLAGGED

        # 5. Open world: open season. NPCs of any role aggro outlaws.
        #    Regular cross-race aggro for citizens applies normally
        #    (handled by the standard aggro_system module, not here).
        if target_status == OutlawStatus.FLAGGED:
            return True
        return False

    def is_safe_zone_line_target(self,
                                   *,
                                   target_zone: str,
                                   actor_in_combat: bool) -> bool:
        """Anti-mid-fight-escape: a player in combat can't zone-line
        into a safe haven. They have to disengage first."""
        zone_type, _ = classify_zone(target_zone)
        if zone_type != ZoneType.SAFE_HAVEN:
            return True   # any non-safe-haven zone is a normal zoneline
        return not actor_in_combat
