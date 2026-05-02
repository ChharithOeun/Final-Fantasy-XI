"""Job abilities — JA catalog with cooldowns + 2-hour SP abilities.

Each job has a list of abilities unlocked at specific levels. Most
JAs share a 1-minute global recast pool plus a per-ability recast.
2-hour SPs (Mighty Strikes, Hundred Fists, Manafont, Chainspell, etc.)
have a 2-hour individual cooldown.

Public surface
--------------
    JobAbility catalog
    AbilityCategory enum
    PlayerJATracker
        .can_use(ability_id, now)
        .use(ability_id, now)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AbilityCategory(str, enum.Enum):
    JOB_ABILITY = "job_ability"           # standard JA
    SP_TWO_HOUR = "sp_two_hour"           # SP, 2-hr CD
    PET_COMMAND = "pet_command"           # BST/PUP/SMN
    WEAPON_SKILL_RELATED = "ws_related"


SP_TWO_HOUR_RECAST = 2 * 60 * 60         # 2 hours
GLOBAL_JA_RECAST = 1                      # 1-second global lockout


@dataclasses.dataclass(frozen=True)
class JobAbility:
    ability_id: str
    label: str
    job: str
    level_required: int
    category: AbilityCategory
    recast_seconds: int                   # ability-specific recast
    duration_seconds: int = 0             # 0 = instant


# Sample catalog (canonical FFXI 2-hours + key JAs)
JA_CATALOG: tuple[JobAbility, ...] = (
    # Warrior
    JobAbility("provoke", "Provoke", job="warrior",
                level_required=4,
                category=AbilityCategory.JOB_ABILITY,
                recast_seconds=30),
    JobAbility("berserk", "Berserk", job="warrior",
                level_required=15,
                category=AbilityCategory.JOB_ABILITY,
                recast_seconds=300, duration_seconds=180),
    JobAbility("warcry", "Warcry", job="warrior",
                level_required=10,
                category=AbilityCategory.JOB_ABILITY,
                recast_seconds=300, duration_seconds=30),
    JobAbility("mighty_strikes", "Mighty Strikes",
                job="warrior", level_required=1,
                category=AbilityCategory.SP_TWO_HOUR,
                recast_seconds=SP_TWO_HOUR_RECAST,
                duration_seconds=45),
    # Monk
    JobAbility("focus", "Focus", job="monk",
                level_required=5,
                category=AbilityCategory.JOB_ABILITY,
                recast_seconds=300, duration_seconds=120),
    JobAbility("hundred_fists", "Hundred Fists",
                job="monk", level_required=1,
                category=AbilityCategory.SP_TWO_HOUR,
                recast_seconds=SP_TWO_HOUR_RECAST,
                duration_seconds=45),
    # WHM
    JobAbility("divine_seal", "Divine Seal",
                job="white_mage", level_required=40,
                category=AbilityCategory.JOB_ABILITY,
                recast_seconds=600),
    JobAbility("benediction", "Benediction",
                job="white_mage", level_required=1,
                category=AbilityCategory.SP_TWO_HOUR,
                recast_seconds=SP_TWO_HOUR_RECAST),
    # BLM
    JobAbility("manafont", "Manafont",
                job="black_mage", level_required=1,
                category=AbilityCategory.SP_TWO_HOUR,
                recast_seconds=SP_TWO_HOUR_RECAST,
                duration_seconds=60),
    # RDM
    JobAbility("chainspell", "Chainspell",
                job="red_mage", level_required=1,
                category=AbilityCategory.SP_TWO_HOUR,
                recast_seconds=SP_TWO_HOUR_RECAST,
                duration_seconds=60),
    # THF
    JobAbility("perfect_dodge", "Perfect Dodge",
                job="thief", level_required=1,
                category=AbilityCategory.SP_TWO_HOUR,
                recast_seconds=SP_TWO_HOUR_RECAST,
                duration_seconds=30),
    # PLD
    JobAbility("invincible", "Invincible",
                job="paladin", level_required=1,
                category=AbilityCategory.SP_TWO_HOUR,
                recast_seconds=SP_TWO_HOUR_RECAST,
                duration_seconds=30),
    # DRK
    JobAbility("blood_weapon", "Blood Weapon",
                job="dark_knight", level_required=1,
                category=AbilityCategory.SP_TWO_HOUR,
                recast_seconds=SP_TWO_HOUR_RECAST,
                duration_seconds=30),
)

JA_BY_ID: dict[str, JobAbility] = {ja.ability_id: ja for ja in JA_CATALOG}


@dataclasses.dataclass(frozen=True)
class UseResult:
    accepted: bool
    ability_id: str
    next_available_tick: t.Optional[int] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerJATracker:
    player_id: str
    last_use: dict[str, int] = dataclasses.field(default_factory=dict)
    last_global_use_tick: int = -GLOBAL_JA_RECAST

    def can_use(
        self, *, ability_id: str, now_tick: int, level: int, job: str,
    ) -> UseResult:
        ja = JA_BY_ID.get(ability_id)
        if ja is None:
            return UseResult(False, ability_id, reason="unknown JA")
        if ja.job != job:
            return UseResult(
                False, ability_id,
                reason=f"requires {ja.job}",
            )
        if level < ja.level_required:
            return UseResult(
                False, ability_id,
                reason=f"need level {ja.level_required}",
            )
        # Global JA cooldown
        if now_tick < self.last_global_use_tick + GLOBAL_JA_RECAST:
            return UseResult(
                False, ability_id, reason="global JA cooldown",
            )
        # Per-ability recast
        last = self.last_use.get(ability_id)
        if last is not None:
            next_avail = last + ja.recast_seconds
            if now_tick < next_avail:
                return UseResult(
                    False, ability_id,
                    next_available_tick=next_avail,
                    reason="on cooldown",
                )
        return UseResult(True, ability_id)

    def use(
        self, *, ability_id: str, now_tick: int, level: int, job: str,
    ) -> UseResult:
        check = self.can_use(
            ability_id=ability_id, now_tick=now_tick,
            level=level, job=job,
        )
        if not check.accepted:
            return check
        self.last_use[ability_id] = now_tick
        self.last_global_use_tick = now_tick
        ja = JA_BY_ID[ability_id]
        return UseResult(
            True, ability_id,
            next_available_tick=now_tick + ja.recast_seconds,
        )


__all__ = [
    "AbilityCategory", "SP_TWO_HOUR_RECAST", "GLOBAL_JA_RECAST",
    "JobAbility", "JA_CATALOG", "JA_BY_ID",
    "UseResult", "PlayerJATracker",
]
