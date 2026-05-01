"""TrustPvpGuard — despawn on PvP attack.

Per the user direction: 'Trusts cannot be used for any type of pvp.
They would just despawn if you attack another player with trusts
out.'

This module is a small observer that the combat pipeline calls when
the owner of a trust party launches an attack at another player.
The trust party is despawned in full.

We also block the inverse: an outlaw player who tries to summon a
trust while in a contested PvP zone gets blocked at summon-time.
"""
from __future__ import annotations

import typing as t

from .party import DespawnReason, TrustParty


# Zones where trust summons are blocked outright (PvP arenas, etc.)
NO_TRUST_ZONES = frozenset({
    "ballista_jugner",
    "ballista_meriphataud",
    "ballista_pashhow",
    "brenner_arena",
    "conflict_arena",
})


class TrustPvpGuard:
    """Owner-attack-player observer + summon-block helper."""

    def notify_owner_attacked_player(self,
                                       party: TrustParty,
                                       *,
                                       target_player_id: str,
                                       now: float) -> list[str]:
        """The owner just landed an attack on another player. If
        any trusts are summoned, despawn them all and return the
        list of removed trust ids."""
        if party.is_empty():
            return []
        return party.despawn_all(DespawnReason.OWNER_ATTACKED_PLAYER)

    def can_summon_in_zone(self, zone: str) -> bool:
        """Block trust summons in PvP arenas regardless of intent."""
        return zone.lower() not in NO_TRUST_ZONES

    def notify_zoned_into_pvp_area(self,
                                     party: TrustParty,
                                     *,
                                     zone: str) -> list[str]:
        """Player just zone-lined into a PvP arena while trusts were
        summoned — despawn them all."""
        if self.can_summon_in_zone(zone):
            return []
        if party.is_empty():
            return []
        return party.despawn_all(DespawnReason.ZONED_INTO_PVP_AREA)
