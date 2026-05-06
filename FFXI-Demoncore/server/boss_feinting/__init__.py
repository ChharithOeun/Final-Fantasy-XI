"""Boss feinting — fake tells to bait premature reactions.

Smart bosses don't always follow through. They feint:
the wind-up animation plays, the dust falls, the weapon
glows — but no ability fires. The point is to make the
alliance burn defensive cooldowns, blow Stoneskin, or
pop a 2hr reactively. Then the real attack comes 2-4
seconds later when those resources are spent.

A feint is registered as a fake-cast: the boss "starts"
ability X but never actually executes it. Players who
don't pay attention waste reactions. Players with
high telegraph_reading_skill can sometimes spot the
feint (their pattern memory says "this tell normally
finishes — this time it stopped").

Boss feint AI uses a per-fight schedule:
    feint_cooldown_seconds   minimum time between feints
    feint_chance_pct         baseline % chance any given
                             telegraph is a feint
    pressure_threshold       feint chance scales up when
                             players spend defensive
                             cooldowns reactively (more
                             rewarding to feint)

Public surface
--------------
    FeintResult dataclass (frozen)
    BossFeinting
        .start_fight(boss_id, fight_id, base_chance_pct,
                     cooldown_seconds, started_at)
        .roll_feint(boss_id, fight_id, ability_id,
                    pressure_score, now_seconds, rng_roll)
            -> FeintResult
        .note_reactive_cooldown_burn(boss_id, fight_id,
                                     amount, now_seconds)
        .total_feints(boss_id, fight_id) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t


# Tuning
DEFAULT_FEINT_COOLDOWN = 30
DEFAULT_BASE_CHANCE = 15      # 15% baseline
PRESSURE_BONUS_PCT_PER_BURN = 5
PRESSURE_BONUS_CAP = 35       # max +35% from pressure
PRESSURE_DECAY_PER_SECOND = 1


@dataclasses.dataclass(frozen=True)
class FeintResult:
    accepted: bool
    is_feint: bool = False
    chance_used_pct: int = 0
    pressure_score: int = 0
    feint_cooldown_remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _FightState:
    fight_id: str
    boss_id: str
    base_chance_pct: int
    cooldown_seconds: int
    last_feint_at: int = -10**9
    pressure_score: int = 0
    last_pressure_tick_at: int = 0
    total_feints: int = 0


@dataclasses.dataclass
class BossFeinting:
    _fights: dict[str, _FightState] = dataclasses.field(default_factory=dict)

    def start_fight(
        self, *, boss_id: str, fight_id: str,
        started_at: int,
        base_chance_pct: int = DEFAULT_BASE_CHANCE,
        cooldown_seconds: int = DEFAULT_FEINT_COOLDOWN,
    ) -> bool:
        if not boss_id or not fight_id:
            return False
        if not (0 <= base_chance_pct <= 100):
            return False
        if cooldown_seconds < 0:
            return False
        if fight_id in self._fights:
            return False
        self._fights[fight_id] = _FightState(
            fight_id=fight_id, boss_id=boss_id,
            base_chance_pct=base_chance_pct,
            cooldown_seconds=cooldown_seconds,
            last_pressure_tick_at=started_at,
        )
        return True

    def note_reactive_cooldown_burn(
        self, *, boss_id: str, fight_id: str,
        burn_count: int, now_seconds: int,
    ) -> bool:
        f = self._fights.get(fight_id)
        if f is None or f.boss_id != boss_id or burn_count <= 0:
            return False
        # natural decay since last note
        elapsed = max(0, now_seconds - f.last_pressure_tick_at)
        f.pressure_score = max(
            0, f.pressure_score - elapsed * PRESSURE_DECAY_PER_SECOND,
        )
        f.pressure_score = min(
            PRESSURE_BONUS_CAP // PRESSURE_BONUS_PCT_PER_BURN,
            f.pressure_score + burn_count,
        )
        f.last_pressure_tick_at = now_seconds
        return True

    def roll_feint(
        self, *, boss_id: str, fight_id: str,
        ability_id: str, now_seconds: int,
        rng_roll_pct: int,
    ) -> FeintResult:
        f = self._fights.get(fight_id)
        if f is None or f.boss_id != boss_id:
            return FeintResult(False, reason="unknown fight")
        if not (1 <= rng_roll_pct <= 100):
            return FeintResult(False, reason="invalid rng roll")
        # decay pressure since last interaction
        elapsed = max(0, now_seconds - f.last_pressure_tick_at)
        f.pressure_score = max(
            0, f.pressure_score - elapsed * PRESSURE_DECAY_PER_SECOND,
        )
        f.last_pressure_tick_at = now_seconds
        # cooldown gate
        cd_remaining = max(
            0, (f.last_feint_at + f.cooldown_seconds) - now_seconds,
        )
        if cd_remaining > 0:
            return FeintResult(
                accepted=True, is_feint=False,
                chance_used_pct=0,
                pressure_score=f.pressure_score,
                feint_cooldown_remaining=cd_remaining,
                reason="cooldown",
            )
        bonus = min(
            PRESSURE_BONUS_CAP,
            f.pressure_score * PRESSURE_BONUS_PCT_PER_BURN,
        )
        chance = min(100, f.base_chance_pct + bonus)
        is_feint = rng_roll_pct <= chance
        if is_feint:
            f.last_feint_at = now_seconds
            f.total_feints += 1
            # reset pressure — alliance won't be as panicked
            f.pressure_score = 0
        return FeintResult(
            accepted=True, is_feint=is_feint,
            chance_used_pct=chance,
            pressure_score=f.pressure_score,
            feint_cooldown_remaining=0 if not is_feint else (
                f.cooldown_seconds
            ),
        )

    def total_feints(
        self, *, boss_id: str, fight_id: str,
    ) -> int:
        f = self._fights.get(fight_id)
        return f.total_feints if f and f.boss_id == boss_id else 0

    def pressure_score(
        self, *, boss_id: str, fight_id: str,
    ) -> int:
        f = self._fights.get(fight_id)
        return f.pressure_score if f and f.boss_id == boss_id else 0


__all__ = [
    "FeintResult", "BossFeinting",
    "DEFAULT_FEINT_COOLDOWN", "DEFAULT_BASE_CHANCE",
    "PRESSURE_BONUS_PCT_PER_BURN", "PRESSURE_BONUS_CAP",
    "PRESSURE_DECAY_PER_SECOND",
]
