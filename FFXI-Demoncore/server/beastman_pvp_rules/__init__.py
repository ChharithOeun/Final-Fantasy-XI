"""Beastman PvP rules — city raid encounters across factions.

When a beastman crosses into a hume nation OR a hume crosses
into a beastman city, the world treats it as a RAID. PvP
becomes legal in raid zones, but with rules:

* RAID_DURATION_SECONDS bounded — a raid auto-resolves after 20
  minutes, win or lose
* OUTSIDER_HP_PENALTY_PCT — invader takes a -10% HP soft debuff
  while inside the city (defenders have home turf)
* CIVILIAN_KILL_PENALTY — killing non-combatant NPCs raises
  bounty
* MUTUAL_BOUNTY_GAIN — a successful raid (objective met) raises
  the invader's bounty in the defender's nation
* DEFENDER_REWARD — defenders who repel the raid get a
  conquest payout

Public surface
--------------
    RaidStatus enum
    RaidObjective enum
    RaidEncounter dataclass
    RaidResolutionResult dataclass
    BeastmanPvPRules
        .declare_raid(invader_id, invader_side, target_zone,
                      objective)
        .record_combat_kill(raid_id, killer_id, victim_id, is_civilian)
        .resolve_raid(raid_id, success)
        .raids_in_zone(zone_id)
        .tick(now_seconds) -> auto-resolve overdue raids
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Defaults.
RAID_DURATION_SECONDS = 20 * 60.0
OUTSIDER_HP_PENALTY_PCT = 10
CIVILIAN_KILL_BOUNTY_PER = 1000
COMBATANT_KILL_BOUNTY_PER = 200
DEFENDER_REWARD_GIL = 5000
SUCCESS_BOUNTY_GIL = 25000


class InvaderSide(str, enum.Enum):
    HUME_NATIONS = "hume_nations"
    BEASTMAN = "beastman"


class RaidObjective(str, enum.Enum):
    LOOT_TREASURY = "loot_treasury"
    BURN_LANDMARK = "burn_landmark"
    CAPTURE_LEADER = "capture_leader"
    LIBERATE_PRISONER = "liberate_prisoner"


class RaidStatus(str, enum.Enum):
    DECLARED = "declared"
    SUCCESS = "success"
    REPELLED = "repelled"
    AUTO_RESOLVED = "auto_resolved"


@dataclasses.dataclass
class RaidEncounter:
    raid_id: str
    invader_id: str
    invader_side: InvaderSide
    target_zone_id: str
    objective: RaidObjective
    declared_at_seconds: float
    expires_at_seconds: float
    status: RaidStatus = RaidStatus.DECLARED
    combatant_kills: int = 0
    civilian_kills: int = 0
    bounty_accrued: int = 0


@dataclasses.dataclass(frozen=True)
class RaidResolutionResult:
    accepted: bool
    raid_id: str
    success: bool
    bounty_owed_by_invader: int
    defender_reward_gil: int
    note: str = ""


@dataclasses.dataclass
class BeastmanPvPRules:
    raid_duration_seconds: float = RAID_DURATION_SECONDS
    outsider_hp_penalty_pct: int = OUTSIDER_HP_PENALTY_PCT
    civilian_kill_bounty_per: int = (
        CIVILIAN_KILL_BOUNTY_PER
    )
    combatant_kill_bounty_per: int = (
        COMBATANT_KILL_BOUNTY_PER
    )
    defender_reward_gil: int = DEFENDER_REWARD_GIL
    success_bounty_gil: int = SUCCESS_BOUNTY_GIL
    _raids: dict[str, RaidEncounter] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def declare_raid(
        self, *, invader_id: str,
        invader_side: InvaderSide,
        target_zone_id: str,
        objective: RaidObjective,
        now_seconds: float = 0.0,
    ) -> t.Optional[RaidEncounter]:
        if not invader_id or not target_zone_id:
            return None
        # Only one active raid per invader at a time
        for r in self._raids.values():
            if (
                r.invader_id == invader_id
                and r.status == RaidStatus.DECLARED
            ):
                return None
        rid = f"raid_{self._next_id}"
        self._next_id += 1
        raid = RaidEncounter(
            raid_id=rid, invader_id=invader_id,
            invader_side=invader_side,
            target_zone_id=target_zone_id,
            objective=objective,
            declared_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + self.raid_duration_seconds
            ),
        )
        self._raids[rid] = raid
        return raid

    def get(self, raid_id: str) -> t.Optional[RaidEncounter]:
        return self._raids.get(raid_id)

    def record_combat_kill(
        self, *, raid_id: str,
        killer_id: str, victim_id: str,
        is_civilian: bool = False,
    ) -> bool:
        raid = self._raids.get(raid_id)
        if raid is None:
            return False
        if raid.status != RaidStatus.DECLARED:
            return False
        if killer_id == victim_id:
            return False
        # Only the invader's actions accrue bounty here
        if killer_id != raid.invader_id:
            return False
        if is_civilian:
            raid.civilian_kills += 1
            raid.bounty_accrued += (
                self.civilian_kill_bounty_per
            )
        else:
            raid.combatant_kills += 1
            raid.bounty_accrued += (
                self.combatant_kill_bounty_per
            )
        return True

    def resolve_raid(
        self, *, raid_id: str, success: bool,
        now_seconds: float = 0.0,
    ) -> t.Optional[RaidResolutionResult]:
        raid = self._raids.get(raid_id)
        if raid is None:
            return None
        if raid.status != RaidStatus.DECLARED:
            return None
        if now_seconds > raid.expires_at_seconds:
            # Past the window — caller should have used tick()
            return None
        if success:
            raid.status = RaidStatus.SUCCESS
            raid.bounty_accrued += self.success_bounty_gil
            return RaidResolutionResult(
                accepted=True, raid_id=raid_id,
                success=True,
                bounty_owed_by_invader=raid.bounty_accrued,
                defender_reward_gil=0,
            )
        raid.status = RaidStatus.REPELLED
        return RaidResolutionResult(
            accepted=True, raid_id=raid_id,
            success=False,
            bounty_owed_by_invader=raid.bounty_accrued,
            defender_reward_gil=self.defender_reward_gil,
        )

    def raids_in_zone(
        self, zone_id: str,
    ) -> tuple[RaidEncounter, ...]:
        return tuple(
            r for r in self._raids.values()
            if r.target_zone_id == zone_id
            and r.status == RaidStatus.DECLARED
        )

    def active_raid_for(
        self, *, invader_id: str,
    ) -> t.Optional[RaidEncounter]:
        for r in self._raids.values():
            if (
                r.invader_id == invader_id
                and r.status == RaidStatus.DECLARED
            ):
                return r
        return None

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        auto_resolved: list[str] = []
        for raid in self._raids.values():
            if raid.status != RaidStatus.DECLARED:
                continue
            if now_seconds < raid.expires_at_seconds:
                continue
            raid.status = RaidStatus.AUTO_RESOLVED
            auto_resolved.append(raid.raid_id)
        return tuple(auto_resolved)

    def total_raids(self) -> int:
        return len(self._raids)


__all__ = [
    "RAID_DURATION_SECONDS",
    "OUTSIDER_HP_PENALTY_PCT",
    "CIVILIAN_KILL_BOUNTY_PER",
    "COMBATANT_KILL_BOUNTY_PER",
    "DEFENDER_REWARD_GIL",
    "SUCCESS_BOUNTY_GIL",
    "InvaderSide", "RaidObjective", "RaidStatus",
    "RaidEncounter", "RaidResolutionResult",
    "BeastmanPvPRules",
]
