"""Coalition Imprimaturs — uncapped, Sparks/Unity vendor.

Coalition Imprimaturs are canonical FFXI items earned by
participating in Adoulin Coalition assignments. Retail caps the
weekly draw at a small number; Demoncore lifts the cap entirely
and adds two new vendor sources:

* SPARKS NPC — sells imprimaturs for Sparks of Eminence
* UNITY NPC — sells imprimaturs for Unity points

Each imprimatur stands in for a coalition's seal (Mummers,
Pioneers, Inventors, Peacekeepers, Scouts, Couriers). They're
inputs to coalition shop trades — finer gear, dyes, runes, etc.

Public surface
--------------
    Coalition enum (six)
    ImprimaturKind dataclass
    IMPRIMATUR_CATALOG
    sparks_price_for(coalition) -> int
    unity_price_for(coalition) -> int
    PlayerImprimaturs (uncapped wallet)
        .grant(coalition, n)
        .spend(coalition, n)
        .buy_with_sparks(coalition, sparks_balance)
        .buy_with_unity(coalition, unity_balance)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Coalition(str, enum.Enum):
    MUMMERS = "mummers"            # cosmetic / arts
    PIONEERS = "pioneers"          # exploration / mounts
    INVENTORS = "inventors"        # crafting / synergy
    PEACEKEEPERS = "peacekeepers"  # combat / weapons
    SCOUTS = "scouts"              # ranged / sneaking
    COURIERS = "couriers"          # logistics / inventory


@dataclasses.dataclass(frozen=True)
class ImprimaturKind:
    coalition: Coalition
    label: str
    sparks_price: int
    unity_price: int


# Per-coalition pricing — Mummers cheapest (most cosmetic),
# Peacekeepers most expensive (combat).
IMPRIMATUR_CATALOG: dict[Coalition, ImprimaturKind] = {
    Coalition.MUMMERS: ImprimaturKind(
        Coalition.MUMMERS, "Imprimatur of the Mummers",
        sparks_price=8000, unity_price=400,
    ),
    Coalition.PIONEERS: ImprimaturKind(
        Coalition.PIONEERS, "Imprimatur of the Pioneers",
        sparks_price=10000, unity_price=500,
    ),
    Coalition.INVENTORS: ImprimaturKind(
        Coalition.INVENTORS, "Imprimatur of the Inventors",
        sparks_price=12000, unity_price=600,
    ),
    Coalition.PEACEKEEPERS: ImprimaturKind(
        Coalition.PEACEKEEPERS, "Imprimatur of the Peacekeepers",
        sparks_price=15000, unity_price=750,
    ),
    Coalition.SCOUTS: ImprimaturKind(
        Coalition.SCOUTS, "Imprimatur of the Scouts",
        sparks_price=11000, unity_price=550,
    ),
    Coalition.COURIERS: ImprimaturKind(
        Coalition.COURIERS, "Imprimatur of the Couriers",
        sparks_price=9000, unity_price=450,
    ),
}


def sparks_price_for(coalition: Coalition) -> int:
    return IMPRIMATUR_CATALOG[coalition].sparks_price


def unity_price_for(coalition: Coalition) -> int:
    return IMPRIMATUR_CATALOG[coalition].unity_price


@dataclasses.dataclass(frozen=True)
class PurchaseResult:
    accepted: bool
    coalition: t.Optional[Coalition] = None
    quantity: int = 0
    sparks_spent: int = 0
    unity_spent: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerImprimaturs:
    """Uncapped imprimatur wallet — Demoncore removes the canonical
    weekly cap. Players can hold any quantity per coalition."""
    player_id: str
    held: dict[Coalition, int] = dataclasses.field(default_factory=dict)

    def count(self, coalition: Coalition) -> int:
        return self.held.get(coalition, 0)

    def grant(self, *, coalition: Coalition, quantity: int = 1) -> bool:
        if quantity <= 0:
            return False
        self.held[coalition] = self.held.get(coalition, 0) + quantity
        return True

    def spend(self, *, coalition: Coalition, quantity: int = 1) -> bool:
        have = self.held.get(coalition, 0)
        if quantity <= 0 or have < quantity:
            return False
        self.held[coalition] = have - quantity
        return True

    def buy_with_sparks(
        self, *, coalition: Coalition, quantity: int = 1,
        sparks_balance: int,
    ) -> PurchaseResult:
        if quantity <= 0:
            return PurchaseResult(False, reason="quantity must be > 0")
        unit = sparks_price_for(coalition)
        cost = unit * quantity
        if sparks_balance < cost:
            return PurchaseResult(
                False, coalition=coalition,
                reason="insufficient sparks", sparks_spent=0,
            )
        self.grant(coalition=coalition, quantity=quantity)
        return PurchaseResult(
            accepted=True, coalition=coalition,
            quantity=quantity, sparks_spent=cost,
        )

    def buy_with_unity(
        self, *, coalition: Coalition, quantity: int = 1,
        unity_balance: int,
    ) -> PurchaseResult:
        if quantity <= 0:
            return PurchaseResult(False, reason="quantity must be > 0")
        unit = unity_price_for(coalition)
        cost = unit * quantity
        if unity_balance < cost:
            return PurchaseResult(
                False, coalition=coalition,
                reason="insufficient unity points", unity_spent=0,
            )
        self.grant(coalition=coalition, quantity=quantity)
        return PurchaseResult(
            accepted=True, coalition=coalition,
            quantity=quantity, unity_spent=cost,
        )


__all__ = [
    "Coalition", "ImprimaturKind", "IMPRIMATUR_CATALOG",
    "sparks_price_for", "unity_price_for",
    "PurchaseResult", "PlayerImprimaturs",
]
