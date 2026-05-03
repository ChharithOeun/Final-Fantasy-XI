"""Cooking spoilage — food/potion expiration.

Consumables age. Fresh fish goes off in a game-day; cooked meals
last about three; alchemy potions about a week; canonical
"preserved" items don't spoil. Spoiled food eaten gives debuffs
instead of buffs. Cooking skill at 70+ unlocks a Preservation
sub-skill that doubles shelf life.

Public surface
--------------
    Freshness enum (FRESH / AGING / STALE / SPOILED)
    SpoilProfile dataclass — per-item shelf life
    InventoryEntry dataclass — one item with a created_at
    SpoilageRegistry
        .register_profile(profile)
        .add_item(player_id, entry)
        .freshness_of(player_id, entry_id, now)
        .auto_remove_spoiled(player_id, now) -> tuple[entry_id]
        .preservation_bonus(skill) -> float
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


GAME_DAY_SECONDS = 60 * 60 * 24
PRESERVATION_SKILL_THRESHOLD = 70


class Freshness(str, enum.Enum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    SPOILED = "spoiled"


@dataclasses.dataclass(frozen=True)
class SpoilProfile:
    item_id: str
    shelf_life_seconds: float           # base shelf life
    is_preservable: bool = True
    is_immortal: bool = False           # never spoils
    eaten_when_spoiled_debuff: str = ""  # which debuff applies
    notes: str = ""

    @property
    def fresh_window_seconds(self) -> float:
        # First 50% of shelf life
        return self.shelf_life_seconds * 0.5

    @property
    def aging_window_seconds(self) -> float:
        # 50%..80%
        return self.shelf_life_seconds * 0.8

    @property
    def stale_window_seconds(self) -> float:
        # 80%..100%
        return self.shelf_life_seconds


@dataclasses.dataclass(frozen=True)
class InventoryEntry:
    entry_id: str
    item_id: str
    quantity: int = 1
    created_at_seconds: float = 0.0


def preservation_bonus(skill: int) -> float:
    """Cooking skill above the threshold doubles shelf life
    (additively up to 2x). Each skill point above threshold
    grants +1% shelf life, capped at +100%."""
    if skill < PRESERVATION_SKILL_THRESHOLD:
        return 1.0
    bonus_pts = min(100, skill - PRESERVATION_SKILL_THRESHOLD)
    return 1.0 + (bonus_pts / 100)


@dataclasses.dataclass
class SpoilageRegistry:
    _profiles: dict[str, SpoilProfile] = dataclasses.field(
        default_factory=dict,
    )
    # (player_id, entry_id) -> entry
    _inventory: dict[
        tuple[str, str], InventoryEntry,
    ] = dataclasses.field(default_factory=dict)
    # Cached per-entry preservation bonus (set at registration)
    _entry_bonus: dict[
        tuple[str, str], float,
    ] = dataclasses.field(default_factory=dict)

    def register_profile(
        self, profile: SpoilProfile,
    ) -> SpoilProfile:
        self._profiles[profile.item_id] = profile
        return profile

    def profile(self, item_id: str) -> t.Optional[SpoilProfile]:
        return self._profiles.get(item_id)

    def add_item(
        self, *, player_id: str, entry: InventoryEntry,
        cooking_skill: int = 0,
    ) -> bool:
        profile = self._profiles.get(entry.item_id)
        if profile is None:
            return False
        bonus = (
            preservation_bonus(cooking_skill)
            if profile.is_preservable else 1.0
        )
        self._inventory[(player_id, entry.entry_id)] = entry
        self._entry_bonus[
            (player_id, entry.entry_id)
        ] = bonus
        return True

    def freshness_of(
        self, *, player_id: str, entry_id: str,
        now_seconds: float,
    ) -> t.Optional[Freshness]:
        entry = self._inventory.get((player_id, entry_id))
        if entry is None:
            return None
        profile = self._profiles[entry.item_id]
        if profile.is_immortal:
            return Freshness.FRESH
        bonus = self._entry_bonus.get(
            (player_id, entry_id), 1.0,
        )
        age = now_seconds - entry.created_at_seconds
        fresh_w = profile.fresh_window_seconds * bonus
        aging_w = profile.aging_window_seconds * bonus
        stale_w = profile.stale_window_seconds * bonus
        if age <= fresh_w:
            return Freshness.FRESH
        if age <= aging_w:
            return Freshness.AGING
        if age <= stale_w:
            return Freshness.STALE
        return Freshness.SPOILED

    def is_spoiled(
        self, *, player_id: str, entry_id: str,
        now_seconds: float,
    ) -> bool:
        return self.freshness_of(
            player_id=player_id, entry_id=entry_id,
            now_seconds=now_seconds,
        ) == Freshness.SPOILED

    def auto_remove_spoiled(
        self, *, player_id: str, now_seconds: float,
    ) -> tuple[str, ...]:
        removed: list[str] = []
        for key in list(self._inventory.keys()):
            pid, eid = key
            if pid != player_id:
                continue
            if self.is_spoiled(
                player_id=pid, entry_id=eid,
                now_seconds=now_seconds,
            ):
                del self._inventory[key]
                self._entry_bonus.pop(key, None)
                removed.append(eid)
        return tuple(removed)

    def consume(
        self, *, player_id: str, entry_id: str,
        now_seconds: float,
    ) -> tuple[Freshness, t.Optional[str]]:
        """Returns (freshness, debuff_id_if_spoiled)."""
        f = self.freshness_of(
            player_id=player_id, entry_id=entry_id,
            now_seconds=now_seconds,
        )
        entry = self._inventory.get((player_id, entry_id))
        if f is None or entry is None:
            return Freshness.FRESH, None
        profile = self._profiles[entry.item_id]
        # Decrement quantity
        if entry.quantity <= 1:
            del self._inventory[(player_id, entry_id)]
            self._entry_bonus.pop(
                (player_id, entry_id), None,
            )
        else:
            self._inventory[
                (player_id, entry_id)
            ] = dataclasses.replace(
                entry, quantity=entry.quantity - 1,
            )
        if f == Freshness.SPOILED:
            return f, profile.eaten_when_spoiled_debuff or "stomach_ache"
        return f, None

    def total_in_inventory(self, player_id: str) -> int:
        return sum(
            1 for (pid, _eid) in self._inventory
            if pid == player_id
        )

    def total_profiles(self) -> int:
        return len(self._profiles)


# --------------------------------------------------------------------
# Default seed
# --------------------------------------------------------------------
def _default_profiles() -> tuple[SpoilProfile, ...]:
    return (
        SpoilProfile(
            item_id="fish_fresh",
            shelf_life_seconds=GAME_DAY_SECONDS,
            eaten_when_spoiled_debuff="food_poisoning",
        ),
        SpoilProfile(
            item_id="cooked_dish",
            shelf_life_seconds=GAME_DAY_SECONDS * 3,
            eaten_when_spoiled_debuff="food_poisoning",
        ),
        SpoilProfile(
            item_id="cure_potion",
            shelf_life_seconds=GAME_DAY_SECONDS * 7,
            eaten_when_spoiled_debuff="alchemy_failure",
        ),
        SpoilProfile(
            item_id="dried_jerky",
            shelf_life_seconds=GAME_DAY_SECONDS * 30,
            is_preservable=False,
        ),
        SpoilProfile(
            item_id="ether",
            shelf_life_seconds=GAME_DAY_SECONDS * 14,
            eaten_when_spoiled_debuff="alchemy_failure",
        ),
        SpoilProfile(
            item_id="canned_provisions",
            shelf_life_seconds=GAME_DAY_SECONDS * 90,
            is_preservable=False,
        ),
        SpoilProfile(
            item_id="signed_artisan_pie",
            shelf_life_seconds=GAME_DAY_SECONDS * 7,
            is_immortal=False,
        ),
        SpoilProfile(
            item_id="crystal_fire",
            shelf_life_seconds=0,
            is_immortal=True,
        ),
    )


def seed_default_profiles(
    registry: SpoilageRegistry,
) -> SpoilageRegistry:
    for p in _default_profiles():
        registry.register_profile(p)
    return registry


__all__ = [
    "GAME_DAY_SECONDS", "PRESERVATION_SKILL_THRESHOLD",
    "Freshness",
    "SpoilProfile", "InventoryEntry",
    "preservation_bonus",
    "SpoilageRegistry", "seed_default_profiles",
]
