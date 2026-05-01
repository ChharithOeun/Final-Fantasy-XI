"""SP 'Overdrive' — 5x duration and effectiveness multiplier.

Overdrive is PUP's signature SP ability in this design. While it
runs, every synergy ability fired benefits from a 5x multiplier
applied to BOTH duration and effectiveness:

  - Duration: Death Spikes 30s -> 150s (2.5 min) under Overdrive.
  - Effectiveness: Death Spikes 8% spike damage -> 40% spike
    damage under Overdrive.

The multiplier applies at activation time. Firing a synergy
DURING Overdrive gives the modified ability for its full duration,
even if Overdrive expires partway through. Firing a synergy AFTER
Overdrive expires gives the base ability with no multiplier.

This module is pure. Caller tracks Overdrive state externally
(e.g. via player_state SP timer) and passes the boolean in.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .catalog import SynergyAbility


# The official Overdrive multiplier. 5x is the design pin from
# the user requirement: "ability would extend to 5x the duration
# and effectiveness during SP overdrive".
OVERDRIVE_MULTIPLIER = 5


@dataclasses.dataclass(frozen=True)
class ModifiedAbility:
    """A synergy ability with overdrive scaling applied."""
    base: SynergyAbility
    overdrive_active: bool
    duration_seconds: int
    effectiveness_scalar: float

    @property
    def ability_id(self) -> str:
        return self.base.ability_id

    @property
    def name(self) -> str:
        if self.overdrive_active:
            return f"{self.base.name} (Overdrive)"
        return self.base.name

    @property
    def cooldown_seconds(self) -> int:
        # Cooldown is NOT scaled — Overdrive accelerates the
        # *effect* but doesn't shorten the lockout.
        return self.base.cooldown_seconds

    @property
    def aoe_radius_yalms(self) -> float:
        return self.base.aoe_radius_yalms


def compute_modified_ability(
    ability: SynergyAbility,
    *,
    overdrive_active: bool = False,
) -> ModifiedAbility:
    """Apply (or not) the Overdrive 5x multiplier to an ability."""
    if overdrive_active:
        return ModifiedAbility(
            base=ability,
            overdrive_active=True,
            duration_seconds=(
                ability.duration_seconds * OVERDRIVE_MULTIPLIER
            ),
            effectiveness_scalar=float(OVERDRIVE_MULTIPLIER),
        )
    return ModifiedAbility(
        base=ability,
        overdrive_active=False,
        duration_seconds=ability.duration_seconds,
        effectiveness_scalar=1.0,
    )


def scale_effect_value(
    base_value: t.Union[int, float],
    modified: ModifiedAbility,
) -> float:
    """Multiply *base_value* by the modified ability's
    effectiveness scalar. Convenience for effect applicators
    that need to scale a single numeric (damage tier, healing
    amount, debuff magnitude, etc.)."""
    return float(base_value) * modified.effectiveness_scalar


__all__ = [
    "OVERDRIVE_MULTIPLIER",
    "ModifiedAbility",
    "compute_modified_ability",
    "scale_effect_value",
]
