"""Trade window — peer-to-peer item exchange with confirmation.

Two players open a trade window. Each side stages items + gil into
their offer slot. Both must hit Confirm; only when both confirmed
does the swap happen atomically. Either side can cancel until both
confirm.

Public surface
--------------
    TradeStatus enum
    TradeOffer dataclass (per-side offer slot)
    TradeSession lifecycle
        .open(initiator, target) -> TradeSession
        .stage_item / .stage_gil
        .confirm(side)
        .cancel()
        .is_executed
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_ITEMS_PER_OFFER = 8


class TradeStatus(str, enum.Enum):
    OPEN = "open"
    LOCKED_BOTH = "locked_both"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class TradeSide(str, enum.Enum):
    INITIATOR = "initiator"
    TARGET = "target"


@dataclasses.dataclass
class TradeOffer:
    items: list[tuple[str, int]] = dataclasses.field(
        default_factory=list,
    )
    gil: int = 0
    confirmed: bool = False


@dataclasses.dataclass(frozen=True)
class StageResult:
    accepted: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ExecuteResult:
    accepted: bool
    initiator_gives: tuple[tuple[str, int], ...] = ()
    initiator_gil: int = 0
    target_gives: tuple[tuple[str, int], ...] = ()
    target_gil: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class TradeSession:
    initiator_id: str
    target_id: str
    initiator_offer: TradeOffer = dataclasses.field(
        default_factory=TradeOffer,
    )
    target_offer: TradeOffer = dataclasses.field(
        default_factory=TradeOffer,
    )
    status: TradeStatus = TradeStatus.OPEN

    def _offer_for(self, side: TradeSide) -> TradeOffer:
        return (
            self.initiator_offer
            if side == TradeSide.INITIATOR
            else self.target_offer
        )

    def stage_item(
        self, *, side: TradeSide,
        item_id: str, quantity: int,
    ) -> StageResult:
        if self.status != TradeStatus.OPEN:
            return StageResult(False, reason="trade not open")
        if quantity <= 0:
            return StageResult(
                False, reason="quantity must be > 0",
            )
        offer = self._offer_for(side)
        # Any modification while OPEN clears BOTH sides' confirms.
        offer.confirmed = False
        other = self._offer_for(
            TradeSide.TARGET
            if side == TradeSide.INITIATOR
            else TradeSide.INITIATOR
        )
        other.confirmed = False
        if len(offer.items) >= MAX_ITEMS_PER_OFFER:
            return StageResult(
                False, reason="offer full",
            )
        offer.items.append((item_id, quantity))
        return StageResult(True)

    def stage_gil(
        self, *, side: TradeSide, amount: int,
    ) -> StageResult:
        if self.status != TradeStatus.OPEN:
            return StageResult(False, reason="trade not open")
        if amount < 0:
            return StageResult(
                False, reason="amount must be >= 0",
            )
        offer = self._offer_for(side)
        if offer.confirmed or self._offer_for(
            TradeSide.TARGET if side == TradeSide.INITIATOR
            else TradeSide.INITIATOR
        ).confirmed:
            offer.confirmed = False
            self._offer_for(
                TradeSide.TARGET if side == TradeSide.INITIATOR
                else TradeSide.INITIATOR
            ).confirmed = False
        offer.gil = amount
        return StageResult(True)

    def confirm(self, *, side: TradeSide) -> StageResult:
        if self.status != TradeStatus.OPEN:
            return StageResult(False, reason="trade not open")
        offer = self._offer_for(side)
        offer.confirmed = True
        if (
            self.initiator_offer.confirmed
            and self.target_offer.confirmed
        ):
            self.status = TradeStatus.LOCKED_BOTH
        return StageResult(True)

    def execute(self) -> ExecuteResult:
        if self.status != TradeStatus.LOCKED_BOTH:
            return ExecuteResult(
                False, reason="both sides must confirm",
            )
        self.status = TradeStatus.EXECUTED
        return ExecuteResult(
            accepted=True,
            initiator_gives=tuple(self.initiator_offer.items),
            initiator_gil=self.initiator_offer.gil,
            target_gives=tuple(self.target_offer.items),
            target_gil=self.target_offer.gil,
        )

    def cancel(self) -> bool:
        if self.status in (
            TradeStatus.EXECUTED, TradeStatus.CANCELLED,
        ):
            return False
        self.status = TradeStatus.CANCELLED
        return True


def open_trade(
    *, initiator_id: str, target_id: str,
    blocked_by_target: t.Iterable[str] = (),
    in_proximity: bool = True,
) -> t.Optional[TradeSession]:
    """Open a trade. Returns None if not eligible (initiator
    blocked or out of range)."""
    if initiator_id == target_id:
        return None
    if not in_proximity:
        return None
    if initiator_id in set(blocked_by_target):
        return None
    return TradeSession(
        initiator_id=initiator_id,
        target_id=target_id,
    )


__all__ = [
    "MAX_ITEMS_PER_OFFER",
    "TradeStatus", "TradeSide",
    "TradeOffer", "TradeSession",
    "StageResult", "ExecuteResult",
    "open_trade",
]
