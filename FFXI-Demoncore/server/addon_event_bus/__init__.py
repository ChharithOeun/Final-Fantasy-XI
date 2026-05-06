"""Addon event bus — pub/sub for the addon ecosystem.

lua_addon_loader knows what addons exist and what hooks
they registered. This module is the actual dispatcher: a
server-side event happens (on_damage, on_target_change,
on_buff_applied), and every addon subscribed to that hook
gets called with the event payload.

The bus is per-subscriber (not per-player), so the same
bus can carry events for player addons AND mob/NPC addons
on the same hook. A boss's gearswap addon and a player's
gearswap addon both subscribe to "on_engaged" — when
either the boss or the player engages, the event fires
once and BOTH listeners (filtered by entity_id) hear it.

Subscribers are opaque (subscriber_id strings); the actual
Lua VM lives elsewhere. This module only routes events
from event_id → list of subscriber_ids.

Public surface
--------------
    EventEnvelope dataclass (frozen) — payload for one event
    AddonEventBus
        .subscribe(subscriber_id, hook_name) -> bool
        .unsubscribe(subscriber_id, hook_name) -> bool
        .publish(envelope) -> int   (count delivered)
        .subscribers_for(hook_name) -> list[str]
        .subscriptions_for(subscriber_id) -> list[str]
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class EventEnvelope:
    hook_name: str
    source_id: str          # who/what triggered the event
    payload: dict[str, t.Any]
    fired_at: int


@dataclasses.dataclass
class AddonEventBus:
    # hook_name → ordered list of subscriber_ids
    _by_hook: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )
    # subscriber_id → set of hook_names they listen to
    _by_sub: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    # delivery log: hook_name → list of (subscriber_id, fired_at)
    _delivery_log: list[tuple[str, str, int]] = \
        dataclasses.field(default_factory=list)

    def subscribe(
        self, *, subscriber_id: str, hook_name: str,
    ) -> bool:
        if not subscriber_id or not hook_name:
            return False
        subs = self._by_hook.setdefault(hook_name, [])
        if subscriber_id in subs:
            return False
        subs.append(subscriber_id)
        self._by_sub.setdefault(subscriber_id, set()).add(hook_name)
        return True

    def unsubscribe(
        self, *, subscriber_id: str, hook_name: str,
    ) -> bool:
        subs = self._by_hook.get(hook_name)
        if subs is None or subscriber_id not in subs:
            return False
        subs.remove(subscriber_id)
        if subscriber_id in self._by_sub:
            self._by_sub[subscriber_id].discard(hook_name)
        return True

    def unsubscribe_all(
        self, *, subscriber_id: str,
    ) -> int:
        hooks = list(self._by_sub.get(subscriber_id, set()))
        count = 0
        for h in hooks:
            if self.unsubscribe(
                subscriber_id=subscriber_id, hook_name=h,
            ):
                count += 1
        return count

    def publish(self, *, envelope: EventEnvelope) -> int:
        subs = list(self._by_hook.get(envelope.hook_name, []))
        for s in subs:
            self._delivery_log.append(
                (envelope.hook_name, s, envelope.fired_at),
            )
        return len(subs)

    def subscribers_for(
        self, *, hook_name: str,
    ) -> list[str]:
        return list(self._by_hook.get(hook_name, []))

    def subscriptions_for(
        self, *, subscriber_id: str,
    ) -> list[str]:
        return list(self._by_sub.get(subscriber_id, set()))

    def delivery_count(self, *, hook_name: str) -> int:
        return sum(1 for h, _s, _ts in self._delivery_log if h == hook_name)

    def total_subscriptions(self) -> int:
        return sum(len(v) for v in self._by_hook.values())


__all__ = [
    "EventEnvelope", "AddonEventBus",
]
