"""Status slot manager — limited debuff slots + displacement.

Canonical FFXI: a target can hold ONE Bio-family at a time
(Bio I displaced by Bio II / III but not by Dia of any tier);
ONE Burn-family elemental DoT; ONE Slow / Paralyze; etc. New
casts of the same family follow displacement rules:

    HIGHER tier   -> displaces, replaces with new
    SAME tier     -> refreshes duration (extends)
    LOWER tier    -> rejected

Buffs work the same way: one Haste, one Refresh, one Regen
slot per category.

This module owns the slot grid + displacement logic, separate
from `status_effects` (which is the canonical buff/debuff
catalog). Other systems consume `apply()` and check the result.

Public surface
--------------
    SlotCategory enum (BIO_FAMILY / DIA_FAMILY / BURN_DOT /
                       SLOW / PARALYZE / HASTE / REFRESH /
                       REGEN / PROTECT / SHELL)
    Effect dataclass — slot, tier, duration, caster
    ApplyOutcome enum (APPLIED / REFRESHED / DISPLACED / REJECTED)
    ApplyResult dataclass
    StatusSlotManager
        .apply(target_id, effect)
        .active_slots(target_id) -> tuple[Effect, ...]
        .clear_slot(target_id, category)
        .tick(target_id, now_seconds) — drops expired
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SlotCategory(str, enum.Enum):
    BIO_FAMILY = "bio_family"
    DIA_FAMILY = "dia_family"
    BURN_DOT = "burn_dot"           # elemental DoTs
    SLOW = "slow"
    PARALYZE = "paralyze"
    BLIND = "blind"
    SILENCE = "silence"
    POISON = "poison"
    HASTE = "haste"
    REFRESH = "refresh"
    REGEN = "regen"
    PROTECT = "protect"
    SHELL = "shell"
    STONESKIN = "stoneskin"


class ApplyOutcome(str, enum.Enum):
    APPLIED = "applied"           # slot was empty
    REFRESHED = "refreshed"       # same tier extended duration
    DISPLACED = "displaced"       # higher tier replaced lower
    REJECTED = "rejected"         # lower tier hit higher


@dataclasses.dataclass(frozen=True)
class Effect:
    target_id: str
    category: SlotCategory
    effect_id: str                # canonical id (bio_iii etc)
    tier: int                     # higher = stronger
    duration_seconds: int
    caster_id: t.Optional[str] = None
    applied_at_seconds: float = 0.0
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class ApplyResult:
    outcome: ApplyOutcome
    effect: t.Optional[Effect] = None
    displaced_effect: t.Optional[Effect] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class StatusSlotManager:
    # (target_id, category) -> currently held Effect
    _slots: dict[
        tuple[str, SlotCategory], Effect,
    ] = dataclasses.field(default_factory=dict)

    def apply(self, *, effect: Effect) -> ApplyResult:
        if effect.duration_seconds <= 0:
            return ApplyResult(
                outcome=ApplyOutcome.REJECTED,
                reason="duration must be positive",
            )
        if effect.tier < 0:
            return ApplyResult(
                outcome=ApplyOutcome.REJECTED,
                reason="tier must be non-negative",
            )
        key = (effect.target_id, effect.category)
        existing = self._slots.get(key)
        if existing is None:
            self._slots[key] = effect
            return ApplyResult(
                outcome=ApplyOutcome.APPLIED, effect=effect,
            )
        if effect.tier > existing.tier:
            self._slots[key] = effect
            return ApplyResult(
                outcome=ApplyOutcome.DISPLACED,
                effect=effect,
                displaced_effect=existing,
            )
        if effect.tier == existing.tier:
            # Refresh: extend with the new caster + duration
            refreshed = dataclasses.replace(
                effect,
                applied_at_seconds=effect.applied_at_seconds,
            )
            self._slots[key] = refreshed
            return ApplyResult(
                outcome=ApplyOutcome.REFRESHED,
                effect=refreshed,
                displaced_effect=existing,
            )
        return ApplyResult(
            outcome=ApplyOutcome.REJECTED,
            effect=None,
            displaced_effect=None,
            reason=(
                f"existing tier {existing.tier} > new "
                f"tier {effect.tier}"
            ),
        )

    def active_slots(
        self, target_id: str,
    ) -> tuple[Effect, ...]:
        return tuple(
            e for (tid, _cat), e in self._slots.items()
            if tid == target_id
        )

    def get_slot(
        self, *, target_id: str, category: SlotCategory,
    ) -> t.Optional[Effect]:
        return self._slots.get((target_id, category))

    def clear_slot(
        self, *, target_id: str, category: SlotCategory,
    ) -> bool:
        return self._slots.pop(
            (target_id, category), None,
        ) is not None

    def tick(
        self, *, target_id: str, now_seconds: float,
    ) -> tuple[Effect, ...]:
        """Drop effects whose duration has elapsed; return them."""
        dropped: list[Effect] = []
        for key in list(self._slots.keys()):
            tid, cat = key
            if tid != target_id:
                continue
            e = self._slots[key]
            if (
                e.applied_at_seconds + e.duration_seconds
            ) <= now_seconds:
                dropped.append(e)
                del self._slots[key]
        return tuple(dropped)

    def total_active(self) -> int:
        return len(self._slots)


__all__ = [
    "SlotCategory", "ApplyOutcome",
    "Effect", "ApplyResult",
    "StatusSlotManager",
]
