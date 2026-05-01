"""Catalog query API — the menu boss authors and encounter_gen read.

Per MOB_CLASS_LIBRARY.md: 'The library is the menu. Boss authors
pick a class, override specifics, and ship a new boss in 4-6 hours.'

This module is the API on top of families.py + sub_variants.py.
"""
from __future__ import annotations

import typing as t

from .families import FAMILIES, Element, FamilyId, MobFamily
from .sub_variants import (
    SUB_VARIANTS,
    MobRole,
    SubVariant,
    variants_in_family,
)


def families_weak_to(element: Element) -> tuple[MobFamily, ...]:
    """Reverse lookup: which families take 1.25x from this element?"""
    return tuple(f for f in FAMILIES.values() if element in f.weak_to)


def families_strong_vs(element: Element) -> tuple[MobFamily, ...]:
    """Reverse lookup: which families resist this element (0.75x)?"""
    return tuple(f for f in FAMILIES.values() if element in f.strong_vs)


def families_with_affinity(element: Element) -> tuple[MobFamily, ...]:
    """Reverse lookup: which families cast this element themselves?"""
    return tuple(f for f in FAMILIES.values() if f.affinity == element)


def variants_in_level_band(*,
                                level_min: int,
                                level_max: int
                                ) -> tuple[SubVariant, ...]:
    """All sub-variants whose level band overlaps the requested range."""
    if level_min > level_max:
        raise ValueError("level_min cannot exceed level_max")
    return tuple(
        sv for sv in SUB_VARIANTS.values()
        if not (sv.level_max < level_min or sv.level_min > level_max)
    )


def variants_with_role(role: MobRole) -> tuple[SubVariant, ...]:
    return tuple(sv for sv in SUB_VARIANTS.values() if sv.role == role)


def healers_for_family(family: FamilyId) -> tuple[SubVariant, ...]:
    """Mob healers eligible for intervention timing per
    INTERVENTION_MB.md mob-symmetry rules."""
    return tuple(sv for sv in variants_in_family(family)
                  if sv.role == MobRole.HEALER)


def boss_grade_variants() -> tuple[SubVariant, ...]:
    """Sub-variants that qualify as boss-grade encounters.

    Used by boss_critic to seed phase rules from the catalog.
    """
    boss_roles = {
        MobRole.MID_BOSS,
        MobRole.NM,
        MobRole.ENDGAME_NM,
    }
    return tuple(sv for sv in SUB_VARIANTS.values()
                  if sv.role in boss_roles)


def encounter_composition(*,
                              level: int,
                              size: int = 4
                              ) -> tuple[SubVariant, ...]:
    """Pick `size` variants whose level band brackets `level`.

    Bias toward including a healer if available, then a frontline,
    then fillers. The encounter_gen module composes spawn lists by
    calling this then layering AI-density tier assignments.
    """
    if size < 1:
        raise ValueError("size must be >= 1")
    pool = variants_in_level_band(level_min=level, level_max=level)
    if not pool:
        return ()
    out: list[SubVariant] = []
    seen_roles: set[MobRole] = set()

    # Bias-1: include a healer if any
    for sv in pool:
        if sv.role == MobRole.HEALER and sv not in out:
            out.append(sv)
            seen_roles.add(sv.role)
            break

    # Bias-2: frontline
    for sv in pool:
        if sv.role == MobRole.FRONTLINE and sv not in out:
            out.append(sv)
            seen_roles.add(sv.role)
            break

    # Fill remaining
    for sv in pool:
        if sv in out:
            continue
        if len(out) >= size:
            break
        out.append(sv)

    return tuple(out[:size])
