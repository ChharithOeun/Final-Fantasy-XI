"""Skill decay — disuse erodes combat & magic skill levels.

Skills tracked in skill_levels (sword, healing magic, archery,
hand-to-hand, etc.) decay if a player goes too long without
practising them. This is a soft mechanic that:
* Discourages min-max'ing all jobs to cap and never touching them
* Keeps the world feeling alive — your old jobs really did rust
* Gives a reason to revisit lower-level content

Decay never drops a skill below a per-player FLOOR (highest
historical 80%), so you never lose serious progress permanently.
After a few minutes of using the skill again, it ROOSTS back up
to its former cap quickly.

Public surface
--------------
    SkillKind enum (broad — actual ID set lives in skill_levels)
    SkillRecord dataclass
    DecayResult dataclass
    SkillDecayRegistry
        .register_skill(player_id, skill_id, level)
        .practice(player_id, skill_id, gain) -> updated level
        .tick(elapsed_seconds) -> tuple[DecayResult]
        .level(player_id, skill_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default thresholds.
DECAY_GRACE_SECONDS = 7 * 24 * 3600        # 7 days no decay
DECAY_PER_DAY_AFTER_GRACE = 1               # 1 skill point/day past grace
ROOST_RECOVERY_RATE = 5                     # +5 per practice tick when rusty
SKILL_FLOOR_FRACTION = 0.8                  # never below 80% of historical


class SkillKind(str, enum.Enum):
    SWORD = "sword"
    GREATSWORD = "greatsword"
    DAGGER = "dagger"
    AXE = "axe"
    POLEARM = "polearm"
    ARCHERY = "archery"
    HAND_TO_HAND = "hand_to_hand"
    HEALING_MAGIC = "healing_magic"
    ELEMENTAL_MAGIC = "elemental_magic"
    ENFEEBLING_MAGIC = "enfeebling_magic"
    DARK_MAGIC = "dark_magic"
    DIVINE_MAGIC = "divine_magic"
    NINJUTSU = "ninjutsu"
    SUMMONING = "summoning"
    SINGING = "singing"


@dataclasses.dataclass
class SkillRecord:
    player_id: str
    skill_id: str
    level: int = 0
    historical_peak: int = 0
    last_practiced_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class DecayResult:
    player_id: str
    skill_id: str
    old_level: int
    new_level: int
    decayed: int


@dataclasses.dataclass
class SkillDecayRegistry:
    decay_grace_seconds: float = DECAY_GRACE_SECONDS
    decay_per_day_after_grace: int = DECAY_PER_DAY_AFTER_GRACE
    skill_floor_fraction: float = SKILL_FLOOR_FRACTION
    _records: dict[
        tuple[str, str], SkillRecord,
    ] = dataclasses.field(default_factory=dict)

    def register_skill(
        self, *, player_id: str, skill_id: str,
        level: int = 0, now_seconds: float = 0.0,
    ) -> t.Optional[SkillRecord]:
        key = (player_id, skill_id)
        if key in self._records:
            return None
        rec = SkillRecord(
            player_id=player_id, skill_id=skill_id,
            level=max(0, level),
            historical_peak=max(0, level),
            last_practiced_seconds=now_seconds,
        )
        self._records[key] = rec
        return rec

    def level(
        self, *, player_id: str, skill_id: str,
    ) -> int:
        rec = self._records.get((player_id, skill_id))
        return rec.level if rec else 0

    def floor_for(
        self, *, player_id: str, skill_id: str,
    ) -> t.Optional[int]:
        rec = self._records.get((player_id, skill_id))
        if rec is None:
            return None
        return int(rec.historical_peak * self.skill_floor_fraction)

    def practice(
        self, *, player_id: str, skill_id: str,
        gain: int = 1, now_seconds: float = 0.0,
    ) -> t.Optional[int]:
        rec = self._records.get((player_id, skill_id))
        if rec is None or gain <= 0:
            return None
        # If rusty (below historical peak), recover faster
        floor = int(
            rec.historical_peak * self.skill_floor_fraction,
        )
        if rec.level < rec.historical_peak:
            # Roost: skip ahead
            rec.level = min(
                rec.historical_peak,
                rec.level + max(gain, ROOST_RECOVERY_RATE),
            )
        else:
            rec.level += gain
            if rec.level > rec.historical_peak:
                rec.historical_peak = rec.level
        rec.last_practiced_seconds = now_seconds
        # Floor moves up when historical_peak does
        # (no further action needed)
        _ = floor
        return rec.level

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[DecayResult, ...]:
        out: list[DecayResult] = []
        seconds_per_day = 24 * 3600.0
        for rec in self._records.values():
            elapsed = now_seconds - rec.last_practiced_seconds
            if elapsed <= self.decay_grace_seconds:
                continue
            past_grace = elapsed - self.decay_grace_seconds
            days = past_grace / seconds_per_day
            if days < 1.0:
                continue
            decay_amount = (
                int(days) * self.decay_per_day_after_grace
            )
            if decay_amount <= 0:
                continue
            old_level = rec.level
            floor = int(
                rec.historical_peak
                * self.skill_floor_fraction,
            )
            new_level = max(floor, rec.level - decay_amount)
            if new_level == old_level:
                continue
            rec.level = new_level
            # Reset the practice timestamp so we don't double-charge
            rec.last_practiced_seconds = now_seconds
            out.append(DecayResult(
                player_id=rec.player_id,
                skill_id=rec.skill_id,
                old_level=old_level,
                new_level=new_level,
                decayed=old_level - new_level,
            ))
        return tuple(out)

    def total_skills_tracked(self) -> int:
        return len(self._records)


__all__ = [
    "DECAY_GRACE_SECONDS",
    "DECAY_PER_DAY_AFTER_GRACE",
    "ROOST_RECOVERY_RATE",
    "SKILL_FLOOR_FRACTION",
    "SkillKind", "SkillRecord", "DecayResult",
    "SkillDecayRegistry",
]
