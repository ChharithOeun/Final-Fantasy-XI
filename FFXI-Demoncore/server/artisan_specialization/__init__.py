"""Artisan specialization — pick a focus within a craft.

A SMITH (Smithing 100+) reaches a fork: WEAPONSMITH,
ARMORSMITH, or BLACKSMITH (general-purpose, no
specialization, but reduced specialty bonuses). Picking
a specialization grants:
    - Permanent +5 effective skill in your specialty's
      recipe family
    - Permanent -5 effective skill in OTHER families
      (you've focused; the rest atrophies a bit)
    - Access to specialty-only recipes
    - A title and signature etched into your masterwork
      items ("Cid the Weaponsmith")

Specializations per craft (loadable):
    SMITHING       WEAPONSMITH / ARMORSMITH / BLACKSMITH
    GOLDSMITHING   JEWELER / ARTISAN
    LEATHERCRAFT   TANNER / FURRIER
    BONECRAFT      SCRIMSHAW / TOTEMIC
    CLOTHCRAFT     TAILOR / WEAVER
    ALCHEMY        APOTHECARY / ENCHANTER
    COOKING        CHEF / BREWER

Switching specialization is allowed but COSTLY: a 7-day
cooldown lock on your skill level (no gain) and a fee.
The intent is that picking is committal but not
permanent.

Public surface
--------------
    Craft enum
    SpecializationDefinition dataclass (frozen)
    SpecializationGrant dataclass (frozen)
    ArtisanSpecialization
        .register_specialization(definition) -> bool
        .commit(crafter, craft, specialization, now_day)
            -> bool
        .switch(crafter, craft, new_specialization, now_day)
            -> bool
        .effective_skill_modifier(crafter, craft,
                                  recipe_family) -> int
        .current(crafter, craft) -> Optional[str]
        .lockout_until(crafter, craft) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_SWITCH_LOCKOUT_DAYS = 7


class Craft(str, enum.Enum):
    SMITHING = "smithing"
    GOLDSMITHING = "goldsmithing"
    LEATHERCRAFT = "leathercraft"
    BONECRAFT = "bonecraft"
    CLOTHCRAFT = "clothcraft"
    ALCHEMY = "alchemy"
    COOKING = "cooking"


@dataclasses.dataclass(frozen=True)
class SpecializationDefinition:
    craft: Craft
    specialization_id: str
    title: str
    families: tuple[str, ...]    # recipe_family ids in scope
    bonus: int                    # e.g. +5
    penalty: int                  # e.g. -5 outside families


@dataclasses.dataclass(frozen=True)
class SpecializationGrant:
    crafter_id: str
    craft: Craft
    specialization_id: str
    committed_day: int


@dataclasses.dataclass
class _CrafterSpec:
    spec_id: str
    committed_day: int
    lockout_until: int = 0


@dataclasses.dataclass
class ArtisanSpecialization:
    _defs: dict[
        tuple[Craft, str], SpecializationDefinition,
    ] = dataclasses.field(default_factory=dict)
    _grants: dict[
        tuple[str, Craft], _CrafterSpec,
    ] = dataclasses.field(default_factory=dict)

    def register_specialization(
        self, definition: SpecializationDefinition,
    ) -> bool:
        if not definition.specialization_id:
            return False
        if not definition.title:
            return False
        if not definition.families:
            return False
        if definition.bonus < 0 or definition.penalty > 0:
            # bonus must be >=0; penalty as a negative
            # number, so penalty > 0 is the wrong sign
            return False
        key = (definition.craft, definition.specialization_id)
        if key in self._defs:
            return False
        self._defs[key] = definition
        return True

    def commit(
        self, *, crafter_id: str, craft: Craft,
        specialization_id: str, now_day: int,
    ) -> bool:
        if not crafter_id:
            return False
        key = (craft, specialization_id)
        if key not in self._defs:
            return False
        cur_key = (crafter_id, craft)
        if cur_key in self._grants:
            return False  # use switch() to change
        self._grants[cur_key] = _CrafterSpec(
            spec_id=specialization_id,
            committed_day=now_day,
        )
        return True

    def switch(
        self, *, crafter_id: str, craft: Craft,
        new_specialization_id: str, now_day: int,
    ) -> bool:
        cur_key = (crafter_id, craft)
        if cur_key not in self._grants:
            return False
        new_key = (craft, new_specialization_id)
        if new_key not in self._defs:
            return False
        st = self._grants[cur_key]
        if st.spec_id == new_specialization_id:
            return False  # already there
        if now_day < st.lockout_until:
            return False
        st.spec_id = new_specialization_id
        st.committed_day = now_day
        st.lockout_until = now_day + _SWITCH_LOCKOUT_DAYS
        return True

    def effective_skill_modifier(
        self, *, crafter_id: str, craft: Craft,
        recipe_family: str,
    ) -> int:
        cur_key = (crafter_id, craft)
        if cur_key not in self._grants:
            return 0
        st = self._grants[cur_key]
        def_key = (craft, st.spec_id)
        if def_key not in self._defs:
            return 0
        d = self._defs[def_key]
        if recipe_family in d.families:
            return d.bonus
        return d.penalty

    def current(
        self, *, crafter_id: str, craft: Craft,
    ) -> t.Optional[str]:
        cur_key = (crafter_id, craft)
        if cur_key not in self._grants:
            return None
        return self._grants[cur_key].spec_id

    def lockout_until(
        self, *, crafter_id: str, craft: Craft,
    ) -> int:
        cur_key = (crafter_id, craft)
        if cur_key not in self._grants:
            return 0
        return self._grants[cur_key].lockout_until


__all__ = [
    "Craft", "SpecializationDefinition",
    "SpecializationGrant", "ArtisanSpecialization",
]
