"""Arena fortification — pre-battle prep to harden features.

Big battles aren't fought blind. The night before, the
linkshell can shore up the arena: nail planks across
weak walls, lay down anti-frost canvas on the ice
sheet, set timber buttresses against the pillars,
caulk a leaky dam, double-plank the ship hull. Each
fortification consumes crafted materials, requires a
craft skill check, and grants a feature one of:

    HP_BUFF       — feature_hp_max += pct
    ELEMENT_GUARD — multiplier vs a specific element
    BREAK_DELAY   — break event fires AFTER N seconds
                    delay (lets the alliance evacuate)
    CRACK_HEAL    — feature regens HP/sec while
                    DAMAGED but not BROKEN
    COUNTER_GRANT — when the feature breaks, all
                    affected players auto-receive a
                    counter (Featherfall, Float, etc.)

Fortifications are PER-FEATURE, MAX_FORT_PER_FEATURE
stack, decay over time (the planks rot), and require
a fresh prep window before the next attempt. Players
who arrive late can't fortify — the prep window opens
and closes BEFORE the boss spawns.

Public surface
--------------
    FortificationKind enum
    Fortification dataclass (frozen)
    PrepResult dataclass (frozen)
    ArenaFortification
        .open_prep_window(arena_id, opens_at, closes_at)
        .submit(arena_id, feature_id, kind, magnitude,
                materials_spent, craft_skill, now_seconds)
            -> PrepResult
        .effective_hp_max(arena_id, feature_id, base_hp_max)
            -> int
        .element_mult(arena_id, feature_id, element) -> float
        .break_delay_seconds(arena_id, feature_id) -> int
        .counter_grant(arena_id, feature_id) -> Optional[str]
        .clear_arena(arena_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class FortificationKind(str, enum.Enum):
    HP_BUFF = "hp_buff"
    ELEMENT_GUARD = "element_guard"
    BREAK_DELAY = "break_delay"
    CRACK_HEAL = "crack_heal"
    COUNTER_GRANT = "counter_grant"


# Per-feature stack cap so a single feature doesn't soak
# the whole alliance's craft budget.
MAX_FORT_PER_FEATURE = 4

# Minimum craft skill required to fortify (rough proxy
# for a guild rank gate). Below this, the prep is wasted.
MIN_CRAFT_SKILL = 60

# Element guard cap — even fully fortified, an element
# multiplier can't go below 0.10 (10% damage taken). Boss
# fights need to remain dangerous.
MIN_ELEMENT_MULT_AFTER_GUARD = 0.10


@dataclasses.dataclass(frozen=True)
class Fortification:
    feature_id: str
    kind: FortificationKind
    magnitude: int          # interpretation depends on kind
    element: t.Optional[str] = None         # for ELEMENT_GUARD
    counter_id: t.Optional[str] = None      # for COUNTER_GRANT
    expires_at: int = 0     # absolute now_seconds


@dataclasses.dataclass(frozen=True)
class PrepResult:
    accepted: bool
    feature_id: str = ""
    kind: t.Optional[FortificationKind] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _PrepWindow:
    opens_at: int
    closes_at: int


@dataclasses.dataclass
class ArenaFortification:
    _windows: dict[str, _PrepWindow] = dataclasses.field(default_factory=dict)
    # arena_id -> feature_id -> list[Fortification]
    _forts: dict[str, dict[str, list[Fortification]]] = dataclasses.field(
        default_factory=dict,
    )

    def open_prep_window(
        self, *, arena_id: str,
        opens_at: int, closes_at: int,
    ) -> bool:
        if not arena_id or closes_at <= opens_at:
            return False
        self._windows[arena_id] = _PrepWindow(
            opens_at=opens_at, closes_at=closes_at,
        )
        return True

    def submit(
        self, *, arena_id: str, feature_id: str,
        kind: FortificationKind, magnitude: int,
        materials_spent: int, craft_skill: int,
        now_seconds: int,
        element: t.Optional[str] = None,
        counter_id: t.Optional[str] = None,
        expires_at: t.Optional[int] = None,
    ) -> PrepResult:
        win = self._windows.get(arena_id)
        if win is None:
            return PrepResult(False, reason="no prep window")
        if now_seconds < win.opens_at:
            return PrepResult(False, reason="prep window not open")
        if now_seconds >= win.closes_at:
            return PrepResult(False, reason="prep window closed")
        if not feature_id:
            return PrepResult(False, reason="blank feature")
        if magnitude <= 0:
            return PrepResult(False, reason="non-positive magnitude")
        if materials_spent <= 0:
            return PrepResult(False, reason="no materials")
        if craft_skill < MIN_CRAFT_SKILL:
            return PrepResult(False, reason="craft skill too low")
        if kind == FortificationKind.ELEMENT_GUARD and not element:
            return PrepResult(False, reason="element required")
        if kind == FortificationKind.COUNTER_GRANT and not counter_id:
            return PrepResult(False, reason="counter_id required")
        feat_bag = self._forts.setdefault(arena_id, {}).setdefault(
            feature_id, [],
        )
        if len(feat_bag) >= MAX_FORT_PER_FEATURE:
            return PrepResult(False, reason="fort stack cap reached")
        eff_expires = expires_at if expires_at is not None else (
            win.closes_at + 4 * 3600   # 4 hours past close = generous
        )
        feat_bag.append(Fortification(
            feature_id=feature_id, kind=kind, magnitude=magnitude,
            element=element, counter_id=counter_id,
            expires_at=eff_expires,
        ))
        return PrepResult(
            accepted=True, feature_id=feature_id, kind=kind,
        )

    def _active_forts(
        self, *, arena_id: str, feature_id: str,
        now_seconds: int = 10**9,
    ) -> list[Fortification]:
        bag = self._forts.get(arena_id, {}).get(feature_id, [])
        return [f for f in bag if now_seconds < f.expires_at]

    def effective_hp_max(
        self, *, arena_id: str, feature_id: str,
        base_hp_max: int, now_seconds: int = 10**9,
    ) -> int:
        forts = self._active_forts(
            arena_id=arena_id, feature_id=feature_id,
            now_seconds=now_seconds,
        )
        bonus_pct = sum(
            f.magnitude for f in forts
            if f.kind == FortificationKind.HP_BUFF
        )
        return base_hp_max + (base_hp_max * bonus_pct // 100)

    def element_mult(
        self, *, arena_id: str, feature_id: str, element: str,
        base: float = 1.0, now_seconds: int = 10**9,
    ) -> float:
        forts = self._active_forts(
            arena_id=arena_id, feature_id=feature_id,
            now_seconds=now_seconds,
        )
        eff = base
        for f in forts:
            if f.kind != FortificationKind.ELEMENT_GUARD:
                continue
            if f.element != element:
                continue
            # magnitude is the percent reduction
            eff = eff * max(0.0, 1.0 - f.magnitude / 100.0)
        return max(MIN_ELEMENT_MULT_AFTER_GUARD, eff)

    def break_delay_seconds(
        self, *, arena_id: str, feature_id: str,
        now_seconds: int = 10**9,
    ) -> int:
        forts = self._active_forts(
            arena_id=arena_id, feature_id=feature_id,
            now_seconds=now_seconds,
        )
        return sum(
            f.magnitude for f in forts
            if f.kind == FortificationKind.BREAK_DELAY
        )

    def crack_heal_per_second(
        self, *, arena_id: str, feature_id: str,
        now_seconds: int = 10**9,
    ) -> int:
        forts = self._active_forts(
            arena_id=arena_id, feature_id=feature_id,
            now_seconds=now_seconds,
        )
        return sum(
            f.magnitude for f in forts
            if f.kind == FortificationKind.CRACK_HEAL
        )

    def counter_grant(
        self, *, arena_id: str, feature_id: str,
        now_seconds: int = 10**9,
    ) -> t.Optional[str]:
        forts = self._active_forts(
            arena_id=arena_id, feature_id=feature_id,
            now_seconds=now_seconds,
        )
        for f in forts:
            if f.kind == FortificationKind.COUNTER_GRANT and f.counter_id:
                return f.counter_id
        return None

    def clear_arena(self, *, arena_id: str) -> bool:
        if arena_id in self._forts:
            del self._forts[arena_id]
        if arena_id in self._windows:
            del self._windows[arena_id]
        return True


__all__ = [
    "FortificationKind", "Fortification", "PrepResult",
    "ArenaFortification",
    "MAX_FORT_PER_FEATURE", "MIN_CRAFT_SKILL",
    "MIN_ELEMENT_MULT_AFTER_GUARD",
]
