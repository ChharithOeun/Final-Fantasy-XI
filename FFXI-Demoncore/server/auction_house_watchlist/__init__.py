"""Auction house watchlist — track items / sellers / alerts.

A player adds WATCH RULES — match by item_id, seller_id, or
both, plus an optional max_price. When a new AH listing posts
that matches a rule, an ALERT fires for the watcher.

Also tracks DELIST EVENTS so a watcher who just missed a sale
sees they were too slow.

Public surface
--------------
    WatchKind enum
    WatchRule dataclass
    Alert dataclass
    AuctionHouseWatchlist
        .add_rule(player_id, kind, item_id, seller_id, max_price)
        .remove_rule(player_id, rule_id)
        .rules_for(player_id)
        .post_listing(item_id, seller_id, price, listing_id) -> alerts
        .delist(listing_id) -> alerts (for already-watching players)
        .pending_alerts(player_id)
        .ack(player_id, alert_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class WatchKind(str, enum.Enum):
    ITEM_ID = "item_id"           # watch a specific item
    SELLER_ID = "seller_id"        # watch a seller's posts
    ITEM_AND_SELLER = "item_and_seller"


class AlertKind(str, enum.Enum):
    NEW_LISTING = "new_listing"
    PRICE_DROP = "price_drop"
    DELISTED = "delisted"


@dataclasses.dataclass
class WatchRule:
    rule_id: str
    player_id: str
    kind: WatchKind
    item_id: t.Optional[str] = None
    seller_id: t.Optional[str] = None
    max_price: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class Alert:
    alert_id: str
    player_id: str
    rule_id: str
    kind: AlertKind
    listing_id: str
    item_id: str
    seller_id: str
    price: int


@dataclasses.dataclass
class _Listing:
    listing_id: str
    item_id: str
    seller_id: str
    price: int


@dataclasses.dataclass
class AuctionHouseWatchlist:
    _rules: dict[str, WatchRule] = dataclasses.field(
        default_factory=dict,
    )
    _listings: dict[str, _Listing] = dataclasses.field(
        default_factory=dict,
    )
    _alerts: dict[str, Alert] = dataclasses.field(
        default_factory=dict,
    )
    _acked: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    # listing_id -> set of (player_id, rule_id) who saw it
    _seen: dict[
        str, set[tuple[str, str]],
    ] = dataclasses.field(default_factory=dict)
    _next_rule_id: int = 0
    _next_alert_id: int = 0

    def add_rule(
        self, *, player_id: str,
        kind: WatchKind,
        item_id: t.Optional[str] = None,
        seller_id: t.Optional[str] = None,
        max_price: t.Optional[int] = None,
    ) -> t.Optional[WatchRule]:
        # Validate kind / fields
        if kind == WatchKind.ITEM_ID and item_id is None:
            return None
        if kind == WatchKind.SELLER_ID and seller_id is None:
            return None
        if (
            kind == WatchKind.ITEM_AND_SELLER
            and (item_id is None or seller_id is None)
        ):
            return None
        rid = f"rule_{self._next_rule_id}"
        self._next_rule_id += 1
        rule = WatchRule(
            rule_id=rid, player_id=player_id, kind=kind,
            item_id=item_id, seller_id=seller_id,
            max_price=max_price,
        )
        self._rules[rid] = rule
        return rule

    def remove_rule(
        self, *, player_id: str, rule_id: str,
    ) -> bool:
        rule = self._rules.get(rule_id)
        if rule is None or rule.player_id != player_id:
            return False
        del self._rules[rule_id]
        return True

    def rules_for(
        self, player_id: str,
    ) -> tuple[WatchRule, ...]:
        return tuple(
            r for r in self._rules.values()
            if r.player_id == player_id
        )

    def _matches(
        self, rule: WatchRule, listing: _Listing,
    ) -> bool:
        if rule.kind == WatchKind.ITEM_ID:
            ok = rule.item_id == listing.item_id
        elif rule.kind == WatchKind.SELLER_ID:
            ok = rule.seller_id == listing.seller_id
        else:
            ok = (
                rule.item_id == listing.item_id
                and rule.seller_id == listing.seller_id
            )
        if not ok:
            return False
        if rule.max_price is not None:
            return listing.price <= rule.max_price
        return True

    def post_listing(
        self, *, listing_id: str, item_id: str,
        seller_id: str, price: int,
    ) -> tuple[Alert, ...]:
        if not item_id or not seller_id or price < 0:
            return ()
        listing = _Listing(
            listing_id=listing_id, item_id=item_id,
            seller_id=seller_id, price=price,
        )
        self._listings[listing_id] = listing
        out: list[Alert] = []
        for rule in self._rules.values():
            if not self._matches(rule, listing):
                continue
            seen_key = (rule.player_id, rule.rule_id)
            seen_set = self._seen.setdefault(
                listing_id, set(),
            )
            if seen_key in seen_set:
                continue
            seen_set.add(seen_key)
            aid = f"alert_{self._next_alert_id}"
            self._next_alert_id += 1
            alert = Alert(
                alert_id=aid,
                player_id=rule.player_id,
                rule_id=rule.rule_id,
                kind=AlertKind.NEW_LISTING,
                listing_id=listing_id,
                item_id=item_id,
                seller_id=seller_id,
                price=price,
            )
            self._alerts[aid] = alert
            out.append(alert)
        return tuple(out)

    def delist(
        self, *, listing_id: str,
    ) -> tuple[Alert, ...]:
        listing = self._listings.pop(listing_id, None)
        if listing is None:
            return ()
        # Anyone who saw this listing gets a DELISTED alert
        seen = self._seen.pop(listing_id, set())
        out: list[Alert] = []
        for player_id, rule_id in seen:
            aid = f"alert_{self._next_alert_id}"
            self._next_alert_id += 1
            alert = Alert(
                alert_id=aid,
                player_id=player_id,
                rule_id=rule_id,
                kind=AlertKind.DELISTED,
                listing_id=listing_id,
                item_id=listing.item_id,
                seller_id=listing.seller_id,
                price=listing.price,
            )
            self._alerts[aid] = alert
            out.append(alert)
        return tuple(out)

    def pending_alerts(
        self, player_id: str,
    ) -> tuple[Alert, ...]:
        acked = self._acked.get(player_id, set())
        return tuple(
            a for a in self._alerts.values()
            if a.player_id == player_id
            and a.alert_id not in acked
        )

    def ack(
        self, *, player_id: str, alert_id: str,
    ) -> bool:
        a = self._alerts.get(alert_id)
        if a is None or a.player_id != player_id:
            return False
        s = self._acked.setdefault(player_id, set())
        if alert_id in s:
            return False
        s.add(alert_id)
        return True

    def total_rules(self) -> int:
        return len(self._rules)

    def total_alerts(self) -> int:
        return len(self._alerts)


__all__ = [
    "WatchKind", "AlertKind",
    "WatchRule", "Alert",
    "AuctionHouseWatchlist",
]
