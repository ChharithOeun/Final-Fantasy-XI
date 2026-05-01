"""TrustParty manager — summon / despawn / slot accounting.

Standard FFXI party = 6 members. With the player counted, a max
of 5 trust slots are available. This module owns the live trust
roster per player.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .catalog import TrustSpec


# Standard party size minus the player
MAX_TRUST_SLOTS = 5


class DespawnReason(str, enum.Enum):
    OWNER_REQUEST = "owner_request"
    OWNER_DIED = "owner_died"
    OWNER_LOGGED_OUT = "owner_logged_out"
    OWNER_ATTACKED_PLAYER = "owner_attacked_player"   # PvP guard
    TRUST_DIED = "trust_died"
    DURATION_EXPIRED = "duration_expired"
    ZONED_INTO_PVP_AREA = "zoned_into_pvp_area"


@dataclasses.dataclass
class TrustSnapshot:
    """Per-trust runtime state."""
    trust_id: str
    spec: TrustSpec
    owner_id: str
    level: int
    current_hp: int
    max_hp: int
    current_mp: int = 0
    max_mp: int = 0
    is_alive: bool = True
    target_id: t.Optional[str] = None
    last_action_at: float = 0.0
    summoned_at: float = 0.0
    cooldowns: dict[str, float] = dataclasses.field(default_factory=dict)


class TrustParty:
    """The summoned-trust roster for a single owner."""

    def __init__(self, owner_id: str,
                  *,
                  max_slots: int = MAX_TRUST_SLOTS) -> None:
        self.owner_id = owner_id
        self.max_slots = max_slots
        self._trusts: dict[str, TrustSnapshot] = {}

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def summon(self,
                spec: TrustSpec,
                *,
                owner_level: int,
                now: float,
                outlaw_summoner: bool = False) -> t.Optional[TrustSnapshot]:
        """Summon a trust into the party. Returns the snapshot on
        success; None if blocked (full / outlaw-only / already summoned).
        """
        if not self.can_summon_more():
            return None
        if spec.outlaw_aligned and not outlaw_summoner:
            return None
        if spec.trust_id in self._trusts:
            # Already summoned — refresh in place
            snap = self._trusts[spec.trust_id]
            snap.summoned_at = now
            return snap

        # Trust HP/MP scales with owner level (mirror of retail FFXI
        # scaling — trusts stay relevant as the player levels)
        max_hp = self._scaled_max_hp(spec, owner_level)
        max_mp = self._scaled_max_mp(spec, owner_level)
        snap = TrustSnapshot(
            trust_id=spec.trust_id, spec=spec, owner_id=self.owner_id,
            level=owner_level, max_hp=max_hp, current_hp=max_hp,
            max_mp=max_mp, current_mp=max_mp,
            summoned_at=now,
        )
        self._trusts[spec.trust_id] = snap
        return snap

    def despawn(self, trust_id: str, reason: DespawnReason) -> bool:
        """Remove a single trust. Returns True if removed."""
        return self._trusts.pop(trust_id, None) is not None

    def despawn_all(self, reason: DespawnReason) -> list[str]:
        """Remove every trust — used by the PvP guard, owner death,
        zone changes, etc. Returns the list of removed trust_ids."""
        removed = list(self._trusts.keys())
        self._trusts.clear()
        return removed

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def can_summon_more(self) -> bool:
        return len(self._trusts) < self.max_slots

    def slot_count(self) -> int:
        return self.max_slots - len(self._trusts)

    def is_empty(self) -> bool:
        return not self._trusts

    def trusts(self) -> list[TrustSnapshot]:
        return list(self._trusts.values())

    def has(self, trust_id: str) -> bool:
        return trust_id in self._trusts

    def get(self, trust_id: str) -> t.Optional[TrustSnapshot]:
        return self._trusts.get(trust_id)

    # ------------------------------------------------------------------
    # Internal scaling
    # ------------------------------------------------------------------

    @staticmethod
    def _scaled_max_hp(spec: TrustSpec, owner_level: int) -> int:
        """Per-role base HP × level scaling."""
        from .catalog import TrustRole
        role_base = {
            TrustRole.TANK: 280,
            TrustRole.HEALER: 180,
            TrustRole.MELEE_DPS: 250,
            TrustRole.RANGED_DPS: 220,
            TrustRole.SUPPORT: 200,
            TrustRole.DEBUFFER: 200,
            TrustRole.NUKER: 200,
        }[spec.role]
        # 0 base + role_base * level / 99
        return int(role_base * (owner_level / 30))

    @staticmethod
    def _scaled_max_mp(spec: TrustSpec, owner_level: int) -> int:
        from .catalog import TrustRole
        role_base = {
            TrustRole.TANK: 60,
            TrustRole.HEALER: 380,
            TrustRole.MELEE_DPS: 30,
            TrustRole.RANGED_DPS: 40,
            TrustRole.SUPPORT: 240,
            TrustRole.DEBUFFER: 200,
            TrustRole.NUKER: 320,
        }[spec.role]
        return int(role_base * (owner_level / 30))
