"""Flagship designation — one ship per crew gets the flag.

A crew can designate ONE ship in their fleet as the FLAGSHIP.
The flagship gets STAT BUFFS that the rest of the fleet
doesn't, and the captain's gear bonuses (gear_augment etc.)
apply only to the flagship.

Flagship buffs:
  +20% hp_max
  +5 crew_skill (caps after pirate_crew_charter skill-cap rules)
  +10% damage_resist
  ALWAYS_KEEP_AS_PRIZE — prize_court can't scuttle it on
                         capture; if your fleet is full,
                         enemy must scuttle one of THEIR
                         own ships first

Designation rules:
  * Only the captain can designate
  * Only one flagship per crew at a time
  * Re-designating COSTS 30 minutes of cooldown (anti-greif)
  * If the flagship sinks, the slot resets to UNDESIGNATED;
    no automatic promotion

Public surface
--------------
    DesignationResult dataclass
    FlagshipDesignation
        .designate(charter_id, captain_id, ship_id, now_seconds)
        .undesignate(charter_id, captain_id, now_seconds)
        .flagship_for(charter_id) -> ship_id or None
        .buffs_for(ship_id, charter_id) -> FlagshipBuffs
"""
from __future__ import annotations

import dataclasses
import typing as t


HP_MAX_BONUS_PCT = 20
CREW_SKILL_BONUS = 5
DAMAGE_RESIST_BONUS_PCT = 10
REDESIGNATE_COOLDOWN_SECONDS = 30 * 60


@dataclasses.dataclass(frozen=True)
class FlagshipBuffs:
    is_flagship: bool
    hp_max_bonus_pct: int = 0
    crew_skill_bonus: int = 0
    damage_resist_bonus_pct: int = 0
    always_keep_as_prize: bool = False


@dataclasses.dataclass
class _Flagship:
    charter_id: str
    ship_id: str
    captain_id: str
    designated_at: int
    last_redesignate_at: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class DesignationResult:
    accepted: bool
    flagship_ship_id: t.Optional[str] = None
    cooldown_remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class FlagshipDesignation:
    _flagships: dict[str, _Flagship] = dataclasses.field(
        default_factory=dict,
    )

    def designate(
        self, *, charter_id: str,
        captain_id: str,
        ship_id: str,
        now_seconds: int,
    ) -> DesignationResult:
        if not charter_id or not captain_id or not ship_id:
            return DesignationResult(False, reason="bad ids")
        existing = self._flagships.get(charter_id)
        if existing is not None:
            if existing.captain_id != captain_id:
                return DesignationResult(
                    False, reason="not captain of record",
                )
            # cooldown check on re-designation
            anchor = existing.last_redesignate_at or existing.designated_at
            if (
                now_seconds - anchor
                < REDESIGNATE_COOLDOWN_SECONDS
            ):
                return DesignationResult(
                    False,
                    cooldown_remaining=(
                        REDESIGNATE_COOLDOWN_SECONDS
                        - (now_seconds - anchor)
                    ),
                    reason="redesignate cooldown",
                )
            existing.ship_id = ship_id
            existing.last_redesignate_at = now_seconds
            return DesignationResult(
                accepted=True, flagship_ship_id=ship_id,
            )
        self._flagships[charter_id] = _Flagship(
            charter_id=charter_id,
            ship_id=ship_id,
            captain_id=captain_id,
            designated_at=now_seconds,
        )
        return DesignationResult(
            accepted=True, flagship_ship_id=ship_id,
        )

    def undesignate(
        self, *, charter_id: str,
        captain_id: str,
        now_seconds: int,
    ) -> DesignationResult:
        existing = self._flagships.get(charter_id)
        if existing is None:
            return DesignationResult(False, reason="no flagship")
        if existing.captain_id != captain_id:
            return DesignationResult(False, reason="not captain")
        del self._flagships[charter_id]
        return DesignationResult(accepted=True)

    def flagship_for(
        self, *, charter_id: str,
    ) -> t.Optional[str]:
        rec = self._flagships.get(charter_id)
        return rec.ship_id if rec else None

    def buffs_for(
        self, *, ship_id: str, charter_id: str,
    ) -> FlagshipBuffs:
        rec = self._flagships.get(charter_id)
        if rec is None or rec.ship_id != ship_id:
            return FlagshipBuffs(is_flagship=False)
        return FlagshipBuffs(
            is_flagship=True,
            hp_max_bonus_pct=HP_MAX_BONUS_PCT,
            crew_skill_bonus=CREW_SKILL_BONUS,
            damage_resist_bonus_pct=DAMAGE_RESIST_BONUS_PCT,
            always_keep_as_prize=True,
        )

    def report_sunk(
        self, *, charter_id: str, ship_id: str,
    ) -> bool:
        rec = self._flagships.get(charter_id)
        if rec is None or rec.ship_id != ship_id:
            return False
        del self._flagships[charter_id]
        return True


__all__ = [
    "FlagshipBuffs", "DesignationResult", "FlagshipDesignation",
    "HP_MAX_BONUS_PCT", "CREW_SKILL_BONUS",
    "DAMAGE_RESIST_BONUS_PCT", "REDESIGNATE_COOLDOWN_SECONDS",
]
