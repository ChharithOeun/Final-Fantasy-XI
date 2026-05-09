"""Player signature recipe — registered IP with licensing.

A celebrated chef registers a signature recipe — a named
dish that becomes legally theirs in the recipe registry.
Other chefs can license it for a per-cook fee paid to the
owner; unlicensed cooks who serve the dish can be reported
as violators by the owner. Licensing is durable until the
owner revokes it; revocation refunds the unused balance to
the licensee. The system tracks lifetime royalties paid to
each owner — chefs who consistently invent good recipes
build a passive income stream.

Lifecycle (license)
    ACTIVE        currently authorized
    REVOKED       owner pulled it
    EXPIRED       (reserved for time-bounded licenses)

Public surface
--------------
    LicenseState enum
    Recipe dataclass (frozen)
    License dataclass (frozen)
    PlayerSignatureRecipeSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LicenseState(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclasses.dataclass(frozen=True)
class Recipe:
    recipe_id: str
    owner_id: str
    name: str
    difficulty: int
    license_fee_gil: int
    total_royalties_paid_gil: int


@dataclasses.dataclass(frozen=True)
class License:
    license_id: str
    recipe_id: str
    licensee_id: str
    paid_gil: int
    granted_day: int
    state: LicenseState


@dataclasses.dataclass(frozen=True)
class Violation:
    violation_id: str
    recipe_id: str
    violator_id: str
    reported_day: int


@dataclasses.dataclass
class _RState:
    spec: Recipe
    # licensee_id -> license_id (active only)
    active_licensees: dict[str, str] = (
        dataclasses.field(default_factory=dict)
    )
    licenses: dict[str, License] = dataclasses.field(
        default_factory=dict,
    )
    violations: dict[str, Violation] = (
        dataclasses.field(default_factory=dict)
    )


@dataclasses.dataclass
class PlayerSignatureRecipeSystem:
    _recipes: dict[str, _RState] = dataclasses.field(
        default_factory=dict,
    )
    _next_recipe: int = 1
    _next_license: int = 1
    _next_violation: int = 1

    def register_recipe(
        self, *, owner_id: str, name: str,
        difficulty: int, license_fee_gil: int,
    ) -> t.Optional[str]:
        if not owner_id or not name:
            return None
        if not 0 <= difficulty <= 200:
            return None
        if license_fee_gil <= 0:
            return None
        rid = f"recipe_{self._next_recipe}"
        self._next_recipe += 1
        self._recipes[rid] = _RState(
            spec=Recipe(
                recipe_id=rid, owner_id=owner_id,
                name=name, difficulty=difficulty,
                license_fee_gil=license_fee_gil,
                total_royalties_paid_gil=0,
            ),
        )
        return rid

    def grant_license(
        self, *, recipe_id: str, licensee_id: str,
        granted_day: int,
    ) -> t.Optional[str]:
        if recipe_id not in self._recipes:
            return None
        st = self._recipes[recipe_id]
        if not licensee_id:
            return None
        if licensee_id == st.spec.owner_id:
            return None
        if licensee_id in st.active_licensees:
            return None
        if granted_day < 0:
            return None
        lid = f"lic_{self._next_license}"
        self._next_license += 1
        fee = st.spec.license_fee_gil
        st.licenses[lid] = License(
            license_id=lid, recipe_id=recipe_id,
            licensee_id=licensee_id, paid_gil=fee,
            granted_day=granted_day,
            state=LicenseState.ACTIVE,
        )
        st.active_licensees[licensee_id] = lid
        st.spec = dataclasses.replace(
            st.spec,
            total_royalties_paid_gil=(
                st.spec.total_royalties_paid_gil + fee
            ),
        )
        return lid

    def revoke_license(
        self, *, recipe_id: str, license_id: str,
        owner_id: str,
    ) -> bool:
        if recipe_id not in self._recipes:
            return False
        st = self._recipes[recipe_id]
        if st.spec.owner_id != owner_id:
            return False
        if license_id not in st.licenses:
            return False
        lic = st.licenses[license_id]
        if lic.state != LicenseState.ACTIVE:
            return False
        st.licenses[license_id] = dataclasses.replace(
            lic, state=LicenseState.REVOKED,
        )
        if (
            st.active_licensees.get(lic.licensee_id)
            == license_id
        ):
            del st.active_licensees[lic.licensee_id]
        return True

    def report_violation(
        self, *, recipe_id: str, owner_id: str,
        violator_id: str, reported_day: int,
    ) -> t.Optional[str]:
        if recipe_id not in self._recipes:
            return None
        st = self._recipes[recipe_id]
        if st.spec.owner_id != owner_id:
            return None
        if not violator_id:
            return None
        if violator_id == owner_id:
            return None
        # Active licensees can't be reported
        if violator_id in st.active_licensees:
            return None
        # Don't double-report
        for v in st.violations.values():
            if v.violator_id == violator_id:
                return None
        vid = f"viol_{self._next_violation}"
        self._next_violation += 1
        st.violations[vid] = Violation(
            violation_id=vid, recipe_id=recipe_id,
            violator_id=violator_id,
            reported_day=reported_day,
        )
        return vid

    def recipe(
        self, *, recipe_id: str,
    ) -> t.Optional[Recipe]:
        st = self._recipes.get(recipe_id)
        return st.spec if st else None

    def license_lookup(
        self, *, recipe_id: str, license_id: str,
    ) -> t.Optional[License]:
        st = self._recipes.get(recipe_id)
        if st is None:
            return None
        return st.licenses.get(license_id)

    def licensees_for_recipe(
        self, *, recipe_id: str,
    ) -> list[str]:
        st = self._recipes.get(recipe_id)
        if st is None:
            return []
        return sorted(st.active_licensees)

    def violations_for_recipe(
        self, *, recipe_id: str,
    ) -> list[Violation]:
        st = self._recipes.get(recipe_id)
        if st is None:
            return []
        return list(st.violations.values())

    def recipes_by_owner(
        self, *, owner_id: str,
    ) -> list[Recipe]:
        return [
            st.spec for st in self._recipes.values()
            if st.spec.owner_id == owner_id
        ]


__all__ = [
    "LicenseState", "Recipe", "License",
    "Violation", "PlayerSignatureRecipeSystem",
]
