"""Beastman alt-currency converters — race-specific tokens.

Each beastman race accumulates its own iconic raw materials that
double as alt-currency, exchangeable at the relevant city's
TREASURE COMMISSION:

  Yagudo  - PRIME FEATHERS    (drop from yagudo cohorts +
                                shadow dynamis cleanups)
  Quadav  - LACQUERED STONES  (mineral-strike harvest +
                                fortification rubble)
  Lamia   - CORAL SCALES      (tide harvest + ship clears)
  Orc     - REAVER BONES      (raider drops + hunting big mobs)

There are also UNIVERSAL conversions: any of the four can be
traded into SHADOW BYTNES (the shadow dynamis currency) at a
fixed haircut rate to support cross-race purchasing.

Public surface
--------------
    BeastmanCurrency enum  PRIME_FEATHER / LACQUERED_STONE /
                           CORAL_SCALE / REAVER_BONE /
                           SHADOW_BYTNE
    ExchangeKind enum      CITY_VENDOR / UNIVERSAL_BYTNE
    BeastmanAltCurrency
        .grant(player_id, currency, amount)
        .balance(player_id, currency)
        .exchange(player_id, src, dst, src_amount)
        .set_rate(src, dst, rate_pct)   # 100 = 1:1, 90 = 90%
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BeastmanCurrency(str, enum.Enum):
    PRIME_FEATHER = "prime_feather"
    LACQUERED_STONE = "lacquered_stone"
    CORAL_SCALE = "coral_scale"
    REAVER_BONE = "reaver_bone"
    SHADOW_BYTNE = "shadow_bytne"


# Default exchange rates expressed as PERCENT of input value
# delivered as output. 100 = 1:1, 80 = lose 20%, etc.
_DEFAULT_RATES: dict[
    tuple[BeastmanCurrency, BeastmanCurrency], int,
] = {
    # All 4 raw → SHADOW_BYTNE at 60%
    (BeastmanCurrency.PRIME_FEATHER, BeastmanCurrency.SHADOW_BYTNE): 60,
    (BeastmanCurrency.LACQUERED_STONE, BeastmanCurrency.SHADOW_BYTNE): 60,
    (BeastmanCurrency.CORAL_SCALE, BeastmanCurrency.SHADOW_BYTNE): 60,
    (BeastmanCurrency.REAVER_BONE, BeastmanCurrency.SHADOW_BYTNE): 60,
    # Bytne back → raw at 30% (heavy haircut to discourage round-tripping)
    (BeastmanCurrency.SHADOW_BYTNE, BeastmanCurrency.PRIME_FEATHER): 30,
    (BeastmanCurrency.SHADOW_BYTNE, BeastmanCurrency.LACQUERED_STONE): 30,
    (BeastmanCurrency.SHADOW_BYTNE, BeastmanCurrency.CORAL_SCALE): 30,
    (BeastmanCurrency.SHADOW_BYTNE, BeastmanCurrency.REAVER_BONE): 30,
}


@dataclasses.dataclass(frozen=True)
class GrantResult:
    accepted: bool
    new_balance: int
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ExchangeResult:
    accepted: bool
    src_consumed: int = 0
    dst_received: int = 0
    src_balance_after: int = 0
    dst_balance_after: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanAltCurrency:
    _balances: dict[
        tuple[str, BeastmanCurrency], int,
    ] = dataclasses.field(default_factory=dict)
    _rates: dict[
        tuple[BeastmanCurrency, BeastmanCurrency], int,
    ] = dataclasses.field(
        default_factory=lambda: dict(_DEFAULT_RATES),
    )

    def set_rate(
        self, *, src: BeastmanCurrency,
        dst: BeastmanCurrency,
        rate_pct: int,
    ) -> bool:
        if src == dst:
            return False
        if not (0 <= rate_pct <= 200):
            return False
        self._rates[(src, dst)] = rate_pct
        return True

    def get_rate(
        self, *, src: BeastmanCurrency, dst: BeastmanCurrency,
    ) -> t.Optional[int]:
        return self._rates.get((src, dst))

    def grant(
        self, *, player_id: str,
        currency: BeastmanCurrency,
        amount: int,
    ) -> GrantResult:
        if amount <= 0:
            cur = self._balances.get((player_id, currency), 0)
            return GrantResult(
                False, cur, reason="non-positive amount",
            )
        key = (player_id, currency)
        new = self._balances.get(key, 0) + amount
        self._balances[key] = new
        return GrantResult(accepted=True, new_balance=new)

    def balance(
        self, *, player_id: str, currency: BeastmanCurrency,
    ) -> int:
        return self._balances.get((player_id, currency), 0)

    def exchange(
        self, *, player_id: str,
        src: BeastmanCurrency,
        dst: BeastmanCurrency,
        src_amount: int,
    ) -> ExchangeResult:
        if src == dst:
            return ExchangeResult(
                False, reason="same source and destination",
            )
        if src_amount <= 0:
            return ExchangeResult(
                False, reason="non-positive amount",
            )
        rate = self._rates.get((src, dst))
        if rate is None:
            return ExchangeResult(
                False, reason="no rate configured",
            )
        cur_src = self._balances.get((player_id, src), 0)
        if cur_src < src_amount:
            return ExchangeResult(
                False, src_balance_after=cur_src,
                reason="insufficient balance",
            )
        # Integer math: src_amount * rate / 100, floor
        dst_received = (src_amount * rate) // 100
        if dst_received <= 0:
            return ExchangeResult(
                False, src_balance_after=cur_src,
                reason="amount too small for rate",
            )
        new_src = cur_src - src_amount
        new_dst = self._balances.get((player_id, dst), 0) + dst_received
        self._balances[(player_id, src)] = new_src
        self._balances[(player_id, dst)] = new_dst
        return ExchangeResult(
            accepted=True,
            src_consumed=src_amount,
            dst_received=dst_received,
            src_balance_after=new_src,
            dst_balance_after=new_dst,
        )

    def total_currencies_held(
        self, *, player_id: str,
    ) -> int:
        return sum(
            v for (pid, _c), v in self._balances.items()
            if pid == player_id and v > 0
        )


__all__ = [
    "BeastmanCurrency",
    "GrantResult", "ExchangeResult",
    "BeastmanAltCurrency",
]
