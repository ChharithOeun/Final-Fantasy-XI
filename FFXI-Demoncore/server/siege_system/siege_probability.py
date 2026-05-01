"""Per-hour siege probability calculator.

Per SIEGE_CAMPAIGN.md siege math:

    attack_probability_per_real_hour =
        base_rate × beastman_strength × inverse_nation_strength × time_modifier

Practical effect: a healthy, well-defended nation sees attacks every
2-3 real weeks. A weak nation under heavy beastman pressure can see
attacks every few days.
"""
from __future__ import annotations

import random
import typing as t


BASE_HOURLY_RATE = 0.005           # 0.5% per hour baseline
WEEK_HOURS = 168.0                 # for the time-since-last-attack modifier


class SiegeProbabilityCalculator:
    """Pure-math probability + roll. Caller owns the per-hour cron."""

    def attack_chance(self,
                       *,
                       beastman_strength: float,
                       nation_strength: float,
                       hours_since_last_attack: float,
                       base_rate: float = BASE_HOURLY_RATE) -> float:
        """Probability of a siege attack this hour. 0.0 - 1.0."""
        if nation_strength <= 0:
            inverse_nation = 5.0   # cap at 5x — nations with no defense
        else:
            inverse_nation = 1.0 / nation_strength

        time_modifier = 1.0 + (hours_since_last_attack / WEEK_HOURS)

        chance = (base_rate
                   * beastman_strength
                   * inverse_nation
                   * time_modifier)
        return max(0.0, min(1.0, chance))

    def should_trigger(self,
                        *,
                        beastman_strength: float,
                        nation_strength: float,
                        hours_since_last_attack: float,
                        rng: t.Optional[random.Random] = None,
                        base_rate: float = BASE_HOURLY_RATE) -> bool:
        """Roll the per-hour dice. Returns True if a siege is launched."""
        rng = rng or random.Random()
        chance = self.attack_chance(
            beastman_strength=beastman_strength,
            nation_strength=nation_strength,
            hours_since_last_attack=hours_since_last_attack,
            base_rate=base_rate,
        )
        return rng.random() < chance

    def expected_hours_between_attacks(self,
                                         *,
                                         beastman_strength: float,
                                         nation_strength: float,
                                         base_rate: float = BASE_HOURLY_RATE,
                                         ) -> float:
        """Expected hours between attacks under stable conditions
        (ignoring time_modifier acceleration). Mostly for analytics /
        tuning. Returns inf if the chance would be 0."""
        # Use 1-week-stale as the stable assumption for estimation
        chance = self.attack_chance(
            beastman_strength=beastman_strength,
            nation_strength=nation_strength,
            hours_since_last_attack=0,
            base_rate=base_rate,
        )
        if chance <= 0:
            return float("inf")
        return 1.0 / chance
