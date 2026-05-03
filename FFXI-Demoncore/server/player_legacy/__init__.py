"""Player legacy — heir system for permadeath continuity.

When a player permadeath-fades (player_state -> permadeath path),
the player's Legacy fires. Their pre-named HEIR receives a
fraction of:
  * gear (top N pieces, picked by tier and value)
  * gil  (a percentage of the deceased's wallet)
  * fame (multiplier per nation)
  * faction reputation (transferred at a configurable rate)

The heir is a NEW character on the same Discord-OAuth account.
Heir creation is gated on having designated an heir BEFORE death;
otherwise the legacy is forfeit. This rewards forward planning
without making permadeath painless.

Public surface
--------------
    InheritanceCategory enum
    HeirDesignation dataclass — predeath registration
    DeceasedEstate dataclass — what the dead player owned
    LegacyTransfer dataclass — what the heir received
    PlayerLegacyRegistry
        .designate_heir(player_id, heir_player_id, ...)
        .deceased(player_id, estate, now_seconds)
        .claim_legacy(heir_id, now_seconds)
        .has_designation(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default inheritance fractions.
DEFAULT_GIL_FRACTION = 0.5      # heir gets 50%
DEFAULT_FAME_FRACTION = 0.5
DEFAULT_REP_FRACTION = 0.4
DEFAULT_TOP_N_ITEMS = 3
LEGACY_CLAIM_WINDOW_SECONDS = 7 * 24 * 3600   # 7 days


class InheritanceCategory(str, enum.Enum):
    GIL = "gil"
    GEAR = "gear"
    FAME = "fame"
    FACTION_REP = "faction_rep"
    TITLES = "titles"


@dataclasses.dataclass(frozen=True)
class HeirDesignation:
    deceased_player_id: str
    heir_player_id: str
    designated_at_seconds: float
    note: str = ""


@dataclasses.dataclass(frozen=True)
class GearItem:
    item_id: str
    tier: int                  # higher = better
    value_gil: int = 0


@dataclasses.dataclass(frozen=True)
class DeceasedEstate:
    player_id: str
    gil: int = 0
    fame_by_nation: t.Mapping[str, int] = dataclasses.field(
        default_factory=dict,
    )
    faction_reputations: t.Mapping[str, int] = dataclasses.field(
        default_factory=dict,
    )
    gear: tuple[GearItem, ...] = ()
    titles: tuple[str, ...] = ()
    died_at_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class LegacyTransfer:
    deceased_player_id: str
    heir_player_id: str
    gil_transferred: int
    gear_transferred: tuple[GearItem, ...]
    fame_transferred_by_nation: dict[str, int]
    rep_transferred: dict[str, int]
    titles_transferred: tuple[str, ...]
    transferred_at_seconds: float


@dataclasses.dataclass
class PlayerLegacyRegistry:
    gil_fraction: float = DEFAULT_GIL_FRACTION
    fame_fraction: float = DEFAULT_FAME_FRACTION
    rep_fraction: float = DEFAULT_REP_FRACTION
    top_n_items: int = DEFAULT_TOP_N_ITEMS
    claim_window_seconds: float = LEGACY_CLAIM_WINDOW_SECONDS
    _designations: dict[str, HeirDesignation] = dataclasses.field(
        default_factory=dict,
    )
    _estates: dict[str, DeceasedEstate] = dataclasses.field(
        default_factory=dict,
    )
    _transfers: dict[str, LegacyTransfer] = dataclasses.field(
        default_factory=dict,
    )

    def designate_heir(
        self, *, player_id: str, heir_player_id: str,
        now_seconds: float = 0.0, note: str = "",
    ) -> bool:
        if player_id == heir_player_id:
            return False
        # Allow re-designation (overwrites)
        self._designations[player_id] = HeirDesignation(
            deceased_player_id=player_id,
            heir_player_id=heir_player_id,
            designated_at_seconds=now_seconds,
            note=note,
        )
        return True

    def has_designation(self, player_id: str) -> bool:
        return player_id in self._designations

    def heir_for(
        self, player_id: str,
    ) -> t.Optional[str]:
        d = self._designations.get(player_id)
        return d.heir_player_id if d else None

    def deceased(
        self, *, estate: DeceasedEstate,
    ) -> bool:
        if estate.player_id in self._estates:
            return False
        self._estates[estate.player_id] = estate
        return True

    def claim_legacy(
        self, *, heir_player_id: str,
        deceased_player_id: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[LegacyTransfer]:
        designation = self._designations.get(
            deceased_player_id,
        )
        if designation is None:
            return None
        if designation.heir_player_id != heir_player_id:
            return None
        estate = self._estates.get(deceased_player_id)
        if estate is None:
            return None
        # Already claimed?
        if deceased_player_id in self._transfers:
            return None
        # Check claim window
        elapsed = now_seconds - estate.died_at_seconds
        if elapsed > self.claim_window_seconds:
            return None
        # Compute transfer
        gil_transferred = int(estate.gil * self.gil_fraction)
        # Gear: top N by tier desc, ties broken by value desc
        sorted_gear = sorted(
            estate.gear,
            key=lambda g: (-g.tier, -g.value_gil, g.item_id),
        )
        gear_transferred = tuple(
            sorted_gear[: self.top_n_items],
        )
        fame_transferred = {
            nation: int(amt * self.fame_fraction)
            for nation, amt in estate.fame_by_nation.items()
        }
        rep_transferred = {
            faction: int(amt * self.rep_fraction)
            for faction, amt in estate.faction_reputations.items()
        }
        # All titles transfer
        titles_transferred = estate.titles

        transfer = LegacyTransfer(
            deceased_player_id=deceased_player_id,
            heir_player_id=heir_player_id,
            gil_transferred=gil_transferred,
            gear_transferred=gear_transferred,
            fame_transferred_by_nation=fame_transferred,
            rep_transferred=rep_transferred,
            titles_transferred=titles_transferred,
            transferred_at_seconds=now_seconds,
        )
        self._transfers[deceased_player_id] = transfer
        return transfer

    def transfer_for(
        self, deceased_player_id: str,
    ) -> t.Optional[LegacyTransfer]:
        return self._transfers.get(deceased_player_id)

    def total_designations(self) -> int:
        return len(self._designations)

    def total_estates(self) -> int:
        return len(self._estates)

    def total_transfers(self) -> int:
        return len(self._transfers)


__all__ = [
    "DEFAULT_GIL_FRACTION", "DEFAULT_FAME_FRACTION",
    "DEFAULT_REP_FRACTION", "DEFAULT_TOP_N_ITEMS",
    "LEGACY_CLAIM_WINDOW_SECONDS",
    "InheritanceCategory",
    "HeirDesignation", "GearItem", "DeceasedEstate",
    "LegacyTransfer",
    "PlayerLegacyRegistry",
]
