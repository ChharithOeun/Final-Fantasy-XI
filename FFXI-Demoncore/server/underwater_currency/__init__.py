"""Underwater currency — coral-shells & seapearls.

Underwater vendors (Sirenhall mermaids, Reef Spire shark
quartermasters, Coral Caverns scholars) don't trade in
surface gil. They trade in CORAL_SHELLS (low) and SEAPEARLS
(high). Players earn these through underwater activities
(harpoon catches, bloom harvesting, kraken loot, etc.) and
spend them at city vendors.

Currencies are PER-PLAYER and CAPPED. Coral-shells cap at
99,999. Seapearls cap at 9,999. The cap is enforced by
gain — over-earning beyond the cap is silently truncated
and the surplus is lost (deliberate sink).

Conversion (manual at NPC):
  100 coral_shells -> 1 seapearl   (one-way; can't reverse)

Public surface
--------------
    Currency enum
    GainResult / SpendResult / ConvertResult dataclasses
    UnderwaterCurrency
        .gain(player_id, currency, amount)
        .spend(player_id, currency, amount)
        .balance(player_id, currency)
        .convert_shells_to_pearls(player_id, shells_to_convert)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Currency(str, enum.Enum):
    CORAL_SHELL = "coral_shell"
    SEAPEARL = "seapearl"


_CAP: dict[Currency, int] = {
    Currency.CORAL_SHELL: 99_999,
    Currency.SEAPEARL: 9_999,
}

SHELLS_PER_PEARL = 100


@dataclasses.dataclass(frozen=True)
class GainResult:
    accepted: bool
    currency: t.Optional[Currency] = None
    granted: int = 0
    truncated: int = 0       # how much overflow was lost
    new_balance: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class SpendResult:
    accepted: bool
    currency: t.Optional[Currency] = None
    spent: int = 0
    new_balance: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ConvertResult:
    accepted: bool
    shells_consumed: int = 0
    pearls_granted: int = 0
    new_shell_balance: int = 0
    new_pearl_balance: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class UnderwaterCurrency:
    _purses: dict[str, dict[Currency, int]] = dataclasses.field(
        default_factory=dict,
    )

    def _purse(self, player_id: str) -> dict[Currency, int]:
        return self._purses.setdefault(
            player_id, {c: 0 for c in Currency},
        )

    def balance(
        self, *, player_id: str, currency: Currency,
    ) -> int:
        purse = self._purses.get(player_id)
        if purse is None:
            return 0
        return purse.get(currency, 0)

    def gain(
        self, *, player_id: str,
        currency: Currency,
        amount: int,
    ) -> GainResult:
        if not player_id:
            return GainResult(False, reason="bad player")
        if currency not in _CAP:
            return GainResult(False, reason="unknown currency")
        if amount <= 0:
            return GainResult(False, reason="bad amount")
        purse = self._purse(player_id)
        cap = _CAP[currency]
        current = purse[currency]
        room = max(0, cap - current)
        granted = min(amount, room)
        truncated = amount - granted
        purse[currency] = current + granted
        return GainResult(
            accepted=True, currency=currency,
            granted=granted, truncated=truncated,
            new_balance=purse[currency],
        )

    def spend(
        self, *, player_id: str,
        currency: Currency,
        amount: int,
    ) -> SpendResult:
        if currency not in _CAP:
            return SpendResult(False, reason="unknown currency")
        if amount <= 0:
            return SpendResult(False, reason="bad amount")
        purse = self._purses.get(player_id)
        if purse is None or purse.get(currency, 0) < amount:
            return SpendResult(False, reason="insufficient")
        purse[currency] = purse[currency] - amount
        return SpendResult(
            accepted=True, currency=currency,
            spent=amount, new_balance=purse[currency],
        )

    def convert_shells_to_pearls(
        self, *, player_id: str,
        shells_to_convert: int,
    ) -> ConvertResult:
        if shells_to_convert <= 0:
            return ConvertResult(False, reason="bad amount")
        if shells_to_convert % SHELLS_PER_PEARL != 0:
            return ConvertResult(
                False, reason="must be multiple of 100",
            )
        spend = self.spend(
            player_id=player_id,
            currency=Currency.CORAL_SHELL,
            amount=shells_to_convert,
        )
        if not spend.accepted:
            return ConvertResult(False, reason=spend.reason)
        pearls = shells_to_convert // SHELLS_PER_PEARL
        gain = self.gain(
            player_id=player_id,
            currency=Currency.SEAPEARL,
            amount=pearls,
        )
        return ConvertResult(
            accepted=True,
            shells_consumed=shells_to_convert,
            pearls_granted=gain.granted,
            new_shell_balance=spend.new_balance,
            new_pearl_balance=gain.new_balance,
        )


__all__ = [
    "Currency", "GainResult", "SpendResult", "ConvertResult",
    "UnderwaterCurrency", "SHELLS_PER_PEARL",
]
