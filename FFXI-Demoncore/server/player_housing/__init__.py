"""Player housing — Mog House extended with build/decorate.

Builds on top of the existing Mog House by adding ROOMS, FLOORS,
and EXTERIOR slots a player can decorate. Each placed
furnishing carries stat-mood bonuses (overlapping with the
existing furnishings system) and contributes to the house's
AMBIANCE — which gates passive buffs like extra resting regen
or a small experience bonus while logged out from inside.

Each house has VISIT_PERMISSIONS controlling who can enter:
PRIVATE / FRIENDS / LINKSHELL / PUBLIC. A visitor only gets
the AMBIANCE bonus while inside.

Public surface
--------------
    HouseTier enum
    AmbianceTier enum
    DecorSlotKind enum
    VisitPermission enum
    PlacedDecor dataclass
    HouseProfile dataclass
    PlayerHousing
        .charter_house(player_id, tier, nation)
        .upgrade_tier(player_id)
        .place_decor(player_id, slot, item_id, ambiance_bonus)
        .remove_decor(player_id, slot)
        .set_visit_permission(player_id, permission)
        .visit(visitor_id, host_id) -> ambiance bonus
        .ambiance_for(player_id) -> AmbianceTier
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Caps.
MAX_FRIENDS_PER_HOUSE = 100
AMBIANCE_TIER_THRESHOLDS: tuple[
    tuple[str, int], ...,
] = (
    ("legendary", 200),
    ("luxurious", 100),
    ("comfortable", 50),
    ("homely", 20),
    ("bare", 0),
)


class HouseTier(str, enum.Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    MANOR = "manor"
    ESTATE = "estate"


class AmbianceTier(str, enum.Enum):
    BARE = "bare"
    HOMELY = "homely"
    COMFORTABLE = "comfortable"
    LUXURIOUS = "luxurious"
    LEGENDARY = "legendary"


class DecorSlotKind(str, enum.Enum):
    LIVING_ROOM_1 = "living_room_1"
    LIVING_ROOM_2 = "living_room_2"
    BEDROOM_1 = "bedroom_1"
    BEDROOM_2 = "bedroom_2"
    GARDEN_1 = "garden_1"
    GARDEN_2 = "garden_2"
    EXTERIOR_FRONT = "exterior_front"
    EXTERIOR_BACK = "exterior_back"
    SHOWCASE = "showcase"
    HEARTH = "hearth"


# Decor slot allowance per tier.
_TIER_SLOT_ALLOWANCE: dict[HouseTier, int] = {
    HouseTier.APARTMENT: 4,
    HouseTier.HOUSE: 6,
    HouseTier.MANOR: 8,
    HouseTier.ESTATE: 10,
}


class VisitPermission(str, enum.Enum):
    PRIVATE = "private"
    FRIENDS = "friends"
    LINKSHELL = "linkshell"
    PUBLIC = "public"


@dataclasses.dataclass(frozen=True)
class PlacedDecor:
    slot: DecorSlotKind
    item_id: str
    ambiance_bonus: int


@dataclasses.dataclass
class HouseProfile:
    player_id: str
    tier: HouseTier
    nation: str
    decor: dict[DecorSlotKind, PlacedDecor] = (
        dataclasses.field(default_factory=dict)
    )
    visit_permission: VisitPermission = (
        VisitPermission.FRIENDS
    )
    friends_allowed: set[str] = dataclasses.field(
        default_factory=set,
    )
    linkshell_id: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class VisitOutcome:
    accepted: bool
    host_id: str
    ambiance: AmbianceTier
    bonus_pct: int
    reason: t.Optional[str] = None


def _ambiance_for_score(score: int) -> AmbianceTier:
    for label, threshold in AMBIANCE_TIER_THRESHOLDS:
        if score >= threshold:
            return AmbianceTier(label)
    return AmbianceTier.BARE


def _bonus_pct_for_ambiance(
    tier: AmbianceTier,
) -> int:
    return {
        AmbianceTier.BARE: 0,
        AmbianceTier.HOMELY: 2,
        AmbianceTier.COMFORTABLE: 5,
        AmbianceTier.LUXURIOUS: 10,
        AmbianceTier.LEGENDARY: 20,
    }[tier]


@dataclasses.dataclass
class PlayerHousing:
    _houses: dict[str, HouseProfile] = dataclasses.field(
        default_factory=dict,
    )

    def charter_house(
        self, *, player_id: str,
        tier: HouseTier = HouseTier.APARTMENT,
        nation: str = "",
    ) -> t.Optional[HouseProfile]:
        if player_id in self._houses:
            return None
        h = HouseProfile(
            player_id=player_id, tier=tier, nation=nation,
        )
        self._houses[player_id] = h
        return h

    def upgrade_tier(
        self, *, player_id: str,
    ) -> t.Optional[HouseTier]:
        h = self._houses.get(player_id)
        if h is None:
            return None
        order = list(HouseTier)
        idx = order.index(h.tier)
        if idx >= len(order) - 1:
            return None
        h.tier = order[idx + 1]
        return h.tier

    def place_decor(
        self, *, player_id: str,
        slot: DecorSlotKind, item_id: str,
        ambiance_bonus: int = 1,
    ) -> bool:
        h = self._houses.get(player_id)
        if h is None or not item_id:
            return False
        if ambiance_bonus < 0:
            return False
        # Check slot allowance vs tier
        slots_used = (
            sum(1 for s in h.decor if s != slot)
            + (1 if slot not in h.decor else 0)
        )
        # Simpler: count distinct slots after placement
        proposed_count = (
            len(h.decor)
            if slot in h.decor
            else len(h.decor) + 1
        )
        if proposed_count > _TIER_SLOT_ALLOWANCE[h.tier]:
            return False
        h.decor[slot] = PlacedDecor(
            slot=slot, item_id=item_id,
            ambiance_bonus=ambiance_bonus,
        )
        return True

    def remove_decor(
        self, *, player_id: str,
        slot: DecorSlotKind,
    ) -> bool:
        h = self._houses.get(player_id)
        if h is None or slot not in h.decor:
            return False
        del h.decor[slot]
        return True

    def set_visit_permission(
        self, *, player_id: str,
        permission: VisitPermission,
    ) -> bool:
        h = self._houses.get(player_id)
        if h is None:
            return False
        h.visit_permission = permission
        return True

    def add_friend(
        self, *, player_id: str, friend_id: str,
    ) -> bool:
        h = self._houses.get(player_id)
        if h is None:
            return False
        if friend_id == player_id:
            return False
        if len(h.friends_allowed) >= MAX_FRIENDS_PER_HOUSE:
            return False
        if friend_id in h.friends_allowed:
            return False
        h.friends_allowed.add(friend_id)
        return True

    def set_linkshell(
        self, *, player_id: str,
        linkshell_id: t.Optional[str],
    ) -> bool:
        h = self._houses.get(player_id)
        if h is None:
            return False
        h.linkshell_id = linkshell_id
        return True

    def ambiance_for(
        self, *, player_id: str,
    ) -> t.Optional[AmbianceTier]:
        h = self._houses.get(player_id)
        if h is None:
            return None
        score = sum(
            d.ambiance_bonus for d in h.decor.values()
        )
        return _ambiance_for_score(score)

    def visit(
        self, *, visitor_id: str, host_id: str,
        visitor_linkshells: tuple[str, ...] = (),
    ) -> VisitOutcome:
        h = self._houses.get(host_id)
        if h is None:
            return VisitOutcome(
                accepted=False, host_id=host_id,
                ambiance=AmbianceTier.BARE,
                bonus_pct=0,
                reason="no such house",
            )
        # Self-visit always allowed
        if visitor_id == host_id:
            allowed = True
        elif h.visit_permission == VisitPermission.PUBLIC:
            allowed = True
        elif h.visit_permission == VisitPermission.PRIVATE:
            allowed = False
        elif h.visit_permission == VisitPermission.FRIENDS:
            allowed = visitor_id in h.friends_allowed
        elif h.visit_permission == VisitPermission.LINKSHELL:
            allowed = (
                h.linkshell_id is not None
                and h.linkshell_id in visitor_linkshells
            )
        else:
            allowed = False
        if not allowed:
            return VisitOutcome(
                accepted=False, host_id=host_id,
                ambiance=AmbianceTier.BARE,
                bonus_pct=0,
                reason="permission denied",
            )
        amb = self.ambiance_for(player_id=host_id)
        return VisitOutcome(
            accepted=True, host_id=host_id,
            ambiance=amb,
            bonus_pct=_bonus_pct_for_ambiance(amb),
        )

    def total_houses(self) -> int:
        return len(self._houses)


__all__ = [
    "MAX_FRIENDS_PER_HOUSE",
    "HouseTier", "AmbianceTier",
    "DecorSlotKind", "VisitPermission",
    "PlacedDecor", "HouseProfile",
    "VisitOutcome",
    "PlayerHousing",
]
