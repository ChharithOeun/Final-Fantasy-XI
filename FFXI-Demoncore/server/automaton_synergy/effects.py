"""Effect instance — concrete record of a fired synergy.

Why
---
The catalog defines what an ability IS; the cooldown tracker
gates WHEN it can fire; Overdrive scales the magnitude — but
something has to be the live record of a single firing event:

  - which master fired it
  - which ability
  - when it fires (now_tick)
  - when it expires
  - effective duration (post-Overdrive)
  - effectiveness scalar (post-Overdrive)
  - AOE radius (carried forward from catalog)
  - resolved effect payload (with scaled numerics)

That record is EffectInstance. Downstream consumers (mood event
hooks, magic-burst pipeline, party-buff applier, encounter
generator that adjusts mob aggro for stealth-buffed parties) all
read from EffectInstance rather than reaching back into the
catalog.

This module is the bridge between the synergy abstraction and
the broader effect-application machinery. We don't apply the
effect HERE — we just package it up. Other systems subscribe.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .catalog import EffectKind, SynergyAbility
from .overdrive import ModifiedAbility


# Numeric payload keys whose values should be scaled by the
# Overdrive effectiveness scalar. Listed explicitly so that
# non-scalable values (booleans, statuses, formulas, string
# enums) stay untouched.
_SCALABLE_PAYLOAD_KEYS: frozenset[str] = frozenset({
    "spike_damage_pct",
    "dot_per_tick",
    "ticks",
    "heal_to_party_pct",
    "magic_defense_pct",
    "evasion_pct",
    "magic_evasion_pct",
    "accuracy_pct",
    "attack_pct",
    "defense_pct",
    "phys_damage_taken_pct",
    "enmity_pct",
    "slow_pct",
    "shots_per_attack",
    "knockback_yalms",
    "damage_scalar",
    "damage_per_tick",
    "base_damage",
    "mp_per_tick",
    "on_resurrect_hp_pct",
    "on_strike_heal_master_pct",
    "hp_cost_per_strike_pct",
    "damage_bonus_pct_of_cost",
    "reraise_tier",
})


@dataclasses.dataclass(frozen=True)
class EffectInstance:
    """A single fired synergy ability.

    Immutable once created. The activation layer constructs one
    of these per successful trigger and hands it to whatever
    subsystem needs to know.
    """
    ability_id: str
    name: str
    master_id: str
    head: t.Any                      # Head enum value
    frame: t.Any                     # Frame enum value
    effect_kind: EffectKind
    fired_at_tick: int
    expires_at_tick: int             # equals fired_at_tick if instant
    aoe_radius_yalms: float
    overdrive_active: bool
    effectiveness_scalar: float
    payload: tuple[tuple[str, t.Any], ...]
    next_available_tick: int         # cooldown lockout end

    @property
    def is_instant(self) -> bool:
        return self.expires_at_tick == self.fired_at_tick

    @property
    def is_active_at(self) -> t.Callable[[int], bool]:
        """Curried predicate: is this effect active at tick T?"""
        fired = self.fired_at_tick
        expires = self.expires_at_tick

        def _check(now_tick: int) -> bool:
            if self.is_instant:
                return now_tick == fired
            return fired <= now_tick < expires
        return _check

    def payload_dict(self) -> dict[str, t.Any]:
        return dict(self.payload)


def _scale_payload(
    payload: t.Iterable[tuple[str, t.Any]],
    scalar: float,
) -> tuple[tuple[str, t.Any], ...]:
    """Return the payload with numeric scalable keys multiplied by
    *scalar*. Non-scalable keys pass through unchanged."""
    out: list[tuple[str, t.Any]] = []
    for key, value in payload:
        if key in _SCALABLE_PAYLOAD_KEYS and isinstance(
            value, (int, float)
        ) and not isinstance(value, bool):
            out.append((key, type(value)(value * scalar)
                        if scalar == 1.0
                        else float(value) * scalar))
        else:
            out.append((key, value))
    return tuple(out)


def build_effect_instance(
    *,
    modified: ModifiedAbility,
    master_id: str,
    fired_at_tick: int,
    next_available_tick: int,
) -> EffectInstance:
    """Package a fired synergy into an EffectInstance.

    Scales the payload's numeric values by the modified ability's
    effectiveness scalar; passes booleans/strings/formulas
    untouched. Computes expires_at_tick from duration.
    """
    scaled_payload = _scale_payload(
        modified.base.effect_payload,
        modified.effectiveness_scalar,
    )
    return EffectInstance(
        ability_id=modified.base.ability_id,
        name=modified.name,
        master_id=master_id,
        head=modified.base.head,
        frame=modified.base.frame,
        effect_kind=modified.base.effect_kind,
        fired_at_tick=fired_at_tick,
        expires_at_tick=fired_at_tick + modified.duration_seconds,
        aoe_radius_yalms=modified.aoe_radius_yalms,
        overdrive_active=modified.overdrive_active,
        effectiveness_scalar=modified.effectiveness_scalar,
        payload=scaled_payload,
        next_available_tick=next_available_tick,
    )


__all__ = [
    "EffectInstance",
    "build_effect_instance",
]
