"""Economy demand signal — track per-item consumption pressure.

Where economy_supply_index measures how much of an item EXISTS,
this module measures how fast it's being CONSUMED. The regulator
combines the two to find scarcity (high demand + falling supply).

Demand events
-------------
The orchestrator publishes a `DemandEvent` whenever an item is:

* PURCHASED at an NPC vendor
* WON at AH auction
* CRAFTED INTO another item (recipe consumption)
* TURNED IN as a quest objective deliverable
* USED (consumable: potion drunk, scroll cast)
* LOST on death (Demoncore permadeath)

Each event has a count and timestamp. The DemandSignal aggregates
events into a per-item rate (events per game-hour) over a sliding
window, plus a trend (rate this period vs. previous period).

Public surface
--------------
    DemandKind enum
    DemandEvent dataclass
    DemandSignal dataclass — current snapshot
    EconomyDemandTracker
        .record(item_id, kind, count, now_seconds)
        .signal_for(item_id, now_seconds) -> DemandSignal
        .top_demanded(top_n, now_seconds)
        .compact_old(now_seconds, max_age_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Sliding window for the rate computation (default 1 game-hour).
DEFAULT_WINDOW_SECONDS = 3600.0


class DemandKind(str, enum.Enum):
    PURCHASE_NPC = "purchase_npc"
    PURCHASE_AH = "purchase_ah"
    CRAFT_CONSUMED = "craft_consumed"
    QUEST_TURN_IN = "quest_turn_in"
    USED_CONSUMABLE = "used_consumable"
    LOST_ON_DEATH = "lost_on_death"


@dataclasses.dataclass(frozen=True)
class DemandEvent:
    item_id: str
    kind: DemandKind
    count: int
    recorded_at_seconds: float


@dataclasses.dataclass(frozen=True)
class DemandSignal:
    item_id: str
    rate_per_hour: float
    trend_pct: float            # current vs. previous window
    sample_event_count: int     # events in current window
    previous_window_count: int  # events in previous window (for cold-start gating)
    by_kind: dict[DemandKind, int]
    window_seconds: float


@dataclasses.dataclass
class EconomyDemandTracker:
    window_seconds: float = DEFAULT_WINDOW_SECONDS
    _events: dict[str, list[DemandEvent]] = dataclasses.field(
        default_factory=dict,
    )

    def record(
        self, *, item_id: str, kind: DemandKind,
        count: int = 1, now_seconds: float = 0.0,
    ) -> None:
        if count <= 0:
            raise ValueError(
                f"count {count} must be positive",
            )
        ev = DemandEvent(
            item_id=item_id, kind=kind, count=count,
            recorded_at_seconds=now_seconds,
        )
        self._events.setdefault(item_id, []).append(ev)
        # Trim old events beyond 2x window so trend computation
        # has the previous window available.
        cutoff = now_seconds - 2 * self.window_seconds
        events = self._events[item_id]
        while events and events[0].recorded_at_seconds < cutoff:
            events.pop(0)

    def signal_for(
        self, *, item_id: str, now_seconds: float,
    ) -> DemandSignal:
        events = self._events.get(item_id, [])
        if not events:
            return DemandSignal(
                item_id=item_id, rate_per_hour=0.0,
                trend_pct=0.0, sample_event_count=0,
                previous_window_count=0,
                by_kind={},
                window_seconds=self.window_seconds,
            )
        # Current window (0..window_seconds ago)
        cur_cutoff = now_seconds - self.window_seconds
        prev_cutoff = now_seconds - 2 * self.window_seconds
        cur_count = 0
        prev_count = 0
        by_kind: dict[DemandKind, int] = {}
        sampled = 0
        for ev in events:
            if ev.recorded_at_seconds >= cur_cutoff:
                cur_count += ev.count
                by_kind[ev.kind] = by_kind.get(
                    ev.kind, 0,
                ) + ev.count
                sampled += 1
            elif ev.recorded_at_seconds >= prev_cutoff:
                prev_count += ev.count
        rate = cur_count / (self.window_seconds / 3600.0)
        if prev_count == 0:
            trend = 100.0 if cur_count > 0 else 0.0
        else:
            trend = ((cur_count - prev_count) / prev_count) * 100.0
        return DemandSignal(
            item_id=item_id, rate_per_hour=rate,
            trend_pct=trend, sample_event_count=sampled,
            previous_window_count=prev_count,
            by_kind=by_kind,
            window_seconds=self.window_seconds,
        )

    def top_demanded(
        self, *, top_n: int, now_seconds: float,
    ) -> tuple[DemandSignal, ...]:
        signals = [
            self.signal_for(item_id=i, now_seconds=now_seconds)
            for i in self._events
        ]
        signals.sort(key=lambda s: s.rate_per_hour, reverse=True)
        return tuple(signals[:top_n])

    def all_items(self) -> tuple[str, ...]:
        return tuple(self._events.keys())

    def compact_old(
        self, *, now_seconds: float,
        max_age_seconds: t.Optional[float] = None,
    ) -> int:
        ma = max_age_seconds or (2 * self.window_seconds)
        cutoff = now_seconds - ma
        dropped = 0
        for events in self._events.values():
            before = len(events)
            while events and events[0].recorded_at_seconds < cutoff:
                events.pop(0)
            dropped += before - len(events)
        return dropped


__all__ = [
    "DEFAULT_WINDOW_SECONDS",
    "DemandKind", "DemandEvent", "DemandSignal",
    "EconomyDemandTracker",
]
