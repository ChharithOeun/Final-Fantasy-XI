"""Minimap difficulty check — click mob dot, get con + element.

When a player clicks (or hovers) a mob's dot on the new minimap,
this module produces the canonical FFXI 'check' verdict — Too
Weak / Easy Prey / Decent Challenge / Even Match / Tough /
Very Tough / Incredibly Tough. Plus an element vulnerability
hint (when player has high enough enfeebling magic skill) and
a defensive lean (DEF or EVA notably high).

Distinct from mob_resistances (the mechanic) and combat_outcomes
(the math): this is the player-facing CHECK string, plus extra
flags that gate revealing more info to higher-skilled players.

Public surface
--------------
    ConVerdict enum
    DefenseLean enum
    DifficultyCheck dataclass
    MinimapDifficultyChecker
        .register_mob(mob_id, level, defense_lean, ...)
        .check_mob(viewer_level, mob_id,
                   enfeebling_skill_for_element_hint=False)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Element hint gate: skill needed to see element vulnerability.
ELEMENT_HINT_SKILL_GATE = 200


class ConVerdict(str, enum.Enum):
    TOO_WEAK = "too_weak"          # gray
    EASY_PREY = "easy_prey"        # blue
    DECENT_CHALLENGE = "decent_challenge"  # green
    EVEN_MATCH = "even_match"      # yellow
    TOUGH = "tough"                # orange
    VERY_TOUGH = "very_tough"      # red
    INCREDIBLY_TOUGH = "incredibly_tough"  # bright red


class DefenseLean(str, enum.Enum):
    BALANCED = "balanced"
    HEAVY_DEF = "heavy_def"        # high physical DEF
    HIGH_EVA = "high_eva"          # high evasion
    HIGH_MDEF = "high_mdef"        # high magic defense
    GLASS_CANNON = "glass_cannon"  # low DEF, high attack


class ElementHint(str, enum.Enum):
    NONE = "none"
    FIRE = "fire"
    ICE = "ice"
    WIND = "wind"
    EARTH = "earth"
    LIGHTNING = "lightning"
    WATER = "water"
    LIGHT = "light"
    DARK = "dark"


@dataclasses.dataclass(frozen=True)
class MobCard:
    mob_id: str
    level: int
    defense_lean: DefenseLean = DefenseLean.BALANCED
    element_weakness: ElementHint = ElementHint.NONE
    label: str = ""


@dataclasses.dataclass(frozen=True)
class DifficultyCheck:
    mob_id: str
    label: str
    verdict: ConVerdict
    level_delta: int            # mob_level - viewer_level
    defense_lean: DefenseLean
    element_hint: ElementHint   # NONE if gate not met
    note: str = ""


def _verdict_for_delta(delta: int) -> ConVerdict:
    """Match canonical FFXI delta bands."""
    if delta <= -8:
        return ConVerdict.TOO_WEAK
    if delta <= -4:
        return ConVerdict.EASY_PREY
    if delta <= -1:
        return ConVerdict.DECENT_CHALLENGE
    if delta == 0:
        return ConVerdict.EVEN_MATCH
    if delta <= 3:
        return ConVerdict.TOUGH
    if delta <= 7:
        return ConVerdict.VERY_TOUGH
    return ConVerdict.INCREDIBLY_TOUGH


@dataclasses.dataclass
class MinimapDifficultyChecker:
    element_hint_skill_gate: int = ELEMENT_HINT_SKILL_GATE
    _mobs: dict[str, MobCard] = dataclasses.field(
        default_factory=dict,
    )

    def register_mob(
        self, *, mob_id: str, level: int,
        defense_lean: DefenseLean = DefenseLean.BALANCED,
        element_weakness: ElementHint = ElementHint.NONE,
        label: str = "",
    ) -> t.Optional[MobCard]:
        if mob_id in self._mobs:
            return None
        if level < 1:
            return None
        card = MobCard(
            mob_id=mob_id, level=level,
            defense_lean=defense_lean,
            element_weakness=element_weakness,
            label=label or mob_id,
        )
        self._mobs[mob_id] = card
        return card

    def get(
        self, mob_id: str,
    ) -> t.Optional[MobCard]:
        return self._mobs.get(mob_id)

    def check_mob(
        self, *, mob_id: str, viewer_level: int,
        enfeebling_skill: int = 0,
    ) -> t.Optional[DifficultyCheck]:
        card = self._mobs.get(mob_id)
        if card is None:
            return None
        delta = card.level - max(1, viewer_level)
        verdict = _verdict_for_delta(delta)
        # Element hint gate
        if (
            enfeebling_skill >= self.element_hint_skill_gate
            and card.element_weakness != ElementHint.NONE
        ):
            element_hint = card.element_weakness
        else:
            element_hint = ElementHint.NONE
        return DifficultyCheck(
            mob_id=mob_id, label=card.label,
            verdict=verdict, level_delta=delta,
            defense_lean=card.defense_lean,
            element_hint=element_hint,
        )

    def total_mobs(self) -> int:
        return len(self._mobs)


__all__ = [
    "ELEMENT_HINT_SKILL_GATE",
    "ConVerdict", "DefenseLean", "ElementHint",
    "MobCard", "DifficultyCheck",
    "MinimapDifficultyChecker",
]
