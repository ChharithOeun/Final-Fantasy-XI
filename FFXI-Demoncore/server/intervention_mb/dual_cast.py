"""Dual-cast unlock — 30s parallel-cast slot per spell family.

Per INTERVENTION_MB.md a successful intervention unlocks dual-cast
for that spell family for 30 seconds. The caster can fire two
spells in parallel during the window.

GEO is special: instead of dual-cast, GEO gets `LuopanRadius_Doubled`
for the same duration. We expose this via a separate buff id but
the same manager.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .amplification import SpellFamily


# Doc: 'caster.add_buff("DualCast_Family_X", duration=30s)'
DUAL_CAST_DURATION_SECONDS: float = 30.0


class DualCastBuffId(str, enum.Enum):
    """One id per supported family. GEO is the special case."""
    DUAL_CAST_CURE = "DualCast_Cure"
    DUAL_CAST_ENHANCE = "DualCast_Enhance"
    DUAL_CAST_DEBUFF = "DualCast_Debuff"
    DUAL_CAST_SONG = "DualCast_Song"
    DUAL_CAST_HELIX = "DualCast_Helix"
    LUOPAN_RADIUS_DOUBLED = "LuopanRadius_Doubled"
    TANK_ENMITY_SPIKE = "Tank_Enmity_Spike"


# Mapping from spell family to the buff that gets unlocked.
FAMILY_TO_BUFF: dict[SpellFamily, DualCastBuffId] = {
    SpellFamily.CURE: DualCastBuffId.DUAL_CAST_CURE,
    SpellFamily.CURAGA: DualCastBuffId.DUAL_CAST_CURE,
    SpellFamily.NA_SPELL: DualCastBuffId.DUAL_CAST_CURE,
    SpellFamily.ERASE: DualCastBuffId.DUAL_CAST_CURE,
    SpellFamily.RDM_ENHANCING: DualCastBuffId.DUAL_CAST_ENHANCE,
    SpellFamily.BLM_DEBUFF: DualCastBuffId.DUAL_CAST_DEBUFF,
    SpellFamily.BRD_SONG: DualCastBuffId.DUAL_CAST_SONG,
    SpellFamily.SCH_HELIX: DualCastBuffId.DUAL_CAST_HELIX,
    SpellFamily.GEO_LUOPAN: DualCastBuffId.LUOPAN_RADIUS_DOUBLED,
    SpellFamily.TANK_FLASH: DualCastBuffId.TANK_ENMITY_SPIKE,
}


@dataclasses.dataclass
class DualCastBuff:
    """One active 30s buff."""
    caster_id: str
    buff_id: DualCastBuffId
    expires_at: float

    def is_active(self, *, now: float) -> bool:
        return now < self.expires_at


class DualCastManager:
    """Per-server registry of active dual-cast buffs."""

    def __init__(self) -> None:
        # caster_id -> {buff_id -> DualCastBuff}
        self._buffs: dict[str, dict[DualCastBuffId, DualCastBuff]] = {}

    def grant(self,
                *,
                caster_id: str,
                family: SpellFamily,
                now: float,
                duration_override: t.Optional[float] = None
                ) -> DualCastBuff:
        """Grant the dual-cast buff for `family` to `caster_id`.

        Idempotent: re-granting refreshes the expiry rather than
        stacking.
        """
        if family not in FAMILY_TO_BUFF:
            raise ValueError(f"family {family} has no dual-cast buff")
        duration = duration_override
        if duration is None:
            duration = DUAL_CAST_DURATION_SECONDS
        if duration < 0:
            raise ValueError("duration must be non-negative")
        buff_id = FAMILY_TO_BUFF[family]
        buff = DualCastBuff(
            caster_id=caster_id, buff_id=buff_id,
            expires_at=now + duration,
        )
        self._buffs.setdefault(caster_id, {})[buff_id] = buff
        return buff

    def is_active_for(self,
                          *,
                          caster_id: str,
                          family: SpellFamily,
                          now: float) -> bool:
        if family not in FAMILY_TO_BUFF:
            return False
        buff = self._buffs.get(caster_id, {}).get(FAMILY_TO_BUFF[family])
        return buff is not None and buff.is_active(now=now)

    def active_buffs(self, *, caster_id: str, now: float
                      ) -> set[DualCastBuffId]:
        out: set[DualCastBuffId] = set()
        for buff_id, buff in self._buffs.get(caster_id, {}).items():
            if buff.is_active(now=now):
                out.add(buff_id)
        return out

    def expire_all(self, *, now: float) -> int:
        removed = 0
        for caster_id in list(self._buffs.keys()):
            buffs = self._buffs[caster_id]
            for buff_id in list(buffs.keys()):
                if not buffs[buff_id].is_active(now=now):
                    del buffs[buff_id]
                    removed += 1
            if not buffs:
                del self._buffs[caster_id]
        return removed
