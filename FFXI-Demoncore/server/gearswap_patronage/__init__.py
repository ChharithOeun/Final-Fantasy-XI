"""GearSwap patronage — tip an author gil.

Sometimes a player wants to thank Chharith for the build
that carried them through Maat without arguing about
star ratings or filing reports. They just want to say
"here's 10,000 gil, thanks." Patronage is the gift
channel — one-way, no expectation, separate from the
rating signal.

Patronage is gil only (no items — items go through
delivery_box for clarity). The patron must:
    - have at least min_tip_gil to give (sanity gate)
    - tip ≤ daily_cap_per_recipient_gil to one author
      per day (anti-laundering — patrons can't shovel
      gil to a friend's character to dodge the AH)

Tips show up in the recipient's inbox via
delivery_box-style messaging, but we don't actually
deposit there directly — that's the controller's job.
We record the entry so the author dashboard can show
"top patrons of all time" and "this week's tips" and
the ledger stays auditable.

Tipping a publish (not just an author) is supported via
optional publish_id — the dashboard lights up "lua
that earned 50,000 gil from 5 patrons" so authors see
which build is the breadwinner.

Public surface
--------------
    TipRecord dataclass (frozen)
    TipResult dataclass (frozen)
    GearswapPatronage
        .tip(patron_id, recipient_id, gil_amount,
             publish_id, posted_at) -> TipResult
        .total_gil_received(recipient_id) -> int
        .total_gil_given(patron_id) -> int
        .top_patrons(recipient_id, limit) -> list[tuple[str, int]]
        .tips_for_publish(publish_id) -> list[TipRecord]
        .gil_received_this_window(recipient_id, now,
            day_window) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t


_SECONDS_PER_DAY = 86400
_MIN_TIP_GIL = 100
_DAILY_CAP_PER_RECIPIENT_GIL = 1_000_000


@dataclasses.dataclass(frozen=True)
class TipRecord:
    patron_id: str
    recipient_id: str
    gil_amount: int
    publish_id: str    # "" if author-level tip
    posted_at: int


@dataclasses.dataclass(frozen=True)
class TipResult:
    success: bool
    reason: str        # "" on success
    record: t.Optional[TipRecord]


@dataclasses.dataclass
class GearswapPatronage:
    _tips: list[TipRecord] = dataclasses.field(
        default_factory=list,
    )

    def _given_today(
        self, *, patron_id: str, recipient_id: str, now: int,
    ) -> int:
        cutoff = now - _SECONDS_PER_DAY
        return sum(
            r.gil_amount for r in self._tips
            if r.patron_id == patron_id
            and r.recipient_id == recipient_id
            and r.posted_at >= cutoff
        )

    def tip(
        self, *, patron_id: str, recipient_id: str,
        gil_amount: int, publish_id: str = "",
        posted_at: int,
    ) -> TipResult:
        if not patron_id or not recipient_id:
            return TipResult(
                success=False, reason="ids_required",
                record=None,
            )
        if patron_id == recipient_id:
            return TipResult(
                success=False, reason="self_tip",
                record=None,
            )
        if gil_amount < _MIN_TIP_GIL:
            return TipResult(
                success=False, reason="below_min",
                record=None,
            )
        already = self._given_today(
            patron_id=patron_id, recipient_id=recipient_id,
            now=posted_at,
        )
        if already + gil_amount > _DAILY_CAP_PER_RECIPIENT_GIL:
            return TipResult(
                success=False,
                reason="daily_cap_to_recipient",
                record=None,
            )
        rec = TipRecord(
            patron_id=patron_id, recipient_id=recipient_id,
            gil_amount=gil_amount, publish_id=publish_id,
            posted_at=posted_at,
        )
        self._tips.append(rec)
        return TipResult(
            success=True, reason="", record=rec,
        )

    def total_gil_received(
        self, *, recipient_id: str,
    ) -> int:
        return sum(
            r.gil_amount for r in self._tips
            if r.recipient_id == recipient_id
        )

    def total_gil_given(
        self, *, patron_id: str,
    ) -> int:
        return sum(
            r.gil_amount for r in self._tips
            if r.patron_id == patron_id
        )

    def top_patrons(
        self, *, recipient_id: str, limit: int = 10,
    ) -> list[tuple[str, int]]:
        if limit <= 0:
            return []
        agg: dict[str, int] = {}
        for r in self._tips:
            if r.recipient_id != recipient_id:
                continue
            agg[r.patron_id] = agg.get(
                r.patron_id, 0,
            ) + r.gil_amount
        out = sorted(
            agg.items(), key=lambda kv: (-kv[1], kv[0]),
        )
        return out[:limit]

    def tips_for_publish(
        self, *, publish_id: str,
    ) -> list[TipRecord]:
        out = [
            r for r in self._tips
            if r.publish_id == publish_id
        ]
        out.sort(key=lambda r: r.posted_at)
        return out

    def gil_received_this_window(
        self, *, recipient_id: str, now: int,
        day_window: int,
    ) -> int:
        if day_window <= 0:
            return 0
        cutoff = now - (day_window * _SECONDS_PER_DAY)
        return sum(
            r.gil_amount for r in self._tips
            if r.recipient_id == recipient_id
            and r.posted_at >= cutoff
        )

    def total_tips(self) -> int:
        return len(self._tips)


__all__ = [
    "TipRecord", "TipResult", "GearswapPatronage",
]
