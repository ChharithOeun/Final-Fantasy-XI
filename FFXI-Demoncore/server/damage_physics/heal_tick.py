"""Healing tick — natural regeneration after the heal_delay window.

Per DAMAGE_PHYSICS_HEALING.md:
    'while no damage has been taken for heal_delay_s seconds, each
    tick adds heal_rate * dt HP. When HP crosses a stage boundary
    upward, the visible state animates back: chunks reverse-fly into
    place on a 1-2 second tween, decals fade, dust clears, magic
    stitch particle effect plays.'

We compute the math here. UE5 BPC_HealingStructure plays the tween;
LSB only broadcasts when the visible state stage actually changes
('the network doesn't flood with HP ticks').
"""
from __future__ import annotations

import dataclasses
import typing as t

from .structure_state import (
    HealingStructure,
    VisibleState,
    resolve_visible_state,
)


@dataclasses.dataclass(frozen=True)
class HealEvent:
    """Result of one heal tick. Caller broadcasts only when
    state_changed is True."""
    structure_id: str
    hp_before: int
    hp_after: int
    state_before: VisibleState
    state_after: VisibleState
    healed_amount: int
    at_time: float

    @property
    def state_changed(self) -> bool:
        return self.state_before != self.state_after

    @property
    def healed(self) -> bool:
        return self.healed_amount > 0


def can_heal(structure: HealingStructure, *, now: float) -> bool:
    """Heal eligibility per the doc rules."""
    if structure.permanent:
        return False
    if structure.hp_current >= structure.hp_max:
        return False
    if structure.last_hit_at is None:
        # Never hit; no need to heal.
        return False
    return (now - structure.last_hit_at) >= structure.heal_delay_s


def heal_tick(
    structure: HealingStructure,
    *,
    now: float,
    dt: float,
) -> HealEvent:
    """Advance one structure by `dt` real-world seconds.

    Returns a HealEvent describing the change. If the structure is
    not eligible to heal, healed_amount = 0 and state_changed = False.
    """
    if dt < 0:
        raise ValueError("dt must be non-negative")
    hp_before = structure.hp_current
    state_before = structure.visible_state

    if not can_heal(structure, now=now):
        return HealEvent(
            structure_id=structure.structure_id,
            hp_before=hp_before, hp_after=hp_before,
            state_before=state_before, state_after=state_before,
            healed_amount=0, at_time=now,
        )

    # Heal math is fractional internally; we round to int after.
    raw_new_hp = min(float(structure.hp_max),
                      hp_before + structure.heal_rate * dt)
    new_hp = int(round(raw_new_hp))
    # Round down if we'd overshoot; max == cap.
    if new_hp > structure.hp_max:
        new_hp = structure.hp_max
    structure.hp_current = new_hp
    structure.visible_state = resolve_visible_state(new_hp,
                                                       structure.hp_max)
    if new_hp >= structure.hp_max:
        # Fully healed — clear last_hit_at so next damage starts
        # the heal_delay from scratch. Doc implies this; LSB pseudocode
        # never re-heals an already-full structure.
        structure.last_hit_at = None

    return HealEvent(
        structure_id=structure.structure_id,
        hp_before=hp_before, hp_after=new_hp,
        state_before=state_before, state_after=structure.visible_state,
        healed_amount=new_hp - hp_before, at_time=now,
    )


def heal_tick_many(
    structures: t.Iterable[HealingStructure],
    *,
    now: float,
    dt: float,
) -> list[HealEvent]:
    """Run heal_tick on each structure; return only state-change
    events (the only ones LSB broadcasts to clients).

    The caller can opt to filter further; we return all events here
    so test code can inspect every tick.
    """
    return [heal_tick(s, now=now, dt=dt) for s in structures]


def filter_broadcastable(events: t.Iterable[HealEvent]) -> list[HealEvent]:
    """Keep only events that crossed a stage boundary upward.

    Per the doc: 'broadcast structure_healed updates only when state
    stage changes (so the network doesn't flood with HP ticks)'.
    """
    return [e for e in events if e.state_changed]
