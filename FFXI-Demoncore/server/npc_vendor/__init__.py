"""NPC vendor — shop with rotating inventory + conquest discounts.

Each vendor has a base catalog with prices. Some items rotate daily;
others restock every conquest tally. Players in the controlling
nation get a discount in their nation's vendors. Stock is capped
per item; sold-out items reappear after the rotation cycle.

Public surface
--------------
    Vendor catalog
    StockState per vendor (current inventory)
        .rotate_daily / .rotate_on_conquest_tally
        .buy(item, gil) -> BuyResult
        .sell(item, qty) -> SellResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RotationCadence(str, enum.Enum):
    NEVER = "never"
    DAILY = "daily"
    CONQUEST_TALLY = "conquest_tally"


@dataclasses.dataclass(frozen=True)
class VendorItem:
    item_id: str
    base_price_gil: int
    stock_per_cycle: int
    rotation: RotationCadence = RotationCadence.NEVER
    sell_back_pct: int = 50          # vendor pays this % when selling


@dataclasses.dataclass(frozen=True)
class Vendor:
    vendor_id: str
    name: str
    nation: str                       # bastok / sandy / windy / neutral
    catalog: tuple[VendorItem, ...]


# Sample vendors
VENDORS: tuple[Vendor, ...] = (
    Vendor(
        vendor_id="bastok_smithy", name="Bastok Smithy",
        nation="bastok",
        catalog=(
            VendorItem("bronze_dagger", base_price_gil=85,
                        stock_per_cycle=99),
            VendorItem("iron_sword", base_price_gil=720,
                        stock_per_cycle=20,
                        rotation=RotationCadence.DAILY),
            VendorItem("mythril_dagger", base_price_gil=4400,
                        stock_per_cycle=3,
                        rotation=RotationCadence.CONQUEST_TALLY),
        ),
    ),
    Vendor(
        vendor_id="sandy_armorer", name="Sandy Armorer",
        nation="sandy",
        catalog=(
            VendorItem("bronze_cap", base_price_gil=64,
                        stock_per_cycle=99),
            VendorItem("brass_scale_armor", base_price_gil=480,
                        stock_per_cycle=20,
                        rotation=RotationCadence.DAILY),
        ),
    ),
    Vendor(
        vendor_id="windy_apothecary", name="Windy Apothecary",
        nation="windy",
        catalog=(
            VendorItem("potion", base_price_gil=80,
                        stock_per_cycle=99),
            VendorItem("ether", base_price_gil=4000,
                        stock_per_cycle=99),
            VendorItem("antidote", base_price_gil=20,
                        stock_per_cycle=99),
        ),
    ),
)

VENDOR_BY_ID: dict[str, Vendor] = {v.vendor_id: v for v in VENDORS}


CONQUEST_DISCOUNT_PCT = 15


@dataclasses.dataclass(frozen=True)
class BuyResult:
    accepted: bool
    item_id: str
    gil_charged: int = 0
    quantity: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class SellResult:
    accepted: bool
    item_id: str
    gil_received: int = 0
    quantity: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class StockState:
    vendor_id: str
    inventory: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def initialize(self) -> None:
        """Set inventory to full per item."""
        v = VENDOR_BY_ID[self.vendor_id]
        for entry in v.catalog:
            self.inventory[entry.item_id] = entry.stock_per_cycle

    def rotate_daily(self) -> int:
        """Refill DAILY items. Returns number of items refilled."""
        v = VENDOR_BY_ID[self.vendor_id]
        n = 0
        for entry in v.catalog:
            if entry.rotation == RotationCadence.DAILY:
                self.inventory[entry.item_id] = entry.stock_per_cycle
                n += 1
        return n

    def rotate_on_conquest_tally(self) -> int:
        v = VENDOR_BY_ID[self.vendor_id]
        n = 0
        for entry in v.catalog:
            if entry.rotation == RotationCadence.CONQUEST_TALLY:
                self.inventory[entry.item_id] = entry.stock_per_cycle
                n += 1
        return n

    def stock(self, item_id: str) -> int:
        return self.inventory.get(item_id, 0)


def _price_with_discount(
    base: int, *, buyer_nation: str, vendor_nation: str,
) -> int:
    if vendor_nation == "neutral":
        return base
    if buyer_nation != vendor_nation:
        return base
    # Buyer is in vendor's nation -> discount
    return int(base * (1.0 - CONQUEST_DISCOUNT_PCT / 100.0))


def buy(
    *,
    state: StockState,
    item_id: str,
    quantity: int,
    buyer_gil: int,
    buyer_nation: str,
) -> BuyResult:
    if quantity <= 0:
        return BuyResult(False, item_id, reason="invalid quantity")
    vendor = VENDOR_BY_ID[state.vendor_id]
    entry = next(
        (e for e in vendor.catalog if e.item_id == item_id), None,
    )
    if entry is None:
        return BuyResult(False, item_id, reason="not stocked")
    available = state.stock(item_id)
    if available < quantity:
        return BuyResult(
            False, item_id,
            reason=f"only {available} in stock",
        )
    unit_price = _price_with_discount(
        entry.base_price_gil,
        buyer_nation=buyer_nation,
        vendor_nation=vendor.nation,
    )
    total = unit_price * quantity
    if buyer_gil < total:
        return BuyResult(
            False, item_id,
            reason=f"need {total} gil",
        )
    state.inventory[item_id] = available - quantity
    return BuyResult(
        True, item_id,
        gil_charged=total, quantity=quantity,
    )


def sell(
    *,
    state: StockState,
    item_id: str,
    quantity: int,
) -> SellResult:
    if quantity <= 0:
        return SellResult(False, item_id, reason="invalid quantity")
    vendor = VENDOR_BY_ID[state.vendor_id]
    entry = next(
        (e for e in vendor.catalog if e.item_id == item_id), None,
    )
    if entry is None:
        return SellResult(False, item_id,
                          reason="vendor doesn't take this item")
    unit = int(
        entry.base_price_gil * entry.sell_back_pct / 100.0,
    )
    return SellResult(
        True, item_id,
        gil_received=unit * quantity, quantity=quantity,
    )


__all__ = [
    "RotationCadence", "VendorItem", "Vendor",
    "VENDORS", "VENDOR_BY_ID",
    "CONQUEST_DISCOUNT_PCT",
    "BuyResult", "SellResult", "StockState",
    "buy", "sell",
]
