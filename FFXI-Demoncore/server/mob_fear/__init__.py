"""Mob fear — morale + rout when allies die.

When a mob dies in front of its pack, the survivors don't keep
fighting like robots. Each nearby same-family mob rolls a morale
check; below threshold the mob ROUTS — it disengages, flees the
fight, and re-evaluates. Some mob personalities (zealots, undead,
golems) are FEARLESS and never rout.

Inputs to the check
-------------------
* the witnessing mob's COURAGE (mob_personality)
* whether the PACK_LEADER is still alive (huge stabilizer)
* the level differential vs the killer (lower-level mobs panic
  more easily)
* the FEARLESS flag (set on undead, golems, raid bosses)
* a fear-cascade bonus: if multiple allies died in the same
  window, the fear stacks (each prior death within `cascade_window`
  adds +5 fear)

Public surface
--------------
    FearOutcome enum (HOLD / WAVER / ROUT)
    AllyDeathContext dataclass
    MobMoraleProfile dataclass
    FearResolution dataclass
    MobFearRegistry
        .register_mob(profile)
        .record_ally_death(witness_id, dying_id, killer_level, now)
        .has_routed(witness_id) / .restore_morale(witness_id)
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


# Default thresholds
WAVER_THRESHOLD = 40       # roll d100; <= waver_threshold = ROUT
HOLD_THRESHOLD = 70        # >70 = HOLD; 41..70 = WAVER
CASCADE_WINDOW_SECONDS = 30.0
CASCADE_FEAR_BONUS = 5
PACK_LEADER_BONUS = 25     # leader alive = +25 morale
LEVEL_DIFFERENTIAL_PER_TIER = 5


class FearOutcome(str, enum.Enum):
    HOLD = "hold"
    WAVER = "waver"
    ROUT = "rout"


@dataclasses.dataclass(frozen=True)
class MobMoraleProfile:
    mob_id: str
    family_id: str
    courage: int = 50          # 0..100
    level: int = 30
    is_fearless: bool = False
    is_pack_leader: bool = False


@dataclasses.dataclass(frozen=True)
class FearResolution:
    witness_id: str
    outcome: FearOutcome
    morale_score: int
    notes: str = ""


@dataclasses.dataclass
class _RecentDeath:
    family_id: str
    occurred_at_seconds: float


@dataclasses.dataclass
class MobFearRegistry:
    waver_threshold: int = WAVER_THRESHOLD
    hold_threshold: int = HOLD_THRESHOLD
    _profiles: dict[str, MobMoraleProfile] = dataclasses.field(
        default_factory=dict,
    )
    _routed: set[str] = dataclasses.field(default_factory=set)
    _recent_deaths: list[_RecentDeath] = dataclasses.field(
        default_factory=list,
    )
    # Tracks pack leader status per family
    _live_pack_leaders: set[str] = dataclasses.field(
        default_factory=set,
    )

    def register_mob(
        self, profile: MobMoraleProfile,
    ) -> MobMoraleProfile:
        self._profiles[profile.mob_id] = profile
        if profile.is_pack_leader:
            self._live_pack_leaders.add(profile.family_id)
        return profile

    def get(self, mob_id: str) -> t.Optional[MobMoraleProfile]:
        return self._profiles.get(mob_id)

    def kill_mob(
        self, *, mob_id: str, now_seconds: float,
    ) -> t.Optional[MobMoraleProfile]:
        p = self._profiles.get(mob_id)
        if p is None:
            return None
        # Track recent death for cascade
        self._recent_deaths.append(_RecentDeath(
            family_id=p.family_id, occurred_at_seconds=now_seconds,
        ))
        if p.is_pack_leader and p.family_id in self._live_pack_leaders:
            # Last leader dying — flag family un-lead
            other_leader_alive = any(
                pp.is_pack_leader and pp.mob_id != mob_id
                and pp.family_id == p.family_id
                for pp in self._profiles.values()
                if pp.mob_id != mob_id
            )
            if not other_leader_alive:
                self._live_pack_leaders.discard(p.family_id)
        return p

    def _cascade_count(
        self, *, family_id: str, now_seconds: float,
    ) -> int:
        cutoff = now_seconds - CASCADE_WINDOW_SECONDS
        return sum(
            1 for d in self._recent_deaths
            if d.family_id == family_id
            and d.occurred_at_seconds >= cutoff
        )

    def witness_ally_death(
        self, *, witness_id: str, dying_id: str,
        killer_level: int, now_seconds: float,
        rng: t.Optional[random.Random] = None,
    ) -> FearResolution:
        """Roll a morale check for the witnessing mob. Returns
        HOLD / WAVER / ROUT. ROUT marks the mob as routed."""
        rng = rng or random.Random()
        witness = self._profiles.get(witness_id)
        dying = self._profiles.get(dying_id)
        if witness is None or dying is None:
            return FearResolution(
                witness_id=witness_id,
                outcome=FearOutcome.HOLD,
                morale_score=100,
                notes="unknown actors",
            )
        # Different family — no fear effect
        if witness.family_id != dying.family_id:
            return FearResolution(
                witness_id=witness_id,
                outcome=FearOutcome.HOLD,
                morale_score=100,
                notes="different family",
            )
        if witness.is_fearless:
            return FearResolution(
                witness_id=witness_id,
                outcome=FearOutcome.HOLD,
                morale_score=100,
                notes="fearless",
            )
        if witness_id in self._routed:
            return FearResolution(
                witness_id=witness_id,
                outcome=FearOutcome.ROUT,
                morale_score=0,
                notes="already routed",
            )
        # Score: courage + leader bonus + level differential
        score = witness.courage
        if witness.family_id in self._live_pack_leaders:
            score += PACK_LEADER_BONUS
        # Level differential: lower mob loses morale faster
        diff_tiers = (witness.level - killer_level) // 10
        score += diff_tiers * LEVEL_DIFFERENTIAL_PER_TIER
        # Cascade penalty
        cascade = self._cascade_count(
            family_id=witness.family_id,
            now_seconds=now_seconds,
        )
        # Subtract per prior death (excluding the current one
        # which is already counted)
        score -= max(0, cascade - 1) * CASCADE_FEAR_BONUS
        score = max(0, min(100, score))
        roll = rng.randint(1, 100)
        if score >= self.hold_threshold and roll <= score:
            return FearResolution(
                witness_id=witness_id,
                outcome=FearOutcome.HOLD,
                morale_score=score,
            )
        if score >= self.waver_threshold and roll <= score:
            return FearResolution(
                witness_id=witness_id,
                outcome=FearOutcome.WAVER,
                morale_score=score,
            )
        # Below threshold or failed roll -> ROUT
        self._routed.add(witness_id)
        return FearResolution(
            witness_id=witness_id,
            outcome=FearOutcome.ROUT,
            morale_score=score,
        )

    def has_routed(self, mob_id: str) -> bool:
        return mob_id in self._routed

    def restore_morale(self, *, mob_id: str) -> bool:
        return self._routed.discard(mob_id) is None and (
            mob_id not in self._routed
        )

    def force_rout(self, *, mob_id: str) -> bool:
        if mob_id not in self._profiles:
            return False
        self._routed.add(mob_id)
        return True

    def total_routed(self) -> int:
        return len(self._routed)


__all__ = [
    "WAVER_THRESHOLD", "HOLD_THRESHOLD",
    "CASCADE_WINDOW_SECONDS", "CASCADE_FEAR_BONUS",
    "PACK_LEADER_BONUS", "LEVEL_DIFFERENTIAL_PER_TIER",
    "FearOutcome",
    "MobMoraleProfile", "FearResolution",
    "MobFearRegistry",
]
