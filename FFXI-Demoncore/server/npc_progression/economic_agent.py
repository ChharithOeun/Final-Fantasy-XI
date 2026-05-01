"""NPC economic agent — wallet + observe-market + purchase decisions.

Per NPC_PROGRESSION.md decision loop:

    For each NPC:
      earn_gil(role × level × ambient activity)
      observe_market(local vendors + AH listings × stat priorities)
      if can_afford(top_wishlist_item) and item_is_better(item, current):
        purchase(item)
        equip(item)
        update_wishlist()

NPCs become BUYERS, not just stock-providers — keeps mid-tier gear
demand high even with no players online; AH listings get cleared
even outside player active hours.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .civilian import NpcRole, NpcSnapshot


# Per-role per-Vana'diel-hour gil earn rate, scaled by level.
HOURLY_GIL_BY_ROLE: dict[NpcRole, int] = {
    NpcRole.SHOPKEEPER: 200,
    NpcRole.GUILD_MASTER: 350,
    NpcRole.GUARD: 80,
    NpcRole.AMBIENT_TOWNFOLK: 30,
    NpcRole.QUEST_GIVER: 120,
}


@dataclasses.dataclass(frozen=True)
class MarketListing:
    """A purchasable item the NPC can observe + consider buying."""
    item_id: str
    seller_id: str
    price: int
    item_tier: int               # 0-99; matches the role's gear progression
    item_role_fit: dict[NpcRole, float]   # role -> 0..1 fit score
    stats_score: float = 0.0     # composite score for 'is this better'


@dataclasses.dataclass
class EquippedItem:
    """A piece of gear currently equipped by the NPC."""
    item_id: str
    item_tier: int
    stats_score: float
    role_fit: float


def earn_gil_for_role(state: NpcSnapshot,
                       *,
                       hours_elapsed: float = 1.0) -> int:
    """Award gil based on role + level. Returns gil added.

    Per the doc: 'role × level × ambient activity'. Level scaling
    is sub-linear so apex shopkeepers don't pump the economy.
    """
    if state.is_retired:
        return 0
    base = HOURLY_GIL_BY_ROLE.get(state.role, 50)
    # Sub-linear level multiplier: 1 + level/30 (so lvl 99 ≈ 4.3x base)
    level_mult = 1.0 + state.level / 30.0
    earned = int(base * level_mult * hours_elapsed)
    state.gil += earned
    return earned


def can_afford(state: NpcSnapshot, listing: MarketListing) -> bool:
    """NPC keeps a 20% buffer below current gil — they don't drain
    their wallet for every upgrade."""
    BUFFER_FRACTION = 0.20
    spending_cap = int(state.gil * (1.0 - BUFFER_FRACTION))
    return listing.price <= spending_cap


def is_item_better(listing: MarketListing,
                    current: t.Optional[EquippedItem]) -> bool:
    """An item is 'better' if its tier is strictly higher OR its
    composite stats score is strictly higher (with tier ties broken
    by fit-to-role)."""
    if current is None:
        return True
    if listing.item_tier > current.item_tier:
        return True
    if listing.item_tier == current.item_tier:
        return listing.stats_score > current.stats_score
    return False


def choose_purchase(state: NpcSnapshot,
                     *,
                     listings: list[MarketListing],
                     current_gear: dict[str, EquippedItem],
                     ) -> t.Optional[MarketListing]:
    """Apply the decision loop and return the listing the NPC will
    buy this tick (or None).

    Strategy:
      1. Filter to listings with role_fit >= 0.5 for our role
      2. Sort by stats_score descending
      3. Walk the sorted list; pick the first that's affordable AND
         strictly better than current gear in that slot
      4. If nothing qualifies, return None (NPC keeps shopping next tick)

    `current_gear` keys are slot names ('body' / 'head' / etc.); we
    match by item_id-prefix conventionally (caller ensures the slot
    keys correspond to listing.item_id slot prefixes).
    """
    if state.is_retired:
        return None

    role_listings = [l for l in listings
                       if l.item_role_fit.get(state.role, 0.0) >= 0.5]
    if not role_listings:
        return None
    role_listings.sort(key=lambda l: l.stats_score, reverse=True)

    for listing in role_listings:
        if not can_afford(state, listing):
            continue
        # Look up the slot the listing would occupy (use item_id prefix
        # before the first '/' or '_' as the slot key, default 'misc')
        slot_key = listing.item_id.split("_", 1)[0]
        current = current_gear.get(slot_key)
        if is_item_better(listing, current):
            return listing
    return None


# ----------------------------------------------------------------------
# Manager (one EconomicAgent per NPC; thin wrapper around state)
# ----------------------------------------------------------------------

@dataclasses.dataclass
class EconomicAgent:
    """A live economic agent for one NPC — bundles their state, gear,
    and the decision loop."""
    state: NpcSnapshot
    current_gear: dict[str, EquippedItem] = dataclasses.field(
        default_factory=dict)

    def tick(self,
              *,
              hours_elapsed: float,
              listings: list[MarketListing],
              now: float = 0) -> t.Optional[MarketListing]:
        """One Vana'diel-hour tick. Earns gil, considers purchases,
        returns the bought listing if anything was acquired."""
        earn_gil_for_role(self.state, hours_elapsed=hours_elapsed)
        purchase = choose_purchase(
            self.state,
            listings=listings,
            current_gear=self.current_gear,
        )
        if purchase is None:
            return None

        # Apply the purchase
        self.state.gil -= purchase.price
        slot_key = purchase.item_id.split("_", 1)[0]
        self.current_gear[slot_key] = EquippedItem(
            item_id=purchase.item_id,
            item_tier=purchase.item_tier,
            stats_score=purchase.stats_score,
            role_fit=purchase.item_role_fit.get(self.state.role, 0.0),
        )
        return purchase
