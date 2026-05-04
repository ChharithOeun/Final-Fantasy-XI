"""Beastman legacy heir — heir on permadeath continuity.

Beastman-side counterpart to player_legacy. When a beastman
character permadies, the player can transmit a portion of their
estate to a designated HEIR — a fresh beastman character of the
same race the player rolls afterward.

Each heir slot inherits at MOST a budget of:
  - GIL (capped at 50% of remaining estate, max 1_000_000)
  - SHADOW_BYTNES (capped at 25% of remaining)
  - One titled HEIRLOOM ITEM (e.g., relic dagger / mythic horn)
  - LAIR rights (the new char inherits the previous lair tier
    minus 1, never below BURROW)

The system enforces the SAME RACE rule (you can't pass an
Orc relic to a Yagudo heir; some heirlooms are race-locked).

Public surface
--------------
    HeirRace enum  (mirrors BeastmanRace)
    Heirloom dataclass
    BeastmanLegacyHeir
        .declare_heir(deceased_id, heir_id, race)
        .set_estate(deceased_id, gil, bytnes, lair_tier_index)
        .add_heirloom(deceased_id, item_id, race_locked)
        .execute_inheritance(deceased_id)  -> InheritResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


_GIL_INHERIT_PCT = 50
_BYTNE_INHERIT_PCT = 25
_GIL_HARD_CAP = 1_000_000
_BYTNE_HARD_CAP = 100_000


@dataclasses.dataclass(frozen=True)
class Heirloom:
    item_id: str
    race_locked: t.Optional[BeastmanRace] = None


@dataclasses.dataclass
class _Estate:
    deceased_id: str
    heir_id: t.Optional[str] = None
    heir_race: t.Optional[BeastmanRace] = None
    gil: int = 0
    bytnes: int = 0
    lair_tier_index: int = 0
    heirloom: t.Optional[Heirloom] = None
    inheritance_executed: bool = False


@dataclasses.dataclass(frozen=True)
class InheritResult:
    accepted: bool
    deceased_id: str
    heir_id: str = ""
    gil_passed: int = 0
    bytnes_passed: int = 0
    heirloom_id: str = ""
    new_lair_tier_index: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanLegacyHeir:
    _estates: dict[str, _Estate] = dataclasses.field(
        default_factory=dict,
    )

    def declare_heir(
        self, *, deceased_id: str,
        heir_id: str,
        race: BeastmanRace,
    ) -> bool:
        if not deceased_id or not heir_id:
            return False
        e = self._estates.get(deceased_id)
        if e is None:
            e = _Estate(deceased_id=deceased_id)
            self._estates[deceased_id] = e
        if e.inheritance_executed:
            return False
        if e.heir_id is not None:
            return False
        e.heir_id = heir_id
        e.heir_race = race
        return True

    def set_estate(
        self, *, deceased_id: str,
        gil: int, bytnes: int,
        lair_tier_index: int,
    ) -> bool:
        if gil < 0 or bytnes < 0:
            return False
        if lair_tier_index < 0:
            return False
        e = self._estates.get(deceased_id)
        if e is None:
            e = _Estate(deceased_id=deceased_id)
            self._estates[deceased_id] = e
        if e.inheritance_executed:
            return False
        e.gil = gil
        e.bytnes = bytnes
        e.lair_tier_index = lair_tier_index
        return True

    def add_heirloom(
        self, *, deceased_id: str,
        item_id: str,
        race_locked: t.Optional[BeastmanRace] = None,
    ) -> bool:
        e = self._estates.get(deceased_id)
        if e is None:
            return False
        if e.inheritance_executed:
            return False
        if e.heirloom is not None:
            return False
        if not item_id:
            return False
        e.heirloom = Heirloom(item_id=item_id, race_locked=race_locked)
        return True

    def execute_inheritance(
        self, *, deceased_id: str,
    ) -> InheritResult:
        e = self._estates.get(deceased_id)
        if e is None:
            return InheritResult(
                False, deceased_id, reason="no estate",
            )
        if e.inheritance_executed:
            return InheritResult(
                False, deceased_id, reason="already executed",
            )
        if e.heir_id is None or e.heir_race is None:
            return InheritResult(
                False, deceased_id, reason="no heir declared",
            )
        gil_share = min(
            (e.gil * _GIL_INHERIT_PCT) // 100,
            _GIL_HARD_CAP,
        )
        bytne_share = min(
            (e.bytnes * _BYTNE_INHERIT_PCT) // 100,
            _BYTNE_HARD_CAP,
        )
        # Lair: drop one tier, never below 0
        new_lair = max(0, e.lair_tier_index - 1)
        # Heirloom: only pass if race lock allows
        heirloom_id = ""
        if e.heirloom is not None:
            if (
                e.heirloom.race_locked is None
                or e.heirloom.race_locked == e.heir_race
            ):
                heirloom_id = e.heirloom.item_id
        e.inheritance_executed = True
        return InheritResult(
            accepted=True,
            deceased_id=deceased_id,
            heir_id=e.heir_id,
            gil_passed=gil_share,
            bytnes_passed=bytne_share,
            heirloom_id=heirloom_id,
            new_lair_tier_index=new_lair,
        )

    def total_estates(self) -> int:
        return len(self._estates)


__all__ = [
    "Heirloom", "InheritResult",
    "BeastmanLegacyHeir",
]
