"""Beastman trust NPCs — beastman-side Trust roster.

Just as humes summon Trusts (Shantotto, Volker, etc), beastman
players summon their own pantheon of allied beastmen. Each
race has a roster of canonical heroes / dignitaries who can
be called as Trusts after completing the unlock quest tied to
that NPC.

Each Trust has a JOB ROLE (TANK / HEALER / DPS_MELEE /
DPS_RANGED / SUPPORT) and a flavor description. Summoning is
gated on having unlocked the Trust through its quest.

Public surface
--------------
    TrustRole enum
    TrustNpcDef dataclass
    TrustUnlockResult dataclass
    BeastmanTrustNpcs
        .register_trust(trust_id, race, role, label, unlock_quest)
        .unlock(player_id, trust_id)
        .summon(player_id, trust_id) -> bool
        .roster_for(race) -> tuple[TrustNpcDef]
        .available_for(player_id, race) -> tuple[TrustNpcDef]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class TrustRole(str, enum.Enum):
    TANK = "tank"
    HEALER = "healer"
    DPS_MELEE = "dps_melee"
    DPS_RANGED = "dps_ranged"
    SUPPORT = "support"


@dataclasses.dataclass(frozen=True)
class TrustNpcDef:
    trust_id: str
    race: BeastmanRace
    role: TrustRole
    label: str
    unlock_quest_id: str
    flavor: str = ""


@dataclasses.dataclass(frozen=True)
class TrustUnlockResult:
    accepted: bool
    trust_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanTrustNpcs:
    _trusts: dict[str, TrustNpcDef] = dataclasses.field(
        default_factory=dict,
    )
    _unlocked: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )

    def register_trust(
        self, *, trust_id: str,
        race: BeastmanRace,
        role: TrustRole,
        label: str,
        unlock_quest_id: str,
        flavor: str = "",
    ) -> t.Optional[TrustNpcDef]:
        if trust_id in self._trusts:
            return None
        if not label or not unlock_quest_id:
            return None
        npc = TrustNpcDef(
            trust_id=trust_id, race=race, role=role,
            label=label, unlock_quest_id=unlock_quest_id,
            flavor=flavor,
        )
        self._trusts[trust_id] = npc
        return npc

    def get(self, trust_id: str) -> t.Optional[TrustNpcDef]:
        return self._trusts.get(trust_id)

    def unlock(
        self, *, player_id: str, trust_id: str,
    ) -> TrustUnlockResult:
        npc = self._trusts.get(trust_id)
        if npc is None:
            return TrustUnlockResult(
                False, trust_id=trust_id,
                reason="no such trust",
            )
        s = self._unlocked.setdefault(player_id, set())
        if trust_id in s:
            return TrustUnlockResult(
                False, trust_id=trust_id,
                reason="already unlocked",
            )
        s.add(trust_id)
        return TrustUnlockResult(
            accepted=True, trust_id=trust_id,
        )

    def has_unlocked(
        self, *, player_id: str, trust_id: str,
    ) -> bool:
        return trust_id in self._unlocked.get(
            player_id, set(),
        )

    def summon(
        self, *, player_id: str, trust_id: str,
    ) -> bool:
        if trust_id not in self._trusts:
            return False
        return self.has_unlocked(
            player_id=player_id, trust_id=trust_id,
        )

    def roster_for(
        self, *, race: BeastmanRace,
    ) -> tuple[TrustNpcDef, ...]:
        rows = [
            t for t in self._trusts.values()
            if t.race == race
        ]
        rows.sort(key=lambda x: x.trust_id)
        return tuple(rows)

    def available_for(
        self, *, player_id: str,
        race: BeastmanRace,
    ) -> tuple[TrustNpcDef, ...]:
        s = self._unlocked.get(player_id, set())
        rows = [
            t for t in self._trusts.values()
            if t.race == race and t.trust_id in s
        ]
        rows.sort(key=lambda x: x.trust_id)
        return tuple(rows)

    def total_trusts(self) -> int:
        return len(self._trusts)

    def total_unlocks(
        self, *, player_id: str,
    ) -> int:
        return len(self._unlocked.get(player_id, set()))


__all__ = [
    "TrustRole",
    "TrustNpcDef", "TrustUnlockResult",
    "BeastmanTrustNpcs",
]
