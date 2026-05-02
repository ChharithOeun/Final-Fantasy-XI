"""Scholar Light/Dark Arts + stratagem charges.

SCH at level 1 has no Arts active. At level 10 they unlock both
Light and Dark Arts; only one can be active at a time. Each Art
modifies certain spell families:

* Light Arts: enhancing/healing/cure spells get reduced cost +
  potency bonus. Dark spells suffer a penalty.
* Dark Arts: enfeebling + elemental nuke spells get cost
  reduction + potency. Light spells suffer.

Stratagems are ability charges (max 5, regen 1/120s) the SCH
spends to apply Light/Dark Arts modifiers to ONE spell:

Light Arts stratagems:
  PENURY    -> half MP cost on next spell
  ACCESSION -> next AoE buff hits whole alliance
  RAPTURE   -> next cure +50% potency
  ALTRUISM  -> next cure also targets caster
  TRANQUIL_HEART -> next cure builds less enmity

Dark Arts stratagems:
  PARSIMONY  -> half MP on next dark spell
  MANIFESTATION -> next nuke is AoE
  EBULLIENCE -> next nuke +50% potency
  FOCALIZATION -> next nuke builds less enmity
  EQUANIMITY -> next enfeeble +50% accuracy

Public surface
--------------
    ArtMode enum (NONE / LIGHT / DARK)
    StratagemKind enum
    ScholarState
        .switch_art(mode) -> bool
        .tick(dt_seconds) -> charges regen
        .use_stratagem(kind) -> StrategyResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_STRATAGEMS = 5
STRATAGEM_REGEN_SECONDS = 120


class ArtMode(str, enum.Enum):
    NONE = "none"
    LIGHT = "light"
    DARK = "dark"


class StratagemKind(str, enum.Enum):
    # Light Arts
    PENURY = "penury"
    ACCESSION = "accession"
    RAPTURE = "rapture"
    ALTRUISM = "altruism"
    TRANQUIL_HEART = "tranquil_heart"
    # Dark Arts
    PARSIMONY = "parsimony"
    MANIFESTATION = "manifestation"
    EBULLIENCE = "ebullience"
    FOCALIZATION = "focalization"
    EQUANIMITY = "equanimity"


_LIGHT_STRATAGEMS = {
    StratagemKind.PENURY,
    StratagemKind.ACCESSION,
    StratagemKind.RAPTURE,
    StratagemKind.ALTRUISM,
    StratagemKind.TRANQUIL_HEART,
}


_DARK_STRATAGEMS = {
    StratagemKind.PARSIMONY,
    StratagemKind.MANIFESTATION,
    StratagemKind.EBULLIENCE,
    StratagemKind.FOCALIZATION,
    StratagemKind.EQUANIMITY,
}


@dataclasses.dataclass(frozen=True)
class StratagemResult:
    accepted: bool
    charges_remaining: int = 0
    next_spell_modifier: t.Optional[StratagemKind] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class ScholarState:
    player_id: str
    art_mode: ArtMode = ArtMode.NONE
    charges: int = MAX_STRATAGEMS
    _regen_carry: float = 0.0   # accumulated time toward next charge
    queued_modifier: t.Optional[StratagemKind] = None

    # ------------------------------------------------------------------
    # Art mode
    # ------------------------------------------------------------------
    def switch_art(self, *, mode: ArtMode) -> bool:
        if mode == self.art_mode:
            return False
        self.art_mode = mode
        # Switching mode clears any pending modifier
        self.queued_modifier = None
        return True

    # ------------------------------------------------------------------
    # Time-driven charge regen
    # ------------------------------------------------------------------
    def tick(self, *, dt_seconds: float) -> None:
        if self.charges >= MAX_STRATAGEMS:
            self._regen_carry = 0.0
            return
        self._regen_carry += dt_seconds
        while self._regen_carry >= STRATAGEM_REGEN_SECONDS:
            self._regen_carry -= STRATAGEM_REGEN_SECONDS
            self.charges = min(MAX_STRATAGEMS, self.charges + 1)
            if self.charges >= MAX_STRATAGEMS:
                self._regen_carry = 0.0
                break

    # ------------------------------------------------------------------
    # Use a stratagem
    # ------------------------------------------------------------------
    def use_stratagem(self, *, kind: StratagemKind) -> StratagemResult:
        if self.charges <= 0:
            return StratagemResult(False, reason="no charges")
        if kind in _LIGHT_STRATAGEMS and self.art_mode != ArtMode.LIGHT:
            return StratagemResult(
                False, reason="requires Light Arts active",
            )
        if kind in _DARK_STRATAGEMS and self.art_mode != ArtMode.DARK:
            return StratagemResult(
                False, reason="requires Dark Arts active",
            )
        self.charges -= 1
        self.queued_modifier = kind
        return StratagemResult(
            accepted=True,
            charges_remaining=self.charges,
            next_spell_modifier=kind,
        )

    # ------------------------------------------------------------------
    # Consume the queued modifier when a spell goes off
    # ------------------------------------------------------------------
    def consume_modifier(self) -> t.Optional[StratagemKind]:
        m = self.queued_modifier
        self.queued_modifier = None
        return m


__all__ = [
    "MAX_STRATAGEMS", "STRATAGEM_REGEN_SECONDS",
    "ArtMode", "StratagemKind", "StratagemResult",
    "ScholarState",
]
