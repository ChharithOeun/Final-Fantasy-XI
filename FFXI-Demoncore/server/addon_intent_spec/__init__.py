"""Addon intent spec — the structured 'what do you want' form.

The Lua forge UI walks the player through a series of
questions: which job? which weapons? what modes do you
want toggleable? which food? what spells should auto-
cast at low MP? The answers fill an IntentSpec. The
spec is validated, then the forge renders it into a
working addon Lua file.

Modeled after the canonical RDM.lua GearSwap shape Tart
shared as the reference: weapon set, idle set, offense
modes, lockstyle, macro book/set, food, signature spells.

Why a spec rather than free text: the forge generates
DETERMINISTIC output. The same spec → the same lua,
byte-for-byte. That makes diffs reviewable, makes
"my addon broke after the update" a fix-once-distribute
problem, and lets the repair engine round-trip an
existing file by extracting its spec.

Public surface
--------------
    GearSetEntry dataclass (frozen)
    OffenseMode dataclass (frozen)
    SpellRule dataclass (frozen) — auto-cast rule
    AddonIntentSpec dataclass (mutable)
    SpecValidationResult dataclass (frozen)
    validate(spec) -> SpecValidationResult
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class GearSetEntry:
    set_name: str
    slot_to_item: dict[str, str]   # "main" → "Naegling" etc.


@dataclasses.dataclass(frozen=True)
class OffenseMode:
    mode_name: str        # "TP" / "ACC" / "DT" / "PDL" etc.
    weaponskill_target: str    # the WS this mode optimizes for


@dataclasses.dataclass(frozen=True)
class SpellRule:
    spell_id: str         # "cure_iv", "stoneskin", etc.
    auto_cast_when: str   # opaque trigger description
    target: str           # "self" / "lowest_hp_party" / "main_target"


@dataclasses.dataclass
class AddonIntentSpec:
    addon_id: str
    job: str
    weapon_sets: dict[str, GearSetEntry] = dataclasses.field(
        default_factory=dict,
    )
    offense_modes: list[OffenseMode] = dataclasses.field(
        default_factory=list,
    )
    idle_set: t.Optional[GearSetEntry] = None
    food_item: str = ""
    lockstyle_pallet: str = ""
    macro_book: str = ""
    macro_set: str = ""
    spell_rules: list[SpellRule] = dataclasses.field(
        default_factory=list,
    )
    default_offense_mode: str = ""


@dataclasses.dataclass(frozen=True)
class SpecValidationResult:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def validate(spec: AddonIntentSpec) -> SpecValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not spec.addon_id:
        errors.append("addon_id is required")
    if not spec.job:
        errors.append("job is required")

    # Weapon sets must each have at least a main slot.
    for name, entry in spec.weapon_sets.items():
        if not name:
            errors.append("weapon set with blank name")
            continue
        if "main" not in entry.slot_to_item:
            errors.append(
                f"weapon set '{name}' missing main slot",
            )

    # Offense modes must reference declared weapon sets.
    declared_modes = {m.mode_name for m in spec.offense_modes}
    if spec.default_offense_mode:
        if spec.default_offense_mode not in declared_modes:
            errors.append(
                "default_offense_mode "
                f"'{spec.default_offense_mode}' not in declared modes",
            )

    # Soft warnings — present but not blocking.
    if not spec.idle_set:
        warnings.append("no idle_set defined")
    if not spec.food_item:
        warnings.append("no food_item set — auto-feed will be off")
    if not spec.macro_book:
        warnings.append("no macro_book set")

    # Spell rules must have a target.
    for rule in spec.spell_rules:
        if not rule.spell_id:
            errors.append("spell rule with blank spell_id")
        if not rule.target:
            errors.append(
                f"spell rule '{rule.spell_id}' has blank target",
            )

    return SpecValidationResult(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


__all__ = [
    "GearSetEntry", "OffenseMode", "SpellRule",
    "AddonIntentSpec", "SpecValidationResult", "validate",
]
