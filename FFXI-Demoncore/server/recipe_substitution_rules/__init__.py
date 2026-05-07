"""Recipe substitution rules — author-marked acceptable
mat alternates.

Real recipes have flexibility. The author of a sushi
recipe knows that "any tier-1 grain works fine" or "use
yellow rock OR white rock crystal interchangeably". The
adopter shouldn't have to fail-craft 5 times to figure
that out, and the recipe shouldn't have to be republished
every time mat prices shift.

Substitution kinds:
    EXACT_OK    these N items are interchangeable for
                THIS slot (e.g., "fire crystal" ↔
                "fire cluster"-style)
    TIER_OK     any item in this tier-tag works
                (e.g., "tier1_grain" matches dough,
                rice flour, etc.)
    HQ_OK       a HQ version of the original mat works
                (chef-only QoL: "you can use HQ flour
                if that's what you have")

Substitutions are author-asserted, not validated by the
synthesis engine — the synthesis engine sees the actual
mats used. This module is purely a UI hint: if Bob's
inventory has only HQ flour and the recipe says "flour",
the UI shows a green check ("author marked HQ_OK").

Per-recipe rules are stored as a list of SubstitutionRule
records. Up to 5 rules per recipe; up to 6 alternates
per EXACT_OK rule.

Public surface
--------------
    SubKind enum
    SubstitutionRule dataclass (frozen)
    RecipeSubstitutionRules
        .add_rule(recipe_id, original_mat, kind,
                  alternates, tier_tag, posted_at) -> bool
        .rules_for(recipe_id) -> list[SubstitutionRule]
        .accepts(recipe_id, slot_mat, candidate_mat,
                 tier_tags) -> bool
        .clear_rules(recipe_id, author_owner_id,
                     publisher_lookup_owner) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MAX_RULES_PER_RECIPE = 5
_MAX_ALTERNATES = 6


class SubKind(str, enum.Enum):
    EXACT_OK = "exact_ok"
    TIER_OK = "tier_ok"
    HQ_OK = "hq_ok"


@dataclasses.dataclass(frozen=True)
class SubstitutionRule:
    recipe_id: str
    original_mat: str
    kind: SubKind
    alternates: tuple[str, ...]   # for EXACT_OK
    tier_tag: str                 # for TIER_OK
    posted_at: int


@dataclasses.dataclass
class RecipeSubstitutionRules:
    _rules: dict[
        str, list[SubstitutionRule],
    ] = dataclasses.field(default_factory=dict)

    def add_rule(
        self, *, recipe_id: str, original_mat: str,
        kind: SubKind,
        alternates: t.Optional[list[str]] = None,
        tier_tag: str = "",
        posted_at: int,
    ) -> bool:
        if not recipe_id or not original_mat.strip():
            return False
        rules = self._rules.setdefault(recipe_id, [])
        if len(rules) >= _MAX_RULES_PER_RECIPE:
            return False
        # Validate by kind
        alts = tuple(alternates or [])
        if kind == SubKind.EXACT_OK:
            if not alts:
                return False
            if len(alts) > _MAX_ALTERNATES:
                return False
            if any(not a.strip() for a in alts):
                return False
            if original_mat in alts:
                return False  # don't list the original
        elif kind == SubKind.TIER_OK:
            if not tier_tag.strip():
                return False
            if alts:
                return False  # alternates not used
        else:   # HQ_OK
            if alts or tier_tag:
                return False
        # Reject duplicate (recipe_id, original_mat, kind)
        for r in rules:
            if (r.original_mat == original_mat
                    and r.kind == kind):
                return False
        rules.append(SubstitutionRule(
            recipe_id=recipe_id,
            original_mat=original_mat,
            kind=kind, alternates=alts,
            tier_tag=tier_tag, posted_at=posted_at,
        ))
        return True

    def rules_for(
        self, *, recipe_id: str,
    ) -> list[SubstitutionRule]:
        return list(self._rules.get(recipe_id, []))

    def accepts(
        self, *, recipe_id: str, slot_mat: str,
        candidate_mat: str,
        tier_tags: t.Optional[list[str]] = None,
    ) -> bool:
        """Does any rule say candidate_mat can stand in
        for slot_mat in this recipe? tier_tags is the
        candidate's tier list (caller-supplied from item
        registry)."""
        if slot_mat == candidate_mat:
            return True   # trivially yes
        for r in self._rules.get(recipe_id, []):
            if r.original_mat != slot_mat:
                continue
            if r.kind == SubKind.EXACT_OK:
                if candidate_mat in r.alternates:
                    return True
            elif r.kind == SubKind.TIER_OK:
                if tier_tags and r.tier_tag in tier_tags:
                    return True
            elif r.kind == SubKind.HQ_OK:
                # Convention: HQ candidates are named
                # "<original>_hq" — caller can also
                # use any naming, this is the simplest
                # check. Real wiring would query an
                # item-registry HQ relationship.
                if candidate_mat == f"{slot_mat}_hq":
                    return True
        return False

    def total_rules(self) -> int:
        return sum(len(rs) for rs in self._rules.values())


__all__ = [
    "SubKind", "SubstitutionRule",
    "RecipeSubstitutionRules",
]
