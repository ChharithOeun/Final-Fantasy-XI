"""Lightning strike — the storm reaches down.

During thunderstorms, lightning has a chance to strike a
target each tick. The chance is influenced by:
    - storm intensity (higher = more chance)
    - target's metal armor mass (more = more attractive)
    - target's elevation flag (high ground = more attractive)
    - "lightning_rod" key item — guarantees strike (and
      survives, redirecting damage to a small radius)

Damage scales with intensity and the target's lightning
resistance reduction (caller can pass 0..100 reduction).

Public surface
--------------
    StrikeResult dataclass (frozen)
    LightningStrikeEngine
        .roll_strike(target_id, intensity, metal_mass,
                     on_high_ground, has_lightning_rod,
                     resist_pct, rng_roll_pct) -> StrikeResult
"""
from __future__ import annotations

import dataclasses


# threshold below this rolls miss; rolls above STRIKE_FLOOR
# get a hit when score crosses
_STRIKE_BASE_PCT = 1   # 1% baseline at intensity 100
_BASE_DAMAGE = 600     # at intensity 100, no resist
_LIGHTNING_ROD_BONUS = 0.5  # damage gets halved when rod absorbs


@dataclasses.dataclass(frozen=True)
class StrikeResult:
    struck: bool
    damage: int
    redirected: bool        # True iff lightning rod absorbed
    chance_pct: int         # the chance that was rolled against


@dataclasses.dataclass
class LightningStrikeEngine:

    def roll_strike(
        self, *, target_id: str, intensity: int,
        metal_mass: int = 0,
        on_high_ground: bool = False,
        has_lightning_rod: bool = False,
        resist_pct: int = 0,
        rng_roll_pct: int = 50,
    ) -> StrikeResult:
        if not target_id or intensity <= 0:
            return StrikeResult(
                struck=False, damage=0,
                redirected=False, chance_pct=0,
            )
        # rod always strikes (it's literally inviting it)
        if has_lightning_rod:
            base = max(1, _BASE_DAMAGE * intensity // 100)
            after_resist = base * (100 - max(0, min(100, resist_pct))) // 100
            damage = int(after_resist * _LIGHTNING_ROD_BONUS)
            return StrikeResult(
                struck=True, damage=damage,
                redirected=True, chance_pct=100,
            )
        # otherwise compute chance %
        chance = _STRIKE_BASE_PCT * intensity // 100
        # metal mass: each unit adds %
        chance += metal_mass
        if on_high_ground:
            chance += 5
        chance = max(0, min(100, chance))
        if rng_roll_pct >= chance:
            return StrikeResult(
                struck=False, damage=0,
                redirected=False, chance_pct=chance,
            )
        # struck — damage scales with intensity, reduced by resist
        base = max(1, _BASE_DAMAGE * intensity // 100)
        damage = base * (100 - max(0, min(100, resist_pct))) // 100
        return StrikeResult(
            struck=True, damage=damage,
            redirected=False, chance_pct=chance,
        )


__all__ = ["StrikeResult", "LightningStrikeEngine"]
