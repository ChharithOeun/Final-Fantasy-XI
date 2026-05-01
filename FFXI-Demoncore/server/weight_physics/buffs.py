"""Weight-modifying buffs and debuffs.

Per WEIGHT_PHYSICS.md, spells/songs/abilities adjust *effective*
weight (not literal gear weight). The character's gear stays the
same; the math sees a different number. Stacking is multiplicative.

Example: WAR at gear_weight=120 with Haste III (-40%) + March III
(-15%) effective_weight = 120 * 0.6 * 0.85 = 61.2 — almost like
a NIN.

Gravity (+50%) hits heavy classes hardest by design: a WAR at
gear=120 under Gravity = 180 (walking pace); a WHM at gear=12
under Gravity = 18 (barely affected).
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class WeightModifier:
    """One buff or debuff that scales effective weight."""
    name: str
    multiplier: float          # 0.6 = -40%, 1.5 = +50%
    is_debuff: bool = False    # True for Gravity, Slow, Heavy
    duration_seconds: t.Optional[float] = None   # None = until removed
    notes: str = ""


# Per the design doc weight-modifying tables.
KNOWN_MODIFIERS: dict[str, WeightModifier] = {
    # Reducers (lift effective weight)
    "haste":          WeightModifier("haste",          0.80, notes="-20%"),
    "haste_ii":       WeightModifier("haste_ii",       0.70, notes="-30%"),
    "haste_iii":      WeightModifier("haste_iii",      0.60, notes="-40%"),
    "ballad_i":       WeightModifier("ballad_i",       0.92, notes="-8%"),
    "ballad_ii":      WeightModifier("ballad_ii",      0.84, notes="-16%"),
    "mazurka":        WeightModifier("mazurka",        0.75, notes="mounted -25%"),
    "hermes_quencher":WeightModifier("hermes_quencher",0.90, notes="-10%"),
    "refresh":        WeightModifier("refresh",        0.95, notes="-5%"),
    "march_i":        WeightModifier("march_i",        0.95, notes="-5%"),
    "march_ii":       WeightModifier("march_ii",       0.90, notes="-10%"),
    "march_iii":      WeightModifier("march_iii",      0.85, notes="-15%"),
    "mnk_mantra":     WeightModifier("mnk_mantra",     0.75, notes="-25%"),
    "thf_flee":       WeightModifier("thf_flee",       0.10, duration_seconds=60,
                                       notes="-90% for 60s"),

    # Increasers (worsen effective weight)
    "gravity":        WeightModifier("gravity",        1.50, is_debuff=True,
                                       notes="+50% (hits heavy hardest)"),
    "slow":           WeightModifier("slow",           1.25, is_debuff=True),
    "slow_ii":        WeightModifier("slow_ii",        1.50, is_debuff=True),
    "heavy":          WeightModifier("heavy",          1.35, is_debuff=True,
                                       notes="Earth-EM proc"),
    "encumber_stack": WeightModifier("encumber_stack", 1.10, is_debuff=True,
                                       notes="+10% per stack"),
    "mounted_no_mazurka": WeightModifier("mounted_no_mazurka", 1.20,
                                            is_debuff=True,
                                            notes="+20% (slower mounted)"),
}


class WeightModifierStack:
    """Per-character active modifier stack.

    Composes buffs/debuffs multiplicatively. Add modifiers as they
    proc, remove on expiration / dispel. Query effective_weight() to
    feed the formulas.
    """

    def __init__(self) -> None:
        # Each entry: (modifier, expires_at_or_None, stack_count)
        self._active: list[tuple[WeightModifier, t.Optional[float], int]] = []

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def apply(self,
               name_or_modifier: t.Union[str, WeightModifier],
               *,
               now: float = 0,
               stacks: int = 1) -> None:
        """Add a modifier. Looks up by name from KNOWN_MODIFIERS if
        a string is provided; otherwise uses the supplied modifier
        directly. Re-applying refreshes the duration. Stack-able mods
        (encumber) accumulate stack_count."""
        if isinstance(name_or_modifier, str):
            mod = KNOWN_MODIFIERS.get(name_or_modifier)
            if mod is None:
                raise KeyError(f"unknown modifier: {name_or_modifier}")
        else:
            mod = name_or_modifier

        expires_at: t.Optional[float] = None
        if mod.duration_seconds is not None:
            expires_at = now + mod.duration_seconds

        # If we already have this modifier, refresh / accumulate
        for i, (existing, _, count) in enumerate(self._active):
            if existing.name == mod.name:
                self._active[i] = (mod, expires_at, count + stacks)
                return
        self._active.append((mod, expires_at, stacks))

    def remove(self, name: str) -> bool:
        """Remove a modifier (e.g. dispelled). Returns True if removed."""
        for i, (mod, _, _) in enumerate(self._active):
            if mod.name == name:
                self._active.pop(i)
                return True
        return False

    def tick_expirations(self, *, now: float) -> list[str]:
        """Remove expired entries. Returns names of removed modifiers."""
        kept: list[tuple[WeightModifier, t.Optional[float], int]] = []
        removed: list[str] = []
        for mod, expires_at, count in self._active:
            if expires_at is not None and expires_at <= now:
                removed.append(mod.name)
                continue
            kept.append((mod, expires_at, count))
        self._active = kept
        return removed

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------

    def stack_multiplier(self) -> float:
        """The combined multiplicative factor across all active mods.

        Stack-able mods (encumber) compound their multiplier per stack:
        encumber × 3 = 1.10^3 = 1.331."""
        product = 1.0
        for mod, _, count in self._active:
            product *= mod.multiplier ** count
        return product

    def effective_weight(self, base_weight: float) -> float:
        return base_weight * self.stack_multiplier()

    def has(self, name: str) -> bool:
        return any(m.name == name for m, _, _ in self._active)

    def stacks_of(self, name: str) -> int:
        for m, _, count in self._active:
            if m.name == name:
                return count
        return 0

    def active_names(self) -> list[str]:
        return [m.name for m, _, _ in self._active]
