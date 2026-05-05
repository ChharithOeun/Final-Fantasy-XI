"""Mermaid diplomacy council — Sirenhall court politics.

Inside SILMARIL_SIRENHALL the mermaid matriarchy is split
between three factions, and which one controls the council
determines whether the surface gets safe passage, paid
tribute, or full siren raids on its own lanes.

Council factions:
  TIDE_KEEPERS    - moderate; favor trade with surface
  DEEP_FAITHFUL   - cult; aligned with the Kraken / Drowned
                    Princes; want the surface drowned
  MERCHANT_PEARL  - capitalist; favor whoever pays best
                    (siren_tribute REP biases this faction)

Each faction has SEATS on the council. The faction with the
plurality of seats holds COURT and decides council POLICY:
  TRADE_OPEN      - sirens DO NOT cast against tributaries
  TRIBUTE_FOR_PEACE - sirens cast unless paid (current default)
  RAID_THE_SURFACE  - sirens cast freely; lanes go DANGEROUS

Players move seats by completing council quests, returning
abducted mermaids (TIDE_KEEPERS), feeding the cult
(DEEP_FAITHFUL — generally a bad idea), or funneling
tribute to MERCHANT_PEARL.

Public surface
--------------
    Faction enum
    Policy enum
    DiplomacyCouncil
        .seat(faction, count)
        .move_seats(from_faction, to_faction, count)
        .holding_court() -> Faction or None
        .current_policy() -> Policy
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Faction(str, enum.Enum):
    TIDE_KEEPERS = "tide_keepers"
    DEEP_FAITHFUL = "deep_faithful"
    MERCHANT_PEARL = "merchant_pearl"


class Policy(str, enum.Enum):
    TRADE_OPEN = "trade_open"
    TRIBUTE_FOR_PEACE = "tribute_for_peace"
    RAID_THE_SURFACE = "raid_the_surface"


_FACTION_POLICY: dict[Faction, Policy] = {
    Faction.TIDE_KEEPERS: Policy.TRADE_OPEN,
    Faction.MERCHANT_PEARL: Policy.TRIBUTE_FOR_PEACE,
    Faction.DEEP_FAITHFUL: Policy.RAID_THE_SURFACE,
}

DEFAULT_POLICY = Policy.TRIBUTE_FOR_PEACE


@dataclasses.dataclass(frozen=True)
class SeatChange:
    accepted: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass
class DiplomacyCouncil:
    _seats: dict[Faction, int] = dataclasses.field(
        default_factory=lambda: {f: 0 for f in Faction},
    )

    def seat(
        self, *, faction: Faction, count: int,
    ) -> SeatChange:
        if faction not in _FACTION_POLICY:
            return SeatChange(False, reason="unknown faction")
        if count < 0:
            return SeatChange(False, reason="negative count")
        self._seats[faction] = self._seats.get(faction, 0) + count
        return SeatChange(True)

    def remove_seats(
        self, *, faction: Faction, count: int,
    ) -> SeatChange:
        if faction not in _FACTION_POLICY:
            return SeatChange(False, reason="unknown faction")
        if count < 0:
            return SeatChange(False, reason="negative count")
        current = self._seats.get(faction, 0)
        if current < count:
            return SeatChange(
                False, reason="not enough seats to remove",
            )
        self._seats[faction] = current - count
        return SeatChange(True)

    def move_seats(
        self, *, from_faction: Faction,
        to_faction: Faction, count: int,
    ) -> SeatChange:
        if from_faction == to_faction:
            return SeatChange(False, reason="same faction")
        rm = self.remove_seats(faction=from_faction, count=count)
        if not rm.accepted:
            return rm
        return self.seat(faction=to_faction, count=count)

    def seats_for(self, *, faction: Faction) -> int:
        return self._seats.get(faction, 0)

    def holding_court(self) -> t.Optional[Faction]:
        if not self._seats:
            return None
        max_seats = max(self._seats.values(), default=0)
        if max_seats <= 0:
            return None
        # plurality: only one faction at the top
        leaders = [
            f for f, s in self._seats.items() if s == max_seats
        ]
        if len(leaders) > 1:
            return None
        return leaders[0]

    def current_policy(self) -> Policy:
        leader = self.holding_court()
        if leader is None:
            return DEFAULT_POLICY
        return _FACTION_POLICY[leader]


__all__ = [
    "Faction", "Policy", "SeatChange", "DiplomacyCouncil",
    "DEFAULT_POLICY",
]
