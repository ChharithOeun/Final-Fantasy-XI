"""Damage resolution — server-authoritative HP application.

Per DAMAGE_PHYSICS_HEALING.md the flow is:
    client -> LSB:  "I cast Earthquake at X,Y,Z radius R damage D"
    LSB:    compute_aoe_damage(...) for each structure within R:
                structure.hp -= damage
                structure.last_hit_at = now()
                if structure.hp <= 0 and permanent_threshold reached:
                    structure.permanent = true
    LSB:    broadcast: "structure_damaged" {id, new_hp, new_state}

This module performs the math; the caller (LSB bridge / siege system)
is responsible for actually broadcasting events and persisting state.
"""
from __future__ import annotations

import dataclasses
import math
import typing as t

from .structure_state import (
    HealingStructure,
    VisibleState,
    resolve_visible_state,
)


@dataclasses.dataclass(frozen=True)
class DamageEvent:
    """Result of applying damage to one structure."""
    structure_id: str
    amount_dealt: int               # actual HP removed (clamped)
    hp_before: int
    hp_after: int
    state_before: VisibleState
    state_after: VisibleState
    became_permanent: bool          # crossed threshold this hit
    at_time: float

    @property
    def state_changed(self) -> bool:
        return self.state_before != self.state_after


def apply_damage(
    structure: HealingStructure,
    *,
    amount: int,
    now: float,
) -> DamageEvent:
    """Apply `amount` damage to a single structure and update its state.

    Returns a DamageEvent describing what happened. Caller decides
    whether to broadcast / persist.
    """
    if amount < 0:
        raise ValueError("damage amount must be non-negative")
    hp_before = structure.hp_current
    state_before = structure.visible_state

    # Permanent already? No further damage state changes.
    if structure.permanent:
        return DamageEvent(
            structure_id=structure.structure_id,
            amount_dealt=0,
            hp_before=hp_before,
            hp_after=hp_before,
            state_before=state_before,
            state_after=state_before,
            became_permanent=False,
            at_time=now,
        )

    new_hp = max(0, hp_before - amount)
    structure.hp_current = new_hp
    structure.last_hit_at = now
    structure.visible_state = resolve_visible_state(new_hp,
                                                       structure.hp_max)

    # Permanent flag: triggered when current HP at-or-below the
    # permanent_threshold fraction of HP_max. Doc: 'city walls
    # typically 0.05 - once hit for 95%+, the chunk stays gone'.
    became_permanent = False
    threshold_hp = math.floor(structure.permanent_threshold *
                                  structure.hp_max)
    if (structure.permanent_threshold < 1.0
            and new_hp <= threshold_hp):
        structure.permanent = True
        became_permanent = True
        # Force destroyed state for permanent damage above the
        # threshold; this matches the doc 'past it, debris stays +
        # smolder VFX' behavior.
        structure.hp_current = 0
        structure.visible_state = VisibleState.DESTROYED

    return DamageEvent(
        structure_id=structure.structure_id,
        amount_dealt=hp_before - structure.hp_current,
        hp_before=hp_before,
        hp_after=structure.hp_current,
        state_before=state_before,
        state_after=structure.visible_state,
        became_permanent=became_permanent,
        at_time=now,
    )


def _distance_3d(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def aoe_damage(
    structures: t.Iterable[HealingStructure],
    *,
    epicenter: tuple[float, float, float],
    radius: float,
    damage: int,
    now: float,
    falloff: t.Optional[t.Callable[[float, float], float]] = None,
) -> list[DamageEvent]:
    """Apply AOE damage to every structure within radius of epicenter.

    `falloff(distance, radius)` returns a multiplier in [0..1]; default
    is no falloff (every hit takes full damage). Earthquake-style
    full-damage AOE is the common case for siege events; for spells
    with falloff (e.g. linear-tip cone), pass a falloff callable.
    """
    if radius < 0:
        raise ValueError("radius must be non-negative")
    events: list[DamageEvent] = []
    for s in structures:
        d = _distance_3d(s.position, epicenter)
        if d > radius:
            continue
        scale = 1.0
        if falloff is not None:
            scale = max(0.0, min(1.0, falloff(d, radius)))
        actual = max(0, int(round(damage * scale)))
        events.append(apply_damage(s, amount=actual, now=now))
    return events


def linear_falloff(distance: float, radius: float) -> float:
    """Linear edge-falloff: full damage at center, 0 at edge."""
    if radius <= 0:
        return 0.0
    return max(0.0, 1.0 - (distance / radius))
