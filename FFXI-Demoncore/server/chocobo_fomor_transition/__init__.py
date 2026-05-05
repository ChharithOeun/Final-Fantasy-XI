"""Chocobo fomor transition — death state machine for chocobos.

When a chocobo dies it does NOT respawn. Instead it transitions
permanently into a FOMOR variant of itself: a hostile, undead
echo of the original mount that wanders the world. The original
color shapes the fomor variant's profile (a Red chocobo becomes
a FOMOR_RED, etc.).

Exception: RAINBOW chocobos do NOT transition into a fomor.
Instead, on death they leave behind a RAINBOW R/EX EGG that the
breeder must take through the full hatch + train workflow again
(see chocobo_egg_lifecycle).

Public surface
--------------
    DeathOutcome enum    FOMOR / RAINBOW_EGG_REX
    TransitionResult dataclass
    ChocoboFomorTransition
        .record_death(chocobo_id, color, owner_id, now_seconds)
        .lookup(chocobo_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.chocobo_colors import ChocoboColor


class DeathOutcome(str, enum.Enum):
    FOMOR = "fomor"
    RAINBOW_EGG_REX = "rainbow_egg_rex"


_FOMOR_VARIANT: dict[ChocoboColor, str] = {
    ChocoboColor.YELLOW: "fomor_yellow",
    ChocoboColor.BROWN: "fomor_brown",
    ChocoboColor.LIGHT_BLUE: "fomor_light_blue",
    ChocoboColor.BLUE: "fomor_blue",
    ChocoboColor.LIGHT_PURPLE: "fomor_light_purple",
    ChocoboColor.GREEN: "fomor_green",
    ChocoboColor.RED: "fomor_red",
    ChocoboColor.WHITE: "fomor_white",
    ChocoboColor.GREY: "fomor_grey",
    # RAINBOW intentionally absent — handled separately
}


@dataclasses.dataclass(frozen=True)
class TransitionRecord:
    chocobo_id: str
    color: ChocoboColor
    owner_id: str
    outcome: DeathOutcome
    fomor_variant_id: str
    rex_egg_id: str
    died_at: int


@dataclasses.dataclass(frozen=True)
class TransitionResult:
    accepted: bool
    chocobo_id: str
    outcome: DeathOutcome
    fomor_variant_id: str = ""
    rex_egg_id: str = ""
    reason: t.Optional[str] = None


@dataclasses.dataclass
class ChocoboFomorTransition:
    _records: dict[str, TransitionRecord] = dataclasses.field(
        default_factory=dict,
    )

    def record_death(
        self, *, chocobo_id: str,
        color: ChocoboColor,
        owner_id: str,
        now_seconds: int,
    ) -> TransitionResult:
        if not chocobo_id or not owner_id:
            return TransitionResult(
                False, chocobo_id, DeathOutcome.FOMOR,
                reason="missing chocobo or owner",
            )
        if chocobo_id in self._records:
            return TransitionResult(
                False, chocobo_id, DeathOutcome.FOMOR,
                reason="death already recorded",
            )
        if color == ChocoboColor.RAINBOW:
            rex_id = f"{chocobo_id}_rainbow_rex_egg"
            rec = TransitionRecord(
                chocobo_id=chocobo_id,
                color=color,
                owner_id=owner_id,
                outcome=DeathOutcome.RAINBOW_EGG_REX,
                fomor_variant_id="",
                rex_egg_id=rex_id,
                died_at=now_seconds,
            )
            self._records[chocobo_id] = rec
            return TransitionResult(
                accepted=True,
                chocobo_id=chocobo_id,
                outcome=DeathOutcome.RAINBOW_EGG_REX,
                rex_egg_id=rex_id,
            )
        variant = _FOMOR_VARIANT.get(color)
        if variant is None:
            return TransitionResult(
                False, chocobo_id, DeathOutcome.FOMOR,
                reason="unknown color",
            )
        rec = TransitionRecord(
            chocobo_id=chocobo_id,
            color=color,
            owner_id=owner_id,
            outcome=DeathOutcome.FOMOR,
            fomor_variant_id=variant,
            rex_egg_id="",
            died_at=now_seconds,
        )
        self._records[chocobo_id] = rec
        return TransitionResult(
            accepted=True,
            chocobo_id=chocobo_id,
            outcome=DeathOutcome.FOMOR,
            fomor_variant_id=variant,
        )

    def lookup(
        self, *, chocobo_id: str,
    ) -> t.Optional[TransitionRecord]:
        return self._records.get(chocobo_id)

    def total_records(self) -> int:
        return len(self._records)


__all__ = [
    "DeathOutcome", "TransitionRecord",
    "TransitionResult",
    "ChocoboFomorTransition",
]
