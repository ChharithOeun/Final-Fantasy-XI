"""Economy supply index — track live supply per item.

The economy regulator needs to know how much of each item exists
in the world right now. This module aggregates supply across all
sources:

* PLAYER_INVENTORY — items held by players
* AH_LISTING — items listed on the auction house
* NPC_VENDOR_STOCK — what merchants are holding
* CARAVAN_IN_TRANSIT — goods moving on trade routes
* MOB_DROP_EXPECTED — projected drops at current kill rates
* CRAFT_OUTPUT_EXPECTED — projected synth output

Each source publishes a SnapshotEntry; the index sums them and
keeps a trailing 24-hour history so the regulator can see TRENDS,
not just point-in-time numbers. A material whose supply is HIGH
but TRENDING DOWN sharply is more "scarce" than one that's low
but stable.

Public surface
--------------
    SupplySource enum
    SnapshotEntry dataclass
    SupplyIndex dataclass — current snapshot + history
    EconomySupplyIndex
        .publish(item_id, source, count, now_seconds)
        .total(item_id) / .by_source(item_id) / .trend_pct(item_id)
        .snapshot_at(item_id, now_seconds)
        .compact_old(now_seconds, max_age)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# How long we retain snapshot history. 24 game-hours by default
# so the regulator can compute a meaningful trend.
DEFAULT_HISTORY_SECONDS = 60 * 60 * 24


class SupplySource(str, enum.Enum):
    PLAYER_INVENTORY = "player_inventory"
    AH_LISTING = "ah_listing"
    NPC_VENDOR_STOCK = "npc_vendor_stock"
    CARAVAN_IN_TRANSIT = "caravan_in_transit"
    MOB_DROP_EXPECTED = "mob_drop_expected"
    CRAFT_OUTPUT_EXPECTED = "craft_output_expected"


@dataclasses.dataclass(frozen=True)
class SnapshotEntry:
    item_id: str
    source: SupplySource
    count: int
    recorded_at_seconds: float


@dataclasses.dataclass(frozen=True)
class SupplyIndex:
    item_id: str
    total_count: int
    by_source: dict[SupplySource, int]
    trend_pct: float            # negative = supply dropping
    history_window_seconds: float
    sample_count: int


@dataclasses.dataclass
class EconomySupplyIndex:
    history_seconds: float = DEFAULT_HISTORY_SECONDS
    # Latest count per (item, source) — the LIVE state
    _latest: dict[
        tuple[str, SupplySource], int,
    ] = dataclasses.field(default_factory=dict)
    # Trailing history per item — list of (timestamp, total) pairs
    _history: dict[
        str, list[tuple[float, int]],
    ] = dataclasses.field(default_factory=dict)

    def publish(
        self, *, item_id: str, source: SupplySource,
        count: int, now_seconds: float,
    ) -> int:
        """Record current count for (item, source). Returns the
        new total across all sources."""
        if count < 0:
            raise ValueError(f"count {count} cannot be negative")
        self._latest[(item_id, source)] = count
        total = self.total(item_id)
        history = self._history.setdefault(item_id, [])
        history.append((now_seconds, total))
        # Drop history beyond the window
        cutoff = now_seconds - self.history_seconds
        while history and history[0][0] < cutoff:
            history.pop(0)
        return total

    def total(self, item_id: str) -> int:
        return sum(
            count for (i_id, _src), count
            in self._latest.items()
            if i_id == item_id
        )

    def by_source(
        self, item_id: str,
    ) -> dict[SupplySource, int]:
        out: dict[SupplySource, int] = {}
        for (i_id, src), count in self._latest.items():
            if i_id == item_id:
                out[src] = count
        return out

    def trend_pct(
        self, *, item_id: str, now_seconds: float,
    ) -> float:
        """Percentage change in total supply over the history
        window. Returns 0.0 if there's not enough data."""
        history = self._history.get(item_id, [])
        if len(history) < 2:
            return 0.0
        oldest_ts, oldest_total = history[0]
        latest_ts, latest_total = history[-1]
        if oldest_total == 0:
            return 100.0 if latest_total > 0 else 0.0
        return ((latest_total - oldest_total) / oldest_total) * 100.0

    def snapshot_at(
        self, *, item_id: str, now_seconds: float,
    ) -> SupplyIndex:
        return SupplyIndex(
            item_id=item_id,
            total_count=self.total(item_id),
            by_source=self.by_source(item_id),
            trend_pct=self.trend_pct(
                item_id=item_id, now_seconds=now_seconds,
            ),
            history_window_seconds=self.history_seconds,
            sample_count=len(self._history.get(item_id, [])),
        )

    def all_items(self) -> tuple[str, ...]:
        return tuple({
            i_id for (i_id, _src) in self._latest
        })

    def compact_old(
        self, *, now_seconds: float,
        max_age_seconds: t.Optional[float] = None,
    ) -> int:
        """Drop history points older than max_age. Defaults to
        history_seconds. Returns count dropped."""
        ma = max_age_seconds or self.history_seconds
        cutoff = now_seconds - ma
        dropped = 0
        for hist in self._history.values():
            before = len(hist)
            while hist and hist[0][0] < cutoff:
                hist.pop(0)
            dropped += before - len(hist)
        return dropped


__all__ = [
    "DEFAULT_HISTORY_SECONDS",
    "SupplySource", "SnapshotEntry", "SupplyIndex",
    "EconomySupplyIndex",
]
