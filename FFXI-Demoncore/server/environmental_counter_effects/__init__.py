"""Environmental counter effects — every hazard has a counter.

Big-battle environment hazards aren't unblockable suffering.
Every effect has a counter the player can prepare or
improvise:

    FLOOR_COLLAPSE  → Featherfall (BLM/SCH cast or scroll)
                      negates fall damage; Float spell
                      (BLM Lvl 35) gives the same and
                      lasts 5 minutes
    ICE_BREAK       → Swimming Skill (Norg trainer) lets
                      you swim back to a hole faster;
                      Cold Resist or Cold Resist+ gear
                      shortens FROST_SLEEP; Erase from a
                      WHM removes it instantly
    CEILING_CRUMBLE → Shield Block roll vs debris;
                      Stoneskin absorbs one debris hit;
                      Stun Resist shortens stun duration
    PILLAR_FALL     → Spatial awareness — sidestep
                      reduces by 50% if you're outside
                      the lean cone; Phalanx absorbs
                      crush damage
    BRIDGE_SEVER    → Teleport (BLM/SCH/RDM) re-unifies;
                      WHM Raise can revive across the
                      gap; rope-shot from RNG bridges it
    DAM_BURST       → Climb to higher band; SMN's
                      Leviathan blesses pools and grants
                      WATER_WALK; SCH Aquaveil + RDM
                      Refresh keeps casters alive
    SHIP_LIST       → Sea legs (passive Sailor's Charm
                      key item) reduces slide; Hold
                      ground macro halves it
    HABITAT_AMBUSH  → Sneak/Invis dampens aggro of
                      neutral habitat creatures; pre-
                      placed RNG/RNG+THF widescan flags
                      them BEFORE breach so the alliance
                      can pre-buff

Each player can have multiple ACTIVE counters at once
— they stack (caps at 100% mitigation per kind). The
module also tracks WHO had which counter when the hazard
fired, for post-mortem and achievement tracking.

Public surface
--------------
    CounterId enum
    CounterStatus dataclass (frozen)
    CounterApplyResult dataclass (frozen)
    EnvironmentalCounters
        .grant_counter(player_id, counter_id, magnitude_pct,
                       expires_at)
        .has_counter(player_id, counter_id, now_seconds) -> bool
        .mitigate(player_id, hazard_kind, raw_value,
                  now_seconds) -> CounterApplyResult
        .clear_expired(now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.environment_hazards import HazardKind


class CounterId(str, enum.Enum):
    FEATHERFALL = "featherfall"
    FLOAT = "float"
    SWIMMING_SKILL = "swimming_skill"
    COLD_RESIST = "cold_resist"
    SHIELD_BLOCK = "shield_block"
    STONESKIN = "stoneskin"
    STUN_RESIST = "stun_resist"
    PHALANX = "phalanx"
    SIDESTEP = "sidestep"
    TELEPORT_READY = "teleport_ready"
    WATER_WALK = "water_walk"
    SEA_LEGS = "sea_legs"
    SNEAK_INVIS = "sneak_invis"
    WIDESCAN_PRE_FLAGGED = "widescan_pre_flagged"


# Map hazard → which counters reduce its effect
HAZARD_COUNTER_MAP: dict[HazardKind, tuple[CounterId, ...]] = {
    HazardKind.FLOOR_COLLAPSE: (CounterId.FEATHERFALL, CounterId.FLOAT),
    HazardKind.ICE_BREAK: (CounterId.SWIMMING_SKILL, CounterId.COLD_RESIST),
    HazardKind.CEILING_CRUMBLE: (
        CounterId.SHIELD_BLOCK, CounterId.STONESKIN, CounterId.STUN_RESIST,
    ),
    HazardKind.PILLAR_FALL: (CounterId.SIDESTEP, CounterId.PHALANX),
    HazardKind.BRIDGE_SEVER: (CounterId.TELEPORT_READY,),
    HazardKind.DAM_BURST: (CounterId.WATER_WALK,),
    HazardKind.SHIP_LIST: (CounterId.SEA_LEGS,),
    HazardKind.WALL_BREACH: (
        CounterId.SNEAK_INVIS, CounterId.WIDESCAN_PRE_FLAGGED,
    ),
}


@dataclasses.dataclass(frozen=True)
class CounterStatus:
    counter_id: CounterId
    magnitude_pct: int    # 0..100
    expires_at: int       # absolute now_seconds


@dataclasses.dataclass(frozen=True)
class CounterApplyResult:
    raw_value: int
    final_value: int
    mitigated_amount: int
    counters_used: tuple[CounterId, ...]


@dataclasses.dataclass
class EnvironmentalCounters:
    # player_id -> counter_id -> CounterStatus
    _grants: dict[str, dict[CounterId, CounterStatus]] = dataclasses.field(
        default_factory=dict,
    )

    def grant_counter(
        self, *, player_id: str, counter_id: CounterId,
        magnitude_pct: int, expires_at: int,
    ) -> bool:
        if not player_id:
            return False
        if not (1 <= magnitude_pct <= 100):
            return False
        bag = self._grants.setdefault(player_id, {})
        # if they already have this counter, take the better
        existing = bag.get(counter_id)
        if existing is not None:
            if (existing.magnitude_pct >= magnitude_pct
                    and existing.expires_at >= expires_at):
                return False
        bag[counter_id] = CounterStatus(
            counter_id=counter_id,
            magnitude_pct=magnitude_pct,
            expires_at=expires_at,
        )
        return True

    def has_counter(
        self, *, player_id: str, counter_id: CounterId,
        now_seconds: int,
    ) -> bool:
        bag = self._grants.get(player_id, {})
        s = bag.get(counter_id)
        if s is None:
            return False
        return now_seconds < s.expires_at

    def mitigate(
        self, *, player_id: str, hazard: HazardKind,
        raw_value: int, now_seconds: int,
    ) -> CounterApplyResult:
        if raw_value <= 0:
            return CounterApplyResult(
                raw_value=raw_value, final_value=raw_value,
                mitigated_amount=0, counters_used=(),
            )
        possible = HAZARD_COUNTER_MAP.get(hazard, ())
        bag = self._grants.get(player_id, {})
        used: list[CounterId] = []
        total_pct = 0
        for cid in possible:
            s = bag.get(cid)
            if s is None or now_seconds >= s.expires_at:
                continue
            used.append(cid)
            total_pct += s.magnitude_pct
        # cap at 100%
        eff_pct = min(100, total_pct)
        mitigated = (raw_value * eff_pct) // 100
        return CounterApplyResult(
            raw_value=raw_value,
            final_value=max(0, raw_value - mitigated),
            mitigated_amount=mitigated,
            counters_used=tuple(used),
        )

    def clear_expired(self, *, now_seconds: int) -> int:
        cleared = 0
        for player_id, bag in self._grants.items():
            expired = [
                cid for cid, s in bag.items()
                if now_seconds >= s.expires_at
            ]
            for cid in expired:
                del bag[cid]
                cleared += 1
        return cleared

    def active_counter_ids(
        self, *, player_id: str, now_seconds: int,
    ) -> tuple[CounterId, ...]:
        bag = self._grants.get(player_id, {})
        return tuple(
            cid for cid, s in bag.items()
            if now_seconds < s.expires_at
        )


__all__ = [
    "CounterId", "CounterStatus", "CounterApplyResult",
    "EnvironmentalCounters", "HAZARD_COUNTER_MAP",
]
