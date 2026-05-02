"""Rune Fencer runes + ward / effusion abilities.

RUN activates elemental runes one at a time. Up to 3 runes
can be active simultaneously (older rune drops off as a 4th
is activated). Each rune has an element and a magic-defense
bonus vs the opposing element.

Wards consume ALL active runes for a self-buff (Vallation,
Valiance, Pflug, etc.). Stronger ward effects per rune count.

Effusions consume ALL active runes for an offensive enspell
or magic burst (Lunge, Swipe, Gambit, Rayke, etc.).

Public surface
--------------
    RuneElement enum (Ignis/Gelus/Flabra/Tellus/Sulpor/Unda/Lux/Tenebrae)
    WardKind / EffusionKind enums
    RunicState
        .activate_rune(element) -> RuneResult
        .ward(kind) -> WardResult       (consumes all runes)
        .effusion(kind) -> EffusionResult (consumes all runes)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_ACTIVE_RUNES = 3


class RuneElement(str, enum.Enum):
    IGNIS = "ignis"           # fire
    GELUS = "gelus"           # ice
    FLABRA = "flabra"         # wind
    TELLUS = "tellus"         # earth
    SULPOR = "sulpor"         # thunder
    UNDA = "unda"             # water
    LUX = "lux"               # light
    TENEBRAE = "tenebrae"     # dark


# Opposing-element table (canonical FFXI element wheel)
_OPPOSING: dict[RuneElement, RuneElement] = {
    RuneElement.IGNIS: RuneElement.UNDA,
    RuneElement.UNDA: RuneElement.IGNIS,
    RuneElement.GELUS: RuneElement.SULPOR,
    RuneElement.SULPOR: RuneElement.GELUS,
    RuneElement.FLABRA: RuneElement.TELLUS,
    RuneElement.TELLUS: RuneElement.FLABRA,
    RuneElement.LUX: RuneElement.TENEBRAE,
    RuneElement.TENEBRAE: RuneElement.LUX,
}


class WardKind(str, enum.Enum):
    VALLATION = "vallation"     # phys def
    VALIANCE = "valiance"       # ally vallation
    PFLUG = "pflug"             # status resist
    BATTUTA = "battuta"         # parry rate
    LIEMENT = "liement"         # absorb element matching rune
    GAMBIT = "gambit"           # mDef boost vs target


class EffusionKind(str, enum.Enum):
    LUNGE = "lunge"             # ranged elemental
    SWIPE = "swipe"             # melee elemental
    GAMBIT = "gambit"           # debuff target by rune element
    RAYKE = "rayke"             # break target's resist


@dataclasses.dataclass(frozen=True)
class RuneResult:
    accepted: bool
    active_after: tuple[RuneElement, ...] = ()
    dropped_oldest: t.Optional[RuneElement] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class WardResult:
    accepted: bool
    runes_consumed: int = 0
    elements: tuple[RuneElement, ...] = ()
    base_potency: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class EffusionResult:
    accepted: bool
    runes_consumed: int = 0
    elements: tuple[RuneElement, ...] = ()
    damage_mult: int = 100   # percent multiplier vs base
    reason: t.Optional[str] = None


@dataclasses.dataclass
class RunicState:
    player_id: str
    _active: list[RuneElement] = dataclasses.field(default_factory=list)

    @property
    def active_runes(self) -> tuple[RuneElement, ...]:
        return tuple(self._active)

    @property
    def rune_count(self) -> int:
        return len(self._active)

    # ------------------------------------------------------------------
    # Activate
    # ------------------------------------------------------------------
    def activate_rune(self, *, element: RuneElement) -> RuneResult:
        dropped = None
        if len(self._active) >= MAX_ACTIVE_RUNES:
            dropped = self._active.pop(0)   # oldest first-in
        self._active.append(element)
        return RuneResult(
            accepted=True,
            active_after=tuple(self._active),
            dropped_oldest=dropped,
        )

    # ------------------------------------------------------------------
    # Wards
    # ------------------------------------------------------------------
    def ward(self, *, kind: WardKind) -> WardResult:
        if not self._active:
            return WardResult(False, reason="no active runes")
        # Per-rune potency: 25 base + 15 per rune.
        n = len(self._active)
        base = 25 + 15 * n
        elements = tuple(self._active)
        self._active.clear()
        return WardResult(
            accepted=True, runes_consumed=n,
            elements=elements, base_potency=base,
        )

    # ------------------------------------------------------------------
    # Effusions
    # ------------------------------------------------------------------
    def effusion(self, *, kind: EffusionKind) -> EffusionResult:
        if not self._active:
            return EffusionResult(False, reason="no active runes")
        n = len(self._active)
        # Damage scales as 100% + 50%*n (so 1 rune = 150%, 3 = 250%)
        mult = 100 + 50 * n
        elements = tuple(self._active)
        self._active.clear()
        return EffusionResult(
            accepted=True, runes_consumed=n,
            elements=elements, damage_mult=mult,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def magic_defense_vs(self, *, attacking_element: RuneElement) -> int:
        """Sum of MDef bonus from runes that oppose the attacker."""
        opposing = _OPPOSING[attacking_element]
        bonus = 0
        for r in self._active:
            if r == opposing:
                bonus += 20
        return bonus


__all__ = [
    "MAX_ACTIVE_RUNES",
    "RuneElement", "WardKind", "EffusionKind",
    "RuneResult", "WardResult", "EffusionResult",
    "RunicState",
]
