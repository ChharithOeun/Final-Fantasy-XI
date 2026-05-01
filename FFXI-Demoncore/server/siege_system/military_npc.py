"""Military NPC lifecycle: spawn, kill, XP, 8-hour respawn.

Per the user spec: military NPCs gain XP on the same scale as
players, level up, and die in combat. Respawn timer is 8 hours.
Death doesn't reset progression — they come back at full level.
"""
from __future__ import annotations

import dataclasses
import typing as t


MILITARY_RESPAWN_SECONDS = 8 * 3600   # 8 hours


@dataclasses.dataclass
class MilitaryNpcSnapshot:
    npc_id: str
    nation: str
    role: str
    zone: str
    level: int = 30           # default deploy level
    xp: int = 0
    is_alive: bool = True
    died_at: t.Optional[float] = None
    is_captain: bool = False
    is_flag_bearer: bool = False
    deaths_total: int = 0


class MilitaryNpcManager:
    """Tracks the live + respawning roster of military NPCs."""

    def __init__(self) -> None:
        self._roster: dict[str, MilitaryNpcSnapshot] = {}

    # ------------------------------------------------------------------
    # Roster mutators
    # ------------------------------------------------------------------

    def deploy(self, snapshot: MilitaryNpcSnapshot) -> None:
        self._roster[snapshot.npc_id] = snapshot

    def get(self, npc_id: str) -> t.Optional[MilitaryNpcSnapshot]:
        return self._roster.get(npc_id)

    def notify_killed(self, npc_id: str, *, now: float) -> None:
        npc = self._roster.get(npc_id)
        if npc is None:
            return
        npc.is_alive = False
        npc.died_at = now
        npc.deaths_total += 1

    def grant_xp(self, npc_id: str, *, xp: int) -> int:
        """Add XP, level up if threshold crossed. Returns new level."""
        npc = self._roster.get(npc_id)
        if npc is None or not npc.is_alive:
            return 0
        npc.xp += xp
        # Simple curve: level n requires n * 1000 XP into the level
        while npc.xp >= self._xp_for_level(npc.level + 1) - self._xp_for_level(npc.level):
            cost = (self._xp_for_level(npc.level + 1)
                     - self._xp_for_level(npc.level))
            npc.xp -= cost
            npc.level += 1
        return npc.level

    def respawn_eligible(self, *, now: float) -> list[str]:
        """Return npc_ids whose 8-hour respawn timer has expired.
        Caller is expected to call respawn() to actually bring them back."""
        out = []
        for npc_id, npc in self._roster.items():
            if (not npc.is_alive
                    and npc.died_at is not None
                    and (now - npc.died_at) >= MILITARY_RESPAWN_SECONDS):
                out.append(npc_id)
        return out

    def respawn(self, npc_id: str) -> bool:
        npc = self._roster.get(npc_id)
        if npc is None:
            return False
        npc.is_alive = True
        npc.died_at = None
        return True

    def time_until_respawn(self, npc_id: str, *, now: float) -> float:
        npc = self._roster.get(npc_id)
        if npc is None or npc.is_alive or npc.died_at is None:
            return 0.0
        elapsed = now - npc.died_at
        if elapsed >= MILITARY_RESPAWN_SECONDS:
            return 0.0
        return MILITARY_RESPAWN_SECONDS - elapsed

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def alive_in_zone(self, zone: str) -> list[MilitaryNpcSnapshot]:
        return [n for n in self._roster.values()
                  if n.zone == zone and n.is_alive]

    def squad_effectiveness(self, *, zone: str, nation: str) -> float:
        """Squad effectiveness multiplier in a zone. Drops to 0.9
        when the flag-bearer has died (per the design doc:
        'their death demoralizes the unit; immediate -10% combat
        effectiveness for the squad')."""
        flag_bearer_alive = any(
            n.is_flag_bearer and n.is_alive
            for n in self._roster.values()
            if n.zone == zone and n.nation == nation
        )
        flag_bearer_exists = any(
            n.is_flag_bearer
            for n in self._roster.values()
            if n.zone == zone and n.nation == nation
        )
        if flag_bearer_exists and not flag_bearer_alive:
            return 0.9
        return 1.0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _xp_for_level(level: int) -> int:
        """Cumulative XP required to reach `level`. level n needs sum
        i=1..n-1 of (i * 1000)."""
        if level <= 1:
            return 0
        # 1->2 = 1000, 2->3 = 2000, 3->4 = 3000, ...
        return sum(i * 1000 for i in range(1, level))
