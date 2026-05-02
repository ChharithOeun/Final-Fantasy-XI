"""Status effects — canonical buff/debuff catalog + per-target tracker.

Effects sit in named slots (POISON, PARALYZE, SILENCE, etc). Each
slot has stack rules:

  OVERWRITE  - new application replaces the old (most debuffs)
  REFRESH    - resets the timer; magnitude unchanged (e.g. Regen)
  STACK      - magnitudes add (rare; e.g. some shadow effects)
  IGNORE     - new application drops if effect already active

Caller drives the clock: tick(now_tick) advances all timers and
expires anything past its end. apply() honors stack rules.

Public surface
--------------
    StatusKind enum (POISON, PARALYZE, etc.)
    StackRule enum
    StatusEffectSpec immutable catalog entry
    EFFECT_CATALOG sample
    StatusInstance live record
    StatusTable per-target
        .apply(spec, magnitude, duration, now_tick)
        .has(kind) / .magnitude(kind)
        .tick(now_tick) -> tuple[StatusKind, ...] expired this tick
        .remove(kind)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class StatusKind(str, enum.Enum):
    # Debuffs
    POISON = "poison"
    PARALYZE = "paralyze"
    SILENCE = "silence"
    SLEEP = "sleep"
    BIND = "bind"
    GRAVITY = "gravity"
    SLOW = "slow"
    BLIND = "blind"
    AMNESIA = "amnesia"
    PETRIFY = "petrify"
    CURSE = "curse"
    DOOM = "doom"
    BURN = "burn"
    FROST = "frost"
    CHOKE = "choke"
    RASP = "rasp"
    SHOCK = "shock"
    DROWN = "drown"
    DIA = "dia"
    BIO = "bio"
    # Buffs
    PROTECT = "protect"
    SHELL = "shell"
    HASTE = "haste"
    REGEN = "regen"
    REFRESH = "refresh"
    STONESKIN = "stoneskin"
    BLINK = "blink"
    AQUAVEIL = "aquaveil"
    PHALANX = "phalanx"
    REPRISAL = "reprisal"
    BERSERK = "berserk"
    DEFENDER = "defender"


class StackRule(str, enum.Enum):
    OVERWRITE = "overwrite"
    REFRESH = "refresh"
    STACK = "stack"
    IGNORE = "ignore"


@dataclasses.dataclass(frozen=True)
class StatusEffectSpec:
    kind: StatusKind
    label: str
    is_buff: bool
    stack_rule: StackRule
    description: str = ""


# Sample catalog — designers add to this dict by registering more.
EFFECT_CATALOG: dict[StatusKind, StatusEffectSpec] = {
    StatusKind.POISON: StatusEffectSpec(
        StatusKind.POISON, "Poison",
        is_buff=False, stack_rule=StackRule.OVERWRITE),
    StatusKind.PARALYZE: StatusEffectSpec(
        StatusKind.PARALYZE, "Paralyze",
        is_buff=False, stack_rule=StackRule.OVERWRITE),
    StatusKind.SILENCE: StatusEffectSpec(
        StatusKind.SILENCE, "Silence",
        is_buff=False, stack_rule=StackRule.OVERWRITE),
    StatusKind.SLEEP: StatusEffectSpec(
        StatusKind.SLEEP, "Sleep",
        is_buff=False, stack_rule=StackRule.OVERWRITE),
    StatusKind.SLOW: StatusEffectSpec(
        StatusKind.SLOW, "Slow",
        is_buff=False, stack_rule=StackRule.OVERWRITE),
    StatusKind.BLIND: StatusEffectSpec(
        StatusKind.BLIND, "Blind",
        is_buff=False, stack_rule=StackRule.OVERWRITE),
    StatusKind.DOOM: StatusEffectSpec(
        StatusKind.DOOM, "Doom",
        is_buff=False, stack_rule=StackRule.IGNORE,
        description="Cannot be reapplied while active."),
    StatusKind.DIA: StatusEffectSpec(
        StatusKind.DIA, "Dia",
        is_buff=False, stack_rule=StackRule.OVERWRITE),
    StatusKind.BIO: StatusEffectSpec(
        StatusKind.BIO, "Bio",
        is_buff=False, stack_rule=StackRule.OVERWRITE),
    StatusKind.PROTECT: StatusEffectSpec(
        StatusKind.PROTECT, "Protect",
        is_buff=True, stack_rule=StackRule.OVERWRITE),
    StatusKind.SHELL: StatusEffectSpec(
        StatusKind.SHELL, "Shell",
        is_buff=True, stack_rule=StackRule.OVERWRITE),
    StatusKind.HASTE: StatusEffectSpec(
        StatusKind.HASTE, "Haste",
        is_buff=True, stack_rule=StackRule.OVERWRITE),
    StatusKind.REGEN: StatusEffectSpec(
        StatusKind.REGEN, "Regen",
        is_buff=True, stack_rule=StackRule.REFRESH),
    StatusKind.REFRESH: StatusEffectSpec(
        StatusKind.REFRESH, "Refresh",
        is_buff=True, stack_rule=StackRule.REFRESH),
    StatusKind.STONESKIN: StatusEffectSpec(
        StatusKind.STONESKIN, "Stoneskin",
        is_buff=True, stack_rule=StackRule.OVERWRITE),
    StatusKind.BLINK: StatusEffectSpec(
        StatusKind.BLINK, "Blink",
        is_buff=True, stack_rule=StackRule.STACK,
        description="Stacks shadow count up to 3."),
}


@dataclasses.dataclass
class StatusInstance:
    kind: StatusKind
    magnitude: int
    applied_at_tick: int
    expires_at_tick: int        # exclusive
    source_actor_id: str = ""


@dataclasses.dataclass
class StatusTable:
    """Per-target status records."""
    target_id: str
    _effects: dict[StatusKind, StatusInstance] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def apply(
        self, *,
        kind: StatusKind,
        magnitude: int,
        duration_seconds: int,
        now_tick: int,
        source_actor_id: str = "",
    ) -> bool:
        """Apply per stack rule. Returns True if applied/refreshed."""
        spec = EFFECT_CATALOG.get(kind)
        if spec is None:
            raise ValueError(f"unknown status: {kind}")
        if duration_seconds < 0:
            raise ValueError("duration must be >= 0")
        existing = self._effects.get(kind)
        # Existing-and-not-expired check
        if existing is not None and existing.expires_at_tick > now_tick:
            if spec.stack_rule == StackRule.IGNORE:
                return False
            if spec.stack_rule == StackRule.REFRESH:
                existing.expires_at_tick = now_tick + duration_seconds
                return True
            if spec.stack_rule == StackRule.STACK:
                existing.magnitude += magnitude
                existing.expires_at_tick = max(
                    existing.expires_at_tick,
                    now_tick + duration_seconds,
                )
                return True
            # OVERWRITE
        self._effects[kind] = StatusInstance(
            kind=kind, magnitude=magnitude,
            applied_at_tick=now_tick,
            expires_at_tick=now_tick + duration_seconds,
            source_actor_id=source_actor_id,
        )
        return True

    def has(self, kind: StatusKind, *, now_tick: int) -> bool:
        e = self._effects.get(kind)
        if e is None:
            return False
        return e.expires_at_tick > now_tick

    def magnitude(
        self, kind: StatusKind, *, now_tick: int,
    ) -> int:
        e = self._effects.get(kind)
        if e is None or e.expires_at_tick <= now_tick:
            return 0
        return e.magnitude

    def remove(self, kind: StatusKind) -> bool:
        if kind in self._effects:
            del self._effects[kind]
            return True
        return False

    def tick(self, *, now_tick: int) -> tuple[StatusKind, ...]:
        """Expire effects whose end <= now_tick. Returns expired kinds."""
        expired: list[StatusKind] = []
        for kind, e in list(self._effects.items()):
            if e.expires_at_tick <= now_tick:
                expired.append(kind)
                del self._effects[kind]
        return tuple(expired)

    def active_kinds(self, *, now_tick: int) -> tuple[StatusKind, ...]:
        return tuple(
            k for k, e in self._effects.items()
            if e.expires_at_tick > now_tick
        )


__all__ = [
    "StatusKind", "StackRule", "StatusEffectSpec",
    "EFFECT_CATALOG",
    "StatusInstance", "StatusTable",
]
