"""Signature items — crafted items bear the maker's name.

In retail FFXI a HQ piece is "+1/+2/+3"; the maker is
forgotten the second it leaves their inventory.
Demoncore preserves the maker's identity ON the item
itself. A crafted piece (HQ tier or Masterwork) is born
with a SIGNATURE — a small etched mark, a player_id
embedded in the item's metadata, and a fame counter on
the maker side that ticks every time the item changes
hands or is used in combat.

Per-item we track:
    item_id         the unique instance id (not the
                    item template — each crafted instance
                    is its own record)
    template_id     the recipe/template (e.g. "vermillion_cloak")
    maker_id        the crafter
    tier            HQ1 / HQ2 / HQ3 / MASTERWORK
    forged_day      the day it was crafted
    times_traded    number of player-to-player transfers
                    (delivery_box, trade_window)
    times_used_in_combat number of weapon-skills /
                          spell-casts done with it
                          equipped

Maker fame: an aggregate score per crafter computed from
all signed items they've made. The more your items
travel and survive in combat, the more famous you become.
This feeds into honor_reputation and
research_log/recipe_book_ui (recipes get a "discovered
by" credit too).

Public surface
--------------
    Tier enum
    SignedItem dataclass (frozen)
    SignatureItems
        .forge(item_id, template_id, maker_id, tier, day)
            -> bool
        .record_trade(item_id) -> bool
        .record_combat_use(item_id) -> bool
        .item(item_id) -> Optional[SignedItem]
        .items_by_maker(maker_id) -> list[SignedItem]
        .maker_fame(maker_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Tier(str, enum.Enum):
    NQ = "nq"
    HQ1 = "hq1"
    HQ2 = "hq2"
    HQ3 = "hq3"
    MASTERWORK = "masterwork"


_TIER_FAME_BASE = {
    Tier.NQ: 0,
    Tier.HQ1: 1,
    Tier.HQ2: 2,
    Tier.HQ3: 4,
    Tier.MASTERWORK: 10,
}


@dataclasses.dataclass(frozen=True)
class SignedItem:
    item_id: str
    template_id: str
    maker_id: str
    tier: Tier
    forged_day: int
    times_traded: int
    times_used_in_combat: int


@dataclasses.dataclass
class _Sig:
    template_id: str
    maker_id: str
    tier: Tier
    forged_day: int
    times_traded: int = 0
    times_used: int = 0


@dataclasses.dataclass
class SignatureItems:
    _items: dict[str, _Sig] = dataclasses.field(
        default_factory=dict,
    )

    def forge(
        self, *, item_id: str, template_id: str,
        maker_id: str, tier: Tier, forged_day: int,
    ) -> bool:
        if not item_id or not template_id or not maker_id:
            return False
        # NQ items are not signed
        if tier == Tier.NQ:
            return False
        if forged_day < 0:
            return False
        if item_id in self._items:
            return False
        self._items[item_id] = _Sig(
            template_id=template_id, maker_id=maker_id,
            tier=tier, forged_day=forged_day,
        )
        return True

    def record_trade(self, *, item_id: str) -> bool:
        if item_id not in self._items:
            return False
        self._items[item_id].times_traded += 1
        return True

    def record_combat_use(self, *, item_id: str) -> bool:
        if item_id not in self._items:
            return False
        self._items[item_id].times_used += 1
        return True

    def item(
        self, *, item_id: str,
    ) -> t.Optional[SignedItem]:
        if item_id not in self._items:
            return None
        s = self._items[item_id]
        return SignedItem(
            item_id=item_id, template_id=s.template_id,
            maker_id=s.maker_id, tier=s.tier,
            forged_day=s.forged_day,
            times_traded=s.times_traded,
            times_used_in_combat=s.times_used,
        )

    def items_by_maker(
        self, *, maker_id: str,
    ) -> list[SignedItem]:
        out = []
        for item_id, s in self._items.items():
            if s.maker_id == maker_id:
                out.append(SignedItem(
                    item_id=item_id, template_id=s.template_id,
                    maker_id=s.maker_id, tier=s.tier,
                    forged_day=s.forged_day,
                    times_traded=s.times_traded,
                    times_used_in_combat=s.times_used,
                ))
        out.sort(key=lambda it: it.item_id)
        return out

    def maker_fame(self, *, maker_id: str) -> int:
        total = 0
        for s in self._items.values():
            if s.maker_id != maker_id:
                continue
            base = _TIER_FAME_BASE[s.tier]
            # Items that travel/fight contribute more
            multiplier = 1 + (s.times_traded // 5)
            usage_bonus = s.times_used // 50
            total += base * multiplier + usage_bonus
        return total


__all__ = [
    "Tier", "SignedItem", "SignatureItems",
]
