"""Currency exchange — alt-currency wallet + exchange matrix.

FFXI has a zoo of secondary currencies: conquest points, byne bills,
lebondopt wings, ancient beastcoin, alexandrite, riftborn boulders,
sparks of eminence, allied notes, and more. Each ties to a specific
NPC vendor or content tier.

This module models a per-player wallet across all currencies plus
an exchange-rate matrix for canonical conversion paths (e.g. 100
1-byne bills = 1 byne-piece). Conversions are gated by a daily cap
on certain currencies (gil sinks).

Public surface
--------------
    Currency enum (~12 currencies)
    Wallet per-player
        .balance(currency)
        .deposit(currency, amount)
        .withdraw(currency, amount) -> bool
    EXCHANGE_RATES dict
    convert(wallet, from_currency, to_currency, from_amount)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Currency(str, enum.Enum):
    GIL = "gil"
    CONQUEST_POINTS = "conquest_points"
    IMPERIAL_STANDING = "imperial_standing"
    ALLIED_NOTES = "allied_notes"
    BYNE_BILL = "byne_bill"
    LUNGO_NANGO_JADESHELL = "lungo_nango_jadeshell"
    LEBONDOPT_WING = "lebondopt_wing"
    ANCIENT_BEASTCOIN = "ancient_beastcoin"
    MYTHRIL_BEASTCOIN = "mythril_beastcoin"
    ALEXANDRITE = "alexandrite"
    RIFTBORN_BOULDER = "riftborn_boulder"
    SPARKS_OF_EMINENCE = "sparks_of_eminence"


# Conversion: (from_currency, to_currency) -> (units_in, units_out)
# Means: spend N units_in, gain N units_out.
EXCHANGE_RATES: dict[
    tuple[Currency, Currency], tuple[int, int]
] = {
    # Byne family conversions
    (Currency.BYNE_BILL, Currency.LUNGO_NANGO_JADESHELL): (100, 1),
    (Currency.LUNGO_NANGO_JADESHELL, Currency.BYNE_BILL): (1, 100),
    # Beastcoin -> ancient
    (Currency.MYTHRIL_BEASTCOIN, Currency.ANCIENT_BEASTCOIN): (10, 1),
    # Sparks -> Allied Notes
    (Currency.SPARKS_OF_EMINENCE, Currency.ALLIED_NOTES): (200, 1),
    # Conquest points -> imperial standing (cross-nation goodwill)
    (Currency.CONQUEST_POINTS, Currency.IMPERIAL_STANDING): (4, 1),
}


@dataclasses.dataclass
class Wallet:
    player_id: str
    _balances: dict[Currency, int] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def balance(self, currency: Currency) -> int:
        return self._balances.get(currency, 0)

    def deposit(self, currency: Currency, amount: int) -> None:
        if amount < 0:
            raise ValueError("amount must be >= 0")
        self._balances[currency] = (
            self._balances.get(currency, 0) + amount
        )

    def withdraw(self, currency: Currency, amount: int) -> bool:
        if amount < 0:
            raise ValueError("amount must be >= 0")
        cur = self._balances.get(currency, 0)
        if cur < amount:
            return False
        self._balances[currency] = cur - amount
        return True


@dataclasses.dataclass(frozen=True)
class ConvertResult:
    accepted: bool
    from_currency: Currency
    to_currency: Currency
    spent: int = 0
    received: int = 0
    reason: t.Optional[str] = None


def convert(
    *,
    wallet: Wallet,
    from_currency: Currency, to_currency: Currency,
    from_amount: int,
) -> ConvertResult:
    """Convert *from_amount* of from_currency to to_currency using
    the registered exchange rate. The from_amount must be a multiple
    of the rate's input unit (no partial-rate conversions)."""
    if from_amount <= 0:
        return ConvertResult(
            False, from_currency, to_currency,
            reason="amount must be > 0",
        )
    rate = EXCHANGE_RATES.get((from_currency, to_currency))
    if rate is None:
        return ConvertResult(
            False, from_currency, to_currency,
            reason="no exchange rate registered",
        )
    units_in, units_out = rate
    if from_amount % units_in != 0:
        return ConvertResult(
            False, from_currency, to_currency,
            reason=f"amount must be multiple of {units_in}",
        )
    if wallet.balance(from_currency) < from_amount:
        return ConvertResult(
            False, from_currency, to_currency,
            reason="insufficient balance",
        )
    received = (from_amount // units_in) * units_out
    wallet.withdraw(from_currency, from_amount)
    wallet.deposit(to_currency, received)
    return ConvertResult(
        True, from_currency, to_currency,
        spent=from_amount, received=received,
    )


__all__ = [
    "Currency", "EXCHANGE_RATES",
    "Wallet", "ConvertResult", "convert",
]
