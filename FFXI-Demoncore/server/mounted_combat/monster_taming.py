"""Wild-monster taming for mounted combat.

Per the user direction: 'at lvl 75 if you raise your own mount or
capture a wild monster it could be used for mounted combat'. Tamed
monsters become alternative mounts with their own stat profiles
and combat traits — a wolf is fast, a dhalmel reaches far, a tiger
maul-burst is brutal.

Taming flow:
    1. Reduce target monster to <= TAME_THRESHOLD_HP_PCT (10%)
    2. Use a Tame Beast skill at lvl 75+
    3. Roll against tame_difficulty + monster_species_resist
    4. On success, the monster becomes a mountable companion
"""
from __future__ import annotations

import dataclasses
import random
import typing as t


TAME_THRESHOLD_HP_PCT = 0.10            # target must be <= 10% HP
TAME_UNLOCK_LEVEL = 75
BASE_TAME_SUCCESS = 0.40                # at exact level parity


@dataclasses.dataclass(frozen=True)
class TameableMonster:
    """A wild monster species that can be tamed at lvl 75+."""
    species: str
    label: str                       # human-friendly
    base_hp: int
    base_damage: int
    movement_ms: float
    cavalry_traits: tuple[str, ...]
    feed_required_per_day: int
    tame_difficulty: int             # min effective rider level required
    notes: str = ""


WILD_MOUNTS: dict[str, TameableMonster] = {
    "wolf": TameableMonster(
        species="wolf", label="Wolf",
        base_hp=2500, base_damage=80,
        movement_ms=14.0,
        cavalry_traits=("fast", "lunge", "scent_track"),
        feed_required_per_day=2,
        tame_difficulty=75,
        notes="fast and biting; weak on long charge but lethal on lunge",
    ),
    "dhalmel": TameableMonster(
        species="dhalmel", label="Dhalmel",
        base_hp=4500, base_damage=60,
        movement_ms=11.0,
        cavalry_traits=("tanky", "long_reach", "high_carry"),
        feed_required_per_day=4,
        tame_difficulty=78,
        notes="tanky neck-reach; carries heavier saddlebags",
    ),
    "raptor": TameableMonster(
        species="raptor", label="Raptor",
        base_hp=2200, base_damage=120,
        movement_ms=15.0,
        cavalry_traits=("fast", "burst_damage", "unstable"),
        feed_required_per_day=3,
        tame_difficulty=80,
        notes="apex burst-damage mount; hard to control",
    ),
    "tiger": TameableMonster(
        species="tiger", label="Tiger",
        base_hp=3000, base_damage=100,
        movement_ms=13.5,
        cavalry_traits=("balanced", "maul", "intimidate"),
        feed_required_per_day=3,
        tame_difficulty=82,
        notes="balanced cavalry; fear-aura intimidates lower-level mobs",
    ),
    "buffalo": TameableMonster(
        species="buffalo", label="Buffalo",
        base_hp=5000, base_damage=70,
        movement_ms=10.0,
        cavalry_traits=("very_tanky", "trample_strong", "slow"),
        feed_required_per_day=5,
        tame_difficulty=76,
        notes="trample-king; slow but unstoppable in a charge",
    ),
}


# ----------------------------------------------------------------------
# Taming attempt
# ----------------------------------------------------------------------

@dataclasses.dataclass
class TameResult:
    success: bool
    monster: t.Optional[TameableMonster]
    reason: str = ""
    success_rate: float = 0.0


def attempt_tame(*,
                  rider_level: int,
                  rider_has_tame_skill: bool,
                  monster_species: str,
                  monster_hp_pct: float,
                  rng: t.Optional[random.Random] = None,
                  ) -> TameResult:
    """Try to tame a wild monster. Returns TameResult with success
    flag + the species record on success."""
    rng = rng or random.Random()

    if rider_level < TAME_UNLOCK_LEVEL:
        return TameResult(
            success=False, monster=None,
            reason=f"taming requires rider level >= {TAME_UNLOCK_LEVEL}",
        )
    if not rider_has_tame_skill:
        return TameResult(
            success=False, monster=None,
            reason="rider lacks the Tame Beast skill",
        )
    if monster_hp_pct > TAME_THRESHOLD_HP_PCT:
        return TameResult(
            success=False, monster=None,
            reason=(f"monster HP must be <= {TAME_THRESHOLD_HP_PCT * 100:.0f}%; "
                     f"current {monster_hp_pct * 100:.1f}%"),
        )

    monster = WILD_MOUNTS.get(monster_species.lower())
    if monster is None:
        return TameResult(
            success=False, monster=None,
            reason=f"unknown / un-tameable species: {monster_species}",
        )

    # Success rate: BASE_TAME_SUCCESS at parity (rider_level vs
    # tame_difficulty), +5% per level above difficulty, -10% per below.
    diff = rider_level - monster.tame_difficulty
    if diff >= 0:
        rate = BASE_TAME_SUCCESS + 0.05 * diff
    else:
        rate = BASE_TAME_SUCCESS + 0.10 * diff   # 10% per level below
    rate = max(0.0, min(0.95, rate))

    if rng.random() < rate:
        return TameResult(
            success=True, monster=monster,
            success_rate=rate,
        )
    return TameResult(
        success=False, monster=None,
        reason="tame attempt failed (RNG)",
        success_rate=rate,
    )
